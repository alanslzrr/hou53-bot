# Model Card — HOU53-bot

> Model cards (Mitchell et al., 2019) describe a trained model's intended
> use, evaluation, and known limitations. This file is regenerated each
> time the artifact under `models/` changes.

## Model details

- **Name:** `hou53-pipeline`
- **Current artifact:** `models/hou53-pipeline.joblib`
- **Production estimator:** **XGBoost** (`XGBRegressor`, defaults from
  `hou53_ml.models.boosting.DEFAULT_PARAMS`).
- **Baseline compared against:** Ridge with the same preprocessor
  (numbers below). Each retrain runs both, logs both to MLflow, and
  emits a warning if XGBoost loses on CV by more than the noise floor.
- **Algorithm:** scikit-learn `Pipeline` =
  `NeighborhoodLotFrontageImputer → DerivedFeatures →
  NeighborhoodTargetEncoder → ColumnTransformer (impute + log +
  ordinal + one-hot) → XGBRegressor`, wrapped in
  `TransformedTargetRegressor(func=np.log1p, inverse_func=np.expm1)`.
- **Encoded feature count after preprocessing:** **237**. Explicit
  ordinal encodings reduce one-hot width while engineered features add
  structural signal.
- **Training date:** captured in `models/model_metadata.json`
  (`trained_at_utc` field).
- **Training dataset hash:** SHA-256 over `data/raw/house_prices.csv`,
  in the same JSON.
- **Framework versions:** scikit-learn 1.8.0, XGBoost 3.2.0,
  Python 3.14.5.
- **License:** MIT (same as the repository).

## Intended use

- **Primary use case:** Estimating the sale price of a single-family
  home in Ames, Iowa, given its structural and locational attributes
  as described by the dataset schema.
- **Primary users:** Educational users of the NTT Data challenge and,
  internally, the reviewers evaluating the submission.
- **Out-of-scope uses:**
  - Appraisals outside Ames, Iowa or outside the 2006–2010 time window.
  - Any automated decision that materially affects a person.
  - Commercial or multi-family properties.

## Training data

- **Source:** [Ames Housing](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques)
  (Dean De Cock, 2011), as adapted by Inria's scikit-learn MOOC.
- **Size:** 1,460 rows × 79 features + target. The two documented
  low-price large-area outliers (`GrLivArea > 4000` and
  `SalePrice < $300k`) are removed before splitting. The evaluation
  split trains on **1,166 rows** and tests on **292 rows**; the
  deployable artifact is then fit on all **1,458 cleaned rows**.
- **Preprocessing decisions** (full justification in
  [`docs/eda/report.md`](./eda/report.md) § 10):
  1. Drop `Id`.
  2. `log1p(SalePrice)` via `TransformedTargetRegressor`.
  3. Drop 2 documented non-market outliers before split.
  4. Impute `LotFrontage` from same-neighborhood medians.
  5. Derive 16 structural features: areas, bathrooms, age, presence
     flags, and `OverallQual × area` interactions.
  6. Target-encode `Neighborhood` fold-safely as `NeighborhoodPriceLog`.
  7. Ordinal-encode 10 quality columns plus ordered non-quality scales.
  8. `log1p` skewed numeric columns and selected engineered magnitudes.
  9. One-hot encode only unordered categoricals with `min_frequency=10`.

## Evaluation

- **Primary metric:** RMSE on `log1p(SalePrice)`.
- **Split:** Stratified 80/20 on quintiles of `SalePrice`,
  `random_state=42`.
- **Cross-validation:** 5-fold KFold, `shuffle=True`, `random_state=42`.

### Current results (XGBoost artifact)

|  | Ridge (baseline) | **XGBoost (production)** |
|---|---:|---:|
| **CV RMSE-log** | 0.1203 ± 0.0091 | **0.1167 ± 0.0074** |
| **Test RMSE-log** | **0.1243** | 0.1249 |
| Test MAE (USD) | $13,432 | **$12,791** |
| Test R² (USD) | 0.920 | **0.927** |
| Test median APE | **5.63 %** | 5.79 % |

#### How to read these numbers

- **XGBoost now clears the sanity floor.** CV RMSE-log improves from
  Ridge's 0.1203 to 0.1167, so the production model wins on the primary
  metric instead of merely tying.
- **Held-out test is effectively tied on RMSE-log.** Ridge is lower by
  0.0006, which is not a meaningful difference. XGBoost still wins on
  MAE ($641 better) and raw-dollar R².
- **Median APE 5.79 %.** Half of the held-out XGBoost predictions are
  within 5.79 % of the true price. This is the user-facing accuracy
  metric the API can surface.

### Per-prediction explanation (SHAP)

Verified end-to-end on the persisted artifact. Three sample
predictions, all within $1–3 k of the actual:

| Row | Actual | Predicted | Top 3 SHAP drivers |
|---:|---:|---:|---|
| 0 | $208,500 | $204,822 | NeighborhoodPriceLog +$6,409, QualArea +$6,046, QualTotalSF +$4,579 |
| 100 | $205,000 | $210,961 | TotalSF +$8,376, NeighborhoodPriceLog +$5,952, QualTotalSF +$5,357 |
| 500 | $113,000 | $112,025 | NeighborhoodPriceLog −$12,338, QualTotalSF −$6,494, LotArea −$6,007 |

The SHAP baseline (`E[predict]` on a 50-row background) is
**$156,513** — the typical Ames home in the training distribution.

## Explainability

Every prediction returned by the API will include:

- The predicted `SalePrice` in dollars.
- The top 5 contributing features with their SHAP values (in log-dollar
  space) and an approximate dollar contribution.
- A plain-English sentence ("Estimated price: $X. This is above the
  typical Ames home (~$Y) by roughly $Z. Main drivers: …").
- The API supplies a fixed training-row background sample when it
  instantiates the explainer, so baseline computation is stable per
  process.

The wrapper is :class:`hou53_ml.explainability.PipelineSHAPExplainer`
and operates on tree-based estimators (XGBoost, RandomForest,
HistGradientBoosting). The API in Phase 4 will instantiate it once
at startup against the loaded artifact.

## Ethical considerations

- Explanations reveal **correlations, not causes**. A SHAP attribution
  that says "Neighborhood X raised the estimate" is a statement about
  this dataset, not a claim about what a house *should* cost.
- The model relies heavily on `Neighborhood`, `OverallQual`, and
  `GrLivArea`. The first two encode information that, in a deployed
  product, would need additional fairness scrutiny — Ames Housing is
  used here for educational purposes only.

## Caveats and recommendations

- Predictions outside the feature ranges seen in training should be
  flagged. The current model metadata is sufficient to add this as an
  API warning gate; it is not part of the estimator itself.
- Cheap homes are noisier to price than expensive ones; expect a
  natural floor on accuracy at the bottom of the price distribution.

## Citations

- De Cock, D. (2011). *Ames, Iowa: Alternative to the Boston Housing
  Data as an End of Semester Regression Project.*
  [JSE 19(3)](https://jse.amstat.org/v19n3/decock.pdf).
- Mitchell, M. et al. (2019). *Model Cards for Model Reporting.* FAT* '19.
- Lundberg, S. M., Lee, S.-I. (2017). *A Unified Approach to
  Interpreting Model Predictions.* NeurIPS.
