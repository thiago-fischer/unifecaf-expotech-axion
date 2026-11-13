FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_LINK_MODE=copy \
    PATH="/app/controller/.venv/bin:$PATH"

WORKDIR /app/controller
COPY controller/pyproject.toml controller/uv.lock ./
RUN uv sync --locked --no-dev
COPY controller/axion_controller ./axion_controller

USER 10001
EXPOSE 8001
CMD ["uvicorn", "axion_controller.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001"]
