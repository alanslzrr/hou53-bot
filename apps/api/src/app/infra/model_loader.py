"""Model artifact loader and SHAP explainer cache.

Loaded once at startup (FastAPI lifespan) and shared across requests.
Encapsulated behind :class:`LoadedModel` so the rest of the service
sees an opaque object with two methods (``predict`` / ``explain``)
instead of a sklearn pipeline + a SHAP explainer.

This is the only module that knows the artifact lives on disk. Tests
build a :class:`LoadedModel` directly with in-memory fakes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from hou53_ml.constants import NUMERIC_BUT_CATEGORICAL
from hou53_ml.explainability import Explanation, PipelineSHAPExplainer
from hou53_ml.io import AmesHousingLoader, Schema
from hou53_ml.serialization import ArtifactMetadata, ModelArtifact

from app.infra.logging import get_logger

_log = get_logger(__name__)


@dataclass(slots=True)
class LoadedModel:
    """A loaded artifact + a fitted SHAP explainer.

    Attributes:
        pipeline: The fitted sklearn ``TransformedTargetRegressor``.
        explainer: SHAP wrapper, ready to ``.explain(row)``.
        metadata: Sidecar JSON metadata.
        schema: Column metadata used to build complete request rows.
    """

    pipeline: Any
    explainer: PipelineSHAPExplainer
    metadata: ArtifactMetadata
    schema: Schema

    # --- Public surface ------------------------------------------------------
    def predict_dollars(self, row: pd.DataFrame) -> float:
        """Predict the sale price in dollars for a single row."""
        if len(row) != 1:
            msg = f"predict_dollars expects a single-row DataFrame, got {len(row)}"
            raise ValueError(msg)
        return float(self.pipeline.predict(row)[0])

    def explain(self, row: pd.DataFrame, *, top_k: int | None = None) -> Explanation:
        """Compute SHAP attribution for a single-row DataFrame."""
        return self.explainer.explain(row, top_k=top_k)

    def complete_row(self, partial: dict[str, Any]) -> pd.DataFrame:
        """Turn a partial input dict into a 1-row DataFrame ready to predict.

        - Every column the schema knows about is present in the output
          (``None`` for fields the user did not provide). The pipeline
          handles missing values via its own imputers.
        - :data:`NUMERIC_BUT_CATEGORICAL` columns (``MSSubClass``,
          ``MoSold``, ``YrSold``) are coerced to ``string`` dtype so
          the one-hot encoder sees the same category space it was fit
          on, regardless of whether the user typed a number or a string.

        Args:
            partial: User-supplied feature values. Unknown keys are
                ignored. Missing keys are filled with ``None``.

        Returns:
            A single-row :class:`pandas.DataFrame` with the columns the
            pipeline expects, in deterministic schema order.
        """
        all_inputs = (self.schema.id_column, *self.schema.all_features)
        row_data: dict[str, Any] = {}
        for col in all_inputs:
            value = partial.get(col)
            if col == self.schema.id_column and value is None:
                # Id is dropped by the preprocessor; any value works.
                value = 0
            if col in NUMERIC_BUT_CATEGORICAL and value is not None:
                value = str(value)
            row_data[col] = value
        # Single-row frame; ``object`` dtype is fine — the pipeline's
        # transformers are typed and will coerce.
        return pd.DataFrame([row_data], columns=list(all_inputs))


def load_model(
    *,
    models_dir: Path,
    background_size: int,
    background_seed: int,
    shap_top_k: int,
    csv_for_background: Path,
) -> LoadedModel:
    """Load the artifact and pre-fit the SHAP explainer.

    Args:
        models_dir: Directory containing ``hou53-pipeline.joblib`` and
            ``model_metadata.json``.
        background_size: Number of training rows sampled for the
            SHAP background. 50 is plenty for stable baselines.
        background_seed: RNG seed for the background sample.
        shap_top_k: Default top-K features to surface in explanations.
        csv_for_background: Path to the raw CSV — used to draw the
            SHAP background sample. The model itself does not need it
            (the pipeline is already fit), but :class:`shap.TreeExplainer`
            does.

    Returns:
        A populated :class:`LoadedModel`.
    """
    _log.info("loading_artifact", models_dir=str(models_dir))
    artifact = ModelArtifact.load(models_dir)
    _log.info(
        "artifact_loaded",
        model_name=artifact.metadata.model_name,
        trained_at=artifact.metadata.trained_at_utc,
        dataset_sha256=artifact.metadata.dataset_sha256[:16],
    )

    schema = Schema.default()
    background = _sample_background(
        csv_for_background=csv_for_background,
        n=background_size,
        seed=background_seed,
        schema=schema,
    )
    _log.info("building_shap_explainer", background_rows=len(background), top_k=shap_top_k)
    explainer = PipelineSHAPExplainer(artifact.pipeline, background=background, top_k=shap_top_k)

    return LoadedModel(
        pipeline=artifact.pipeline,
        explainer=explainer,
        metadata=artifact.metadata,
        schema=schema,
    )


def _sample_background(
    *,
    csv_for_background: Path,
    n: int,
    seed: int,
    schema: Schema,
) -> pd.DataFrame:
    """Draw a fixed background sample for SHAP from the raw CSV.

    SHAP TreeExplainer needs concrete rows to estimate the
    expected-value baseline. Using a fixed-seed sample of the training
    data keeps explanations reproducible across deployments of the
    same artifact.
    """
    if not csv_for_background.exists():
        msg = (
            f"SHAP background CSV not found at {csv_for_background}. "
            "Either commit a small sample to the repo, or ship the raw "
            "CSV with the artifact."
        )
        raise FileNotFoundError(msg)

    df = AmesHousingLoader(csv_for_background).load().frame
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(df), size=min(n, len(df)), replace=False)
    return df.drop(columns=[schema.target]).iloc[indices].reset_index(drop=True)
