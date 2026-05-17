"""Model-info endpoint behaviour."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_model_info_returns_metadata_fields(stub_client: TestClient) -> None:
    response = stub_client.get("/v1/model/info")
    assert response.status_code == 200
    body = response.json()
    assert body["model_name"] == "stub"
    assert body["model_version"] == "0.0.0-test"
    assert body["dataset_sha256"] == "0" * 64
    assert "metrics" in body
    assert body["feature_count_after_preprocess"] == 2
