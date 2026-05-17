"""Infrastructure adapters (model loader, logging).

Hidden behind these modules so the rest of the service depends on
abstractions, not on filesystem / sklearn / structlog directly.
"""

from app.infra.logging import configure_logging, get_logger
from app.infra.model_loader import LoadedModel, load_model

__all__ = ["LoadedModel", "configure_logging", "get_logger", "load_model"]
