import os
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import URL, make_url
from sqlalchemy.exc import ArgumentError

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE_URL_ENV = "AXION_DATABASE_URL"


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
