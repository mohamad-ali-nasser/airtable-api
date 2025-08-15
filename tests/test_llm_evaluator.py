import pytest
from unittest.mock import patch, MagicMock
import json
from services.llm_evaluator import llm_evaluate_applicant


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


@pytest.fixture
def payload():
    return {
        "summary": (
            "John Doe is a highly experienced software engineer with 7+ years at top tech "
            "companies (Google, Meta). Proficient in Python, JavaScript, React, and cloud "
            "technologies. Currently seeking $90/hr with full-time availability. Based in New York."
        ),
        "score": 9,
        "issues": "No current role listed, limited details on specific project achievements",
        "follow_ups": (
            "• What projects are you most proud of from your time at Google?\n"
            "• What kind of team structure do you work best in?\n"
            "• Are you open to remote work or only local opportunities?"
        ),
    }


@pytest.fixture
def empty_applicant():
    return {"personal": {}, "experience": [], "salary": {}}


@pytest.fixture
def payload_empty():
    # what the LLM would return; choose any consistent stub
    return {
        "summary": "Insufficient data provided. Please supply experience, role, and rate details.",
        "score": 0,
        "issues": "Missing experience, missing role/skills, missing rates/availability",
        "follow_ups": (
            "• What role are you targeting?\n"
            "• Summarize your most recent experience and key skills.\n"
            "• What is your preferred hourly rate and weekly availability?"
        ),
    }


@pytest.fixture
def mock_response(payload):
    """Return a fake SDK response object whose .output_text is valid JSON."""
    fake_resp = MagicMock()
    fake_resp.output_text = json.dumps(payload)
    return fake_resp


@pytest.fixture
def mock_empty_response(payload_empty):
    fake = MagicMock()
    fake.output_text = json.dumps(payload_empty)  # valid JSON string
    return fake


@patch("services.llm_evaluator.client.responses.create")
def test_llm_evaluate_applicant(mock_create, sample_applicant_json, mock_response, payload):
    # Arrange: make the SDK call return our fake response
    mock_create.return_value = mock_response

    # Act
    result = llm_evaluate_applicant(sample_applicant_json)

    # Assert SDK call & prompt
    mock_create.assert_called_once()
    _, kwargs = mock_create.call_args
    assert kwargs["model"] == "gpt-5-nano"
    assert "Applicant JSON:" in kwargs["input"]
    assert json.dumps(sample_applicant_json, separators=(",", ":")) in kwargs["input"]

    # Assert parsed result (dict), not the MagicMock
    assert isinstance(result, dict)
    for k in ["summary", "score", "issues", "follow_ups"]:
        assert k in result

    # Optional: exact value checks
    assert result["score"] == payload["score"]
    assert "highly experienced software engineer" in result["summary"]
    assert "No current role listed" in result["issues"]
    assert "What projects are you most proud of" in result["follow_ups"]


@patch("services.llm_evaluator.client.responses.create")
def test_llm_evaluate_empty_applicant(mock_create, mock_empty_response, empty_applicant, payload_empty):
    # Arrange
    mock_create.return_value = mock_empty_response

    # Act
    result = llm_evaluate_applicant(empty_applicant)

    # Assert SDK call & prompt content
    mock_create.assert_called_once()
    _, kwargs = mock_create.call_args
    assert json.dumps(empty_applicant, separators=(",", ":")) in kwargs["input"]

    # Assert we got a dict parsed from JSON (NOT the MagicMock)
    assert isinstance(result, dict)
    for k in ["summary", "score", "issues", "follow_ups"]:
        assert k in result

    # Optionally assert exact values (recommended, since you control the stub)
    assert result == payload_empty
    assert result["score"] == 0
    assert "Insufficient data" in result["summary"]


@patch("services.llm_evaluator.client.responses.create", side_effect=Exception("API Error"))
def test_llm_evaluate_applicant_error_handling(mock_create, sample_applicant_json):
    # Test error handling
    with pytest.raises(Exception) as excinfo:
        llm_evaluate_applicant(sample_applicant_json)

    assert "API Error" in str(excinfo.value)
