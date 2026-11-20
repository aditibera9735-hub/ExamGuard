
import pytest

from examguard.models import IntegrityEvent
from examguard.scoring_engine import ScoringEngine
from examguard.scoring_config import (
    ScoringConfig,
    ScoringRule,
)


def make_event(
    event_type="TAB_HIDDEN",
    session_id="session-1",
    confidence=None,
    evidence=None,
):
    return IntegrityEvent.create(
        candidate_id="candidate-1",
        session_id=session_id,
        event_type=event_type,
        confidence=confidence,
        evidence=evidence,
    )


def test_normal_score_calculation():
    engine = ScoringEngine()

    event = make_event("TAB_HIDDEN")

    result = engine.calculate_score([event])

    assert result["score"] == 10
    assert result["scoring_version"] == "1.0.0"
    assert result["scored_event_count"] == 1


def test_multiple_events_score():
    engine = ScoringEngine()

    events = [
        make_event("TAB_HIDDEN"),
        make_event("FOCUS_LOST"),
        make_event("FULLSCREEN_EXIT"),
    ]

    result = engine.calculate_score(events)

    assert result["score"] == 20
    assert result["scored_event_count"] == 3


def test_score_is_capped_at_100():
    config = ScoringConfig(
        maximum_score=100,
        rules={
            "TAB_HIDDEN": ScoringRule(
                event_type="TAB_HIDDEN",
                weight=60,
                explanation="Tab hidden",
                requires_evidence=False,
                minimum_confidence=0.0,
            )
        }
    )

    engine = ScoringEngine(config)

    events = [
        make_event("TAB_HIDDEN"),
        make_event("TAB_HIDDEN"),
    ]

    result = engine.calculate_score(events)

    assert result["raw_score"] == 120
    assert result["score"] == 100


def test_duplicate_event_is_ignored():
    engine = ScoringEngine()

    event = make_event("TAB_HIDDEN")

    result = engine.calculate_score([event, event])

    assert result["score"] == 10
    assert len(result["skipped_events"]) == 1


def test_missing_evidence_is_skipped():
    engine = ScoringEngine()

    event = make_event(
        event_type="FACE_ABSENT",
        confidence=0.95,
    )

    result = engine.calculate_score([event])

    assert result["score"] == 0
    assert result["skipped_events"][0]["reason"] == (
        "Required evidence is missing"
    )


def test_low_confidence_event_is_skipped():
    engine = ScoringEngine()

    event = make_event(
        event_type="FACE_ABSENT",
        confidence=0.50,
        evidence={"available": True},
    )

    result = engine.calculate_score([event])

    assert result["score"] == 0
    assert result["skipped_events"][0]["reason"] == (
        "Detection confidence is below threshold"
    )


def test_custom_scoring_configuration():
    config = ScoringConfig(
        version="2.0.0",
        maximum_score=50,
        rules={
            "TAB_HIDDEN": ScoringRule(
                event_type="TAB_HIDDEN",
                weight=25,
                explanation="Custom tab hidden rule",
                requires_evidence=False,
                minimum_confidence=0.0,
            )
        }
    )

    engine = ScoringEngine(config)

    result = engine.calculate_score([
        make_event("TAB_HIDDEN")
    ])

    assert result["score"] == 25
    assert result["maximum_score"] == 50
    assert result["scoring_version"] == "2.0.0"


def test_different_sessions_are_rejected():
    engine = ScoringEngine()

    events = [
        make_event("TAB_HIDDEN", "session-1"),
        make_event("FOCUS_LOST", "session-2"),
    ]

    with pytest.raises(ValueError):
        engine.calculate_score(events)


def test_timestamp_and_version_are_returned():
    engine = ScoringEngine()

    result = engine.calculate_score([
        make_event("TAB_HIDDEN")
    ])

    assert result["calculated_at"].endswith("Z")
    assert result["scoring_version"] == "1.0.0"


def test_human_review_is_required():
    engine = ScoringEngine()

    result = engine.calculate_score([
        make_event("TAB_HIDDEN")
    ])

    assert result["human_review_required"] is True
    assert result["automatic_decision"] is False
    assert result["decision_support_only"] is True
