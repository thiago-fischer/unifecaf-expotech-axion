import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import URL, make_url
from sqlalchemy.exc import ArgumentError

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE_URL_ENV = "AXION_DATABASE_URL"


def _integer_setting(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} deve ser um número inteiro.") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} deve estar entre {minimum} e {maximum}.")
    return value


def _boolean_setting(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, str(default)).strip().lower()
    if raw not in {"true", "false", "1", "0"}:
        raise RuntimeError(f"{name} deve ser true ou false.")
    return raw in {"true", "1"}


def _validate_http_url(name: str, value: str, *, local_only: bool = False) -> None:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError(f"{name} deve ser uma URL HTTP válida.")
    if parsed.username or parsed.password:
        raise RuntimeError(f"{name} não pode conter credenciais.")
    if local_only and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError(f"{name} deve apontar para o host local.")


def load_database_url() -> URL:
    raw_url = os.environ.get(DATABASE_URL_ENV)
    if not raw_url:
        raise RuntimeError(f"Defina {DATABASE_URL_ENV} com a URL do PostgreSQL.")
    try:
        url = make_url(raw_url)
    except ArgumentError as exc:
        raise RuntimeError(f"{DATABASE_URL_ENV} contém uma URL inválida.") from exc
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError(f"{DATABASE_URL_ENV} deve usar o driver postgresql+psycopg.")
    if not url.host or not url.database:
        raise RuntimeError(f"{DATABASE_URL_ENV} deve informar host e nome do banco PostgreSQL.")
    return url


@dataclass(frozen=True)
class Settings:
    database_url: URL = field(default_factory=load_database_url)
    controller_url: str = field(
        default_factory=lambda: os.environ.get("AXION_CONTROLLER_URL", "http://127.0.0.1:8001")
    )
    controller_events_token: str = field(
        default_factory=lambda: os.environ.get("AXION_CONTROLLER_EVENTS_TOKEN", "")
    )
    capture_token: str = field(default_factory=lambda: os.environ.get("AXION_CAPTURE_TOKEN", ""))
    network_capture_enabled: bool = field(
        default_factory=lambda: _boolean_setting("AXION_NETWORK_CAPTURE_ENABLED")
    )
    network_event_buffer_size: int = field(
        default_factory=lambda: _integer_setting("AXION_NETWORK_EVENT_BUFFER_SIZE", 200, 10, 2000)
    )
    network_bucket_seconds: int = field(
        default_factory=lambda: _integer_setting("AXION_NETWORK_BUCKET_SECONDS", 10, 1, 300)
    )
    network_metrics_retention_hours: int = field(
        default_factory=lambda: _integer_setting(
            "AXION_NETWORK_METRICS_RETENTION_HOURS", 168, 1, 24 * 90
        )
    )
    network_batch_retention_hours: int = field(
        default_factory=lambda: _integer_setting("AXION_NETWORK_BATCH_RETENTION_HOURS", 24, 1, 168)
    )
    grafana_url: str = field(
        default_factory=lambda: os.environ.get("AXION_GRAFANA_URL", "http://127.0.0.1:3000")
    )
    grafana_public_url: str = field(
        default_factory=lambda: os.environ.get("AXION_GRAFANA_PUBLIC_URL", "http://127.0.0.1:3000")
    )
    grafana_network_dashboard_uid: str = field(
        default_factory=lambda: os.environ.get(
            "AXION_GRAFANA_NETWORK_DASHBOARD_UID", "axion-rede-comunicacao"
        )
    )

    def __post_init__(self) -> None:
        if self.network_capture_enabled and not self.capture_token:
            raise RuntimeError(
                "Defina AXION_CAPTURE_TOKEN quando AXION_NETWORK_CAPTURE_ENABLED=true."
            )
        _validate_http_url("AXION_GRAFANA_URL", self.grafana_url)
        _validate_http_url("AXION_GRAFANA_PUBLIC_URL", self.grafana_public_url, local_only=True)
