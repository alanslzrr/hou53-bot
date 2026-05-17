# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 01 — Exploratory Data Analysis: Ames Housing
#
# **Goal of this notebook.** Build a defensible picture of the dataset
# before we touch a single estimator, and use it to justify every
# decision that lands in the Phase-2 preprocessing pipeline.
#
# **Source of truth.** Findings consolidated in
# [`docs/eda/report.md`](../../docs/eda/report.md). This notebook is the
# scratch pad; the markdown report is what reviewers and Phase-2 code
# read.
#
# **Reproducibility.** Every helper used here is a tested function in
# `hou53_ml.eda.summary`. The plots are the only thing this notebook
# owns. If a finding influences the pipeline, the helper that computes
# it is what Phase 2 imports — there is no notebook-only logic.

# %%
from __future__ import annotations

import matplotlib.pyplot as plt
import missingno as msno
import numpy as np
import pandas as pd
import seaborn as sns
from hou53_ml import get_settings
from hou53_ml.constants import (
    GRLIVAREA_OUTLIER_THRESHOLD,
    QUALITY_ORDER,
)
from hou53_ml.eda import (
    categorical_cardinality,
    correlation_with_target,
    missing_summary,
    numeric_skew,
    target_summary,
)
from hou53_ml.features import DerivedFeatures
from hou53_ml.io import AmesHousingLoader, Schema
from hou53_ml.training import documented_outlier_mask
from IPython.display import display

sns.set_theme(style="whitegrid", context="notebook")
pd.set_option("display.max_columns", 100)
pd.set_option("display.width", 140)

# %%
settings = get_settings()
loader = AmesHousingLoader(settings.data_raw / "house_prices.csv")
result = loader.load()
df = result.frame
schema = Schema.default()
schema.assert_covers(list(df.columns))

print(f"shape: {df.shape}")
print(f"loaded from: {result.source}")
print("schema covers dataset: ✓")

# %% [markdown]
# ## 1 — Shape and dtypes

# %%
df.dtypes.value_counts().to_frame("count")

# %%
df.head()

# %% [markdown]
# ## 2 — Target distribution
#
# `SalePrice` is **heavily right-skewed** (skew ≈ 1.88, kurtosis ≈ 6.5).
# Applying `log1p` drops skew to ~0.12 — that single transform is the
# difference between an XGBoost that overweights luxury outliers and one
# that learns proportional error. See ADR-0007.

# %%
ts = target_summary(df["SalePrice"])
pd.Series(
    {
        "n": ts.n,
        "mean": f"${ts.mean:,.0f}",
        "median": f"${ts.median:,.0f}",
        "std": f"${ts.std:,.0f}",
        "min": f"${ts.min:,.0f}",
        "max": f"${ts.max:,.0f}",
        "skew (raw)": round(ts.skew, 3),
        "kurtosis": round(ts.kurtosis, 3),
        "skew (log1p)": round(ts.log_skew, 3),
    }
).to_frame("SalePrice")

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].hist(df["SalePrice"], bins=40, edgecolor="black")
axes[0].set(title="SalePrice (raw)", xlabel="USD")
axes[1].hist(np.log1p(df["SalePrice"]), bins=40, edgecolor="black", color="C1")
axes[1].set(title="log1p(SalePrice)", xlabel="log USD")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 3 — Missing value analysis
#
# The loader has already separated **legit-NA categories** (e.g.,
# `PoolQC="NA"` = no pool) from **actual missing** values. Only 4
# columns have real missingness — the headline is that this dataset is
# remarkably clean once the convention is honored.

# %%
ms = missing_summary(df)
print(
    f"total cells: {ms.total_cells:,}  "
    f"actual missings: {ms.total_missing_actual:,}  "
    f"share: {ms.actual_pct * 100:.3f}%"
)
ms.per_column[ms.per_column["kind"] == "actual"]

# %%
# Legit-NA columns: the loader has converted these to the string "NA".
# Shown here so reviewers see them surfaced.
legit = ms.per_column[ms.per_column["kind"] == "legit_na"]
print(f"{len(legit)} legit-NA columns:")
print(", ".join(legit["column"].tolist()))

# %%
# Missingno matrix — clusters columns by missingness pattern. With only
# 4 actual-missing columns the matrix is mostly white, which is exactly
# what we want to see.
fig, ax = plt.subplots(figsize=(14, 5))
msno.matrix(df[ms.per_column[ms.per_column["kind"] == "actual"]["column"]], ax=ax)
plt.show()

