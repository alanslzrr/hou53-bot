"""Domain entities for the prediction workflow.

Pure dataclasses with no FastAPI / sklearn imports. The HTTP DTOs in
:mod:`app.api.dtos` translate to/from these.

Why a separate domain layer at all
----------------------------------
For a four-endpoint service this looks like over-engineering. It pays
off the moment a second consumer (the natural-language parser, a CLI,
or a batch worker) needs the same orchestration without dragging
FastAPI request models around. Keeping the orchestration in
:mod:`app.services` operating on these dataclasses means we get that
optionality for free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class FeatureContribution:
    """One feature's contribution to a single prediction (mirrors SHAP)."""

    feature: str
    shap_value: float
    contribution_usd: float
    direction: str  # "up" | "down"


@dataclass(frozen=True, slots=True)
class Prediction:
    """The result of explaining a single house."""

    value_usd: float
    baseline_usd: float
    top_features: tuple[FeatureContribution, ...]
    natural_language: str
    model_name: str
    model_version: str
    trained_at_utc: str
    extras: dict[str, Any] = field(default_factory=dict)
