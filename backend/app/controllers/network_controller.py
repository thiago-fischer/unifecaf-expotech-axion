from secrets import compare_digest
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.database import get_session
from app.schemas.network_schema import (
    CaptureBatch,
    CaptureHeartbeat,
    NetworkConnection,
    NetworkEventsResponse,
    NetworkOverview,
    NetworkSecurity,
    ServiceHealth,
)
from app.services.controller_client import ControllerError
from app.services.execution_service import ExecutionManager
from app.services.network_service import NetworkEventBuffer, NetworkIngestionService

router = APIRouter(prefix="/network", tags=["network"])


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_buffer(request: Request) -> NetworkEventBuffer:
    return request.app.state.network_event_buffer


def authorize_capture(token: str, settings: Settings) -> None:
    if not settings.capture_token or not compare_digest(
        token.encode(), settings.capture_token.encode()
    ):
        raise HTTPException(403, detail="Captura não autorizada.")


def verify_capture_access(
    settings: Annotated[Settings, Depends(get_settings)],
    buffer: Annotated[NetworkEventBuffer, Depends(get_buffer)],
    token: Annotated[str, Header(alias="X-Axion-Capture-Token")] = "",
) -> Settings:
    try:
        authorize_capture(token, settings)
    except HTTPException:
        buffer.blocked_batch()
        raise
    return settings


def get_manager(request: Request) -> ExecutionManager:
    return request.app.state.execution_manager


@router.post("/capture/events", status_code=status.HTTP_204_NO_CONTENT)
def receive_capture_events(
    settings: Annotated[Settings, Depends(verify_capture_access)],
    batch: CaptureBatch,
    session: Annotated[Session, Depends(get_session)],
    buffer: Annotated[NetworkEventBuffer, Depends(get_buffer)],
) -> None:
    try:
        NetworkIngestionService(session, buffer, settings).ingest(batch)
        buffer.accepted_batch()
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail="Persistência de métricas indisponível.") from exc


@router.post("/capture/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def receive_capture_heartbeat(
    settings: Annotated[Settings, Depends(verify_capture_access)],
    heartbeat: CaptureHeartbeat,
    buffer: Annotated[NetworkEventBuffer, Depends(get_buffer)],
) -> None:
    buffer.heartbeat(heartbeat.capture_session_id)


@router.get("/events", response_model=NetworkEventsResponse)
def recent_events(
    buffer: Annotated[NetworkEventBuffer, Depends(get_buffer)],
    after: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    capture_session_id: UUID | None = None,
) -> NetworkEventsResponse:
    return buffer.events(after, limit, capture_session_id)


@router.get("/overview", response_model=NetworkOverview)
def network_overview(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    buffer: Annotated[NetworkEventBuffer, Depends(get_buffer)],
    manager: Annotated[ExecutionManager, Depends(get_manager)],
) -> NetworkOverview:
    services: dict[str, ServiceHealth] = {"backend": ServiceHealth(state="online")}
    try:
        session.execute(text("SELECT 1"))
        services["database"] = ServiceHealth(state="online")
    except SQLAlchemyError:
        services["database"] = ServiceHealth(state="offline", detail="Consulta de saúde falhou.")
        session.rollback()

    try:
        manager.controller_status(max_age=2)
        services["controller"] = ServiceHealth(state="online")
    except ControllerError:
        services["controller"] = ServiceHealth(
            state="offline", detail="Controlador não respondeu à consulta de saúde."
        )

    capture_session, last_event, age, observed = buffer.snapshot()
    if not settings.network_capture_enabled:
        services["capture"] = ServiceHealth(state="disabled")
    elif age is None:
        services["capture"] = ServiceHealth(state="unknown", detail="Nenhum lote recebido.")
    elif age <= 5_000:
        services["capture"] = ServiceHealth(state="online")
    elif age <= 15_000:
        services["capture"] = ServiceHealth(state="degraded", detail="Captura sem lote recente.")
    else:
        services["capture"] = ServiceHealth(state="offline", detail="Captura interrompida.")

    try:
        with urlopen(settings.grafana_url.rstrip("/") + "/api/health", timeout=1) as response:
            grafana_online = response.status == 200
    except (HTTPError, URLError, OSError):
        grafana_online = False
    services["grafana"] = ServiceHealth(
        state="online" if grafana_online else "offline",
        detail=None if grafana_online else "Grafana não respondeu à consulta de saúde.",
    )

    configured = [
        ("frontend", "backend"),
        ("backend", "controller"),
        ("backend", "database"),
        ("grafana", "database"),
    ]
    connections = [
        NetworkConnection(
            source=source,
            destination=destination,
            visibility=(
                "observed"
                if (source, destination) in observed or (destination, source) in observed
                else "configured"
            ),
        )
        for source, destination in configured
    ]
    accepted_batches, blocked_batches = buffer.counters()
    return NetworkOverview(
        capture_session_id=capture_session,
        last_event_at=last_event,
        last_batch_age_ms=age,
        services=services,
        connections=connections,
        security=NetworkSecurity(
            controller_token_configured=bool(settings.controller_events_token),
            capture_token_configured=bool(settings.capture_token),
            accepted_batches=accepted_batches,
            blocked_batches=blocked_batches,
        ),
        grafana_public_url=settings.grafana_public_url,
        grafana_dashboard_uid=settings.grafana_network_dashboard_uid,
    )
