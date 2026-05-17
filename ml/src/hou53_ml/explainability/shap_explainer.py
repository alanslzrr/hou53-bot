"""SHAP-based per-prediction explainer.

The challenge brief makes explainability a hard requirement, and a
useful explanation has to do two things at once:

1. **Be correct** — the attributions must reflect what the model
   actually used. For tree-based regressors that means SHAP via
   :class:`shap.TreeExplainer` (exact, fast, locally accurate).
2. **Be readable** — a non-technical user does not want to see a
   sparse 200-dim vector. They want a paragraph: "your house is
   estimated above the typical Ames home because X and Y, but pulled
   down by Z."

This module produces both: a structured :class:`Explanation` (consumed
by the API/frontend) and a natural-language sentence (rendered in the
UI as the headline).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
import shap
from sklearn.compose import TransformedTargetRegressor
from sklearn.pipeline import Pipeline


@dataclass(frozen=True, slots=True)
class FeatureContribution:
    """Per-feature contribution for a single prediction.

    Attributes:
        feature: Encoded feature name as returned by the preprocessor.
        shap_value: Contribution in log-dollar space (the model's
            native target space).
        contribution_usd: Approximate contribution in dollars, computed
            by ``expm1(baseline + shap) - expm1(baseline)``. This is a
            *local* linear approximation around the prediction; it is
            order-correct and the right number to show a user.
        direction: ``"up"`` if positive, ``"down"`` if negative.
    """

    feature: str
    shap_value: float
    contribution_usd: float
    direction: str


@dataclass(frozen=True, slots=True)
class Explanation:
    """Structured explanation for a single prediction.

    Attributes:
        prediction_usd: Model's predicted price in dollars.
        baseline_usd: ``expm1`` of the SHAP base value — the average
            log-prediction across the explainer's background set,
            back-transformed to dollars. The "prior" the explanation
            departs from.
        top_features: ``FeatureContribution`` rows for the ``top_k``
            most-influential features (by absolute SHAP).
        natural_language: One-paragraph summary built from
            ``top_features``.
    """

    prediction_usd: float
    baseline_usd: float
    top_features: list[FeatureContribution]
    natural_language: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["top_features"] = [asdict(f) for f in self.top_features]
        return d


class PipelineSHAPExplainer:
    """Wrap :class:`shap.TreeExplainer` around the full training pipeline.

    The training pipeline is a
    :class:`TransformedTargetRegressor(regressor=Pipeline([derived,
    preprocess, estimator]))`. The SHAP explainer needs the *fitted
    tree estimator*, but the inputs it operates on are the *encoded*
    features. We extract both at construction time and store them.

    The class is initialised once per process (the API does this in
    its startup hook), then ``explain(row)`` is called per request.

    Args:
        pipeline: Fitted :class:`TransformedTargetRegressor` produced
            by :func:`hou53_ml.pipelines.builders.build_pipeline`.
        background: A small sample of training rows used to estimate
            the expected-value baseline. 50-200 rows is plenty.
        top_k: Default number of top features to surface in
            :class:`Explanation`.
    """

    def __init__(
        self,
        pipeline: TransformedTargetRegressor,
        background: pd.DataFrame,
        *,
        top_k: int = 5,
    ) -> None:
        self._pipeline = pipeline
        self._top_k = top_k

        # ``TransformedTargetRegressor`` stores the FITTED inner
        # estimator under ``regressor_`` (trailing underscore). The
        # plain ``regressor`` is the unfitted prototype passed at
        # construction time.
        inner = getattr(pipeline, "regressor_", None) or pipeline.regressor
        if not isinstance(inner, Pipeline):
            msg = (
                "PipelineSHAPExplainer expects a sklearn Pipeline inside "
                "the TransformedTargetRegressor"
            )
            raise TypeError(msg)

        # Reach into the fitted pipeline to get the estimator and the
        # transform-only steps before it. We never replicate this logic
        # elsewhere — encapsulating it here is the whole point.
        self._pre_estimator_steps = inner.steps[:-1]
        self._preprocess = inner.named_steps["preprocess"]
        self._estimator = inner.named_steps["estimator"]

        encoded_background = self._encode(background)
        self._feature_names = list(encoded_background.columns)

        # TreeExplainer infers the right algorithm from the estimator
        # (XGBoost / sklearn trees / HGBR all supported).
        self._explainer = shap.TreeExplainer(
            self._estimator,
            data=encoded_background,
            feature_perturbation="interventional",
        )
        # Baseline in log-dollar space (the estimator's native target).
        self._baseline_log = float(self._explainer.expected_value)

    # --- Public API ----------------------------------------------------------
    def explain(self, X: pd.DataFrame, *, top_k: int | None = None) -> Explanation:
        """Explain a single-row prediction.

        Args:
            X: Single-row DataFrame in raw input format (pre-derivation,
                pre-encoding). Must have the same columns the pipeline
                was fitted with.
            top_k: Override the default ``top_k`` for this call.

        Returns:
            A populated :class:`Explanation`.
        """
        if len(X) != 1:
            msg = f"explain() expects a single-row DataFrame, got {len(X)}"
            raise ValueError(msg)

        encoded = self._encode(X)
        shap_values = np.asarray(self._explainer.shap_values(encoded))
        # shap_values shape is (1, n_features) for regression.
        row_shap = shap_values[0] if shap_values.ndim == 2 else shap_values

        # The prediction in log-space is baseline + sum(shap).
        prediction_log = self._baseline_log + float(row_shap.sum())
        prediction_usd = float(np.expm1(prediction_log))
        baseline_usd = float(np.expm1(self._baseline_log))

        # Rank features by absolute SHAP, take top-k.
        k = top_k or self._top_k
        order = np.argsort(np.abs(row_shap))[::-1][:k]

        top_features: list[FeatureContribution] = []
        for idx in order:
            sv = float(row_shap[idx])
            # Dollar contribution is the marginal effect of adding this
            # SHAP value on top of the baseline — a local linear
            # approximation. Order-correct, magnitude approximately
            # correct.
            contrib_usd = float(np.expm1(self._baseline_log + sv) - np.expm1(self._baseline_log))
            top_features.append(
                FeatureContribution(
                    feature=self._feature_names[idx],
                    shap_value=sv,
                    contribution_usd=contrib_usd,
                    direction="up" if sv >= 0 else "down",
                )
            )

        return Explanation(
            prediction_usd=prediction_usd,
            baseline_usd=baseline_usd,
            top_features=top_features,
            natural_language=self._to_sentence(prediction_usd, baseline_usd, top_features),
        )

    # --- Internals -----------------------------------------------------------
    def _encode(self, X: pd.DataFrame) -> pd.DataFrame:
        """Run all pre-estimator transform steps; return a DataFrame."""
        encoded: Any = X
        for _, step in self._pre_estimator_steps:
            encoded = step.transform(encoded)
        # ColumnTransformer with ``set_output("pandas")`` returns a
        # DataFrame. Defensive cast in case of numpy fallback.
        if not isinstance(encoded, pd.DataFrame):
            cols = self._preprocess.get_feature_names_out()
            encoded = pd.DataFrame(encoded, columns=cols, index=X.index)
        return encoded

    @staticmethod
    def _to_sentence(
        prediction_usd: float,
        baseline_usd: float,
        contributions: list[FeatureContribution],
    ) -> str:
        """Render the top contributions as a single English paragraph.

        Kept inside the explainer (rather than on the API side) because
        the right phrasing follows directly from the SHAP semantics —
        not a place to invent two divergent implementations.
        """
        diff = prediction_usd - baseline_usd
        direction_word = "above" if diff >= 0 else "below"
        intro = (
            f"Estimated price: ${prediction_usd:,.0f}. "
            f"This is {direction_word} the typical Ames home "
            f"(${baseline_usd:,.0f}) "
            f"by roughly ${abs(diff):,.0f}."
        )
        if not contributions:
            return intro
        bullets = []
        for c in contributions:
            verb = "raised" if c.direction == "up" else "lowered"
            bullets.append(f"{c.feature} {verb} the estimate by ~${abs(c.contribution_usd):,.0f}")
        body = "Main drivers: " + "; ".join(bullets) + "."
        return f"{intro} {body}"
