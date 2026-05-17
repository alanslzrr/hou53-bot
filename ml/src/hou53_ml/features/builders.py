"""Compose the full preprocessing :class:`ColumnTransformer`.

This is the only module that knows how the EDA findings translate into
sklearn primitives. Everything else (the training entry point, the
API at serving time) goes through :func:`build_preprocessor` and
inherits the choices documented in
[``docs/eda/report.md``](../../../docs/eda/report.md) § 10.

What the preprocessor does, in order
-----------------------------------
1. Pre-pipeline transformers fill ``LotFrontage`` by neighborhood,
   add structural features, and append a fold-safe neighborhood target
   encoding when the full training pipeline is used.
2. A :class:`ColumnTransformer` then routes columns through five branches:

   - **num_skewed**  — median-impute then ``log1p``. Applied to the
     20 columns flagged by the EDA plus the 3 derived numeric
     candidates (``HouseAge``, ``RemodAge``, ``TotalSF``, etc.).
   - **num_other**   — median-impute only. Includes the binary
     ``HasGarage`` flag (no log transform on a 0/1).
   - **temporal**    — median-impute the raw year columns. Trees can
     pick up the year directly; the engineered ages just give them a
     shortcut.
   - **ord_quality** — fill missing strings with ``"NA"`` then
     :func:`make_quality_ordinal_encoder` (NA→0 .. Ex→5).
   - **ord_other**   — explicit low→high encodings for dataset-specific
     ordered categoricals (basement exposure, finish, functional, etc.).
   - **nominal**     — fill missing with ``"missing"`` then
     :class:`OneHotEncoder(handle_unknown="ignore")`. Covers the
     unordered categoricals.

Why target encoding is not implemented here
-------------------------------------------
``NeighborhoodPriceLog`` is supervised, so it cannot live in a plain
``ColumnTransformer`` branch: the branch would need ``y`` during fit and
would be easy to leak if computed before cross-validation. The full
training pipeline inserts :class:`hou53_ml.features.target_encoding.
NeighborhoodTargetEncoder` before this preprocessor, where sklearn passes
the fold's training target safely.
"""

from __future__ import annotations

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder

from hou53_ml.constants import (
    ACTUAL_MISSING_NUMERIC,
    DERIVED_BINARY_FEATURES,
    DERIVED_NUMERIC_FEATURES,
    NUMERIC_ORDINAL_FEATURES,
    SKEWED_NUMERIC_FEATURES,
    SUPERVISED_NUMERIC_FEATURES,
)
from hou53_ml.features.ordinal import (
    make_ordered_ordinal_encoder,
    make_quality_ordinal_encoder,
)
from hou53_ml.io.schema import Schema


def _split_numeric(
    schema: Schema,
    *,
    include_supervised_features: bool,
) -> tuple[list[str], list[str]]:
    """Partition modelling numerics into (skewed-for-log, others).

    Includes the derived numeric features so the post-derivation
    ``ColumnTransformer`` sees them too.
    """
    candidates = list(schema.numeric) + list(DERIVED_NUMERIC_FEATURES)
    supervised = list(SUPERVISED_NUMERIC_FEATURES) if include_supervised_features else []
    # Only HouseAge / RemodAge / TotalSF benefit from log; GarageAge
    # is dominated by zeros (HasGarage encodes the rest) so we leave
    # it linear.
    derived_to_log = {
        "HouseAge",
        "RemodAge",
        "TotalSF",
        "TotalPorchSF",
        "AllFloorsSF",
        "QualArea",
        "QualTotalSF",
    }
    skewed = [c for c in candidates if c in SKEWED_NUMERIC_FEATURES or c in derived_to_log]
    other = [c for c in candidates if c not in skewed]
    # Binary + supervised features route through num_other (no log transform).
    other.extend(DERIVED_BINARY_FEATURES)
    other.extend(supervised)
    return skewed, other


