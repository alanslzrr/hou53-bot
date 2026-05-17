"""Derived (engineered) features.

:class:`DerivedFeatures` appends structural columns; the originals are
preserved:

- ``HouseAge``  = ``YrSold`` - ``YearBuilt``
- ``RemodAge``  = ``YrSold`` - ``YearRemodAdd``
- ``GarageAge`` = ``max(0, YrSold - GarageYrBlt)`` (NaN-safe)
- ``TotalSF``   = ``1stFlrSF`` + ``2ndFlrSF`` + ``TotalBsmtSF``
- ``HasGarage`` = ``int8`` indicator for non-null ``GarageYrBlt``
- plus bathrooms, porch area, quality-area interactions, and presence flags

A custom transformer is required because ``ColumnTransformer`` slots
are independent column groups and cannot produce columns derived from
multiple inputs. Implementing the sklearn transformer contract here
makes the derivation a step inside the serialised pipeline; the API
loads one joblib blob and serving-time semantics match training-time.

SOLID:

- SRP: appends derived columns only. No imputation, scaling, encoding,
  or dropping.
- OCP: new derived features are added by extending ``OUTPUT_NAMES``
  and ``_compute``.
- LSP: implements the sklearn transformer contract (``fit`` returns
  ``self``; ``transform`` returns a DataFrame with unchanged row count).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from hou53_ml.constants import DERIVED_BINARY_FEATURES, DERIVED_NUMERIC_FEATURES

#: All output column names this transformer is responsible for.
OUTPUT_NAMES: tuple[str, ...] = (*DERIVED_NUMERIC_FEATURES, *DERIVED_BINARY_FEATURES)


class DerivedFeatures(BaseEstimator, TransformerMixin):
    """Add age + total-square-feet + has-garage features.

    Args:
        clamp_negative_ages: When ``True`` (default), ages computed as
            ``YrSold - YearXxx`` are clamped at zero. A handful of
            rows have ``GarageYrBlt > YrSold`` (data-entry errors in
            the source); clamping renders them as "brand new" garages
            rather than negative ages. Set to ``False`` to surface the
            raw values in tests.

    Attributes:
        feature_names_in_: Set during ``fit`` for compatibility with
            scikit-learn's ``set_output(transform="pandas")`` machinery.
        n_features_in_: Same.
    """

    # Columns the transformer reads. Class-level constant so the input
    # can be validated early (fail-fast with a clear message if the
    # upstream loader's schema changes).
    REQUIRED_COLUMNS: tuple[str, ...] = (
        "YrSold",
        "YearBuilt",
        "YearRemodAdd",
        "GarageYrBlt",
        "1stFlrSF",
        "2ndFlrSF",
        "TotalBsmtSF",
        "FullBath",
        "HalfBath",
        "BsmtFullBath",
        "BsmtHalfBath",
        "OpenPorchSF",
        "EnclosedPorch",
        "3SsnPorch",
        "ScreenPorch",
        "PoolArea",
        "GarageArea",
        "Fireplaces",
        "OverallQual",
        "GrLivArea",
    )

    def __init__(self, *, clamp_negative_ages: bool = True) -> None:
        self.clamp_negative_ages = clamp_negative_ages

    # --- sklearn contract ----------------------------------------------------
    def fit(self, X: pd.DataFrame, y: object | None = None) -> DerivedFeatures:
        """Validate the input columns and remember the schema."""
        self._validate_input(X)
        # Stored attributes follow sklearn's convention (trailing underscore).
        self.feature_names_in_ = np.asarray(X.columns)
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Return ``X`` with the five derived columns appended."""
        self._validate_input(X)
        out = X.copy()
        derived = self._compute(out)
        for name, series in derived.items():
            out[name] = series
        return out

    def get_feature_names_out(self, input_features: list[str] | None = None) -> np.ndarray:
        """All input columns plus the derived ones, in deterministic order."""
        names = (
            list(input_features)
            if input_features is not None
            else list(getattr(self, "feature_names_in_", []))
        )
        return np.asarray([*names, *OUTPUT_NAMES])

    # --- Internals -----------------------------------------------------------
    def _validate_input(self, X: pd.DataFrame) -> None:
        if not isinstance(X, pd.DataFrame):
            msg = f"DerivedFeatures expects a DataFrame, got {type(X).__name__}"
            raise TypeError(msg)
        missing = [c for c in self.REQUIRED_COLUMNS if c not in X.columns]
        if missing:
            msg = (
                f"DerivedFeatures input is missing required column(s): "
                f"{missing}. Upstream loader / preprocessor changed?"
            )
            raise ValueError(msg)

    def _compute(self, X: pd.DataFrame) -> dict[str, pd.Series]:
        """Compute the derived columns. Pure function over ``X``."""

        def num(column: str) -> pd.Series:
            return pd.to_numeric(X[column], errors="coerce")

        # YrSold may arrive as string (loader coerces it); cast safely.
        yr_sold = num("YrSold")

        house_age = yr_sold - num("YearBuilt")
        remod_age = yr_sold - num("YearRemodAdd")
        garage_age = yr_sold - num("GarageYrBlt")

        if self.clamp_negative_ages:
            house_age = house_age.clip(lower=0)
            remod_age = remod_age.clip(lower=0)
            garage_age = garage_age.clip(lower=0)

        # GarageAge is NaN when no garage exists. Fill with 0 and add
        # HasGarage as a separate signal so the model distinguishes
        # "no garage" from "brand-new garage".
        has_garage = (X["GarageYrBlt"].notna() | (num("GarageArea") > 0)).astype(np.int8)
        garage_age = garage_age.fillna(0)

        first_floor = num("1stFlrSF").fillna(0)
        second_floor = num("2ndFlrSF").fillna(0)
        basement = num("TotalBsmtSF").fillna(0)
        gr_liv_area = num("GrLivArea").fillna(0)
        overall_qual = num("OverallQual").fillna(0)
        pool_area = num("PoolArea").fillna(0)
        fireplaces = num("Fireplaces").fillna(0)

        total_sf = first_floor + second_floor + basement
        total_bathrooms = (
            num("FullBath").fillna(0)
            + 0.5 * num("HalfBath").fillna(0)
            + num("BsmtFullBath").fillna(0)
            + 0.5 * num("BsmtHalfBath").fillna(0)
        )
        total_porch_sf = (
            num("OpenPorchSF").fillna(0)
            + num("EnclosedPorch").fillna(0)
            + num("3SsnPorch").fillna(0)
            + num("ScreenPorch").fillna(0)
        )
        all_floors_sf = first_floor + second_floor

        return {
            "HouseAge": house_age.astype(float),
            "RemodAge": remod_age.astype(float),
            "GarageAge": garage_age.astype(float),
            "TotalSF": total_sf.astype(float),
            "TotalBathrooms": total_bathrooms.astype(float),
            "TotalPorchSF": total_porch_sf.astype(float),
            "AllFloorsSF": all_floors_sf.astype(float),
            "QualArea": (overall_qual * gr_liv_area).astype(float),
            "QualTotalSF": (overall_qual * total_sf).astype(float),
            "HasGarage": has_garage,
            "IsRemodeled": (num("YearRemodAdd") != num("YearBuilt")).astype(np.int8),
            "IsNewHouse": (yr_sold == num("YearBuilt")).astype(np.int8),
            "HasPool": (pool_area > 0).astype(np.int8),
            "Has2ndFloor": (second_floor > 0).astype(np.int8),
            "HasBsmt": (basement > 0).astype(np.int8),
            "HasFireplace": (fireplaces > 0).astype(np.int8),
        }
