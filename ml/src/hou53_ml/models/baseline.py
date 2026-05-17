"""Ridge regression baseline.

Sole purpose: detect pipeline bugs. If the production XGBoost does not
clearly beat a Ridge trained on the same preprocessor, something is
wrong upstream (leakage, mislabelled targets, missing inverse
transform). The training entry point logs a warning when this
condition fires.

The Ridge is not deployed in the API.
"""

from __future__ import annotations

from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def make_ridge(*, alpha: float = 1.0, random_state: int = 42) -> Pipeline:
    """Build a scaled Ridge regressor.

    Ridge requires scaled inputs (XGBoost does not), so a
    :class:`StandardScaler` is paired in front. The result composes
    cleanly with the upstream :class:`ColumnTransformer`: the scaler
    receives already-encoded numeric features and treats them
    uniformly.

    Args:
        alpha: L2 regularisation strength.
        random_state: Forwarded to Ridge for reproducibility on solvers
            that use randomness (saga). The default solver is
            deterministic; the seed is set for hygiene.

    Returns:
        Unfitted :class:`Pipeline` of ``[StandardScaler, Ridge]``.
    """
    return Pipeline(
        steps=[
            ("scale", StandardScaler(with_mean=True, with_std=True)),
            ("ridge", Ridge(alpha=alpha, random_state=random_state)),
        ]
    )
