"""Model metadata endpoint — what's serving right now."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import LoadedModelDep
from app.api.dtos import ModelInfoResponse

router = APIRouter(prefix="/v1/model", tags=["meta"])


@router.get("/info", response_model=ModelInfoResponse, summary="Loaded artifact info")
def model_info(model: LoadedModelDep) -> ModelInfoResponse:
    md = model.metadata
    return ModelInfoResponse(
        model_name=md.model_name,
        model_version=md.hou53_ml_version,
        trained_at_utc=md.trained_at_utc,
        dataset_sha256=md.dataset_sha256,
        library_versions=md.library_versions,
        feature_count_after_preprocess=len(md.feature_names_after_preprocess),
        metrics=md.metrics,
        schema_fingerprint=md.schema_fingerprint,
    )
