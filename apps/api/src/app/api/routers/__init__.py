"""HTTP routers (FastAPI APIRouter instances)."""

from app.api.routers import health, model_info, predict

__all__ = ["health", "model_info", "predict"]
