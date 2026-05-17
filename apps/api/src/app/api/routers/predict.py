"""Single-row prediction endpoint."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import get_prediction_service
from app.api.dtos import HousePredictionRequest, PredictionResponseModel
from app.infra.logging import get_logger
from app.services import PredictionService

router = APIRouter(prefix="/v1", tags=["predict"])
_log = get_logger(__name__)
PredictionServiceDep = Annotated[PredictionService, Depends(get_prediction_service)]


@router.post(
    "/predict",
    response_model=PredictionResponseModel,
    summary="Predict a house's sale price with SHAP explanation",
    response_model_exclude_none=True,
)
def predict(
    payload: HousePredictionRequest,  # type: ignore[valid-type]
    service: PredictionServiceDep,
) -> PredictionResponseModel:
    """Validate the input, run the model, return the structured result.

    The router stays deliberately thin: it deserialises into the
    Pydantic model (which catches range / type errors with a 422),
    calls the service, and re-serialises into the response model.
    All ML knowledge stays inside :mod:`app.services`.
    """
    # ``model_dump`` with ``by_alias=True`` rebuilds the dataset's
    # canonical column names ("1stFlrSF" instead of "f_1stFlrSF").
    partial = cast(BaseModel, payload).model_dump(by_alias=True, exclude_none=True)

    try:
        prediction = service.predict(partial)
    except ValueError as exc:
        _log.warning("prediction_validation_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return PredictionResponseModel(
        prediction={
            "value_usd": round(prediction.value_usd, 2),
            "currency": "USD",
        },
        explanation={
            "baseline_usd": round(prediction.baseline_usd, 2),
            "natural_language": prediction.natural_language,
            "top_features": [asdict(c) for c in prediction.top_features],
        },
        model={
            "name": prediction.model_name,
            "version": prediction.model_version,
            "trained_at_utc": prediction.trained_at_utc,
        },
    )
