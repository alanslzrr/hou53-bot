"""Domain constants for the Ames Housing dataset.

These are facts about the data that we have learned from the description
file (`data/external/data_description.txt`) and from the Kaggle community.
Encoding them as constants here — rather than as magic strings scattered
across the pipeline — gives us a single place to update when we discover
new quirks of the dataset, and makes the feature-engineering code read as
declarative configuration rather than as a bag of special cases.

Source of truth for decisions like "which fields legitimately use 'NA' as
a category" is the De Cock paper + the description file. Any change to
these constants should cite both.
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
NUMERIC_BUT_CATEGORICAL: Final[frozenset[str]] = frozenset(
    {"MSSubClass", "MoSold", "YrSold"}
)

#: Per the De Cock paper (2011), removing partial-sale outliers with
#: ``GrLivArea > 4000`` improves generalization. We log the removal in a
#: training artifact rather than silently dropping rows.
GRLIVAREA_OUTLIER_THRESHOLD: Final[float] = 4000.0
