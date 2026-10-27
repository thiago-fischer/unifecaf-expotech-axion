from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.schemas.progress_schema import (
    ProgressEventCreate,
    ProgressEventRead,
    ProgressEventReceipt,
)
from app.services.progress_service import (
    ProgressEventConflictError,
    ProgressOrderNotFoundError,
    ProgressProductNotInOrderError,
    ProgressService,
)

router = APIRouter(prefix="/orders", tags=["production-progress"])


def get_progress_service(session: Annotated[Session, Depends(get_session)]) -> ProgressService:
    return ProgressService(session)


Service = Annotated[ProgressService, Depends(get_progress_service)]


@router.post(
    "/{order_id}/progress",
    response_model=ProgressEventReceipt,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Evento repetido e reconhecido idempotentemente"},
        404: {"description": "Ordem de produção não encontrada"},
        409: {"description": "Identificador de evento reutilizado com outro conteúdo"},
        422: {"description": "Produto não pertence à ordem ou entrada inválida"},
    },
)
def record_progress(
    order_id: Annotated[int, Path(gt=0)],
    data: ProgressEventCreate,
    service: Service,
    response: Response,
) -> ProgressEventReceipt:
    try:
        event, duplicate = service.record(order_id, data)
    except ProgressOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordem de produção não encontrada.",
        ) from exc
    except ProgressProductNotInOrderError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O produto informado não pertence à ordem.",
        ) from exc
    except ProgressEventConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O identificador do evento já foi utilizado com outro conteúdo.",
        ) from exc

    response.status_code = status.HTTP_200_OK if duplicate else status.HTTP_201_CREATED
    return ProgressEventReceipt(
        event=ProgressEventRead.model_validate(event),
        duplicate=duplicate,
    )
