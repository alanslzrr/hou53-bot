# EDA Report — Ames Housing (HOU53-bot)

> Authoritative summary of Phase 1 findings. The notebook
> [`ml/notebooks/01_eda.py`](../../ml/notebooks/01_eda.py) is the
> scratchpad; this file is what Phase-2 code and reviewers read.
> Numbers below were captured from `data/raw/house_prices.csv` via the
> tested helpers in `hou53_ml.eda.summary`.

## 1. Dataset shape

| What | Value |
|---|---|
| Rows | **1,460** |
| Columns | **81** (Id + 79 features + `SalePrice`) |
| Dtypes on disk | 32 `int64`, 28 `object`, 18 `string` (loader-assigned), 3 `float64` |
| Total cells | 118,260 |

The Inria-curated distribution uses the dual-marker convention noted in
their MOOC: `?` is an actual missing value, while the literal string
`"NA"` (when present) is a legitimate categorical level. Our loader
honors this and stays bit-for-bit deterministic between training and
serving — see `hou53_ml.io.loaders.AmesHousingLoader`.

## 2. Target — `SalePrice`

| Statistic | Value |
|---|---|
| n | 1,460 |
| mean | **$180,921** |
| median | $163,000 |
| std | $79,443 |
| min | $34,900 |
| max | $755,000 |
| skew (raw) | **+1.883** |
| kurtosis | 6.536 |
| skew of `log1p(SalePrice)` | **+0.121** |

**Decision.** The target is strongly right-skewed. Training with
`log1p(SalePrice)` reduces skew by 15×, which means an XGBoost
trained on the log target optimizes proportional error (the same
behavior as the Kaggle leaderboard metric). The transform lives inside
the pipeline via `TransformedTargetRegressor(func=np.log1p,
inverse_func=np.expm1)` so the API never sees log dollars. See
[ADR-0007](../adr/0007-evaluation-metric-rmse-log.md).

## 3. Missing values

The dataset is much cleaner than the Kaggle original once the
`?`/`NA` convention is honored.

### Actual-missing columns (only 4 of 79)

| Column | n_missing | % |
|---|---:|---:|
| LotFrontage | 259 | 17.74% |
| GarageYrBlt | 81 | 5.55% |
| MasVnrArea | 8 | 0.55% |
| Electrical | 1 | 0.07% |

**Total cells missing: 349 / 118,260 = 0.295%.**

### Legit-NA columns (15)

`Alley`, `BsmtCond`, `BsmtExposure`, `BsmtFinType1`, `BsmtFinType2`,
`BsmtQual`, `Fence`, `FireplaceQu`, `GarageCond`, `GarageFinish`,
`GarageQual`, `GarageType`, `MasVnrType`, `MiscFeature`, `PoolQC`.

These are already filled with the string `"NA"` by the loader. They
are categorical features, **not** missingness, and we encode them
accordingly in Phase 2.

### Imputation strategy (Phase 2)

| Column | Strategy | Why |
|---|---|---|
| LotFrontage | Median within `Neighborhood`, fallback global median | Frontage is local; same-neighborhood medians are stronger than one global value |
| GarageYrBlt | Median-impute raw year + derived `GarageAge=0` / `HasGarage=0` for absent garages | Keeps the raw year usable while the derived features carry the absence signal |
| MasVnrArea | Median-impute before `log1p` | Only 8 rows missing; `MasVnrType` still carries the absence/category signal |
| Electrical | Constant categorical imputation (`"missing"`) before one-hot | Only one row; preserving explicit missingness is simpler than mode overwrite |

## 4. Numeric features — skewness

Run on the 28 numeric features declared in `Schema.numeric`.

**20 of 28** features have `|skew| > 0.75` and will be `log1p`'d.

| Column | Skew |
|---|---:|
| MiscVal | 24.48 |
| PoolArea | 14.83 |
| LotArea | 12.21 |
| 3SsnPorch | 10.30 |
| LowQualFinSF | 9.01 |
| KitchenAbvGr | 4.49 |
| BsmtFinSF2 | 4.26 |
| ScreenPorch | 4.12 |
| BsmtHalfBath | 4.10 |
| EnclosedPorch | 3.09 |
| MasVnrArea | 2.67 |
| OpenPorchSF | 2.36 |
| _… 8 more above 0.75_ | |

The log transform is applied **per column**, not globally, so columns
that are already well-behaved (e.g., `BedroomAbvGr`) are left alone.

## 5. Numeric features — correlation with `SalePrice` (top 15)

| Rank | Feature | Pearson r |
|---:|---|---:|
| 1 | OverallQual | 0.791 |
| 2 | GrLivArea | 0.709 |
| 3 | GarageCars | 0.640 |
| 4 | GarageArea | 0.623 |
| 5 | TotalBsmtSF | 0.614 |
| 6 | 1stFlrSF | 0.606 |
| 7 | FullBath | 0.561 |
| 8 | TotRmsAbvGrd | 0.534 |
| 9 | YearBuilt | 0.523 |
| 10 | YearRemodAdd | 0.507 |
| 11 | GarageYrBlt | 0.486 |
| 12 | MasVnrArea | 0.477 |
| 13 | Fireplaces | 0.467 |
| 14 | BsmtFinSF1 | 0.386 |
| 15 | LotFrontage | 0.352 |

`OverallQual` alone explains ~63% of variance in `SalePrice`. The
`SHAP` attribution view in the API will need to surface this — for many
predictions, `OverallQual` will dominate the explanation.

## 6. Multicollinearity (top pairs)

