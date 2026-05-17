"""Tests for ``hou53_ml.serialization.artifact``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from hou53_ml.evaluation import EvaluationReport, FoldResult
from hou53_ml.serialization.artifact import (
    METADATA_FILENAME,
    PIPELINE_FILENAME,
    ArtifactMetadata,
    ModelArtifact,
    build_metadata,
)
from sklearn.linear_model import LinearRegression


@pytest.fixture
def dummy_report() -> EvaluationReport:
    return EvaluationReport(
        model_name="dummy",
        cv_fold_results=[
            FoldResult(
                fold=0,
                rmse_log=0.12,
                mae_dollars=15000.0,
                r2_dollars=0.85,
                median_ape=0.07,
            ),
            FoldResult(
                fold=1,
                rmse_log=0.13,
                mae_dollars=16000.0,
                r2_dollars=0.84,
                median_ape=0.08,
            ),
        ],
        cv_mean_rmse_log=0.125,
        cv_std_rmse_log=0.007,
        cv_mean_mae=15500.0,
        cv_mean_r2=0.845,
        test_rmse_log=0.14,
        test_mae_dollars=17000.0,
        test_r2_dollars=0.83,
        test_median_ape=0.075,
        n_train=1167,
        n_test=292,
    )


def test_artifact_round_trip(tmp_path: Path, dummy_report: EvaluationReport) -> None:
    """A saved-then-loaded artifact reproduces the same predictions."""
    pipeline = LinearRegression().fit(
        pd.DataFrame({"x": [1.0, 2.0, 3.0]}),
        pd.Series([10.0, 20.0, 30.0]),
    )
    # The metadata builder hashes the dataset file, so it must exist
    # before we ask for metadata.
    (tmp_path / "fake.csv").write_bytes(b"x\n1\n2\n3\n")
    metadata = build_metadata(
        model_name="linreg",
        dataset_path=tmp_path / "fake.csv",
        schema_columns=["x"],
        feature_names_after_preprocess=["x"],
        report=dummy_report,
        random_seed=42,
    )
    artifact = ModelArtifact(pipeline=pipeline, metadata=metadata)

    paths = artifact.save(tmp_path / "models")
    assert paths[0].name == PIPELINE_FILENAME
    assert paths[1].name == METADATA_FILENAME

    loaded = ModelArtifact.load(tmp_path / "models")
    # Predictions reproduce bit-for-bit.
    new_X = pd.DataFrame({"x": [4.0, 5.0]})
    original_preds = pipeline.predict(new_X)
    loaded_preds = loaded.pipeline.predict(new_X)
    assert (original_preds == loaded_preds).all()

    # Metadata round-trips through JSON.
    assert loaded.metadata.model_name == "linreg"
    assert loaded.metadata.random_seed == 42
    assert loaded.metadata.metrics["test_rmse_log"] == pytest.approx(0.14)


def test_load_raises_when_files_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ModelArtifact.load(tmp_path)


def test_metadata_to_from_json_round_trip(tmp_path: Path, dummy_report: EvaluationReport) -> None:
    (tmp_path / "fake.csv").write_bytes(b"x\n1\n")
    meta = build_metadata(
        model_name="dummy",
        dataset_path=tmp_path / "fake.csv",
        schema_columns=["x"],
        feature_names_after_preprocess=["x"],
        report=dummy_report,
        random_seed=7,
    )
    parsed = ArtifactMetadata.from_json(meta.to_json())
    assert parsed.model_name == meta.model_name
    assert parsed.dataset_sha256 == meta.dataset_sha256
    assert parsed.random_seed == 7
