
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

from examguard.face_event_adapter import FaceEventAdapter
from examguard.event_service import EventService
from examguard.logging_config import configure_logging


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"

DATA.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

logger = configure_logging(
    LOGS / "examguard.log",
    level=logging.INFO,
)

event_service = EventService(
    DATA / "events.jsonl",
    logger,
)

monitor = FaceEventAdapter(
    absence_threshold_seconds=5
)

start = datetime.now(timezone.utc)

observations = [
    ("FACE_PRESENT", 0.98, 0),
    ("FACE_PRESENT", 0.97, 1),
    ("FACE_ABSENT", None, 2),
    ("FACE_ABSENT", None, 5),
    ("FACE_ABSENT", None, 8),
    ("FACE_PRESENT", 0.96, 10),
    ("DETECTION_FAILURE", None, 11),
    ("FACE_PRESENT", 0.95, 13),
]

candidate_id = "STU101"
session_id = "SES001"


def save_completed_event(item):
    severity_map = {
        "FACE_PRESENT": "INFO",
        "FACE_ABSENT": "MEDIUM",
        "DETECTION_FAILURE": "MEDIUM",
    }

    saved = event_service.record_event(
        candidate_id=candidate_id,
        session_id=session_id,
        event_type=item["event_type"],
        severity=severity_map[item["event_type"]],
        source="face-monitor",
        timestamp=item["end_time"],
        confidence=item["confidence"],
        metadata={
            "start_time": item["start_time"],
            "end_time": item["end_time"],
            "duration_seconds": item["duration_seconds"],
            "observation_status": item["observation_status"],
        },
    )

    print(
        f"Saved {saved['event_type']} "
        f"| event_id={saved['event_id']}"
    )


for state, confidence, seconds in observations:
    timestamp = start + timedelta(seconds=seconds)

    completed = monitor.process_observation(
        state=state,
        confidence=confidence,
        timestamp=timestamp,
    )

    if completed:
        save_completed_event(completed)



final_event = monitor.finish_session(
    timestamp=start + timedelta(seconds=14)
)

if final_event:
    save_completed_event(final_event)


print("\nEvents saved for this session:")

saved_events = event_service.get_session_events(
    session_id
)

for event in saved_events:
    print(
        event.event_type,
        "| severity:", event.severity,
        "| timestamp:", event.timestamp,
    )

print("\nStorage file:", DATA / "events.jsonl")
