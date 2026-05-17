"""Test fixtures shared by API tests.

Two flavours:

- :func:`stub_app` — tiny in-memory app with a fake :class:`LoadedModel`
  swapped in via ``app.dependency_overrides``. Fast, no disk I/O, no
  SHAP. Use this for the bulk of router / DTO behaviour tests.

- :func:`real_model_app` — boots the real artifact through the
  lifespan. Use sparingly (one or two end-to-end tests). Skipped if the
  artifact is not present locally.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import pytest
from app.api.dependencies import get_loaded_model
from app.config import Settings, get_settings
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hou53_ml.io import Schema
from hou53_ml.serialization.artifact import ArtifactMetadata


# -----------------------------------------------------------------------------
# Fake LoadedModel for fast tests.
# -----------------------------------------------------------------------------
@dataclass(slots=True)
class _FakeExplanation:
    prediction_usd: float
    baseline_usd: float
    top_features: list[Any] = field(default_factory=list)
    natural_language: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_usd": self.prediction_usd,
            "baseline_usd": self.baseline_usd,
            "top_features": self.top_features,
            "natural_language": self.natural_language,
        }


@dataclass(slots=True)
class _FakeContribution:
    feature: str
    shap_value: float
    contribution_usd: float
    direction: str


@dataclass(slots=True)
class _FakePipeline:
    fixed_value: float = 200_000.0

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self.fixed_value, dtype=float)


@dataclass(slots=True)
class _FakeLoadedModel:
    """Stub conforming to the public surface of ``LoadedModel``."""

    metadata: ArtifactMetadata
    schema: Schema
    pipeline: Any = field(default_factory=_FakePipeline)
    explainer: Any = None  # not used by the stub; SHAP isn't called

    def predict_dollars(self, row: pd.DataFrame) -> float:
        return float(self.pipeline.predict(row)[0])

    def explain(self, row: pd.DataFrame, *, top_k: int | None = None) -> _FakeExplanation:
        contribs = [
            _FakeContribution(
                feature="OverallQual",
                shap_value=0.05,
                contribution_usd=10_000.0,
                direction="up",
            ),
            _FakeContribution(
                feature="GrLivArea",
                shap_value=0.04,
                contribution_usd=8_000.0,
                direction="up",
            ),
        ][: (top_k or 2)]
        return _FakeExplanation(
            prediction_usd=200_000.0,
            baseline_usd=180_000.0,
            top_features=contribs,
            natural_language="Estimated price: $200,000. Stub explanation.",
        )

    def complete_row(self, partial: dict[str, Any]) -> pd.DataFrame:
        # Minimal — the fake pipeline doesn't read the columns.
        return pd.DataFrame([partial or {"_": 0}])


def _fake_metadata() -> ArtifactMetadata:
    return ArtifactMetadata(
        model_name="stub",
        hou53_ml_version="0.0.0-test",
        trained_at_utc="2026-01-01T00:00:00+00:00",
        python_version="3.14.0",
        library_versions={"sklearn": "test"},
        dataset_path="/dev/null",
        dataset_sha256="0" * 64,
        schema_fingerprint=["Id", "SalePrice"],
        feature_names_after_preprocess=["OverallQual", "GrLivArea"],
        metrics={
            "test_rmse_log": 0.15,
            "test_mae_dollars": 15_000.0,
            "test_r2_dollars": 0.85,
        },
        random_seed=42,
        extras={},
    )


@pytest.fixture
def fake_loaded_model() -> _FakeLoadedModel:
    return _FakeLoadedModel(metadata=_fake_metadata(), schema=Schema.default())


@pytest.fixture
def stub_app(
    fake_loaded_model: _FakeLoadedModel,
    tmp_path: Any,
) -> Iterator[FastAPI]:
    """Build a FastAPI app with the real DI graph but a stubbed model.

    ``Settings.repo_root`` points at an empty ``tmp_path`` so the
    lifespan's load attempt fails cleanly (logged once); the
    :func:`get_loaded_model` provider is then overridden with the
    fake. The middleware stack (request ID, CORS) stays on the
    codepath — exercising it is the reason ``TestClient`` is used
    here instead of calling routers directly.
    """
    settings = Settings(repo_root=tmp_path)
    app = create_app(settings)
    app.state.loaded_model = fake_loaded_model
    app.dependency_overrides[get_loaded_model] = lambda: fake_loaded_model
    app.dependency_overrides[get_settings] = lambda: settings
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def stub_client(stub_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(stub_app) as client:
        yield client
