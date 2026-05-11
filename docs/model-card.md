# Model Card — HOU53-bot

> Model cards (Mitchell et al., 2019) are short documents that describe a
> trained model's intended use, its evaluation, and its known limitations.
> Fields marked **TBD** are filled in at the end of Phase 3 when the first
> production artifact is committed.

## Model details

- **Name:** `hou53-pipeline`
- **Version:** TBD (see `models/model_metadata.json`)
- **Type:** Regression
- **Algorithm:** XGBoost regressor wrapped in a scikit-learn `Pipeline`,
  with a `TransformedTargetRegressor` applying `log1p` to `SalePrice`.
- **Baseline compared against:** Ridge regression with the same preprocessor.
- **Training date:** TBD
- **Training dataset hash (DVC):** TBD
- **Framework versions:** scikit-learn `>=1.8`, XGBoost `>=3.2`, Python 3.14.
- **License:** MIT (same as the repository)

## Intended use

- **Primary use case:** Estimating the sale price of a single-family home
  in Ames, Iowa, given its structural and locational attributes as
  described by the dataset schema.
- **Primary users:** Educational users of the NTT Data challenge and,
  internally, the reviewers evaluating the submission.
- **Out-of-scope uses:**
  - Appraisals outside Ames, Iowa or outside the 2006–2010 time window —
    the dataset does not cover them and the model will extrapolate poorly.
  - Any automated decision that materially affects a person (mortgage
    qualification, tax assessment, forced sale). The model is an
    **estimate**, not a substitute for a licensed appraiser.
  - Commercial or multi-family properties.

## Training data

- **Source:** [Ames Housing](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques)
  (Dean De Cock, 2011). Adaptation from
  [Inria's scikit-learn MOOC](https://inria.github.io/scikit-learn-mooc/python_scripts/datasets_ames_housing.html).
- **Size:** ~1,460 training rows, 79 features (mixed numeric/categorical),
  1 target (`SalePrice`).
- **Known biases:**
  - Geography: Ames, Iowa only. Do not generalize to other cities.
  - Time: 2006–2010 sales. Macroeconomic conditions then are not now.
  - Socioeconomics: neighborhood is a strong predictor in this data,
    which can encode historical patterns that do not match fair-housing
    expectations for a *deployed* product. Flagged here; mitigated
    (partially) by making per-prediction SHAP attributions visible to
    the user.

## Preprocessing

- Legitimate-NA categoricals (e.g., `PoolQC="NA"` → "no pool") are kept
  as categories, not imputed.
- Quality scales (`Ex/Gd/TA/Fa/Po`) ordinally encoded `NA=0 .. Ex=5`.
- Numeric-but-categorical columns (`MSSubClass`, `MoSold`, `YrSold`)
  treated as categories.
- `log1p` on skewed numeric features with skew > 0.75.
- `log1p` on the target inside a `TransformedTargetRegressor`.
- `GrLivArea > 4000` rows dropped (partial sales; per De Cock 2011).
- `Neighborhood` target-encoded with out-of-fold leakage protection.

## Evaluation

- **Primary metric:** RMSE on `log1p(SalePrice)`.
- **Split:** Stratified 80/20 on quintiles of `SalePrice`.
- **Cross-validation:** 5-fold KFold, `shuffle=True`, `random_state=42`.
- **Reported:** CV mean ± std (primary) + held-out test (headline).

### Results

| Metric | Baseline (Ridge) | Production (XGBoost) |
|---|---|---|
| RMSE log (CV mean) | TBD | TBD |
| RMSE log (test) | TBD | TBD |
| MAE $ (test) | TBD | TBD |
| R² (test) | TBD | TBD |

## Explainability

Every prediction returns:

- The predicted `SalePrice` in dollars.
- The top-K (default 5) contributing features with their SHAP values,
  expressed both numerically and as a natural-language sentence ("being
  in Neighborhood X raised the estimate by ~$12k").
- A confidence interval (method TBD — see
  [architecture.md](./architecture.md#what-will-change-later-known-unknowns)).

The SHAP background set is a representative sample of training rows,
stored alongside the model artifact.

## Ethical considerations

- Explanations reveal **correlations, not causes**. A SHAP attribution
  that says "Neighborhood X raised the estimate" is a statement about
  this dataset, not a claim that a house *should* be more expensive
  because of its neighborhood.
- The challenge rubric includes explainability precisely because
  black-box pricing models are harmful when deployed without scrutiny.
  We surface the signals the model relied on so that a human can notice
  when the model is picking up on something it should not.

## Caveats and recommendations

- Predictions outside the feature ranges seen in training should be
  flagged. The API performs bounds checks and returns a warning when the
  input sits outside the 1st–99th percentile of training on any
  numeric field.
- Expect a natural floor on accuracy: cheap houses are harder to price
  precisely because transaction prices are noisier at the low end.

## Citations

- De Cock, D. (2011). *Ames, Iowa: Alternative to the Boston Housing
  Data as an End of Semester Regression Project.*
  [JSE 19(3)](https://jse.amstat.org/v19n3/decock.pdf).
- Mitchell, M. et al. (2019). *Model Cards for Model Reporting.* FAT* '19.
