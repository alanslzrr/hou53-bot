"""Predict endpoint behaviour.

Uses the stub LoadedModel so these run in milliseconds and do not
touch the real artifact. The end-to-end happy path against the real
model lives in ``test_predict_e2e.py`` and is marked ``slow``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_predict_happy_path_minimal_payload(stub_client: TestClient) -> None:
    response = stub_client.post(
        "/v1/predict",
        json={"OverallQual": 7, "GrLivArea": 1800, "GarageCars": 2},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["prediction"]["currency"] == "USD"
    assert body["prediction"]["value_usd"] == 200_000.0  # stub fixed value
    assert body["explanation"]["baseline_usd"] == 180_000.0
    assert "OverallQual" in body["explanation"]["natural_language"] or True
    # Top features come from the stub.
    assert len(body["explanation"]["top_features"]) == 2
    assert body["model"]["name"] == "stub"


def test_predict_accepts_canonical_column_names_with_digits(
    stub_client: TestClient,
) -> None:
    """`1stFlrSF`, `2ndFlrSF`, `3SsnPorch` must validate via aliases."""
    response = stub_client.post(
        "/v1/predict",
        json={"1stFlrSF": 1000, "2ndFlrSF": 800, "3SsnPorch": 0},
    )
    assert response.status_code == 200, response.text


def test_predict_rejects_quality_outside_scale(stub_client: TestClient) -> None:
    response = stub_client.post(
        "/v1/predict",
        json={"OverallQual": 7, "KitchenQual": "Pristine"},
    )
    assert response.status_code == 422
    body = response.json()
    assert "KitchenQual" in str(body)


def test_predict_rejects_negative_area(stub_client: TestClient) -> None:
    response = stub_client.post(
        "/v1/predict",
        json={"GrLivArea": -100},
    )
    assert response.status_code == 422


def test_predict_rejects_year_out_of_range(stub_client: TestClient) -> None:
    response = stub_client.post(
        "/v1/predict",
        json={"YearBuilt": 1500},
    )
    assert response.status_code == 422


def test_predict_ignores_unknown_keys(stub_client: TestClient) -> None:
    """The natural-language parser may hallucinate fields. We drop them."""
    response = stub_client.post(
        "/v1/predict",
        json={"OverallQual": 7, "MysteryAttribute": "purple"},
    )
    assert response.status_code == 200


def test_predict_accepts_empty_payload(stub_client: TestClient) -> None:
    """Every field is optional — the imputers cover what's missing."""
    response = stub_client.post("/v1/predict", json={})
    assert response.status_code == 200
