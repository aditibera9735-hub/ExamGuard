
from examguard.event_service import EventService


def test_duplicate_event_is_not_recorded(tmp_path):
    import logging

    events_path = tmp_path / "events.jsonl"
    service = EventService(events_path, logging.getLogger("test"))

    first = service.record_event(
        candidate_id="STU101",
        session_id="SES001",
        event_type="TAB_HIDDEN",
        source="browser",
        timestamp="2026-11-17T10:00:00+00:00",
    )

    second = service.record_event(
        candidate_id="STU101",
        session_id="SES001",
        event_type="TAB_HIDDEN",
        source="browser",
        timestamp="2026-11-17T10:00:02+00:00",
    )

    events = service.get_session_events("SES001")

    assert len(events) == 1
    assert first["event_id"] == second["event_id"]