# %% [markdown]
# ### Missingness ↔ price relationship
#
# Sanity check: do houses without a `LotFrontage` value sell for
# different prices than houses with one? The production pipeline does
# **not** add generic `*_missing` indicators; instead it uses
# feature-aware handling:
#
# - `LotFrontage` is filled from the median frontage of the same
#   `Neighborhood`, with a global fallback for unseen neighborhoods.
# - garage absence is represented by `HasGarage` and `GarageAge=0`.
# - low-cardinality categorical missings are preserved as explicit
#   categorical values before encoding.

# %%
df.assign(LotFrontage_recorded=df["LotFrontage"].notna()).groupby("LotFrontage_recorded")[
    "SalePrice"
].agg(["count", "mean", "median"]).round(0)

# %% [markdown]
# ## 4 — Numeric features
#
# Pull out the numeric block (as defined by `Schema`, **not** by
# `dtypes`), report skewness, and recommend log transforms above 0.75.

# %%
sk = numeric_skew(df, columns=schema.numeric, threshold=0.75)
print(
    f"{len(sk.to_log_transform)} of {len(schema.numeric)} numeric features "
    f"flagged for log1p (|skew| > {sk.threshold})"
)
sk.per_column.head(15)

# %%
# Visual sanity check on the top-3 worst offenders.
worst = sk.per_column["column"].head(3).tolist()
fig, axes = plt.subplots(2, len(worst), figsize=(4 * len(worst), 6))
for col, ax_pair in zip(worst, axes.T, strict=True):
    series = df[col].dropna()
    ax_pair[0].hist(series, bins=40, edgecolor="black")
    ax_pair[0].set(title=f"{col} (raw)", xlabel="")
    ax_pair[1].hist(np.log1p(series), bins=40, edgecolor="black", color="C1")
    ax_pair[1].set(title=f"{col} log1p", xlabel="")
plt.tight_layout()
plt.show()

# %% [markdown]
# ### Correlation with `SalePrice`
#
# Ranked by `|Pearson|`. Spearman would be more robust but Pearson is
# the right thing to look at when the next step is feeding XGBoost with
# log-transformed numerics.

# %%
corr_top = correlation_with_target(df, target="SalePrice", top_k=20)
fig, ax = plt.subplots(figsize=(8, 6))
corr_top.sort_values().plot.barh(ax=ax, color="C0")
ax.set(xlabel="Pearson r with SalePrice", title="Top-20 numeric correlations")
plt.tight_layout()
plt.show()

# %% [markdown]
# ### Multicollinearity check
#
# Several pairs are >0.8 correlated. We do **not** drop columns blindly
# — XGBoost is robust to collinearity — but we want to be aware so
# (1) SHAP attributions are interpreted with care and (2) feature
# engineering does not stack near-duplicate signals.

# %%
collin_pairs = [
    ("GarageCars", "GarageArea"),
    ("TotalBsmtSF", "1stFlrSF"),
    ("GrLivArea", "TotRmsAbvGrd"),
    ("YearBuilt", "GarageYrBlt"),
    ("OverallQual", "GrLivArea"),
]
rows = []
for a, b in collin_pairs:
    sub = df[[a, b]].dropna()
    rows.append({"feature_a": a, "feature_b": b, "pearson_r": sub[a].corr(sub[b])})
pd.DataFrame(rows).round(3)

# %% [markdown]
# ## 5 — Categorical features

# %%
cat = categorical_cardinality(df, columns=schema.categorical_features)
print("Most-degenerate (drop / monitor):")
display_degenerate = cat.head(10)
display(display_degenerate)

# %%
print("Highest cardinality (target-encoding candidates):")
cat.sort_values("n_unique", ascending=False).head(10)

# %%
# Neighborhood is the canonical target-encoding candidate: 25 levels,
# strong price signal.
nbh_price = (
    df.groupby("Neighborhood")["SalePrice"]
    .agg(["count", "mean"])
    .round(0)
    .sort_values("mean", ascending=False)
)
print(
    f"{nbh_price.index.nunique()} neighborhoods, "
    f"price range {nbh_price['mean'].max() / nbh_price['mean'].min():.1f}x"
)
nbh_price.head(8)

