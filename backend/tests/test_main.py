import subprocess
import sys

from sqlalchemy import URL, inspect

from app.config import BACKEND_DIR, Settings
from app.database.database import build_engine


def test_import_does_not_start_server_or_create_schema(database_url: URL) -> None:
    # A fresh process catches import side effects hidden by pytest's module cache.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from unittest.mock import patch; "
            "import uvicorn; "
            "guard = patch.object(uvicorn, 'run', "
            "side_effect=AssertionError('Server started during import')); "
            "guard.start(); "
            "from app.main import app, create_app; "
            "assert callable(create_app); "
            "assert {'/machines', '/products', '/orders', '/orders/{order_id}'} "
            "<= set(app.openapi()['paths'])",
        ],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    engine = build_engine(Settings())
    try:
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()
