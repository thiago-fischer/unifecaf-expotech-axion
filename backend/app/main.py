import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.controllers.machine_controller import router
from app.database.database import build_engine

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    engine = build_engine(settings or Settings())

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Axion API", version="0.1.0", lifespan=lifespan)
    application.state.session_factory = sessionmaker(engine, expire_on_commit=False)
    application.include_router(router)

    @application.exception_handler(SQLAlchemyError)
    async def persistence_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error(
            "Falha de persistência em %s %s", request.method, request.url.path, exc_info=exc
        )
        return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})

    return application


app = create_app()
