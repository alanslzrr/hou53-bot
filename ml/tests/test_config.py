"""Smoke tests for the settings module.

These exist so that a broken import, a missing dependency, or a regression
in path resolution shows up immediately — not three phases from now.
"""

from __future__ import annotations

from pathlib import Path

from hou53_ml.config import Settings, get_settings


class TestSettings:
    def test_get_settings_returns_cached_instance(self) -> None:
        first = get_settings()
        second = get_settings()
        assert first is second, "get_settings() must cache its result"

    def test_default_paths_are_absolute(self) -> None:
        s = get_settings()
        assert s.data_raw.is_absolute()
        assert s.models_path.is_absolute()
        assert s.mlruns_path.is_absolute()

    def test_injected_root_overrides_detection(self, tmp_path: Path) -> None:
        s = Settings(repo_root=tmp_path)
        assert s.data_raw == tmp_path / "data" / "raw"
        assert s.models_path == tmp_path / "models"

    def test_random_seed_defaults_are_deterministic(self) -> None:
        assert get_settings().random_seed == 42
        assert get_settings().cv_folds == 5
