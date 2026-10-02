from collections.abc import Iterator
from sqlite3 import Connection

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from app.config import Settings


def build_engine(settings: Settings) -> Engine:
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection: Connection, connection_record: object) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    return engine


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session
