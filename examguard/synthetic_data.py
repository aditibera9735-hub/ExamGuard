from datetime import datetime, timedelta, timezone

from .models import IntegrityEvent


def make_synthetic_events(
    session_id: str = "session-001",
    candidate_id: str = "candidate-001",
) -> list[IntegrityEvent]:
    """Build deterministic demo events using the canonical model factory."""
    start = datetime(2026, 10, 29, 9, 15, 0, tzinfo=timezone.utc)
    rows = [
        ("SESSION_STARTED", 0, "system", {}),
        ("FACE_PRESENT", 3, "computer_vision", {"confidence": 0.98}),
        ("FACE_ABSENT", 8, "computer_vision", {"duration_seconds": 5}),
        ("MULTIPLE_FACES", 20, "computer_vision", {"face_count": 2}),
        ("CAMERA_UNAVAILABLE", 28, "computer_vision", {"reason": "device_not_found"}),
        ("SESSION_ENDED", 60, "system", {}),
    ]

    events = []
    for kind, seconds, source, metadata in rows:
        timestamp = (
            start + timedelta(seconds=seconds)
        ).isoformat(timespec="seconds").replace("+00:00", "Z")

        events.append(
            IntegrityEvent.create(
                candidate_id=candidate_id,
                session_id=session_id,
                event_type=kind,
                source=source,
                metadata=metadata,
                timestamp=timestamp,
            )
        )

    return events
