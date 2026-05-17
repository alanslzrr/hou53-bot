"""Tests for ``hou53_ml.explainability.shap_explainer``.

We use a sklearn ``RandomForestRegressor`` instead of XGBoost so the
tests run on machines without libomp. SHAP's ``TreeExplainer`` supports
both algorithms identically; the wrapper logic is unchanged.
"""

from __future__ import annotations

import numpy as np
import pytest
from hou53_ml import get_settings
from hou53_ml.explainability import (
    Explanation,
    FeatureContribution,
    PipelineSHAPExplainer,
)
from hou53_ml.features import DerivedFeatures, build_preprocessor
from hou53_ml.io import AmesHousingLoader
from hou53_ml.training.splits import make_split
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline


@pytest.mark.integration
@pytest.mark.slow
class TestPipelineSHAPExplainer:
    """End-to-end SHAP explanations using a RandomForest stand-in."""

    @pytest.fixture(scope="class")
    def fitted_explainer(self) -> tuple[PipelineSHAPExplainer, pd.DataFrame]:  # noqa: F821
        # Skip cleanly if the real CSV is not present.
        csv = get_settings().data_raw / "house_prices.csv"
        if not csv.exists():
            pytest.skip("data/raw/house_prices.csv not available locally")

        df = AmesHousingLoader(csv).load().frame
        split = make_split(df, random_state=42)

        rf_pipeline = TransformedTargetRegressor(
            regressor=Pipeline(
                steps=[
                    ("derived", DerivedFeatures()),
                    ("preprocess", build_preprocessor()),
                    (
                        "estimator",
                        # Tiny forest — fast to fit, fast to SHAP.
                        RandomForestRegressor(
                            n_estimators=30,
                            max_depth=6,
                            random_state=42,
                            n_jobs=1,
                        ),
                    ),
                ]
            ),
            func=np.log1p,
            inverse_func=np.expm1,
            check_inverse=False,
        )
        rf_pipeline.fit(split.X_train, split.y_train)

        # 30-row background — much smaller than the full train; SHAP's
        # ``data=`` argument samples a baseline from it.
        background = split.X_train.head(30)
        explainer = PipelineSHAPExplainer(rf_pipeline, background, top_k=3)
        return explainer, split.X_test

    def test_explanation_has_top_k_features(
        self,
        fitted_explainer: tuple[PipelineSHAPExplainer, pd.DataFrame],  # noqa: F821
    ) -> None:
        explainer, X_test = fitted_explainer
        explanation = explainer.explain(X_test.head(1))
        assert isinstance(explanation, Explanation)
        assert len(explanation.top_features) == 3
        for contrib in explanation.top_features:
            assert isinstance(contrib, FeatureContribution)
            assert contrib.direction in {"up", "down"}

    def test_explanation_prediction_is_positive(
        self,
        fitted_explainer: tuple[PipelineSHAPExplainer, pd.DataFrame],  # noqa: F821
    ) -> None:
        explainer, X_test = fitted_explainer
        explanation = explainer.explain(X_test.head(1))
        assert explanation.prediction_usd > 0
        assert explanation.baseline_usd > 0

    def test_explanation_natural_language_mentions_features(
        self,
        fitted_explainer: tuple[PipelineSHAPExplainer, pd.DataFrame],  # noqa: F821
    ) -> None:
        explainer, X_test = fitted_explainer
        explanation = explainer.explain(X_test.head(1))
        text = explanation.natural_language
        assert "Estimated price" in text
        # At least one of the top features is named in the sentence.
        assert any(c.feature in text for c in explanation.top_features)

    def test_rejects_multi_row_input(
        self,
        fitted_explainer: tuple[PipelineSHAPExplainer, pd.DataFrame],  # noqa: F821
    ) -> None:
        explainer, X_test = fitted_explainer
        with pytest.raises(ValueError, match="single-row"):
            explainer.explain(X_test.head(2))

    def test_explanation_is_serialisable(
        self,
        fitted_explainer: tuple[PipelineSHAPExplainer, pd.DataFrame],  # noqa: F821
    ) -> None:
        explainer, X_test = fitted_explainer
        explanation = explainer.explain(X_test.head(1))
        d = explanation.to_dict()
        assert "prediction_usd" in d
        assert isinstance(d["top_features"], list)
        assert len(d["top_features"]) == 3
