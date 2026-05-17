"""Feature engineering: derived columns + preprocessor builder.

Public surface is intentionally small — anything that needs to compose
features goes through :func:`build_preprocessor` (which already knows
about :class:`DerivedFeatures`) rather than wiring transformers by hand.
"""

from hou53_ml.features.builders import build_preprocessor
from hou53_ml.features.derived import OUTPUT_NAMES, DerivedFeatures
from hou53_ml.features.imputation import NeighborhoodLotFrontageImputer
from hou53_ml.features.ordinal import (
    QUALITY_LEVELS,
    UNKNOWN_VALUE,
    make_ordered_ordinal_encoder,
    make_quality_ordinal_encoder,
)
from hou53_ml.features.target_encoding import NeighborhoodTargetEncoder

__all__ = [
    "OUTPUT_NAMES",
    "QUALITY_LEVELS",
    "UNKNOWN_VALUE",
    "DerivedFeatures",
    "NeighborhoodLotFrontageImputer",
    "NeighborhoodTargetEncoder",
    "build_preprocessor",
    "make_ordered_ordinal_encoder",
    "make_quality_ordinal_encoder",
]
