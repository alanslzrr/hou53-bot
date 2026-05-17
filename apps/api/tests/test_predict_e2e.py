"""End-to-end predict against the real artifact.

Skipped when the artifact is missing locally. One test, on purpose —
the goal is to catch wiring problems (lifespan boots, model loads,
SHAP runs, dollar prediction is sane). All behavioural assertions live
in the stub-backed test files.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient


def _artifact_or_skip() -> None:
    settings = get_settings()
    pipeline_path = settings.models_dir / settings.pipeline_filename
    metadata_path = settings.models_dir / settings.metadata_filename
    if not pipeline_path.exists() or not metadata_path.exists():
        pytest.skip(f"artifact not found at {settings.models_dir}")


@pytest.fixture
def real_client() -> Iterator[TestClient]:
    _artifact_or_skip()
    # The lifespan runs inside TestClient's context manager.
    with TestClient(create_app()) as client:
        yield client


@pytest.mark.integration
@pytest.mark.slow
def test_real_predict_returns_sane_dollar_amount(real_client: TestClient) -> None:
    response = real_client.post(
        "/v1/predict",
        json={
            "OverallQual": 7,
            "GrLivArea": 1800,
            "GarageCars": 2,
            "YearBuilt": 2000,
            "TotalBsmtSF": 800,
            "1stFlrSF": 900,
            "2ndFlrSF": 900,
            "YrSold": 2010,
            "YearRemodAdd": 2005,
            "GarageYrBlt": 2000,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    price = body["prediction"]["value_usd"]
    # Bounded sanity — Ames Housing prices live between ~$30k and ~$800k.
    assert 30_000 < price < 1_000_000, price
    # SHAP attribution surfaced.
    assert body["explanation"]["top_features"]
    top = body["explanation"]["top_features"][0]
    assert "feature" in top
    assert "direction" in top


@pytest.mark.integration
@pytest.mark.slow
def test_real_model_info_carries_xgboost_or_ridge(real_client: TestClient) -> None:
    response = real_client.get("/v1/model/info")
    assert response.status_code == 200
    body = response.json()
    assert body["model_name"] in {"xgboost", "ridge"}
    assert body["dataset_sha256"]
