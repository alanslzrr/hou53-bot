"""Health and readiness endpoint behaviour."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_returns_ok(stub_client: TestClient) -> None:
    response = stub_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_ready_when_model_loaded(stub_client: TestClient) -> None:
    response = stub_client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["model_loaded"] is True


def test_request_id_header_added_to_response(stub_client: TestClient) -> None:
    response = stub_client.get("/healthz")
    assert "x-request-id" in response.headers


def test_request_id_header_echoes_when_provided(stub_client: TestClient) -> None:
    custom_id = "test-request-12345"
    response = stub_client.get("/healthz", headers={"x-request-id": custom_id})
    assert response.headers["x-request-id"] == custom_id
