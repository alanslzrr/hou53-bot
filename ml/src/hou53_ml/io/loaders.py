"""Ames Housing CSV loader.

Single source of truth for raw-data loading. Every consumer (EDA
notebook, training pipeline, API fixtures) goes through
``AmesHousingLoader``.

Design constraints:

- Single responsibility: read the CSV + apply the documented NA
  convention. No transformation, splitting, or schema validation
  beyond the contract below.
- Dependency-injected path: ``AmesHousingLoader(csv_path)``. Tests
  pass a ``tmp_path``-resolved CSV; production code passes
  ``Settings.data_raw / "house_prices.csv"``.
- Explicit return contract: :class:`LoadResult` carries the frame
  plus its source path. ``EXPECTED_RAW_SHAPE`` is asserted on load
  to fail loudly if the file shape drifts upstream.

NA convention (curated Ames distribution):

- ``"?"`` → real missing value. Pandas converts to ``NaN`` via
  ``na_values=["?"]``.
- ``"NA"`` (literal string) → categorical level meaning "no
  <feature>" in the columns listed in
  :data:`hou53_ml.constants.NA_AS_CATEGORY`. ``keep_default_na=False``
  prevents pandas from coercing it to ``NaN``; the loader then
  re-fills ``NaN`` with ``"NA"`` for those specific columns so the
  downstream encoder sees a category, not a missing value.

Result: ``LotFrontage=NaN`` (real missing) and ``PoolQC="NA"`` (no
pool) round-trip cleanly with no per-column logic anywhere else.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from hou53_ml.constants import (
    NA_AS_CATEGORY,
    NUMERIC_BUT_CATEGORICAL,
    TARGET,
)

# read_csv kwargs encoding the dataset's NA convention. Centralised so
# any change to the convention happens in one place and tests can assert
# on it.
_RAW_READ_KWARGS: dict[str, object] = {
    "na_values": ["?"],
    "keep_default_na": False,
}

#: Expected raw shape after load. Asserted to surface upstream file
#: changes immediately instead of silently propagating.
EXPECTED_RAW_SHAPE: tuple[int, int] = (1460, 81)


@dataclass(frozen=True, slots=True)
class LoadResult:
    """Container returned by :class:`AmesHousingLoader`.

    Attributes:
        frame: The loaded dataframe with the NA convention applied.
        source: Absolute path the data was read from.
        rows: Number of rows in :attr:`frame`. Convenience accessor.
        columns: Tuple of column names in their on-disk order.
    """

    frame: pd.DataFrame
    source: Path
    rows: int = field(init=False)
    columns: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        # Frozen dataclasses forbid attribute assignment; ``object.__setattr__``
        # is the standard escape hatch for derived fields.
        object.__setattr__(self, "rows", int(self.frame.shape[0]))
        object.__setattr__(self, "columns", tuple(self.frame.columns))


class AmesHousingLoader:
    """Load the curated Ames Housing CSV into a typed DataFrame.

    The loader is intentionally a thin object rather than a free function:
    instances bind a path at construction, which makes them trivial to
    swap in tests (point at a tiny synthetic CSV under ``tmp_path``) and
    makes the dependency on the filesystem explicit.

    Args:
        csv_path: Absolute path to ``house_prices.csv``. Must exist and be
            readable; no inference is done here.
        validate_shape: When ``True`` (default), raises
            :class:`ValueError` if the loaded frame does not match
            :data:`EXPECTED_RAW_SHAPE`. Set to ``False`` only for
            deliberate subset / fixture loading.

    Example:
        >>> from hou53_ml import get_settings
        >>> from hou53_ml.io.loaders import AmesHousingLoader
        >>> loader = AmesHousingLoader(get_settings().data_raw / "house_prices.csv")
        >>> result = loader.load()
        >>> result.frame.shape
        (1460, 81)
    """

    def __init__(self, csv_path: Path, *, validate_shape: bool = True) -> None:
        self._csv_path = Path(csv_path).resolve()
        self._validate_shape = validate_shape

    # --- Public API ----------------------------------------------------------
    @property
    def source(self) -> Path:
        """Absolute path the loader will read from."""
        return self._csv_path

    def load(self) -> LoadResult:
        """Read the CSV and apply the dataset's NA convention.

        Returns:
            :class:`LoadResult`. Its ``frame`` has:
              - ``?`` markers converted to ``NaN``.
              - ``NaN`` re-filled with the string ``"NA"`` for every
                column in :data:`hou53_ml.constants.NA_AS_CATEGORY`.
              - :data:`hou53_ml.constants.NUMERIC_BUT_CATEGORICAL`
                columns coerced to ``string`` dtype so downstream
                encoders treat them as categories, not magnitudes.

        Raises:
            FileNotFoundError: Configured path does not exist.
            ValueError: ``validate_shape=True`` and the loaded frame
                deviates from :data:`EXPECTED_RAW_SHAPE`, or the target
                column is missing.
        """
        if not self._csv_path.is_file():
            msg = f"Ames Housing CSV not found at {self._csv_path}"
            raise FileNotFoundError(msg)

        frame = pd.read_csv(self._csv_path, **_RAW_READ_KWARGS)
        frame = self._apply_na_convention(frame)
        frame = self._coerce_numeric_categoricals(frame)
        self._assert_contract(frame)
        return LoadResult(frame=frame, source=self._csv_path)

    # --- Internal helpers ----------------------------------------------------
    @staticmethod
    def _apply_na_convention(frame: pd.DataFrame) -> pd.DataFrame:
        """Restore ``"NA"`` as a category in legit-NA columns.

        The CSV is read with ``?`` → ``NaN`` and the pandas default NA
        list disabled. Columns in :data:`NA_AS_CATEGORY` document
        ``"NA"`` as the label for "house lacks this feature"; this
        method re-fills their ``NaN`` cells with ``"NA"`` so the
        downstream ordinal / one-hot encoder treats them as a category.

        Only columns present in the input frame are touched, to stay
        forward-compatible if a future curation drops a column.
        """
        cols_present = NA_AS_CATEGORY.intersection(frame.columns)
        if not cols_present:
            return frame
        # Per-column assign to avoid the deprecated ``fillna(downcast=...)``.
        for col in cols_present:
            frame[col] = frame[col].fillna("NA").astype("string")
        return frame

    @staticmethod
    def _coerce_numeric_categoricals(frame: pd.DataFrame) -> pd.DataFrame:
        """Cast ``MSSubClass``/``MoSold``/``YrSold`` to ``string`` dtype.

        These columns are stored as integers but their values are codes
        (``MSSubClass=60`` means "2-Story 1946 & Newer"), not
        magnitudes. Treating them as numeric would invent ordering.
        Coercing to the nullable ``string`` dtype routes them through
        the categorical branch of the downstream encoder.
        """
        cols_present = NUMERIC_BUT_CATEGORICAL.intersection(frame.columns)
        for col in cols_present:
            frame[col] = frame[col].astype("string")
        return frame

    def _assert_contract(self, frame: pd.DataFrame) -> None:
        """Fail loudly when the file deviates from the documented contract."""
        if TARGET not in frame.columns:
            msg = f"Target column {TARGET!r} missing from {self._csv_path}"
            raise ValueError(msg)

        if self._validate_shape and frame.shape != EXPECTED_RAW_SHAPE:
            msg = (
                f"Unexpected shape for {self._csv_path}: got {frame.shape}, "
                f"expected {EXPECTED_RAW_SHAPE}. If this change is intentional, "
                f"update EXPECTED_RAW_SHAPE in hou53_ml.io.loaders and bump "
                f"the model version."
            )
            raise ValueError(msg)
