FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.4.30 /uv /usr/local/bin/uv

# Install dependencies (no dev/eval/data groups)
COPY pyproject.toml .
RUN uv sync --no-dev

# Copy source
COPY app/ ./app/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
