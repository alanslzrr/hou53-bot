"""Domain constants for the Ames Housing dataset.

Facts derived from the description file
(`data/external/data_description.txt`) and from the Kaggle community.
Centralised here so feature-engineering code reads as declarative
configuration instead of a bag of special cases.

Authoritative sources for decisions like "which fields legitimately use
``'NA'`` as a category": the De Cock (2011) paper and the description
file. Any change to a constant below cites both.
"""

from __future__ import annotations

from typing import Final

TARGET: Final[str] = "SalePrice"

#: Fields where the string ``"NA"`` is a *legitimate category* (e.g.,
#: ``PoolQC="NA"`` means "house has no pool"), not a missing value.
#: Imputing these as missing would destroy information.
NA_AS_CATEGORY: Final[frozenset[str]] = frozenset(
    {
        "Alley",
        "BsmtQual",
        "BsmtCond",
        "BsmtExposure",
        "BsmtFinType1",
        "BsmtFinType2",
        "FireplaceQu",
        "GarageType",
        "GarageFinish",
        "GarageQual",
        "GarageCond",
        "PoolQC",
        "Fence",
        "MiscFeature",
        "MasVnrType",
    }
)

#: Ordinal quality scales. Mapping ``NA -> 0`` is intentional: a missing
#: pool is categorically worse than a "Poor" pool for valuation purposes.
QUALITY_ORDER: Final[dict[str, int]] = {
    "NA": 0,
    "Po": 1,
    "Fa": 2,
    "TA": 3,
    "Gd": 4,
    "Ex": 5,
}

#: Columns whose dtype is numeric on disk but whose *meaning* is categorical
#: (e.g., ``MSSubClass`` is an int code for a building class, not a
#: magnitude). Treating them as numeric would invent ordering where none
#: exists.
NUMERIC_BUT_CATEGORICAL: Final[frozenset[str]] = frozenset({"MSSubClass", "MoSold", "YrSold"})

#: Per the De Cock paper (2011), removing partial-sale outliers with
#: ``GrLivArea > 4000`` and unusually low prices improves generalization.
#: We log the removal in a training artifact rather than silently dropping rows.
GRLIVAREA_OUTLIER_THRESHOLD: Final[float] = 4000.0
LOW_PRICE_OUTLIER_THRESHOLD: Final[float] = 300_000.0

#: Numeric columns with raw skewness > 0.75 in the curated 1,460-row
#: training set (computed in the EDA notebook; see
#: ``docs/eda/report.md`` § 4). Log1p-transformed inside the
#: preprocessor. Hardcoded (not recomputed at fit time) because
#: (a) skew depends on the training distribution and (b) serving-time
#: preprocessing must be deterministic across re-fits on different
#: folds. Adding or removing a column here is an ADR-worthy change.
SKEWED_NUMERIC_FEATURES: Final[frozenset[str]] = frozenset(
    {
        # > 5
        "MiscVal",
        "PoolArea",
        "LotArea",
        "3SsnPorch",
        "LowQualFinSF",
        # 1..5
        "KitchenAbvGr",
        "BsmtFinSF2",
        "ScreenPorch",
        "BsmtHalfBath",
        "EnclosedPorch",
        "MasVnrArea",
        "OpenPorchSF",
        "BsmtFinSF1",
        "WoodDeckSF",
        "TotalBsmtSF",
        "1stFlrSF",
        "GrLivArea",
        "BsmtUnfSF",
        "2ndFlrSF",
        "TotRmsAbvGrd",
    }
)

#: Names of features added by ``hou53_ml.features.derived.DerivedFeatures``.
#: Listed here so the ``ColumnTransformer`` builder can reference them
#: without importing the transformer.
DERIVED_NUMERIC_FEATURES: Final[tuple[str, ...]] = (
    "HouseAge",
    "RemodAge",
    "GarageAge",
    "TotalSF",
    "TotalBathrooms",
    "TotalPorchSF",
    "AllFloorsSF",
    "QualArea",
    "QualTotalSF",
)

DERIVED_BINARY_FEATURES: Final[tuple[str, ...]] = (
    "HasGarage",
    "IsRemodeled",
    "IsNewHouse",
    "HasPool",
    "Has2ndFloor",
    "HasBsmt",
    "HasFireplace",
)

SUPERVISED_NUMERIC_FEATURES: Final[tuple[str, ...]] = ("NeighborhoodPriceLog",)

#: Columns where the missingness itself may carry signal — the
#: numeric imputer adds an ``add_indicator`` flag for these (EDA § 3).
ACTUAL_MISSING_NUMERIC: Final[frozenset[str]] = frozenset(
    {"LotFrontage", "GarageYrBlt", "MasVnrArea"}
)
ACTUAL_MISSING_CATEGORICAL: Final[frozenset[str]] = frozenset({"Electrical"})

#: Ordinal columns whose levels are *integers on disk* rather than
#: strings (``OverallQual``, ``OverallCond`` — both 1..10). They are
#: still ordered, so the API surface validates them as ``int`` with the
#: documented range, and the pipeline routes them through the numeric
#: ordinal branch instead of one-hot encoding them.
NUMERIC_ORDINAL_FEATURES: Final[frozenset[str]] = frozenset({"OverallQual", "OverallCond"})

#: Ordered non-quality categoricals. Category lists are low-to-high so
#: ``OrdinalEncoder`` emits larger numbers for better levels.
ORDINAL_OTHER_ORDERS: Final[dict[str, tuple[str, ...]]] = {
    "LotShape": ("NA", "IR3", "IR2", "IR1", "Reg"),
    "LandSlope": ("NA", "Sev", "Mod", "Gtl"),
    "BsmtExposure": ("NA", "No", "Mn", "Av", "Gd"),
    "BsmtFinType1": ("NA", "Unf", "LwQ", "Rec", "BLQ", "ALQ", "GLQ"),
    "BsmtFinType2": ("NA", "Unf", "LwQ", "Rec", "BLQ", "ALQ", "GLQ"),
    "GarageFinish": ("NA", "Unf", "RFn", "Fin"),
    "PavedDrive": ("NA", "N", "P", "Y"),
    "Functional": ("NA", "Sal", "Sev", "Maj2", "Maj1", "Mod", "Min2", "Min1", "Typ"),
    "Fence": ("NA", "MnWw", "GdWo", "MnPrv", "GdPrv"),
}
