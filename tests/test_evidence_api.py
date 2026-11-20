
import io

import pytest

from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):

    import app as app_module

    from examguard.audit_service import AuditService
    from examguard.evidence_service import EvidenceService

    evidence_dir = tmp_path / "evidence"
    audit_path = tmp_path / "audit.jsonl"

    audit_service = AuditService(audit_path)

    evidence_service = EvidenceService(
        evidence_dir=evidence_dir,
        audit_service=audit_service
    )

    monkeypatch.setattr(
        app_module,
        "EVIDENCE_DIR",
        evidence_dir
    )

    monkeypatch.setattr(
        app_module,
        "evidence_service",
        evidence_service
    )

    monkeypatch.setattr(
        app_module,
        "audit_service",
        audit_service
    )

    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_upload_evidence_success(client):

    response = client.post(
        "/api/evidence/upload",
        data={
            "file": (
                io.BytesIO(b"Sample exam evidence"),
                "evidence.txt"
            )
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 201

    result = response.get_json()

    assert result["status"] == "success"
    assert result["evidence"]["valid"] is True
    assert result["evidence_id"]


def test_upload_without_file(client):

    response = client.post(
        "/api/evidence/upload",
        data={},
        content_type="multipart/form-data"
    )

    assert response.status_code == 400

    assert response.get_json()["status"] == "error"


def test_validate_evidence_success(client):

    client.post(
        "/api/evidence/upload",
        data={
            "file": (
                io.BytesIO(b"Sample exam evidence"),
                "evidence.txt"
            )
        },
        content_type="multipart/form-data"
    )

    import app as app_module

    files = list(app_module.EVIDENCE_DIR.glob("*"))

    assert len(files) == 1

    response = client.post(
        "/api/evidence/validate",
        json={
            "file_name": files[0].name
        }
    )

    assert response.status_code == 200
    assert response.get_json()["evidence"]["valid"] is True


def test_evidence_access_owner_allowed(client):

    response = client.post(
        "/api/evidence/access",
        json={
            "actor_id": "STU101",
            "owner_id": "STU101",
            "evidence_id": "EV001",
            "role": "candidate"
        }
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


def test_evidence_access_other_candidate_denied(client):

    response = client.post(
        "/api/evidence/access",
        json={
            "actor_id": "STU202",
            "owner_id": "STU101",
            "evidence_id": "EV001",
            "role": "candidate"
        }
    )

    assert response.status_code == 403
    assert response.get_json()["message"] == "Access denied"


def test_evidence_access_invigilator_allowed(client):

    response = client.post(
        "/api/evidence/access",
        json={
            "actor_id": "INV001",
            "owner_id": "STU101",
            "evidence_id": "EV001",
            "role": "invigilator"
        }
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "success"
