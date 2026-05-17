"""FastAPI app factory + lifespan.

Everything that needs to live for the duration of the process
(structlog config, the loaded model artifact, the SHAP explainer)
is wired here. Per-request state (request ID, authenticated user when
that arrives) is wired in middleware below.

The :func:`create_app` factory exists so tests can build a fresh app
with a stubbed lifespan and no real model on disk.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.api.routers import health, model_info, predict
from app.config import Settings, get_settings
from app.infra.logging import configure_logging, get_logger
from app.infra.model_loader import load_model

_log = get_logger(__name__)


# -----------------------------------------------------------------------------
# Lifespan: load the model once at startup; release on shutdown.
# -----------------------------------------------------------------------------
@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    configure_logging(level=settings.log_level, as_json=settings.log_format == "json")
    _log.info("startup_begin", environment=settings.log_format)

    csv_path = settings.repo_root / "data" / "raw" / "house_prices.csv"
    try:
        model = load_model(
            models_dir=settings.models_dir,
            background_size=settings.shap_background_size,
            background_seed=settings.shap_background_seed,
            shap_top_k=settings.shap_top_k,
            csv_for_background=csv_path,
        )
        app.state.loaded_model = model
        _log.info("startup_complete", model_name=model.metadata.model_name)
    except Exception as exc:
        app.state.loaded_model = None
        _log.error("model_load_failed", error=str(exc), error_type=type(exc).__name__)

    try:
        yield
    finally:
        _log.info("shutdown")
        app.state.loaded_model = None


# -----------------------------------------------------------------------------
# Middleware: inject a request ID into structlog contextvars so every
# log line in a request handler carries it.
# -----------------------------------------------------------------------------
class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request ID (header or generated) to logs and the response."""

    HEADER = "x-request-id"

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers[self.HEADER] = request_id
        return response


# -----------------------------------------------------------------------------
# App factory.
# -----------------------------------------------------------------------------
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="HOU53-bot API",
        description=(
            "House-price prediction with SHAP explanations. "
            "Trained on Ames Housing — see /v1/model/info for the "
            "exact artifact details."
        ),
        version="0.1.0",
        lifespan=_lifespan,
        # Generate stable operation IDs from function names so the
        # frontend client generator (openapi-typescript) produces
        # readable type names.
        generate_unique_id_function=lambda route: route.name,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=[RequestIdMiddleware.HEADER],
    )

    app.include_router(health.router)
    app.include_router(model_info.router)
    app.include_router(predict.router)

    return app


#: ASGI entry point for ``uvicorn app.main:app``.
app = create_app()
