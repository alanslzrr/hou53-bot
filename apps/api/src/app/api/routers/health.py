"""Liveness + readiness probes.

Liveness checks "is the process up?" — never depends on the model
being loaded. Readiness checks "can the process serve traffic?" — that
DOES require a loaded model.

Kubernetes-style probes; carried over to docker-compose's healthchecks
in Phase 7.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.dtos import HealthResponse, ReadyResponse

router = APIRouter(tags=["meta"])


@router.get("/healthz", response_model=HealthResponse, summary="Liveness probe")
def liveness() -> HealthResponse:
    return HealthResponse()


@router.get("/readyz", response_model=ReadyResponse, summary="Readiness probe")
def readiness(request: Request) -> ReadyResponse:
    loaded = getattr(request.app.state, "loaded_model", None) is not None
    return ReadyResponse(
        status="ready" if loaded else "not-ready",
        model_loaded=loaded,
    )
