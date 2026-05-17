"""FastAPI dependency providers.

Two layers of indirection on purpose:

1. ``get_loaded_model`` reads the model from ``app.state``. The state
   is populated by the lifespan in :mod:`app.main`. This is the seam
   tests use to swap in a stub model — they ``app.dependency_overrides``
   this provider, not the lifespan.

2. ``get_prediction_service`` builds a fresh service per request,
   wired to the loaded model. Stateless service objects are cheap and
   keep the wiring explicit.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.infra.model_loader import LoadedModel
from app.services import PredictionService


def get_app_settings() -> Settings:
    return get_settings()


def get_loaded_model(request: Request) -> LoadedModel:
    """Return the model loaded by the lifespan, or 503 if not loaded."""
    model = getattr(request.app.state, "loaded_model", None)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model artifact not loaded.",
        )
    return cast(LoadedModel, model)


LoadedModelDep = Annotated[LoadedModel, Depends(get_loaded_model)]


def get_prediction_service(
    model: LoadedModelDep,
) -> PredictionService:
    return PredictionService(model)