# %%
# Ordered ordinal scale (Ex/Gd/TA/Fa/Po/NA). Bar plot showing the
# mean SalePrice per level for the headline quality features.
quality_cols = ["ExterQual", "KitchenQual", "BsmtQual", "HeatingQC"]
order = list(QUALITY_ORDER.keys())[::-1]  # NA -> Ex
fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharey=True)
for col, ax in zip(quality_cols, axes.ravel(), strict=True):
    means = df.groupby(col)["SalePrice"].mean().reindex(order)
    ax.bar(means.index, means.values, color="C2")
    ax.set(title=col, xlabel="", ylabel="mean SalePrice")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 6 — Outliers
#
# De Cock (2011) flags very large homes sold for unusually low prices.
# The production rule removes rows with `GrLivArea > 4000` and
# `SalePrice < $300k` before the train/test split. The rule is based
# on size and price, not on the `SaleCondition` label.

# %%
large_area = df["GrLivArea"] > GRLIVAREA_OUTLIER_THRESHOLD
documented = documented_outlier_mask(df)
df.loc[
    large_area,
    ["Id", "GrLivArea", "SalePrice", "SaleCondition", "OverallQual"],
].assign(documented_outlier=large_area & documented)

# %% [markdown]
# Four rows are above 4000 ft². The two under $300k are clearly
# mispriced relative to size and are removed before splitting. The
# high-price large homes are legitimate luxury examples and stay in
# the dataset.

# %% [markdown]
# ## 7 — Production feature candidates
#
# Years, areas, quality, and presence/absence fields combine into
# stronger buyer-facing signals than their raw columns alone. The
# production pipeline implements these as `DerivedFeatures`, so this
# notebook previews the same transformer rather than duplicating the
# formulas in a notebook-only cell.

# %%
yr_sold = pd.to_numeric(df["YrSold"], errors="coerce")
age_preview = pd.DataFrame(
    {
        "HouseAge": yr_sold - df["YearBuilt"],
        "RemodAge": yr_sold - df["YearRemodAdd"],
        "GarageAge": yr_sold - df["GarageYrBlt"],
    }
)
print(f"YearBuilt range: {df['YearBuilt'].min()}-{df['YearBuilt'].max()}")
print(f"YrSold range:    {yr_sold.min()}-{yr_sold.max()}")
age_preview.describe().round(2)

# %% [markdown]
# Two pathologies handled by `DerivedFeatures`:
#
# 1. `GarageYrBlt` is `NaN` for houses without a garage → `GarageAge`
#    is set to `0` and paired with `HasGarage=0`.
# 2. A handful of `GarageYrBlt` values exceed `YrSold` (data-entry
#    errors). The age becomes negative — clamp to ≥ 0 in feature
#    engineering.

# %%
neg_garage = age_preview[age_preview["GarageAge"] < 0]
print(f"rows with negative GarageAge (data error): {len(neg_garage)}")
display(neg_garage)

# %%
raw_features = df.drop(columns=["SalePrice"])
derived_frame = DerivedFeatures().fit_transform(raw_features)
derived_cols = [c for c in derived_frame.columns if c not in raw_features.columns]
derived_corr = correlation_with_target(
    pd.concat([derived_frame[derived_cols], df["SalePrice"]], axis=1),
    target="SalePrice",
)
derived_corr.to_frame("pearson_r").round(3)

# %% [markdown]
# ## 8 — Summary of decisions for Phase 2
#
# These are the concrete preprocessing steps justified by the analysis
# above and implemented in `hou53_ml`:
#
# 1. **Drop `Id`** before modelling.
# 2. **Log1p the target** inside a `TransformedTargetRegressor` (skew
#    1.88 → 0.12).
# 3. **Drop 2 documented non-market outliers** before the split
#    (`GrLivArea > 4000` and `SalePrice < $300k`).
# 4. **Impute `LotFrontage` by `Neighborhood` median**, with a global
#    median fallback for unseen neighborhoods.
# 5. **Add structural derived features**: ages, total areas, bathrooms,
#    porch area, presence flags, and `OverallQual x area` interactions.
# 6. **Impute** numerics with the median and categoricals with explicit
#    constant values before encoding.
# 7. **Ordinal-encode** quality scales and ordered non-quality scales
#    (`BsmtExposure`, `Functional`, `GarageFinish`, etc.).
# 8. **Log1p-transform** skewed numeric columns and selected engineered
#    magnitudes.
# 9. **Target-encode** `Neighborhood` fold-safely as
#    `NeighborhoodPriceLog`.
# 10. **One-hot encode** the remaining unordered nominals.
#
# The validation strategy (5-fold CV, stratified 80/20 hold-out by
# `SalePrice` quintiles) is captured in ADR-0007 and lives in
# `hou53_ml.training.train`.
