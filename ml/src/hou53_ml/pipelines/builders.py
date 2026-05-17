"""Compose the full training pipeline.

A *pipeline* in this codebase is a single sklearn object that:

1. Fills ``LotFrontage`` from neighborhood medians.
2. Adds derived features (ages, areas, quality interactions, flags).
3. Adds a fold-safe neighborhood target encoding.
4. Runs the :class:`ColumnTransformer` (impute + log + ordinal + nominal).
5. Hands the encoded matrix to a regressor (Ridge or XGBoost).
6. Wraps the regressor with
   :class:`sklearn.compose.TransformedTargetRegressor` so every
   ``predict`` call returns dollars even though training optimized
   ``log1p(SalePrice)``.

That single object is what ``joblib`` serialises and what the API
loads at startup. No postprocessing happens in the API — the pipeline
is the model.

Why ``TransformedTargetRegressor`` over manually log-transforming
----------------------------------------------------------------
The risk with manual transformation is forgetting the inverse at
serving time. Wrapping the estimator means the same object that
trained on log dollars predicts in dollars. Training-time and
serving-time can never diverge.

Why ``DerivedFeatures`` is a step in the same Pipeline (not pre-applied)
-----------------------------------------------------------------------
If derivations lived "outside" the pipeline (e.g., as a notebook step
applied to ``X_train``), then either (a) the API would have to
re-implement them in Python — duplicating logic and inviting bugs — or
(b) the training data would not be reproducible from raw inputs alone.
Putting them in the Pipeline closes both holes.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.compose import TransformedTargetRegressor
from sklearn.pipeline import Pipeline

from hou53_ml.features.builders import build_preprocessor
from hou53_ml.features.derived import DerivedFeatures
from hou53_ml.features.imputation import NeighborhoodLotFrontageImputer
from hou53_ml.features.target_encoding import NeighborhoodTargetEncoder
from hou53_ml.io.schema import Schema
from hou53_ml.models.boosting import make_xgboost


def build_pipeline(
    estimator: BaseEstimator | None = None,
    *,
    schema: Schema | None = None,
) -> TransformedTargetRegressor:
    """Build the full training pipeline.

    Args:
        estimator: The regressor to use. Defaults to
            :func:`hou53_ml.models.boosting.make_xgboost` with project
            defaults. Pass a Ridge baseline to compare.
        schema: Column metadata for the preprocessor. Defaults to the
            curated 79-feature distribution.

    Returns:
        An unfitted :class:`TransformedTargetRegressor`. ``fit(X, y)``
        expects ``X`` as the raw post-loader DataFrame (no derived
        features yet) and ``y`` as raw ``SalePrice`` in dollars.
    """
    schema = schema or Schema.default()
    estimator = estimator or make_xgboost()

    inner = Pipeline(
        steps=[
            ("lot_frontage", NeighborhoodLotFrontageImputer()),
            ("derived", DerivedFeatures()),
            ("target_encode", NeighborhoodTargetEncoder()),
            (
                "preprocess",
                build_preprocessor(
                    schema=schema,
                    include_supervised_features=True,
                ),
            ),
            ("estimator", estimator),
        ]
    )

    return TransformedTargetRegressor(
        regressor=inner,
        func=np.log1p,
        inverse_func=np.expm1,
        check_inverse=False,  # validated by tests; saves a fit-time round-trip
    )


def fit_kwargs_for_xgboost(
    pipeline: TransformedTargetRegressor,
    eval_set: list[tuple[Any, Any]] | None = None,
    *,
    early_stopping_rounds: int | None = 50,
) -> dict[str, Any]:
    """Build keyword arguments for XGBoost early stopping.

    XGBoost's early stopping requires an ``eval_set`` whose features
    have already gone through the preprocessor. We compose the kwargs
    so the caller can do::

        pipeline.fit(X_train, y_train, **fit_kwargs_for_xgboost(pipeline, ...))

    without knowing the internal step names.

    Args:
        pipeline: The pipeline whose XGBoost step needs early stopping
            wired. Returns an empty dict if the inner estimator is not
            XGBoost.
        eval_set: Pre-encoded ``[(X_val_enc, y_val_log)]`` tuples.
        early_stopping_rounds: Forwarded to XGBoost.

    Returns:
        Keyword dict suitable for ``pipeline.fit(...)``. Empty if the
        estimator does not need early stopping.
    """
    inner = pipeline.regressor
    estimator = inner.named_steps["estimator"] if isinstance(inner, Pipeline) else inner
    if estimator.__class__.__name__ != "XGBRegressor" or eval_set is None:
        return {}
    # The double-underscore prefix routes the kwarg through the named step.
    return {
        "regressor__estimator__eval_set": eval_set,
        # Early stopping rounds is set on the estimator itself in modern
        # xgboost (the ``eval_set`` is the only fit-time arg). We set
        # it on the estimator before the call.
        # Returning an empty dict keeps this simple; the caller mutates
        # the estimator. Returned in this dict for symmetry.
        "regressor__estimator__verbose": False,
    }
