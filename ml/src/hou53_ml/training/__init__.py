"""Training orchestration.

Public surface kept narrow — most callers should use :func:`train`
directly or the CLI (``python -m hou53_ml.training.train``).
"""

from hou53_ml.training.splits import (
    Split,
    documented_outlier_mask,
    make_split,
    stratify_target,
)
from hou53_ml.training.train import TrainingResult, train

__all__ = [
    "Split",
    "TrainingResult",
    "documented_outlier_mask",
    "make_split",
    "stratify_target",
    "train",
]
