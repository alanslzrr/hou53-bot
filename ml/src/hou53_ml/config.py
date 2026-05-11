"""Typed runtime settings for the ML package.

Principles applied here:

- **Single source of truth** for paths and knobs. Nothing else in the
  package hardcodes a path to `data/` or `models/`.
- **Fail fast at startup**: settings are validated when `get_settings()` is
  first called. A misspelled env var raises immediately, not three minutes
  into a training run.
- **Inversion of control**: callers receive a `Settings` instance; they do
  not reach into environment variables themselves. This makes tests
  trivial — construct a `Settings(...)` with a tmp_path and inject it.
- **Lazy and cached**: `get_settings()` uses `@lru_cache` so imports stay
  cheap and subsequent calls are free.

The actual hyperparameters live in YAML configs under `ml/configs/`;
those are loaded by the training entry point (Phase 2). This module only
handles paths, seeds, and runtime toggles that are cross-cutting.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root() -> Path:
    """Walk upward from this file until a ``pyproject.toml`` with the root
    project name is found. Falls back to three levels up.

    Used as the default when ``HOU53_REPO_ROOT`` is not set. Detecting the
    root from the file's location keeps settings working when the package
    is imported from a notebook, from pytest, or from the FastAPI app.
    """
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        marker = candidate / "pyproject.toml"
        if marker.is_file() and 'name = "hou53-bot"' in marker.read_text(
            encoding="utf-8",
        ):
            return candidate
    return here.parents[3]


class Settings(BaseSettings):
    """Runtime settings for the ML package.

    All fields are overridable via environment variables prefixed with
    ``HOU53_`` (e.g., ``HOU53_RANDOM_SEED=7``). A local ``.env`` at the
    repository root is loaded automatically when present.
    """

    model_config = SettingsConfigDict(
        env_prefix="HOU53_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # --- Paths ----------------------------------------------------------------
    repo_root: Path = Field(default_factory=_find_repo_root)
    data_dir: Path = Field(default=Path("data"))
    models_dir: Path = Field(default=Path("models"))
    mlruns_dir: Path = Field(default=Path("mlruns"))

    # --- Reproducibility ------------------------------------------------------
    random_seed: int = Field(default=42, ge=0)
    cv_folds: int = Field(default=5, ge=2, le=20)

    # --- Training knobs (applicable defaults; YAML configs override) ---------
    test_size: float = Field(default=0.2, gt=0.0, lt=0.5)
    optuna_trials: int = Field(default=50, ge=1)

    @field_validator("data_dir", "models_dir", "mlruns_dir", mode="after")
    @classmethod
    def _resolve_relative(cls, value: Path) -> Path:
        """Leave relative paths relative; callers join against ``repo_root``."""
        return value

    # --- Computed accessors ---------------------------------------------------
    @property
    def data_raw(self) -> Path:
        return (self.repo_root / self.data_dir / "raw").resolve()

    @property
    def data_interim(self) -> Path:
        return (self.repo_root / self.data_dir / "interim").resolve()

    @property
    def data_processed(self) -> Path:
        return (self.repo_root / self.data_dir / "processed").resolve()

    @property
    def data_external(self) -> Path:
        return (self.repo_root / self.data_dir / "external").resolve()

    @property
    def models_path(self) -> Path:
        return (self.repo_root / self.models_dir).resolve()

    @property
    def mlruns_path(self) -> Path:
        return (self.repo_root / self.mlruns_dir).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance.

    Cached via :func:`functools.lru_cache` so imports stay cheap. Tests that
    need a custom instance should construct ``Settings(...)`` directly and
    pass it around rather than mutating the cached singleton.
    """
    return Settings()
