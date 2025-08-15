import pytest
from fastapi.testclient import TestClient
from app import app
from unittest.mock import patch
from services.llm_evaluator import llm_evaluate_applicant

client = TestClient(app)


@pytest.fixture
def sample_applicant_json():
    return {
        "personal": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "location": "New York, US",
            "linkedin": "https://linkedin.com/in/johndoe",
        },
        "experience": [
            {
                "company": "Google",
                "title": "Senior Software Engineer",
                "start": "2018-01-01",
                "end": "2022-12-31",
                "tech": "Python, JavaScript, Cloud",
            },
            {
                "company": "Meta",
                "title": "Software Engineer",
                "start": "2015-03-01",
                "end": "2017-12-31",
                "tech": "React, Node.js, TypeScript",
            },
        ],
        "salary": {"preferred_rate": "90", "min_rate": "75", "currency": "USD", "availability": "40"},
    }


def test_run_llm_evaluate_applicant(sample_applicant_json):
    result = llm_evaluate_applicant(sample_applicant_json)

    # Make sure we got a dict back
    assert isinstance(result, dict), "Expected a dict from llm_evaluate_applicant"

    # Make sure all expected keys exist
    for key in ["summary", "score", "issues", "follow_ups"]:
        assert key in result, f"Missing key in result: {key}"

    # Optionally check types
    assert isinstance(result["summary"], str)
    assert isinstance(result["score"], int)
    assert isinstance(result["issues"], str)
    assert isinstance(result["follow_ups"], str)


def test_run_compressor_missing_fields():
    response = client.post("/run_compressor", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing app_id or rec"


def test_run_compressor_valid():
    body = {"rec": "reclU63Ifw3jE3oDN", "app_id": "APP-20250812-00001"}
    response = client.post("/run_compressor", json=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 200


def test_run_compressor_via_get_valid():
    params = {"app_id": "APP-20250814-00015", "rec": "recQxgWNvJeiuUrL6"}
    response = client.get("/run_compressor", params=params)
    assert response.status_code == 200
    # Optionally check response.json() for expected keys


def test_run_compressor_via_get_all():
    response = client.get("/run_compressor_all")
    assert response.status_code == 200


def test_run_decompressor():
    response = client.post("/run_decompressor", json={"app_id": "APP-20250814-00014", "rec": "recyJj4wsQqqToUUp"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["rec"] == "recyJj4wsQqqToUUp"


def test_run_decompressor_via_get():
    response = client.get("/run_decompressor", params={"app_id": "APP-20250814-00015", "rec": "recQxgWNvJeiuUrL6"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["rec"] == "recQxgWNvJeiuUrL6"


def test_run_decompressor_all():
    response = client.post("/run_decompressor_all")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
