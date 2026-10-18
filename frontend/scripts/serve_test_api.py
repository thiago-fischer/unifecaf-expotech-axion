"""API real com migrations em banco descartável para os testes de navegador."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn


def main() -> None:
    backend = Path(__file__).resolve().parents[2] / "backend"
    with TemporaryDirectory(prefix="axion-frontend-e2e-") as directory:
        os.environ["AXION_DATABASE_PATH"] = str(Path(directory) / "test.db")
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend, check=True
        )
        uvicorn.run("app.main:app", host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
