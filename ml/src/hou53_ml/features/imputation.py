"""Feature-aware imputers used before the ColumnTransformer."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class NeighborhoodLotFrontageImputer(BaseEstimator, TransformerMixin):
    """Fill ``LotFrontage`` with the training median for its neighborhood.

    Lot frontage is the only materially missing numeric field where a global
    median is weaker than a local one. The transformer learns neighborhood
    medians on the training fold only, so cross-validation remains leakage-free.
    """

    def __init__(
        self,
        *,
        frontage_column: str = "LotFrontage",
        neighborhood_column: str = "Neighborhood",
    ) -> None:
        self.frontage_column = frontage_column
        self.neighborhood_column = neighborhood_column

    def fit(
        self,
        X: pd.DataFrame,
        y: object | None = None,
    ) -> NeighborhoodLotFrontageImputer:
        self._validate_input(X)
        frontage = pd.to_numeric(X[self.frontage_column], errors="coerce")
        neighborhoods = X[self.neighborhood_column].astype("string")
        self.neighborhood_medians_ = frontage.groupby(neighborhoods).median().dropna()
        self.global_median_ = float(frontage.median())
        if np.isnan(self.global_median_):
            self.global_median_ = 0.0
        self.feature_names_in_ = np.asarray(X.columns)
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        self._validate_input(X)
        out = X.copy()
        frontage = pd.to_numeric(out[self.frontage_column], errors="coerce")
        fill_values = (
            out[self.neighborhood_column]
            .astype("string")
            .map(self.neighborhood_medians_)
            .fillna(self.global_median_)
        )
        out[self.frontage_column] = frontage.fillna(fill_values).astype(float)
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
        return np.asarray(names)

    def _validate_input(self, X: pd.DataFrame) -> None:
        if not isinstance(X, pd.DataFrame):
            msg = f"NeighborhoodLotFrontageImputer expects a DataFrame, got {type(X).__name__}"
            raise TypeError(msg)
        missing = [
            col for col in (self.frontage_column, self.neighborhood_column) if col not in X.columns
        ]
        if missing:
            msg = f"NeighborhoodLotFrontageImputer input is missing {missing}"
            raise ValueError(msg)
