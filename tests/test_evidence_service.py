
import hashlib

import pytest

from examguard.evidence_service import EvidenceService


def test_valid_evidence_file(tmp_path):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    file_path = evidence_dir / "sample.txt"
    file_path.write_text("ExamGuard evidence", encoding="utf-8")

    service = EvidenceService(evidence_dir)

    result = service.validate_evidence("sample.txt")

    assert result["valid"] is True
    assert result["file_name"] == "sample.txt"
    assert result["sha256"] == hashlib.sha256(
        b"ExamGuard evidence"
    ).hexdigest()


def test_missing_evidence_file(tmp_path):
    service = EvidenceService(tmp_path / "evidence")

    with pytest.raises(ValueError, match="does not exist"):
        service.validate_evidence("missing.txt")


def test_path_traversal_is_rejected(tmp_path):
    service = EvidenceService(tmp_path / "evidence")

    with pytest.raises(ValueError, match="Path traversal"):
        service.validate_evidence("../secret.txt")


def test_wrong_hash_is_rejected(tmp_path):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    file_path = evidence_dir / "sample.txt"
    file_path.write_text("ExamGuard evidence", encoding="utf-8")

    service = EvidenceService(evidence_dir)

    with pytest.raises(ValueError, match="hash mismatch"):
        service.validate_evidence(
            "sample.txt",
            expected_sha256="wronghash"
        )


def test_correct_hash_is_accepted(tmp_path):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    file_path = evidence_dir / "sample.txt"
    file_path.write_text("ExamGuard evidence", encoding="utf-8")

    correct_hash = hashlib.sha256(
        b"ExamGuard evidence"
    ).hexdigest()

    service = EvidenceService(evidence_dir)

    result = service.validate_evidence(
        "sample.txt",
        expected_sha256=correct_hash
    )

    assert result["valid"] is True

from examguard.audit_service import AuditService


def test_owner_can_access_evidence(tmp_path):
    audit = AuditService(tmp_path / "audit.jsonl")
    service = EvidenceService(
        tmp_path / "evidence",
        audit_service=audit,
    )

    allowed = service.check_access(
        actor_id="STU101",
        owner_id="STU101",
        evidence_id="EV001",
    )

    assert allowed is True

    records = audit.list_records(target_id="EV001")
    assert len(records) == 1
    assert records[0]["outcome"] == "SUCCESS"


def test_other_candidate_access_is_denied(tmp_path):
    audit = AuditService(tmp_path / "audit.jsonl")
    service = EvidenceService(
        tmp_path / "evidence",
        audit_service=audit,
    )

    allowed = service.check_access(
        actor_id="STU202",
        owner_id="STU101",
        evidence_id="EV002",
    )

    assert allowed is False

    records = audit.list_records(target_id="EV002")
    assert len(records) == 1
    assert records[0]["outcome"] == "DENIED"


def test_invigilator_can_access_evidence(tmp_path):
    service = EvidenceService(tmp_path / "evidence")

    allowed = service.check_access(
        actor_id="INV001",
        owner_id="STU101",
        evidence_id="EV003",
        role="invigilator",
    )

    assert allowed is True
