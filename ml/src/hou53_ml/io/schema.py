"""Static schema metadata for the Ames Housing dataset.

:class:`Schema` enumerates dataset columns by *role*, not by
dtype-on-disk. The on-disk dtypes lie in several places:

- ``MSSubClass`` is ``int64`` but encodes a category.
- ``OverallQual`` is ``int64`` and is an ordered scale.
- ``MoSold`` is ``int64`` but is a categorical month code.

Routing decisions in feature-engineering code therefore consult
``schema.numeric``, ``schema.ordinal_quality`` etc. instead of
``df.dtypes``. Column-meaning changes happen in one file.

Source: ``data/external/data_description.txt`` and De Cock (2011).
"""

from dataclasses import dataclass

from hou53_ml.constants import QUALITY_ORDER, TARGET

# -----------------------------------------------------------------------------
# Column groupings — single source of truth.
#
# These tuples are exhaustive for the curated 79-feature distribution. They
# are tuples (not sets) to give a deterministic iteration order, which
# matters for ``ColumnTransformer``'s output column ordering downstream.
# -----------------------------------------------------------------------------

#: Identifier; carry through the pipeline but never feed into the model.
ID_COLUMN: str = "Id"

#: Continuous magnitudes. Skewed candidates get ``log1p`` in Phase 2.
NUMERIC_FEATURES: tuple[str, ...] = (
    "LotFrontage",
    "LotArea",
    "MasVnrArea",
    "BsmtFinSF1",
    "BsmtFinSF2",
    "BsmtUnfSF",
    "TotalBsmtSF",
    "1stFlrSF",
    "2ndFlrSF",
    "LowQualFinSF",
    "GrLivArea",
    "BsmtFullBath",
    "BsmtHalfBath",
    "FullBath",
    "HalfBath",
    "BedroomAbvGr",
    "KitchenAbvGr",
    "TotRmsAbvGrd",
    "Fireplaces",
    "GarageCars",
    "GarageArea",
    "WoodDeckSF",
    "OpenPorchSF",
    "EnclosedPorch",
    "3SsnPorch",
    "ScreenPorch",
    "PoolArea",
    "MiscVal",
)

#: Years stored as integers. Routed separately so the feature
#: engineering layer can derive ``HouseAge``, ``RemodAge``,
#: ``GarageAge``.
TEMPORAL_FEATURES: tuple[str, ...] = (
    "YearBuilt",
    "YearRemodAdd",
    "GarageYrBlt",
)

#: Ordered quality / condition scales. Mapping in
#: :data:`hou53_ml.constants.QUALITY_ORDER` (NA -> 0 .. Ex -> 5).
ORDINAL_QUALITY_FEATURES: tuple[str, ...] = (
    "ExterQual",
    "ExterCond",
    "BsmtQual",
    "BsmtCond",
    "HeatingQC",
    "KitchenQual",
    "FireplaceQu",
    "GarageQual",
    "GarageCond",
    "PoolQC",
)

#: Other ordered scales with dataset-specific level orderings (not the
#: Ex/Gd/TA/Fa/Po/NA scale). Encoded with explicit category orderings
#: in Phase 2.
ORDINAL_OTHER_FEATURES: tuple[str, ...] = (
    "LotShape",  # Reg > IR1 > IR2 > IR3
    "LandSlope",  # Gtl > Mod > Sev
    "BsmtExposure",  # Gd > Av > Mn > No > NA
    "BsmtFinType1",  # GLQ > ALQ > BLQ > Rec > LwQ > Unf > NA
    "BsmtFinType2",
    "GarageFinish",  # Fin > RFn > Unf > NA
    "PavedDrive",  # Y > P > N
    "Functional",  # Typ > Min1 > Min2 > Mod > Maj1 > Maj2 > Sev > Sal
    "Fence",  # GdPrv > MnPrv > GdWo > MnWw > NA
    "OverallQual",  # 1..10 (already numeric, semantically ordinal)
    "OverallCond",  # 1..10
)

