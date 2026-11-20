
import logging

import pytest

from examguard.audit_service import AuditService
from examguard.event_service import EventService
from examguard.scoring_service import ScoringService


@pytest.fixture
def services(tmp_path):

    logger = logging.getLogger("scoring-service-test")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())

    event_service = EventService(
        tmp_path / "events.jsonl",
        logger
    )

    audit_service = AuditService(
        tmp_path / "audit.jsonl"
    )

    scoring_service = ScoringService(
        event_service=event_service,
        scores_path=tmp_path / "scores.jsonl",
        audit_service=audit_service,
    )

    return event_service, scoring_service, audit_service


def create_session(event_service):

    event_service.record_event(
        "STU101",
        "SESSION001",
        "TAB_HIDDEN",
        source="browser",
    )

    event_service.record_event(
        "STU101",
        "SESSION001",
        "FOCUS_LOST",
        source="browser",
    )


def test_calculate_and_store_score(services):

    event_service, scoring_service, audit_service = services

    create_session(event_service)

    result = scoring_service.calculate_and_store(
        "SESSION001",
        actor_id="STU101",
    )

    assert result["score"] == 15
    assert result["candidate_id"] == "STU101"
    assert result["scoring_version"] == "1.0.0"

    assert scoring_service.store.read_all()[0]["score_id"]

    audit_records = audit_service.list_records(
        target_id=result["score_id"]
    )

    assert len(audit_records) == 2

    actions = {
        record["action"]
        for record in audit_records
    }

    assert "SCORE_ACCESS" in actions
    assert "SCORE_CALCULATED" in actions


def test_other_candidate_cannot_calculate_score(services):

    event_service, scoring_service, audit_service = services

    create_session(event_service)

    with pytest.raises(PermissionError):
        scoring_service.calculate_and_store(
            "SESSION001",
            actor_id="STU202",
        )

    assert scoring_service.store.read_all() == []

    audit_records = audit_service.list_records()

    assert any(
        record["outcome"] == "DENIED"
        for record in audit_records
    )


def test_invigilator_can_calculate_score(services):

    event_service, scoring_service, _ = services

    create_session(event_service)

    result = scoring_service.calculate_and_store(
        "SESSION001",
        actor_id="INV001",
        role="invigilator",
    )

    assert result["score"] == 15


def test_candidate_can_retrieve_own_score(services):

    event_service, scoring_service, _ = services

    create_session(event_service)

    scoring_service.calculate_and_store(
        "SESSION001",
        actor_id="STU101",
    )

    result = scoring_service.get_score(
        "SESSION001",
        actor_id="STU101",
    )

    assert result is not None
    assert result["candidate_id"] == "STU101"


def test_other_candidate_cannot_retrieve_score(services):

    event_service, scoring_service, _ = services

    create_session(event_service)

    scoring_service.calculate_and_store(
        "SESSION001",
        actor_id="STU101",
    )

    with pytest.raises(PermissionError):
        scoring_service.get_score(
            "SESSION001",
            actor_id="STU202",
        )


def test_invigilator_can_retrieve_score(services):

    event_service, scoring_service, _ = services

    create_session(event_service)

    scoring_service.calculate_and_store(
        "SESSION001",
        actor_id="STU101",
    )

    result = scoring_service.get_score(
        "SESSION001",
        actor_id="INV001",
        role="invigilator",
    )

    assert result["candidate_id"] == "STU101"


def test_recalculation_preserves_history(services):

    event_service, scoring_service, _ = services

    create_session(event_service)

    first = scoring_service.calculate_and_store(
        "SESSION001",
        actor_id="STU101",
    )

    second = scoring_service.recalculate(
        "SESSION001",
        actor_id="INV001",
        role="invigilator",
    )

    records = scoring_service.store.read_all()

    assert len(records) == 2
    assert first["score_id"] != second["score_id"]
    assert second["calculation_type"] == "RECALCULATION"
    assert first["score"] == second["score"]


def test_missing_session_score_returns_none(services):

    _, scoring_service, _ = services

    result = scoring_service.get_score(
        "UNKNOWN",
        actor_id="STU101",
    )

    assert result is None


def test_recalculate_without_previous_score_fails(services):

    _, scoring_service, _ = services

    with pytest.raises(ValueError):
        scoring_service.recalculate(
            "UNKNOWN",
            actor_id="INV001",
            role="invigilator",
        )
