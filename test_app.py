import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_run_compressor_missing_fields():
    response = client.post("/run_compressor", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing app_id or rec"


def test_run_compressor_valid():
    body = {"rec": "reclU63Ifw3jE3oDN", "app_id": "APP-20250812-00001"}
    response = client.post("/run_compressor", json=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 200


def test_run_via_get_valid():
    params = {"app_id": "APP-20250814-00015", "rec": "recQxgWNvJeiuUrL6"}
    response = client.get("/run_compressor", params=params)
    assert response.status_code == 200
    # Optionally check response.json() for expected keys