| Pair | Pearson r |
|---|---:|
| `GarageCars` ↔ `GarageArea` | 0.882 |
| `YearBuilt` ↔ `GarageYrBlt` | 0.826 |
| `GrLivArea` ↔ `TotRmsAbvGrd` | 0.825 |
| `TotalBsmtSF` ↔ `1stFlrSF` | 0.820 |
| `OverallQual` ↔ `GrLivArea` | 0.593 |

**Decision.** We do **not** drop any of these. XGBoost handles
collinearity gracefully; dropping would lose information.
Implications:

- We will **not** compute Phase-2 SHAP values on a "decorrelated"
  representation — SHAP attributions split contribution across
  correlated features in a known way (see Lundberg's writings) and
  surfacing that to the user is acceptable.
- The engineered `TotalSF` feature is **redundant** with its three
  components on linear models — but trees pick the most-useful split
  and ignore the rest, so the redundancy is harmless.

## 7. Categorical features

### Near-constant (dominance > 90%)

| Column | n_unique | top_value | top % |
|---|---:|---|---:|
| Utilities | 2 | AllPub | **99.93%** |
| Street | 2 | Pave | 99.59% |
| Condition2 | 8 | Norm | 98.97% |
| RoofMatl | 8 | CompShg | 98.22% |
| Heating | 6 | GasA | 97.81% |
| LandSlope | 3 | Gtl | 94.66% |
| CentralAir | 2 | Y | 93.49% |

`Utilities` is effectively a constant. We will **keep** it for now
(XGBoost will ignore it) but note it as a candidate to drop if model
size becomes a constraint.

### High-cardinality target-encoding signal

| Column | n_unique |
|---|---:|
| Neighborhood | **25** |
| Exterior2nd | 16 |
| Exterior1st | 15 |
| MSSubClass | 15 |
| MoSold | 12 |

`Neighborhood` shows a **3.4×** spread in mean `SalePrice` between
top and bottom levels:

| Top | mean | | Bottom | mean |
|---|---:|---|---|---:|
| NoRidge | $335,295 | | MeadowV | $98,576 |
| NridgHt | $316,271 | | IDOTRR | $100,124 |
| StoneBr | $310,499 | | BrDale | $104,494 |

We now target-encode `Neighborhood` inside the sklearn pipeline as
`NeighborhoodPriceLog`, so each CV fold learns the mapping only from
its training slice. The raw `Neighborhood` column is still one-hot
encoded, giving XGBoost both the smoothed price prior and the original
category identity.

## 8. Outliers

De Cock (2011) recommends dropping rows where `GrLivArea > 4000`. Our
data has **four** such rows:

| Id | GrLivArea | SalePrice | SaleCondition | OverallQual |
|---:|---:|---:|---|---:|
| 524 | 4,676 | $184,750 | **Partial** | 10 |
| 692 | 4,316 | $755,000 | Normal | 10 |
| 1183 | 4,476 | $745,000 | Abnorml | 10 |
| 1299 | 5,642 | $160,000 | **Partial** | 10 |

**Decision.** Drop the two low-price, very-large rows (524 and 1299)
before the train/test split. These are non-market sales and make both
model fitting and held-out evaluation noisier. The `Normal` and
`Abnorml` luxury rows are kept; their prices are genuine, just rare.

Outliers are filtered in `training.splits.make_split`, not notebook-side,
so cross-validation and artifact training use the same documented rule.

## 9. Temporal features

| Field | Range |
|---|---|
| `YearBuilt` | 1872–2010 (138 years) |
| `YearRemodAdd` | 1950–2010 |
| `YrSold` | 2006–2010 (covers the housing crisis) |
| `YrSold − YearBuilt` (HouseAge) | 0–136 (mean ≈ 37) |

**Engineered features:**

- `HouseAge = YrSold - YearBuilt`
- `RemodAge = YrSold - YearRemodAdd`
- `GarageAge = max(0, YrSold - GarageYrBlt)` (clamped because a
  handful of rows have `GarageYrBlt > YrSold` — data-entry errors)
- `HasGarage = GarageYrBlt.notna()` indicator

## 10. Decisions consolidated for Phase 2

Each decision is implemented as a tested transformer under
`hou53_ml.features.*`.

| # | Decision | Where it lives |
|---|---|---|
| 1 | Drop `Id` before modelling | `features.builders.build_preprocessor` |
| 2 | Log1p the target | `pipelines.builders.build_pipeline` |
| 3 | Drop 2 `Partial`-sale outliers from training | `training.train` |
| 4 | Impute `LotFrontage` by neighborhood median | `features.imputation` |
| 5 | Derive 16 structural features (`TotalSF`, bathrooms, flags, quality×area) | `features.derived` |
| 6 | Median impute numerics; constant-impute categoricals | `features.builders` |
| 7 | Ordinal encode quality + ordered categorical scales | `features.ordinal` |
| 8 | Log1p the skewed numerics and selected engineered magnitudes | `features.builders` |
| 9 | Target encode `Neighborhood` fold-safely as `NeighborhoodPriceLog` | `features.target_encoding` |
| 10 | One-hot the remaining nominals | `features.builders` |

The Phase-2 sanity floor is a `Ridge` baseline applied to the same
preprocessor. XGBoost must beat Ridge on CV RMSE-log; the current
artifact does (`0.1167` vs `0.1203`).

## References

- De Cock, D. (2011). *Ames, Iowa: Alternative to the Boston Housing
  Data as an End of Semester Regression Project.*
  [JSE 19(3)](https://jse.amstat.org/v19n3/decock.pdf).
- Inria scikit-learn MOOC — "Ames Housing" dataset notebook.
  [`inria.github.io`](https://inria.github.io/scikit-learn-mooc/python_scripts/datasets_ames_housing.html).
- Kaggle competition — _House Prices: Advanced Regression Techniques_.
