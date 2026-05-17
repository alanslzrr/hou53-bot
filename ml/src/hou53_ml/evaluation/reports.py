"""Cross-validation and evaluation reports.

Produces an :class:`EvaluationReport` that bundles CV statistics with
held-out-test scores. Used both by the training entry point (to log
to MLflow and to the model card) and by tests (which assert on its
shape, not its values).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.model_selection import KFold

from hou53_ml.evaluation.metrics import (
    mae_dollars,
    median_ape,
    r2_dollars,
    rmse_log,
)


@dataclass(frozen=True, slots=True)
class FoldResult:
    """One cross-validation fold's metrics on its hold-out slice."""

    fold: int
    rmse_log: float
    mae_dollars: float
    r2_dollars: float
    median_ape: float


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Bundle of CV + test metrics for a single trained pipeline.

    Attributes:
        model_name: Free-form label (``"ridge"``, ``"xgboost"``).
        cv_fold_results: One :class:`FoldResult` per CV fold.
        cv_mean_rmse_log: Mean of fold ``rmse_log`` values.
        cv_std_rmse_log: Standard deviation across folds.
        cv_mean_mae: Mean of fold ``mae_dollars`` values.
        cv_mean_r2: Mean of fold ``r2_dollars`` values.
        test_rmse_log: Headline metric on the held-out test set.
        test_mae_dollars: Same on the held-out test.
        test_r2_dollars: Same on the held-out test.
        test_median_ape: Same on the held-out test.
        n_train: Training set size (after outlier removal).
        n_test: Test set size.
    """

    model_name: str
    cv_fold_results: list[FoldResult]
    cv_mean_rmse_log: float
    cv_std_rmse_log: float
    cv_mean_mae: float
    cv_mean_r2: float
    test_rmse_log: float
    test_mae_dollars: float
    test_r2_dollars: float
    test_median_ape: float
    n_train: int
    n_test: int
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable representation, used by the model card."""
        d = asdict(self)
        d["cv_fold_results"] = [asdict(f) for f in self.cv_fold_results]
        return d


def cross_validate_pipeline(
    pipeline_factory: Any,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    n_splits: int = 5,
    random_state: int = 42,
) -> list[FoldResult]:
    """Run K-fold CV using a fresh pipeline per fold.

    A *factory*, not a fitted pipeline, is taken on purpose: each fold
    must fit a brand-new estimator so leakage is impossible.

    Args:
        pipeline_factory: Zero-arg callable returning an unfitted
            pipeline. ``lambda: build_pipeline()`` is the typical form.
        X: Features (raw, post-loader DataFrame).
        y: Target in dollars.
        n_splits: Number of folds.
        random_state: Forwarded to KFold for reproducibility.

    Returns:
        A list of :class:`FoldResult`, one per fold.
    """
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    results: list[FoldResult] = []
    for i, (train_idx, val_idx) in enumerate(kf.split(X)):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        pipeline = pipeline_factory()
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_val)

        results.append(
            FoldResult(
                fold=i,
                rmse_log=rmse_log(y_val, preds),
                mae_dollars=mae_dollars(y_val, preds),
                r2_dollars=r2_dollars(y_val, preds),
                median_ape=median_ape(y_val, preds),
            )
        )
    return results


def build_evaluation_report(
    *,
    model_name: str,
    pipeline_factory: Any,
    fitted_pipeline: BaseEstimator,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    n_splits: int = 5,
    random_state: int = 42,
    extras: dict[str, Any] | None = None,
) -> EvaluationReport:
    """Run CV + test-set evaluation and bundle the results.

    Args:
        model_name: Short label for logs and the model card.
        pipeline_factory: Zero-arg callable producing an unfitted
            pipeline (used for CV folds).
        fitted_pipeline: A pipeline already fit on ``(X_train,
            y_train)`` — used for the test-set predictions.
        X_train: Training features after outlier removal.
        y_train: Training target after outlier removal.
        X_test: Held-out test features.
        y_test: Held-out test target.
        n_splits: CV folds.
        random_state: Reproducibility seed for KFold.
        extras: Free-form payload merged into the report (e.g.,
            ``{"n_estimators_after_early_stopping": 412}``).

    Returns:
        An :class:`EvaluationReport`.
    """
    cv = cross_validate_pipeline(
        pipeline_factory,
        X_train,
        y_train,
        n_splits=n_splits,
        random_state=random_state,
    )
    cv_rmse = np.array([r.rmse_log for r in cv])
    cv_mae = np.array([r.mae_dollars for r in cv])
    cv_r2 = np.array([r.r2_dollars for r in cv])

    test_preds = fitted_pipeline.predict(X_test)

    return EvaluationReport(
        model_name=model_name,
        cv_fold_results=cv,
        cv_mean_rmse_log=float(cv_rmse.mean()),
        cv_std_rmse_log=float(cv_rmse.std(ddof=1)),
        cv_mean_mae=float(cv_mae.mean()),
        cv_mean_r2=float(cv_r2.mean()),
        test_rmse_log=rmse_log(y_test, test_preds),
        test_mae_dollars=mae_dollars(y_test, test_preds),
        test_r2_dollars=r2_dollars(y_test, test_preds),
        test_median_ape=median_ape(y_test, test_preds),
        n_train=len(X_train),
        n_test=len(X_test),
        extras=extras or {},
    )
