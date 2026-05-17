"""Model artifact: pipeline + metadata envelope.

The deployable artifact is **not** just the joblib blob. It is the
joblib blob plus a sidecar ``model_metadata.json`` that captures:

- Code version (``hou53_ml.__version__``).
- Library versions (sklearn, xgboost, numpy, pandas, shap).
- Training dataset hash (sha256 of the raw CSV).
- Schema fingerprint (sorted feature list).
- Headline metrics (CV mean RMSE-log, test RMSE-log, MAE in dollars).
- Training timestamp (UTC, ISO 8601).
- Random seed.

Why a sidecar JSON instead of pickling everything in
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The metadata must be readable without unpickling — by humans, by
reviewers, by CI checks, by the API's `/model/info` endpoint. JSON
beats pickle for that. The two files are produced and consumed
atomically through this module so they never drift.
"""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

import joblib

import hou53_ml
from hou53_ml.evaluation import EvaluationReport

# Filenames are constants so the API and the training entry point cannot
# disagree about where the artifact lives.
PIPELINE_FILENAME: str = "hou53-pipeline.joblib"
METADATA_FILENAME: str = "model_metadata.json"


def _safe_version(name: str) -> str:
    try:
        return package_version(name)
    except PackageNotFoundError:
        return "unknown"


def _hash_file(path: Path, *, chunk_size: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    """Sidecar JSON written next to ``hou53-pipeline.joblib``."""

    model_name: str
    hou53_ml_version: str
    trained_at_utc: str
    python_version: str
    library_versions: dict[str, str]
    dataset_path: str
    dataset_sha256: str
    schema_fingerprint: list[str]
    feature_names_after_preprocess: list[str]
    metrics: dict[str, Any]
    random_seed: int
    extras: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> ArtifactMetadata:
        return cls(**json.loads(text))


@dataclass(slots=True)
class ModelArtifact:
    """Pipeline + metadata pair, atomically saved and loaded."""

    pipeline: Any
    metadata: ArtifactMetadata

    # --- Save ----------------------------------------------------------------
    def save(self, target_dir: Path) -> tuple[Path, Path]:
        """Persist the pipeline and the metadata to ``target_dir``.

        Args:
            target_dir: Directory to write both files to. Created if it
                does not exist.

        Returns:
            ``(pipeline_path, metadata_path)``.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        pipeline_path = target_dir / PIPELINE_FILENAME
        metadata_path = target_dir / METADATA_FILENAME

        joblib.dump(self.pipeline, pipeline_path)
        metadata_path.write_text(self.metadata.to_json(), encoding="utf-8")
        return pipeline_path, metadata_path

    # --- Load ----------------------------------------------------------------
    @classmethod
    def load(cls, source_dir: Path) -> ModelArtifact:
        """Load both files from ``source_dir``.

        Raises:
            FileNotFoundError: If either file is missing.
        """
        pipeline_path = source_dir / PIPELINE_FILENAME
        metadata_path = source_dir / METADATA_FILENAME
        if not pipeline_path.is_file():
            raise FileNotFoundError(f"missing {pipeline_path}")
        if not metadata_path.is_file():
            raise FileNotFoundError(f"missing {metadata_path}")

        pipeline = joblib.load(pipeline_path)
        metadata = ArtifactMetadata.from_json(metadata_path.read_text(encoding="utf-8"))
        return cls(pipeline=pipeline, metadata=metadata)


def build_metadata(
    *,
    model_name: str,
    dataset_path: Path,
    schema_columns: list[str],
    feature_names_after_preprocess: list[str],
    report: EvaluationReport,
    random_seed: int,
    extras: dict[str, Any] | None = None,
) -> ArtifactMetadata:
    """Construct the sidecar metadata for the artifact.

    The dataset hash and the library versions are captured here so that
    when the API later serves a prediction, ``/model/info`` can answer
    "what data trained you and with what versions?" without reaching
    out to anywhere else.
    """
    return ArtifactMetadata(
        model_name=model_name,
        hou53_ml_version=hou53_ml.__version__,
        trained_at_utc=datetime.now(tz=UTC).isoformat(),
        python_version=platform.python_version(),
        library_versions={
            "scikit-learn": _safe_version("scikit-learn"),
            "xgboost": _safe_version("xgboost"),
            "numpy": _safe_version("numpy"),
            "pandas": _safe_version("pandas"),
            "shap": _safe_version("shap"),
            "joblib": _safe_version("joblib"),
        },
        dataset_path=str(dataset_path),
        dataset_sha256=_hash_file(dataset_path),
        schema_fingerprint=sorted(schema_columns),
        feature_names_after_preprocess=list(feature_names_after_preprocess),
        metrics={
            "cv_mean_rmse_log": report.cv_mean_rmse_log,
            "cv_std_rmse_log": report.cv_std_rmse_log,
            "cv_mean_mae_dollars": report.cv_mean_mae,
            "cv_mean_r2_dollars": report.cv_mean_r2,
            "test_rmse_log": report.test_rmse_log,
            "test_mae_dollars": report.test_mae_dollars,
            "test_r2_dollars": report.test_r2_dollars,
            "test_median_ape": report.test_median_ape,
            "n_train": report.n_train,
            "n_test": report.n_test,
        },
        random_seed=random_seed,
        extras=extras or {},
    )
