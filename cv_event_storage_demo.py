import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from examguard.cv_result_adapter import CVResultAdapter
from examguard.event_service import EventService
from examguard.logging_config import configure_logging


# Project directories
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# Configure logging
configure_logging()

logger = logging.getLogger(__name__)


# Initialize event storage
event_service = EventService(
    events_path=DATA_DIR / "cv_events.jsonl",
    logger=logger
)


# Initialize CV adapter
monitor = CVResultAdapter(
    absence_threshold_seconds=5
)


# Candidate and session information
candidate_id = "candidate-demo-001"
session_id = "session-cv-demo-001"


# Simulated CV observations
start = datetime.now(timezone.utc)

cv_results = [
    {
        "face_detected": True,
        "detection_available": True,
        "confidence": 0.98,
        "timestamp": start
    },
    {
        "face_detected": True,
        "detection_available": True,
        "confidence": 0.97,
        "timestamp": start + timedelta(seconds=1)
    },
    {
        "face_detected": False,
        "detection_available": True,
        "confidence": None,
        "timestamp": start + timedelta(seconds=2)
    },
    {
        "face_detected": False,
        "detection_available": True,
        "confidence": None,
        "timestamp": start + timedelta(seconds=5)
    },
    {
        "face_detected": False,
        "detection_available": True,
        "confidence": None,
        "timestamp": start + timedelta(seconds=8)
    },
    {
        "face_detected": True,
        "detection_available": True,
        "confidence": 0.96,
        "timestamp": start + timedelta(seconds=10)
    },
    {
        "face_detected": False,
        "detection_available": False,
        "confidence": None,
        "timestamp": start + timedelta(seconds=11)
    },
    {
        "face_detected": True,
        "detection_available": True,
        "confidence": 0.95,
        "timestamp": start + timedelta(seconds=13)
    }
]


def save_completed_event(event):
    """Save a completed face event using EventService."""

    if event is None:
        return

    event_type = event["event_type"]

    severity = {
        "FACE_PRESENT": "LOW",
        "FACE_ABSENT": "MEDIUM",
        "DETECTION_FAILURE": "LOW"
    }.get(event_type, "MEDIUM")

    metadata = {
        "start_time": event["start_time"],
        "end_time": event["end_time"],
        "duration_seconds": event["duration_seconds"],
        "observation_status": event["observation_status"],
        "detector": "mock-cv-adapter"
    }

    stored_event = event_service.record_event(
        candidate_id=candidate_id,
        session_id=session_id,
        event_type=event_type,
        severity=severity,
        source="mock-cv-monitor",
        confidence=event["confidence"],
        metadata=metadata
    )

    print("\nEvent saved successfully:")
    print(stored_event)


# Process CV results
print("Starting CV Event Storage Demo...")

for result in cv_results:
    completed_event = monitor.process_cv_result(result)

    if completed_event:
        save_completed_event(completed_event)


# Finish monitoring
final_event = monitor.finish_session(
    start + timedelta(seconds=14)
)

if final_event:
    save_completed_event(final_event)


# Retrieve saved events
print("\nRetrieving saved session events...")

saved_events = event_service.get_session_events(session_id)

for event in saved_events:
    print(
        event.event_type,
        "|",
        event.session_id,
        "|",
        event.timestamp
    )


print("\nTotal saved events:", len(saved_events))

print("\nStorage location:")
print(DATA_DIR / "cv_events.jsonl")

print("\nCV event storage demo completed.")