import logging
from datetime import datetime, timedelta, timezone

from examguard.cv_result_adapter import CVResultAdapter
from examguard.event_service import EventService


def test_cv_events_are_saved_correctly(tmp_path):

    
    event_file = tmp_path / "test_events.jsonl"

    service = EventService(
        events_path=event_file,
        logger=logging.getLogger("test")
    )

    
    monitor = CVResultAdapter(absence_threshold_seconds=5)

    candidate_id = "test-candidate"
    session_id = "test-session"

    start = datetime(
        2026, 11, 3, 10, 0, 0,
        tzinfo=timezone.utc
    )

    
    observations = [
        (True, True, 0.98, 0),
        (True, True, 0.97, 1),
        (False, True, None, 2),
        (False, True, None, 5),
        (False, True, None, 8),
        (True, True, 0.96, 10),
        (False, False, None, 11),
        (True, True, 0.95, 13),
    ]

    
    def save_event(event):

        if event is None:
            return

        service.record_event(
            candidate_id=candidate_id,
            session_id=session_id,
            event_type=event["event_type"],
            severity="MEDIUM",
            source="test-cv-monitor",
            confidence=event["confidence"],
            metadata={
                "start_time": event["start_time"],
                "end_time": event["end_time"],
                "duration_seconds": event["duration_seconds"],
                "observation_status": event["observation_status"]
            }
        )


    for face, available, confidence, seconds in observations:

        result = {
            "face_detected": face,
            "detection_available": available,
            "confidence": confidence,
            "timestamp": start + timedelta(seconds=seconds)
        }

        event = monitor.process_cv_result(result)
        save_event(event)

    
    final_event = monitor.finish_session(
        start + timedelta(seconds=14)
    )

    save_event(final_event)

    
    saved_events = service.get_session_events(session_id)

    
    assert len(saved_events) == 5

    
    expected_types = [
        "FACE_PRESENT",
        "FACE_ABSENT",
        "FACE_PRESENT",
        "DETECTION_FAILURE",
        "FACE_PRESENT"
    ]

    actual_types = [
        event.event_type for event in saved_events
    ]

    assert actual_types == expected_types

    
    event_ids = [event.event_id for event in saved_events]

    assert all(event_ids)
    assert len(set(event_ids)) == 5

    
    sequence_numbers = [
        event.sequence_number for event in saved_events
    ]

    assert sequence_numbers == [1, 2, 3, 4, 5]

    
    assert saved_events[1].metadata["duration_seconds"] == 8.0

    
    assert (
        saved_events[3].metadata["observation_status"]
        == "UNCERTAIN"
    )

    
    assert all(
        event.session_id == session_id
        for event in saved_events
    )

    print("CV event storage integration test passed!")