import os
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import URL

BACKEND_DIR = Path(__file__).resolve().parents[1]


def database_path() -> Path:
    path = Path(os.environ.get("AXION_DATABASE_PATH", "data/axion.db")).expanduser()
    return (BACKEND_DIR / path).resolve()


@dataclass(frozen=True)
class Settings:
    database_path: Path = field(default_factory=database_path)

    @property
    def database_url(self) -> URL:
        return URL.create("sqlite+pysqlite", database=str(self.database_path))
