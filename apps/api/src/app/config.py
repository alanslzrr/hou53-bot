"""Typed runtime settings for the API.

Every knob lives here. Nothing else in the service reads ``os.environ``
directly. The ``Settings`` instance is constructed once at startup and
passed through the dependency-injection container so tests can inject
their own.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _detect_repo_root() -> Path:
    """Walk upwards from this file until the root ``pyproject.toml`` is found.

    Used as the default for ``models_dir``.
    """
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        marker = candidate / "pyproject.toml"
        if marker.is_file() and 'name = "hou53-bot"' in marker.read_text(encoding="utf-8"):
            return candidate
    return here.parents[4]


class Settings(BaseSettings):
    """Runtime configuration for the inference service.

    Override any field via the matching ``HOU53_API_<UPPER>`` env var
    (e.g., ``HOU53_API_LOG_LEVEL=DEBUG``). A ``.env`` file at the repo
    root is loaded automatically when present.
    """

    model_config = SettingsConfigDict(
        env_prefix="HOU53_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # --- Artifact ------------------------------------------------------------
    repo_root: Path = Field(default_factory=_detect_repo_root)
    models_dir_name: str = Field(default="models")
    pipeline_filename: str = Field(default="hou53-pipeline.joblib")
    metadata_filename: str = Field(default="model_metadata.json")

    # --- Behaviour -----------------------------------------------------------
    shap_top_k: int = Field(default=5, ge=1, le=20)
    shap_background_size: int = Field(default=50, ge=10, le=500)
    shap_background_seed: int = Field(default=42)

    # --- HTTP ---------------------------------------------------------------
    cors_allow_origins: tuple[str, ...] = Field(
        default=("http://localhost:3000",),
        description=(
            "Origins allowed by the CORS middleware. Set to a tuple "
            "of explicit origins in production; never '*' for an API "
            "that may grow auth-protected endpoints."
        ),
    )

    # --- Logging ------------------------------------------------------------
    log_level: str = Field(default="INFO")
    log_format: str = Field(
        default="json",
        description="'json' for production drains, 'console' for local dev.",
    )

    # --- Computed accessors -------------------------------------------------
    @property
    def models_dir(self) -> Path:
        return (self.repo_root / self.models_dir_name).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide cached settings instance.

    Tests that need a custom configuration construct ``Settings(...)``
    directly and override the FastAPI dependency, rather than mutating
    the singleton.
    """
    return Settings()
