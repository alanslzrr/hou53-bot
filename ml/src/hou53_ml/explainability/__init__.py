"""SHAP-based per-prediction explainer."""

from hou53_ml.explainability.shap_explainer import (
    Explanation,
    FeatureContribution,
    PipelineSHAPExplainer,
)

__all__ = ["Explanation", "FeatureContribution", "PipelineSHAPExplainer"]
