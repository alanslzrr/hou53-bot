"""Shared pytest fixtures for the ML package."""

from __future__ import annotations

from pathlib import Path

import pytest

from hou53_ml.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """A fresh ``Settings`` instance rooted at a temporary directory.

    Tests that need isolated paths (loaders, serializers, DVC-like code)
    depend on this instead of reaching into the module-level singleton.
    Using dependency injection here is the main reason ``get_settings()``
    is a factory rather than a module-level global.
    """
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "data" / "interim").mkdir(parents=True)
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "data" / "external").mkdir(parents=True)
    (tmp_path / "models").mkdir(parents=True)
    (tmp_path / "mlruns").mkdir(parents=True)

    return Settings(repo_root=tmp_path)
