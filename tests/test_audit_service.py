
import pytest

from examguard.audit_service import AuditService


def test_record_action_creates_audit_record(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    service = AuditService(audit_path)

    record = service.record_action(
        actor_id="ADMIN001",
        action="REVIEW_EVENT",
        target_type="INTEGRITY_EVENT",
        target_id="evt-test-001",
        details={"review_status": "REVIEWED"}
    )

    assert record.actor_id == "ADMIN001"
    assert record.action == "REVIEW_EVENT"
    assert record.target_id == "evt-test-001"

    records = service.list_records()

    assert len(records) == 1
    assert records[0]["target_id"] == "evt-test-001"


def test_list_records_filters_by_target_id(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    service = AuditService(audit_path)

    service.record_action(
        actor_id="ADMIN001",
        action="REVIEW_EVENT",
        target_type="INTEGRITY_EVENT",
        target_id="evt-001"
    )

    service.record_action(
        actor_id="ADMIN001",
        action="REVIEW_EVENT",
        target_type="INTEGRITY_EVENT",
        target_id="evt-002"
    )

    records = service.list_records(target_id="evt-001")

    assert len(records) == 1
    assert records[0]["target_id"] == "evt-001"


def test_record_action_rejects_missing_actor_id(tmp_path):
    service = AuditService(tmp_path / "audit.jsonl")

    with pytest.raises(ValueError):
        service.record_action(
            actor_id="",
            action="REVIEW_EVENT",
            target_type="INTEGRITY_EVENT",
            target_id="evt-001"
        )
