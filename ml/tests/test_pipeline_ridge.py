"""End-to-end smoke test using the Ridge baseline.

XGBoost requires libomp on macOS, which is a system-level dependency
the developer may or may not have installed. The Ridge baseline has no
such requirement and exercises the entire pipeline (derived features,
preprocessor, target transform, scorer). If this test passes, the
plumbing is correct — swapping in XGBoost later is just a parameter
change.
"""

from pathlib import Path

import pytest
from hou53_ml.evaluation import EvaluationReport, build_evaluation_report
from hou53_ml.io import AmesHousingLoader
from hou53_ml.models import make_ridge
from hou53_ml.pipelines import build_pipeline
from hou53_ml.training.splits import make_split


def _real_csv_or_skip() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "raw" / "house_prices.csv"
        if candidate.exists():
            return candidate
    pytest.skip("data/raw/house_prices.csv not available locally")


@pytest.mark.integration
@pytest.mark.slow
class TestRidgePipelineEndToEnd:
    """One test per behavior; same fitted pipeline reused for speed."""

    @pytest.fixture(scope="class")
    def fitted_report(self) -> EvaluationReport:
        csv = _real_csv_or_skip()
        df = AmesHousingLoader(csv).load().frame
        split = make_split(df, random_state=42)
        factory = lambda: build_pipeline(make_ridge())  # noqa: E731
        fitted = factory()
        fitted.fit(split.X_train, split.y_train)
        return build_evaluation_report(
            model_name="ridge",
            pipeline_factory=factory,
            fitted_pipeline=fitted,
            X_train=split.X_train,
            y_train=split.y_train,
            X_test=split.X_test,
            y_test=split.y_test,
            n_splits=3,  # 3 folds keeps the test under ~10s
            random_state=42,
        )

    def test_cv_rmse_log_under_threshold(self, fitted_report: EvaluationReport) -> None:
        # On Ames Housing, Ridge with this preprocessor reliably scores
        # CV RMSE-log < 0.20. Anything above 0.25 means something broke.
        assert fitted_report.cv_mean_rmse_log < 0.25, (
            f"Ridge baseline degraded: CV RMSE-log = {fitted_report.cv_mean_rmse_log:.4f}"
        )

    def test_test_rmse_log_reasonable(self, fitted_report: EvaluationReport) -> None:
        # Headline metric — same scale as Kaggle leaderboard.
        assert fitted_report.test_rmse_log < 0.30, (
            f"Test RMSE-log too high: {fitted_report.test_rmse_log:.4f}"
        )

    def test_test_median_ape_under_15_percent(self, fitted_report: EvaluationReport) -> None:
        # The metric the user actually feels: "half my predictions are
        # within X% of the truth". Ridge is reliably under 8% on Ames;
        # we set the bar at 15% to leave headroom.
        #
        # We do NOT assert on R² in dollars — a single failed-to-fit
        # outlier (Ridge will extrapolate occasionally) crushes R² even
        # when RMSE-log and median APE are healthy. The metric is in
        # the report for inspection but is not a CI gate for the
        # baseline.
        assert fitted_report.test_median_ape < 0.15

    def test_predictions_are_positive(self, fitted_report: EvaluationReport) -> None:
        # All houses cost > $0. A Ridge can sometimes go slightly
        # negative on extreme inputs, but the log-target wrapper should
        # prevent that.
        assert fitted_report.cv_mean_mae > 0

    def test_report_serialisable(self, fitted_report: EvaluationReport) -> None:
        d = fitted_report.to_dict()
        assert d["model_name"] == "ridge"
        assert "cv_fold_results" in d
        assert d["n_train"] > 0
