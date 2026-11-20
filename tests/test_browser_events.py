import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_valid_tab_hidden_event(client):
    response = client.post(
        "/api/browser-events",
        json={
            "candidate_id": "STU101",
            "session_id": "TEST_SESSION_001",
            "event_type": "TAB_HIDDEN",
            "timestamp": "2026-11-16T10:00:00Z",
            "metadata": {
                "duration_seconds": 5,
                "incident_id": "browser-test-001"
            }
        }
    )

    assert response.status_code == 201
    assert response.get_json()["status"] == "success"


def test_invalid_browser_event_type(client):
    response = client.post(
        "/api/browser-events",
        json={
            "candidate_id": "STU101",
            "session_id": "TEST_SESSION_002",
            "event_type": "INVALID_EVENT"
        }
    )

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"


def test_missing_required_field(client):
    response = client.post(
        "/api/browser-events",
        json={
            "candidate_id": "STU101",
            "event_type": "TAB_HIDDEN"
        }
    )

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
