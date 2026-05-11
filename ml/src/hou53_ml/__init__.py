"""HOU53-bot ML package.

Offline training, feature engineering, evaluation, and explainability for
the Ames Housing regressor. Re-exports only the stable public surface that
outside callers (the FastAPI service, tests, notebooks) are allowed to
depend on.
"""

from hou53_ml.config import Settings, get_settings

__all__ = ["Settings", "get_settings", "__version__"]

__version__ = "0.1.0"
