"""Service layer — orchestrates infra + domain to fulfil API requests."""

from app.services.prediction_service import PredictionService

__all__ = ["PredictionService"]