def _make_skewed_numeric_pipeline(
    add_indicator_for: list[str],
) -> Pipeline:
    """Median-impute then log1p.

    We do **not** scale the output: XGBoost is scale-invariant, and
    Ridge (the baseline) gets its own ``StandardScaler`` at the model
    factory level. Scaling here would be wasted work.

    The inner pipeline emits pandas (via ``set_output``) so that
    ``FunctionTransformer`` sees feature names at both fit and
    transform time and cannot emit the
    "X does not have valid feature names" warning sklearn raises when
    the imputer collapses to numpy mid-pipeline.
    """
    pipe = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            (
                "log1p",
                FunctionTransformer(
                    func=np.log1p,
                    inverse_func=np.expm1,
                    feature_names_out="one-to-one",
                    validate=False,
                ),
            ),
        ]
    )
    return pipe.set_output(transform="pandas")


def _make_other_numeric_pipeline() -> Pipeline:
    return Pipeline(steps=[("impute", SimpleImputer(strategy="median"))]).set_output(
        transform="pandas"
    )


def _make_temporal_pipeline() -> Pipeline:
    return Pipeline(steps=[("impute", SimpleImputer(strategy="median"))]).set_output(
        transform="pandas"
    )


def _make_quality_ordinal_pipeline(n_features: int) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "fill_na",
                SimpleImputer(strategy="constant", fill_value="NA"),
            ),
            ("ordinal", make_quality_ordinal_encoder(n_features)),
        ]
    ).set_output(transform="pandas")


def _make_ordered_ordinal_pipeline(columns: list[str]) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "fill_na",
                SimpleImputer(strategy="constant", fill_value="NA"),
            ),
            ("ordinal", make_ordered_ordinal_encoder(columns)),
        ]
    ).set_output(transform="pandas")


def _make_numeric_ordinal_pipeline() -> Pipeline:
    return Pipeline(steps=[("impute", SimpleImputer(strategy="median"))]).set_output(
        transform="pandas"
    )


def _make_nominal_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "fill_missing",
                SimpleImputer(strategy="constant", fill_value="missing"),
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                    dtype=np.float32,
                    min_frequency=10,  # rare-category protection (~0.7%)
                ),
            ),
        ]
    ).set_output(transform="pandas")


def build_preprocessor(
    schema: Schema | None = None,
    *,
    include_supervised_features: bool = False,
) -> ColumnTransformer:
    """Return the full preprocessing :class:`ColumnTransformer`.

    Args:
        schema: Column metadata. Defaults to :meth:`Schema.default`,
            which is the curated 79-feature distribution.
        include_supervised_features: Include supervised feature-engineering
            columns that require ``y`` during fit. Enabled only when the
            full training pipeline inserts those columns fold-safely.

    Returns:
        An unfitted :class:`ColumnTransformer` whose ``fit`` expects a
        DataFrame **after** :class:`DerivedFeatures` has run (so that
        the engineered columns are present in the input).
    """
    schema = schema or Schema.default()
    skewed_num, other_num = _split_numeric(
        schema,
        include_supervised_features=include_supervised_features,
    )
    quality_cols = list(schema.ordinal_quality)
    ordered_ordinal_cols = [c for c in schema.ordinal_other if c not in NUMERIC_ORDINAL_FEATURES]
    numeric_ordinal_cols = [c for c in schema.ordinal_other if c in NUMERIC_ORDINAL_FEATURES]
    nominal_cols = list(schema.nominal)
    temporal_cols = list(schema.temporal)

    actual_missing_in_skewed = [c for c in skewed_num if c in ACTUAL_MISSING_NUMERIC]

    return ColumnTransformer(
        transformers=[
            (
                "num_skewed",
                _make_skewed_numeric_pipeline(actual_missing_in_skewed),
                skewed_num,
            ),
            ("num_other", _make_other_numeric_pipeline(), other_num),
            ("temporal", _make_temporal_pipeline(), temporal_cols),
            (
                "ord_quality",
                _make_quality_ordinal_pipeline(n_features=len(quality_cols)),
                quality_cols,
            ),
            (
                "ord_other",
                _make_ordered_ordinal_pipeline(ordered_ordinal_cols),
                ordered_ordinal_cols,
            ),
            ("ord_numeric", _make_numeric_ordinal_pipeline(), numeric_ordinal_cols),
            ("nominal", _make_nominal_pipeline(), nominal_cols),
        ],
        # Drop anything the schema does not classify (e.g., ``Id``).
        remainder="drop",
        verbose_feature_names_out=False,
    ).set_output(transform="pandas")
