from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.telemetry import rag_latency_seconds, rag_requests_total

# Endpoints we want to instrument
_TRACKED = {"/ask", "/ask/incident/summarize", "/ask/incident/diagnose"}


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        method = request.method

        t0 = time.perf_counter()
        response = await call_next(request)
        latency = time.perf_counter() - t0

        if path in _TRACKED and method == "POST":
            status = "ok" if response.status_code < 400 else "error"
            rag_requests_total.labels(endpoint=path, status=status).inc()
            rag_latency_seconds.labels(endpoint=path).observe(latency)

        return response
