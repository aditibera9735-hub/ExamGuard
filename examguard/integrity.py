from __future__ import annotations

from .models import IntegrityEvent

EVENT_POINTS = {
    "FACE_PRESENT": 0,
    "FACE_ABSENT": 10,
    "MULTIPLE_FACES": 20,
    "DETECTION_FAILURE": 0,
    "CAMERA_UNAVAILABLE": 0,
    "SESSION_INTERRUPTED": 0,
}


def summarize_integrity(events: list[IntegrityEvent]) -> dict:
    for event in events:
        event.validate()

    total = min(100, sum(EVENT_POINTS[event.event_type] for event in events))
    if total < 20:
        category = "LOW"
    elif total < 50:
        category = "MODERATE"
    else:
        category = "HIGH"

    reasons = [
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "points": EVENT_POINTS[event.event_type],
            "explanation": f"{event.event_type} contributes {EVENT_POINTS[event.event_type]} demonstration points",
        }
        for event in events
        if EVENT_POINTS[event.event_type] > 0
    ]
    return {
        "session_id": events[0].session_id if events else None,
        "score": total,
        "category": category,
        "event_count": len(events),
        "reasons": reasons,
        "human_review_required": category in {"MODERATE", "HIGH"},
        "notice": (
            "This illustrative score is a review aid, not proof of misconduct. "
            "Technical issues and false detections must be considered by an authorized invigilator."
        ),
    }
