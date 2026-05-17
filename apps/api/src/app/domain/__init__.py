"""Pure domain entities (no FastAPI, no sklearn)."""

from app.domain.prediction import FeatureContribution, Prediction

__all__ = ["FeatureContribution", "Prediction"]