#: Unordered nominals. One-hot encoded in Phase 2.
NOMINAL_FEATURES: tuple[str, ...] = (
    "MSZoning",
    "Street",
    "Alley",
    "LandContour",
    "Utilities",
    "LotConfig",
    "Neighborhood",
    "Condition1",
    "Condition2",
    "BldgType",
    "HouseStyle",
    "RoofStyle",
    "RoofMatl",
    "Exterior1st",
    "Exterior2nd",
    "MasVnrType",
    "Foundation",
    "Heating",
    "CentralAir",
    "Electrical",
    "GarageType",
    "MiscFeature",
    "SaleType",
    "SaleCondition",
    # Numeric-on-disk codes that are categories (see NUMERIC_BUT_CATEGORICAL).
    "MSSubClass",
    "MoSold",
    "YrSold",
)


@dataclass(frozen=True, slots=True)
class Schema:
    """Typed view over the dataset's columns by role.

    Construct with :meth:`default` to get the documented schema. Tests
    can build ad-hoc schemas with the constructor when they need to
    exercise edge cases.
    """

    target: str
    id_column: str
    numeric: tuple[str, ...]
    temporal: tuple[str, ...]
    ordinal_quality: tuple[str, ...]
    ordinal_other: tuple[str, ...]
    nominal: tuple[str, ...]

    # --- Constructors --------------------------------------------------------
    @classmethod
    def default(cls) -> Schema:
        """Return the schema for the curated 79-feature Ames distribution."""
        return cls(
            target=TARGET,
            id_column=ID_COLUMN,
            numeric=NUMERIC_FEATURES,
            temporal=TEMPORAL_FEATURES,
            ordinal_quality=ORDINAL_QUALITY_FEATURES,
            ordinal_other=ORDINAL_OTHER_FEATURES,
            nominal=NOMINAL_FEATURES,
        )

    # --- Derived views -------------------------------------------------------
    @property
    def all_features(self) -> tuple[str, ...]:
        """Every modelling column, in deterministic order.

        Order: numeric → temporal → ordinal_quality → ordinal_other → nominal.
        Stable so that ``ColumnTransformer`` outputs are reproducible.
        """
        return (
            *self.numeric,
            *self.temporal,
            *self.ordinal_quality,
            *self.ordinal_other,
            *self.nominal,
        )

    @property
    def categorical_features(self) -> tuple[str, ...]:
        """Quality + other ordinal + nominal — every non-numeric input."""
        return (*self.ordinal_quality, *self.ordinal_other, *self.nominal)

    @property
    def ordinal_features(self) -> tuple[str, ...]:
        """Union of quality and other ordinal scales."""
        return (*self.ordinal_quality, *self.ordinal_other)

    @property
    def expected_columns(self) -> tuple[str, ...]:
        """All columns expected on disk: ``Id`` + features + target."""
        return (self.id_column, *self.all_features, self.target)

    # --- Validation ----------------------------------------------------------
    def assert_covers(self, columns: list[str]) -> None:
        """Assert that the schema accounts for every column in ``columns``.

        Raises:
            ValueError: If columns are present on disk but missing from
                the schema, or vice versa. The error message names the
                offending columns so the failure is actionable.
        """
        on_disk = set(columns)
        in_schema = set(self.expected_columns)
        unknown_on_disk = on_disk - in_schema
        missing_on_disk = in_schema - on_disk

        if unknown_on_disk or missing_on_disk:
            parts = []
            if unknown_on_disk:
                parts.append(f"on disk but not in schema: {sorted(unknown_on_disk)}")
            if missing_on_disk:
                parts.append(f"in schema but not on disk: {sorted(missing_on_disk)}")
            msg = "Schema mismatch — " + "; ".join(parts)
            raise ValueError(msg)


__all__ = [
    "ID_COLUMN",
    "NOMINAL_FEATURES",
    "NUMERIC_FEATURES",
    "ORDINAL_OTHER_FEATURES",
    "ORDINAL_QUALITY_FEATURES",
    "QUALITY_ORDER",
    "TEMPORAL_FEATURES",
    "Schema",
]
