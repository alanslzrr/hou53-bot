"""Stateless EDA helpers.

Each function takes a DataFrame (or column) and returns a small dataclass
or a typed pandas object. No plotting, no I/O, no side effects — that
keeps them trivial to test and equally usable from the notebook, from
Phase-2 sanity checks, and from a future drift-monitoring job.

Design rules:

- **One function, one question.** ``missing_summary`` answers "how missing
  is each column"; ``target_summary`` answers "is the target skewed"; etc.
- **Return typed values.** Either a pandas object with a documented
  schema, or a frozen dataclass. Tuples-of-floats invite confusion six
  months from now.
- **Cheap.** Every function here runs on the full 1,460-row Ames frame in
  well under a second. Anything heavier belongs in ``evaluation`` or in
  the notebook with explicit caching.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from hou53_ml.constants import NA_AS_CATEGORY


# -----------------------------------------------------------------------------
# Missing values
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class MissingSummary:
    """Per-column missingness, partitioned by semantic kind.

    Attributes:
        per_column: One row per column with ``n_missing``, ``pct_missing``,
            and ``kind`` ∈ {``"actual"``, ``"legit_na"``,
            ``"complete"``}. Sorted by ``pct_missing`` descending.
        total_cells: Total cells in the input frame (rows x cols).
        total_missing_actual: Sum of *actual* missing values (excludes
            legit-NA categoricals that have already been filled with
            ``"NA"`` by the loader).
    """

    per_column: pd.DataFrame
    total_cells: int
    total_missing_actual: int

    @property
    def actual_pct(self) -> float:
        """Fraction of cells that are genuinely missing, in ``[0, 1]``."""
        if self.total_cells == 0:
            return 0.0
        return self.total_missing_actual / self.total_cells


def missing_summary(frame: pd.DataFrame) -> MissingSummary:
    """Build a per-column missingness report.

    A column's *kind* is:
      - ``"legit_na"`` if it is in :data:`NA_AS_CATEGORY` — these are
        columns where the loader has converted what looks like missing to
        the explicit category ``"NA"`` (e.g., ``PoolQC="NA"`` means "no
        pool"). They are listed for transparency but should not drive
        imputation decisions.
      - ``"actual"`` if it is not in :data:`NA_AS_CATEGORY` and has at
        least one ``NaN``.
      - ``"complete"`` if it has no ``NaN``.

    Args:
        frame: The dataset, post-load. Assumes the loader's NA convention
            has already been applied (legit-NA cells filled with the
            string ``"NA"``).

    Returns:
        A :class:`MissingSummary` whose ``per_column`` frame has columns
        ``column``, ``n_missing``, ``pct_missing``, ``kind``.
    """
    n_missing = frame.isna().sum()
    pct_missing = (n_missing / max(len(frame), 1)).astype(float)

    def _kind(col: str) -> str:
        if col in NA_AS_CATEGORY:
            return "legit_na"
        if n_missing[col] > 0:
            return "actual"
        return "complete"

    per_column = pd.DataFrame(
        {
            "column": frame.columns,
            "n_missing": n_missing.to_numpy(),
            "pct_missing": pct_missing.to_numpy(),
            "kind": [_kind(c) for c in frame.columns],
        }
    ).sort_values(["pct_missing", "column"], ascending=[False, True])
    per_column = per_column.reset_index(drop=True)

    actual_mask = per_column["kind"].eq("actual")
    total_missing_actual = int(per_column.loc[actual_mask, "n_missing"].sum())

    return MissingSummary(
        per_column=per_column,
        total_cells=int(frame.size),
        total_missing_actual=total_missing_actual,
    )


# -----------------------------------------------------------------------------
# Target
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class TargetSummary:
    """Distributional stats for the regression target.

    Attributes:
        n: Number of non-null observations.
        mean: Arithmetic mean.
        median: 50th percentile.
        std: Sample standard deviation.
        min: Minimum value.
        max: Maximum value.
        skew: Sample skewness (Fisher-Pearson). Positive => right tail.
        kurtosis: Excess kurtosis (Fisher's definition).
        log_skew: Skewness of ``log1p(target)``. The headline number for
            justifying the log-transform.
    """

    n: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    skew: float
    kurtosis: float
    log_skew: float


def target_summary(target: pd.Series) -> TargetSummary:
    """Summarise the target distribution and quantify the log-transform gain.

    Args:
        target: Numeric series; ``NaN`` is dropped before computing stats.

    Returns:
        A :class:`TargetSummary`. ``log_skew`` is computed on
        ``log1p(target)`` (the same transform the production pipeline
        applies via :class:`sklearn.compose.TransformedTargetRegressor`).

    Raises:
        ValueError: If ``target`` is empty after dropping ``NaN`` or
            contains negative values (``log1p`` requires ``> -1``).
    """
    series = pd.to_numeric(target, errors="coerce").dropna()
    if series.empty:
        msg = "target_summary received an empty series"
        raise ValueError(msg)
    if (series < 0).any():
        msg = "target_summary requires non-negative values for log1p"
        raise ValueError(msg)

    return TargetSummary(
        n=int(series.size),
        mean=float(series.mean()),
        median=float(series.median()),
        std=float(series.std(ddof=1)),
        min=float(series.min()),
        max=float(series.max()),
        skew=float(series.skew()),
        kurtosis=float(series.kurtosis()),
        log_skew=float(np.log1p(series).skew()),
    )


# -----------------------------------------------------------------------------
# Numeric skew
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SkewSummary:
    """Per-column skewness with a recommendation flag.

    Attributes:
        per_column: ``column``, ``skew``, ``abs_skew``, ``recommend_log``.
            Sorted by ``abs_skew`` descending.
        threshold: The ``abs_skew`` threshold used to flag columns.
    """

    per_column: pd.DataFrame
    threshold: float

    @property
    def to_log_transform(self) -> list[str]:
        """Columns where ``abs_skew`` exceeds the threshold."""
        return [
            str(column)
            for column in self.per_column.loc[self.per_column["recommend_log"], "column"].tolist()
        ]


def numeric_skew(
    frame: pd.DataFrame,
    columns: list[str] | tuple[str, ...] | None = None,
    *,
    threshold: float = 0.75,
) -> SkewSummary:
    """Rank numeric columns by skewness and recommend log-transforms.

    The 0.75 default mirrors a common convention from Ames Housing
    notebooks (Pedregosa-style preprocessing tutorials). Anything beyond
    that benefits enough from a ``log1p`` transform that the bias of the
    XGBoost trees on the heavy tail outweighs the small cost of the
    transform.

    Non-numeric columns and columns with all-zero variance are dropped
    silently.

    Args:
        frame: The dataset.
        columns: Subset of columns to consider. Defaults to every numeric
            column in ``frame``.
        threshold: ``abs(skew)`` cutoff for the recommendation flag.

    Returns:
        A :class:`SkewSummary`.
    """
    candidates = list(columns) if columns is not None else list(frame.select_dtypes("number"))
    candidates = [c for c in candidates if c in frame.columns]

    rows = []
    for col in candidates:
        series = pd.to_numeric(frame[col], errors="coerce").dropna()
        if series.empty or series.nunique() <= 1:
            continue
        skew = float(series.skew())
        rows.append(
            {
                "column": col,
                "skew": skew,
                "abs_skew": abs(skew),
                "recommend_log": abs(skew) > threshold,
            }
        )
    per_column = pd.DataFrame(rows).sort_values("abs_skew", ascending=False, ignore_index=True)
    return SkewSummary(per_column=per_column, threshold=threshold)


# -----------------------------------------------------------------------------
# Categorical cardinality
# -----------------------------------------------------------------------------
def categorical_cardinality(
    frame: pd.DataFrame,
    columns: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Report cardinality and dominance for categorical-ish columns.

    Reports per column ``n_unique``, the most-common value
    (``top_value``), and the share of rows it covers (``top_pct``). A
    high ``top_pct`` means the column is near-constant and probably
    useless to the model — those are good candidates for dropping or for
    rare-level grouping.

    Args:
        frame: The dataset.
        columns: Subset to consider. Defaults to ``object`` /
            ``string`` / ``category`` dtypes plus any column whose dtype
            is numeric but whose semantics are categorical.

    Returns:
        A DataFrame indexed 0..N-1 with columns ``column``, ``n_unique``,
        ``top_value``, ``top_pct``. Sorted by ``top_pct`` descending so
        the most-degenerate columns surface first.
    """
    if columns is None:
        candidates = list(frame.select_dtypes(include=["object", "string", "category"]))
    else:
        candidates = [c for c in columns if c in frame.columns]

    rows = []
    n_rows = len(frame)
    for col in candidates:
        series = frame[col].dropna()
        if series.empty:
            continue
        counts = series.value_counts(dropna=False)
        top_value = counts.index[0]
        rows.append(
            {
                "column": col,
                "n_unique": int(series.nunique(dropna=False)),
                "top_value": top_value,
                "top_pct": float(counts.iloc[0] / max(n_rows, 1)),
            }
        )
    return pd.DataFrame(rows).sort_values("top_pct", ascending=False, ignore_index=True)


# -----------------------------------------------------------------------------
# Correlations with target
# -----------------------------------------------------------------------------
def correlation_with_target(
    frame: pd.DataFrame,
    target: str,
    *,
    method: str = "pearson",
    top_k: int | None = None,
) -> pd.Series:
    """Rank numeric features by ``|corr(feature, target)|``.

    Args:
        frame: The dataset (must contain ``target``).
        target: Name of the target column.
        method: One of ``"pearson"``, ``"spearman"``, ``"kendall"`` —
            forwarded to :meth:`pandas.DataFrame.corr`.
        top_k: If given, return only the top ``k`` features.

    Returns:
        A series indexed by feature name, sorted by absolute correlation
        descending. The target itself is excluded from the result.

    Raises:
        KeyError: If ``target`` is not in ``frame``.
    """
    if target not in frame.columns:
        raise KeyError(f"target column {target!r} not in frame")

    numeric = frame.select_dtypes("number").copy()
    if target not in numeric.columns:
        # Target stored as string; coerce.
        numeric[target] = pd.to_numeric(frame[target], errors="coerce")

    corr = numeric.corr(method=method)[target].drop(labels=[target])
    ranked = corr.reindex(corr.abs().sort_values(ascending=False).index)
    return ranked.head(top_k) if top_k else ranked


# -----------------------------------------------------------------------------
# Outliers
# -----------------------------------------------------------------------------
def outlier_mask(
    series: pd.Series,
    *,
    threshold: float | None = None,
    iqr_multiplier: float | None = 3.0,
) -> pd.Series:
    """Boolean mask of outliers in ``series``.

    Either ``threshold`` (an absolute upper bound) or ``iqr_multiplier``
    (Tukey-style fences using the inter-quartile range) must be given.
    When both are given, ``threshold`` wins.

    Args:
        series: Numeric series.
        threshold: If given, anything ``> threshold`` is an outlier. Used
            for documented domain rules (e.g., ``GrLivArea > 4000`` per
            De Cock 2011).
        iqr_multiplier: If given (and ``threshold`` is not), uses
            ``Q3 + multiplier * IQR`` as the upper fence and
            ``Q1 - multiplier * IQR`` as the lower fence.

    Returns:
        Boolean series aligned to ``series`` (True = outlier).
    """
    numeric = pd.to_numeric(series, errors="coerce")

    if threshold is not None:
        return numeric > threshold

    if iqr_multiplier is None:
        msg = "outlier_mask requires either `threshold` or `iqr_multiplier`"
        raise ValueError(msg)

    q1, q3 = numeric.quantile([0.25, 0.75])
    iqr = q3 - q1
    upper = q3 + iqr_multiplier * iqr
    lower = q1 - iqr_multiplier * iqr
    return (numeric < lower) | (numeric > upper)
