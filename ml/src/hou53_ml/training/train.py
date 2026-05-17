"""End-to-end training entry point.

Runs the full Phase-2 pipeline: load data, split, train a baseline,
train XGBoost, evaluate both, persist the production artifact, log to
MLflow. Designed to be runnable from the CLI:

    uv run python -m hou53_ml.training.train

and importable from tests / notebooks via :func:`train`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow

from hou53_ml import get_settings
from hou53_ml.evaluation import EvaluationReport, build_evaluation_report
from hou53_ml.io import AmesHousingLoader, Schema
from hou53_ml.models import make_ridge
from hou53_ml.pipelines import build_pipeline
from hou53_ml.serialization import ModelArtifact, build_metadata
from hou53_ml.training.splits import documented_outlier_mask, make_split

_LOG = logging.getLogger("hou53_ml.train")


@dataclass(frozen=True, slots=True)
class TrainingResult:
    """Return value of :func:`train`."""

    baseline_report: EvaluationReport
    production_report: EvaluationReport
    artifact_path: Path
    metadata_path: Path


def train(
    *,
    csv_path: Path | None = None,
    output_dir: Path | None = None,
    random_state: int = 42,
    test_size: float = 0.2,
    cv_splits: int = 5,
    experiment_name: str = "hou53-xgboost-baseline",
    skip_baseline: bool = False,
    production_model: str = "xgboost",
) -> TrainingResult:
    """Train, evaluate, and persist the production pipeline.

    Args:
        csv_path: Path to the raw CSV. Defaults to
            ``settings.data_raw / "house_prices.csv"``.
        output_dir: Where to write the joblib + metadata pair.
            Defaults to ``settings.models_path``.
        random_state: Seed for splits and estimators.
        test_size: Held-out fraction.
        cv_splits: K for KFold.
        experiment_name: MLflow experiment name.
        skip_baseline: When ``True``, skip the Ridge baseline (faster
            iteration; not recommended for production runs).
        production_model: ``"xgboost"`` (default) or ``"ridge"``. The
            second is the fallback when XGBoost is unavailable (missing
            ``libomp`` on macOS) but the rest of the pipeline still
            needs end-to-end validation.

    Returns:
        A :class:`TrainingResult` with the two reports and the paths
        of the persisted artifact.
    """
    _configure_logging()
    settings = get_settings()
    csv_path = csv_path or (settings.data_raw / "house_prices.csv")
    output_dir = output_dir or settings.models_path

    _LOG.info("loading data from %s", csv_path)
    loader = AmesHousingLoader(csv_path)
    frame = loader.load().frame
    schema = Schema.default()
    schema.assert_covers(list(frame.columns))

    split = make_split(frame, test_size=test_size, random_state=random_state)
    _LOG.info(
        "split: train=%d test=%d outliers_removed=%d",
        len(split.X_train),
        len(split.X_test),
        split.n_outliers_removed,
    )

    mlflow.set_tracking_uri(f"file:{settings.mlruns_path}")
    mlflow.set_experiment(experiment_name)

    baseline_report: EvaluationReport | None = None
    # When the production model is also Ridge, the baseline is identical
    # to it — running both wastes time without gaining a sanity floor.
    if not skip_baseline and production_model != "ridge":
        baseline_report = _train_and_evaluate(
            model_name="ridge",
            pipeline_factory=lambda: build_pipeline(make_ridge(random_state=random_state)),
            split=split,
            cv_splits=cv_splits,
            random_state=random_state,
        )

    if production_model == "ridge":

        def prod_factory() -> Any:
            return build_pipeline(make_ridge(random_state=random_state))
    elif production_model == "xgboost":

        def prod_factory() -> Any:
            return build_pipeline()
    else:
        msg = f"unknown production_model={production_model!r}; expected 'xgboost' or 'ridge'"
        raise ValueError(msg)

    production_report = _train_and_evaluate(
        model_name=production_model,
        pipeline_factory=prod_factory,
        split=split,
        cv_splits=cv_splits,
        random_state=random_state,
    )

    # Compare baseline vs production and warn loudly if XGBoost lost.
    if baseline_report is not None and (
        production_report.cv_mean_rmse_log > baseline_report.cv_mean_rmse_log
    ):
        _LOG.warning(
            "XGBoost (%.4f) did NOT beat Ridge (%.4f) on CV RMSE-log. Investigate before shipping.",
            production_report.cv_mean_rmse_log,
            baseline_report.cv_mean_rmse_log,
        )

    # Persist the production artifact. Evaluation uses a hold-out split, but
    # the deployable model should learn from every cleaned training row.
    clean_mask = ~documented_outlier_mask(frame)
    clean_frame = frame.loc[clean_mask].reset_index(drop=True)
    final_features = clean_frame.drop(columns=[schema.target])
    final_y = clean_frame[schema.target]
    final_pipeline = prod_factory()
    final_pipeline.fit(final_features, final_y)
    # ``TransformedTargetRegressor`` clones the user-passed regressor at
    # fit time and stores the fitted version under ``regressor_``. The
    # unsuffixed ``regressor`` attribute is still the unfitted prototype.
    fitted_inner = final_pipeline.regressor_
    feature_names = fitted_inner.named_steps["preprocess"].get_feature_names_out().tolist()
    metadata = build_metadata(
        model_name=production_model,
        dataset_path=csv_path,
        schema_columns=list(schema.expected_columns),
        feature_names_after_preprocess=feature_names,
        report=production_report,
        random_seed=random_state,
        extras={
            "baseline_cv_rmse_log": (baseline_report.cv_mean_rmse_log if baseline_report else None),
            "n_outliers_removed": split.n_outliers_removed,
            "artifact_training_rows": len(final_features),
        },
    )
    artifact = ModelArtifact(pipeline=final_pipeline, metadata=metadata)
    artifact_path, metadata_path = artifact.save(output_dir)
    _LOG.info("artifact written to %s", artifact_path)

    if baseline_report is None:
        baseline_report = production_report  # surface something in the result

    return TrainingResult(
        baseline_report=baseline_report,
        production_report=production_report,
        artifact_path=artifact_path,
        metadata_path=metadata_path,
    )


# -----------------------------------------------------------------------------
# Internals
# -----------------------------------------------------------------------------
def _train_and_evaluate(
    *,
    model_name: str,
    pipeline_factory: Callable[[], Any],
    split: Any,
    cv_splits: int,
    random_state: int,
) -> EvaluationReport:
    _LOG.info("training %s", model_name)
    with mlflow.start_run(run_name=model_name):
        mlflow.log_params(
            {
                "model_name": model_name,
                "n_train": len(split.X_train),
                "n_test": len(split.X_test),
                "cv_splits": cv_splits,
                "random_state": random_state,
            }
        )

        fitted = pipeline_factory()
        fitted.fit(split.X_train, split.y_train)

        report = build_evaluation_report(
            model_name=model_name,
            pipeline_factory=pipeline_factory,
            fitted_pipeline=fitted,
            X_train=split.X_train,
            y_train=split.y_train,
            X_test=split.X_test,
            y_test=split.y_test,
            n_splits=cv_splits,
            random_state=random_state,
        )
        mlflow.log_metrics(
            {
                "cv_mean_rmse_log": report.cv_mean_rmse_log,
                "cv_std_rmse_log": report.cv_std_rmse_log,
                "cv_mean_mae_dollars": report.cv_mean_mae,
                "test_rmse_log": report.test_rmse_log,
                "test_mae_dollars": report.test_mae_dollars,
                "test_r2_dollars": report.test_r2_dollars,
                "test_median_ape": report.test_median_ape,
            }
        )

        _LOG.info(
            "%s — CV RMSE-log %.4f ± %.4f  |  test RMSE-log %.4f  MAE $%.0f  R² %.3f  med-APE %.3f",
            model_name,
            report.cv_mean_rmse_log,
            report.cv_std_rmse_log,
            report.test_rmse_log,
            report.test_mae_dollars,
            report.test_r2_dollars,
            report.test_median_ape,
        )
    return report


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hou53_ml.training.train",
        description=(
            "Train and evaluate the Ames Housing pipeline. Produces a "
            "joblib artifact + sidecar JSON in --output-dir."
        ),
    )
    parser.add_argument("--csv-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--cv-splits", type=int, default=5)
    parser.add_argument("--experiment-name", type=str, default="hou53-xgboost-baseline")
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip the Ridge sanity floor (not recommended).",
    )
    parser.add_argument(
        "--model",
        choices=["xgboost", "ridge"],
        default="xgboost",
        dest="production_model",
        help=(
            "Production model. Use 'ridge' on macOS without libomp; "
            "switch to 'xgboost' once `brew install libomp` is run."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = train(
        csv_path=args.csv_path,
        output_dir=args.output_dir,
        random_state=args.random_state,
        test_size=args.test_size,
        cv_splits=args.cv_splits,
        experiment_name=args.experiment_name,
        skip_baseline=args.skip_baseline,
        production_model=args.production_model,
    )
    summary = {
        "artifact_path": str(result.artifact_path),
        "metadata_path": str(result.metadata_path),
        "baseline_cv_rmse_log": result.baseline_report.cv_mean_rmse_log,
        "production_cv_rmse_log": result.production_report.cv_mean_rmse_log,
        "production_test_rmse_log": result.production_report.test_rmse_log,
        "production_test_mae_dollars": result.production_report.test_mae_dollars,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
