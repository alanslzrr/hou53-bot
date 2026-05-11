# ADR-0007: RMSE on `log1p(SalePrice)` as the primary metric

- **Status:** proposed
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

House prices are right-skewed: an error of $10,000 on a $100,000 house is
10x more serious than the same absolute error on a $1,000,000 house. The
evaluation metric we optimize must reflect that, and must also be comparable
to the community benchmark so we can sanity-check our numbers against
published Kaggle notebooks.

## Decision Drivers

- The loss function we optimize drives model behavior — it must penalize
  proportional errors, not absolute ones.
- We want to compare our results against the Kaggle competition leaderboard
  as a sanity check, so our primary metric should match theirs.
- The metric should be easy to explain in the model card and in the API
  response (confidence interval).

## Considered Options

1. **MAE on raw `SalePrice`**.
2. **RMSE on raw `SalePrice`**.
3. **MAPE (Mean Absolute Percentage Error)** on raw `SalePrice`.
4. **RMSE on `log1p(SalePrice)`** — the Kaggle competition metric.

## Decision Outcome

Chosen option: **RMSE on `log1p(SalePrice)`**, because it is equivalent to a
relative-error objective, it matches the Kaggle metric so our numbers are
directly comparable, and it is what XGBoost will optimize when given a
log-transformed target with `reg:squarederror`.

### Positive Consequences

- Penalizes proportional errors symmetrically — a ±10% error is weighted
  the same for a cheap house as for an expensive one.
- Lets us compare directly to Kaggle leaderboard scores.
- Works cleanly with `TransformedTargetRegressor` in sklearn, keeping the
  log transform inside the serialized pipeline.

### Negative Consequences / Trade-offs

- The metric is in log space and not intuitive to a non-technical user.
  Mitigated by reporting a **secondary** metric (MAE in dollars) on the
  model card and in the API response.

## Secondary metrics we will track

- **MAE in dollars** — what the user intuitively understands.
- **R² on raw price** — standard regression sanity check.
- **Mean and 90th-percentile absolute percentage error** — for
  communicating "the model is usually within X% of the real price".

These are **reported**, not **optimized** — the CV and hyperparameter search
drive on the primary metric only.

## Target transform as part of the pipeline

The log transform lives inside the scikit-learn pipeline via
`TransformedTargetRegressor(func=np.log1p, inverse_func=np.expm1)`. This
means:

- The API receives raw dollars in `y`, returns raw dollars in the
  prediction.
- Training and serving cannot drift (one object, one transform).
- `joblib.load(...).predict(X)` always returns dollars. No post-processing
  in the API.

## Validation strategy

- **Split:** stratified 80/20 on `SalePrice` quintiles to keep the target
  distribution consistent between train and test.
- **Cross-validation:** 5-fold KFold with `shuffle=True` and
  `random_state=42`. Reported metric on test set is the primary headline
  number; CV mean ± std goes on the model card.

## Links

- [Kaggle — House Prices competition](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/overview/evaluation)
- [`TransformedTargetRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.compose.TransformedTargetRegressor.html)
