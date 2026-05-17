"""Fold-safe supervised encoders."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from hou53_ml.constants import SUPERVISED_NUMERIC_FEATURES


class NeighborhoodTargetEncoder(BaseEstimator, TransformerMixin):
    """Append a fold-safe neighborhood median target feature.

    The transformer sits inside the sklearn pipeline, so during CV each fold
    learns medians from its training slice only. Because the outer pipeline is
    wrapped in ``TransformedTargetRegressor``, ``y`` arrives in log-dollar space;
    the output feature is therefore named ``NeighborhoodPriceLog``.
    """

    def __init__(
        self,
        *,
        source_column: str = "Neighborhood",
        output_column: str = SUPERVISED_NUMERIC_FEATURES[0],
    ) -> None:
        self.source_column = source_column
        self.output_column = output_column

    def fit(
        self,
        X: pd.DataFrame,
        y: object | None = None,
    ) -> NeighborhoodTargetEncoder:
        self._validate_input(X)
        if y is None:
            msg = "NeighborhoodTargetEncoder requires y during fit"
            raise ValueError(msg)
        target = pd.Series(np.asarray(y, dtype=float), index=X.index)
        neighborhoods = X[self.source_column].astype("string")
        self.mapping_ = target.groupby(neighborhoods).median().dropna()
        self.global_value_ = float(target.median())
        self.feature_names_in_ = np.asarray(X.columns)
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        self._validate_input(X)
        out = X.copy()
        encoded = (
            out[self.source_column].astype("string").map(self.mapping_).fillna(self.global_value_)
        )
        out[self.output_column] = encoded.astype(float)
        return out

    def get_feature_names_out(
        self,
        input_features: list[str] | None = None,
    ) -> np.ndarray:
        names = (
            list(input_features)
            if input_features is not None
            else list(getattr(self, "feature_names_in_", []))
        )
        return np.asarray([*names, self.output_column])

    def _validate_input(self, X: pd.DataFrame) -> None:
        if not isinstance(X, pd.DataFrame):
            msg = f"NeighborhoodTargetEncoder expects a DataFrame, got {type(X).__name__}"
            raise TypeError(msg)
        if self.source_column not in X.columns:
            msg = f"NeighborhoodTargetEncoder input is missing {self.source_column!r}"
            raise ValueError(msg)
