"""XGBoost regressor factory.

Hyperparameters live as keyword defaults on :func:`make_xgboost`, mirror
the values in ``ml/configs/default.yaml``, and are documented inline.
The training entry point can override any of them with explicit kwargs.

Why these defaults
------------------
- ``n_estimators=2200``: high enough for the small learning rate while
  still cheap on a 1.5k-row dataset.
- ``learning_rate=0.05``: a conservative default. Smaller than 0.1 to
  reduce fold variance; larger than 0.01 to keep training fast.
- ``max_depth=3``: shallow trees regularize on a 1,458-row cleaned dataset.
- ``subsample=0.5213``, ``colsample_bytree=0.4603``: aggressive row +
  column subsampling that reduced validation error in our local
  comparison runs.
- ``min_child_weight=1.7817`` and ``gamma=0.0468``: mild split
  regularization.
- ``reg_alpha=0.4640``, ``reg_lambda=0.8571``: stronger L1 and mild L2.
- ``tree_method="hist"``: histogram method, fastest on CPU.
- ``objective="reg:squarederror"``: minimum-MSE on the (already
  log-transformed-by-the-pipeline) target.

The pipeline wraps the estimator with
:class:`sklearn.compose.TransformedTargetRegressor`, so the squared
error here is squared error on ``log1p(SalePrice)`` — exactly the
Kaggle leaderboard objective. See ADR-0007.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover — type-only
    from xgboost import XGBRegressor

#: Defaults exposed as a constant so tests can assert on them and the
#: training entry point can pretty-print "running with defaults" runs.
DEFAULT_PARAMS: dict[str, Any] = {
    "n_estimators": 2200,
    "learning_rate": 0.05,
    "max_depth": 3,
    "min_child_weight": 1.7817,
    "subsample": 0.5213,
    "colsample_bytree": 0.4603,
    "gamma": 0.0468,
    "reg_alpha": 0.4640,
    "reg_lambda": 0.8571,
    "objective": "reg:squarederror",
    "tree_method": "hist",
    "n_jobs": -1,
    "random_state": 42,
}


def make_xgboost(**overrides: Any) -> XGBRegressor:
    """Construct an :class:`XGBRegressor` with the project defaults.

    Args:
        **overrides: Any keyword forwarded to
            :class:`xgboost.XGBRegressor`. Overrides win over the
            defaults; unspecified knobs use :data:`DEFAULT_PARAMS`.

    Returns:
        An unfitted :class:`XGBRegressor`.

    Notes:
        ``early_stopping_rounds`` is intentionally absent: it requires
        an ``eval_set`` at ``fit`` time, which the training entry
        point provides. The factory stays agnostic.

        The ``xgboost`` import is deferred to call time so importing
        ``hou53_ml.models`` does not require the OpenMP runtime
        (``libomp`` on macOS). Tests covering the rest of the package
        run on machines without it.
    """
    from xgboost import XGBRegressor

    params = {**DEFAULT_PARAMS, **overrides}
    return XGBRegressor(**params)
