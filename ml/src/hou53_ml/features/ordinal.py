"""Ordinal encoders for the dataset's quality scales.

The Ames Housing dataset has 10 columns on the canonical Ex/Gd/TA/Fa/Po
quality scale (plus the legit-NA category we re-fill in the loader).
Encoding them as integers preserves their natural ordering and is
materially cheaper for the trees than one-hot encoding 10 x 6 = 60
columns of mostly-zero dummies.

This module is a small factory wrapping :class:`OrdinalEncoder` with
the right ``categories`` argument and a stable handling of unseen
levels at serving time.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sklearn.preprocessing import OrdinalEncoder

from hou53_ml.constants import ORDINAL_OTHER_ORDERS, QUALITY_ORDER

#: Categories in the order ``QUALITY_ORDER`` maps to 0, 1, 2, …
#: i.e. ``["NA", "Po", "Fa", "TA", "Gd", "Ex"]`` → 0..5.
QUALITY_LEVELS: tuple[str, ...] = tuple(QUALITY_ORDER.keys())

#: Values the encoder never saw at fit time map to ``-1`` at transform
#: time. We cannot reuse ``QUALITY_ORDER["NA"]`` (= 0) because sklearn
#: rejects an ``unknown_value`` that collides with an encoded category.
#: ``-1`` keeps the dtype small (``int8``) and tells the downstream
#: estimator "this is out-of-vocabulary" — for trees, that becomes its
#: own split; for the Ridge baseline, it is one tick below the worst
#: quality, which is the right inductive bias.
UNKNOWN_VALUE: int = -1


def make_quality_ordinal_encoder(n_features: int) -> OrdinalEncoder:
    """Build an :class:`OrdinalEncoder` for ``n_features`` quality columns.

    Args:
        n_features: Number of columns the encoder will be applied to.
            Used to broadcast the ``categories`` list — sklearn requires
            one entry per input column.

    Returns:
        An unfitted :class:`OrdinalEncoder` with:
          - ``categories=[QUALITY_LEVELS] * n_features`` (every column
            uses the same scale).
          - ``handle_unknown="use_encoded_value"`` and
            ``unknown_value=UNKNOWN_VALUE`` so unseen levels at
            serving time degrade to "NA" instead of throwing.
          - ``dtype=np.int8`` to keep the post-encoded matrix tiny.
    """
    if n_features <= 0:
        msg = "n_features must be positive"
        raise ValueError(msg)
    return OrdinalEncoder(
        categories=[list(QUALITY_LEVELS)] * n_features,
        handle_unknown="use_encoded_value",
        unknown_value=UNKNOWN_VALUE,
        dtype=np.int8,
    )


def make_ordered_ordinal_encoder(columns: Sequence[str]) -> OrdinalEncoder:
    """Build an encoder for dataset-specific ordered categoricals.

    Args:
        columns: Ordered feature names. Each must exist in
            :data:`hou53_ml.constants.ORDINAL_OTHER_ORDERS`.

    Returns:
        An unfitted :class:`OrdinalEncoder` whose category order matches the
        domain order for each column.
    """
    missing = [c for c in columns if c not in ORDINAL_OTHER_ORDERS]
    if missing:
        msg = f"missing ordinal category order(s): {missing}"
        raise ValueError(msg)
    return OrdinalEncoder(
        categories=[list(ORDINAL_OTHER_ORDERS[c]) for c in columns],
        handle_unknown="use_encoded_value",
        unknown_value=UNKNOWN_VALUE,
        dtype=np.int8,
    )
