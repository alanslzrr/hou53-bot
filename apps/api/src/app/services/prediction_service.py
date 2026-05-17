"""Orchestration for turning user features into a domain prediction.

This is the only place that "knows the recipe":

  partial → complete row → predict + explain → bundle into Prediction

The router is thin (deserialise, call the service, serialise). The
infra layer is opaque (loads the model). Swapping the explainer for a
different attribution method, adding caching, or wiring an A/B router
all happen here without touching either side.
"""

from __future__ import annotations

from typing import Any

import hou53_ml

from app.domain.prediction import FeatureContribution, Prediction
from app.infra.logging import get_logger
from app.infra.model_loader import LoadedModel

_log = get_logger(__name__)


class PredictionService:
    """Compose the loaded model into the domain workflow."""

    def __init__(self, model: LoadedModel) -> None:
        self._model = model

    def predict(
        self,
        partial: dict[str, Any],
        *,
        top_k: int | None = None,
    ) -> Prediction:
        """Run a single-row prediction with SHAP explanation.

        Args:
            partial: User-supplied features. Missing keys are filled by
                the model's own imputers via :meth:`LoadedModel.complete_row`.
            top_k: Override the default number of top SHAP features
                returned. ``None`` uses the explainer's default.

        Returns:
            A populated :class:`Prediction`.
        """
        row = self._model.complete_row(partial)
        explanation = self._model.explain(row, top_k=top_k)

        _log.info(
            "prediction_made",
            prediction_usd=round(explanation.prediction_usd, 2),
            top_feature=(explanation.top_features[0].feature if explanation.top_features else None),
            n_user_fields=len(partial),
        )

        return Prediction(
            value_usd=explanation.prediction_usd,
            baseline_usd=explanation.baseline_usd,
            top_features=tuple(
                FeatureContribution(
                    feature=c.feature,
                    shap_value=c.shap_value,
                    contribution_usd=c.contribution_usd,
                    direction=c.direction,
                )
                for c in explanation.top_features
            ),
            natural_language=explanation.natural_language,
            model_name=self._model.metadata.model_name,
            model_version=hou53_ml.__version__,
            trained_at_utc=self._model.metadata.trained_at_utc,
            extras={
                "dataset_sha256": self._model.metadata.dataset_sha256,
                "n_user_fields": len(partial),
            },
        )
