# ADR-0006: XGBoost as the production regressor

- **Status:** proposed
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

We must predict `SalePrice` from 79 mixed-type features on ~1,500 training
rows. The evaluation criteria explicitly mention interpretability, and the
explainability requirement in the challenge brief is non-negotiable. We need
to pick a production regressor that is accurate on tabular data, reproducibly
serializable, and pairs with a mature explainability library.

## Decision Drivers

- Tabular dataset with mixed numeric + categorical, many missing values,
  ~1,500 rows. This is classic gradient-boosting territory — deep learning
  is not competitive here.
- SHAP explanations are a hard requirement. Whichever model we pick must
  support fast, exact SHAP via `TreeExplainer`.
- Must serialize to a single file that the API can load in < 1 s.
- Must be reproducible: same seeds → same model, bit-for-bit.

## Considered Options

1. **Linear regression / Ridge / Lasso** with heavy feature engineering.
2. **Random Forest**.
3. **XGBoost**.
4. **LightGBM**.
5. **CatBoost**.

## Decision Outcome

Chosen option: **XGBoost**, because it is the combination of "best-in-class
on tabular" and "most battle-tested SHAP integration" — and on Ames Housing,
top Kaggle notebooks consistently show gradient-boosted trees outperforming
linear/RF baselines by a meaningful margin.

We will still train a **Ridge baseline** as a sanity floor: if XGBoost does
not clearly beat Ridge on held-out CV RMSE, our pipeline has a bug.

### Positive Consequences

- SHAP's `TreeExplainer` is exact and O(T·L·D²) — fast enough to explain
  every prediction in the API response.
- Handles missing values natively (no imputation required for numeric).
- Mature serialization: `joblib.dump` of the whole sklearn `Pipeline` gives
  us a single-file artifact.
- Well-documented Optuna integration for hyperparameter search.

### Negative Consequences / Trade-offs

- More hyperparameters to tune than a linear model. Mitigated by Optuna
  with a constrained search space (50–100 trials) and early stopping.
- Black-box at the model level. Mitigated by SHAP at the prediction level
  and by the Ridge baseline for sanity.

## Pros and Cons of the Options

### Linear / Ridge / Lasso

- Good, because coefficients are directly interpretable.
- Good, because fast to train and trivially cheap to serve.
- Bad, because it requires substantially more feature engineering to match
  gradient boosting on this dataset.
- Used as a **baseline**, not as the production model.

### Random Forest

- Good, because robust defaults and low tuning burden.
- Bad, because typically 1–3% RMSE behind XGBoost on Ames.
- Bad, because `TreeExplainer` works, but the model is larger on disk.

### XGBoost

- Good, because top of the leaderboard on tabular benchmarks.
- Good, because first-class SHAP.
- Bad, because more tuning effort.

### LightGBM

- Good, because faster to train than XGBoost at similar accuracy.
- Good, because also has SHAP support.
- Bad, because on very small datasets (~1,500 rows) the leaf-wise growth
  can overfit aggressively; XGBoost's default depth-wise is safer here.
- Reasonable alternative — if we later benchmark and LightGBM wins, we
  swap it in with a one-line change and a new ADR.

### CatBoost

- Good, because it handles categoricals natively with minimal
  preprocessing.
- Bad, because SHAP support is less canonical than for XGBoost/LightGBM.
- Bad, because it is the less commonly used of the three, which matters
  for a reviewer skimming the submission.

## Links

- [XGBoost docs](https://xgboost.readthedocs.io/)
- [SHAP TreeExplainer](https://shap.readthedocs.io/en/latest/generated/shap.explainers.Tree.html)
- [ADR-0007 — Evaluation metric](./0007-evaluation-metric-rmse-log.md)
