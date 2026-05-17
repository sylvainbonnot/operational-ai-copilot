from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api import routes_ask, routes_eval, routes_feedback, routes_health
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import PrometheusMiddleware
from app.storage.database import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    logger.info("startup", environment=settings.environment, model=settings.llm_model)
    await init_db()
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Operational AI Copilot",
        description="Production-grade RAG + agentic AI for industrial operations",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router, tags=["health"])
    app.include_router(routes_ask.router, prefix="/ask", tags=["copilot"])
    app.include_router(routes_eval.router, prefix="/eval", tags=["evaluation"])
    app.include_router(routes_feedback.router, prefix="/feedback", tags=["feedback"])

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
