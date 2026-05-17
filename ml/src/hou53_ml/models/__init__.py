"""Estimator factories.

Public surface: a baseline (Ridge) and the production regressor
(XGBoost). Both are pipeline-agnostic — the training pipeline composes
them with the preprocessor and the target transform.
"""

from hou53_ml.models.baseline import make_ridge
from hou53_ml.models.boosting import DEFAULT_PARAMS, make_xgboost

__all__ = ["DEFAULT_PARAMS", "make_ridge", "make_xgboost"]
