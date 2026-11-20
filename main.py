
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from examguard.audit_service import AuditService
from examguard.event_service import EventService
from examguard.integrity import summarize_integrity
from examguard.logging_config import configure_logging
from examguard.synthetic_data import make_synthetic_events




ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"




def run_demo(
    reset: bool = False,
    debug: bool = False
) -> None:

    
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    
    if reset:

        for name in ("events.jsonl", "audit.jsonl"):

            path = DATA / name

            if path.exists():
                path.unlink()


    logger = configure_logging(
        LOGS / "examguard.log",
        level=logging.DEBUG if debug else logging.INFO
    )

    logger.info(
        "ExamGuard demo started",
        extra={
            "session_id": None,
            "event_id": None
        }
    )


    events = EventService(
        DATA / "events.jsonl",
        logger
    )

    audit = AuditService(
        DATA / "audit.jsonl"
    )


    print("\n=== SYNTHETIC EVENT GENERATION ===")

    synthetic_events = make_synthetic_events()

    for item in synthetic_events:

        saved = events.record_event(
            candidate_id=item.candidate_id,
            session_id=item.session_id,
            event_type=item.event_type,
            severity=item.severity,
            source=item.source,
            metadata=item.metadata,
            evidence=item.evidence,
            confidence=item.confidence,
            timestamp=item.timestamp,
        )

        print(
            f"Stored {saved['event_type']:<20} "
            f"session={saved['session_id']} "
            f"event_id={saved['event_id']}"
        )


    print("\n=== MANUAL MOCK OBSERVATIONS ===")

    examples = [

        {
            "event_type": "FACE_PRESENT",
            "timestamp": "2026-10-29T09:15:00Z",
            "severity": "INFO",
            "metadata": {
                "detected_face_count": 1,
                "frame_number": 100
            },
            "confidence": 0.98,
        },

        {
            "event_type": "FACE_ABSENT",
            "timestamp": "2026-10-29T09:15:08Z",
            "severity": "MEDIUM",
            "metadata": {
                "duration_seconds": 8,
                "frame_number": 340
            },
            "confidence": 0.87,
        },

        {
            "event_type": "MULTIPLE_FACES",
            "timestamp": "2026-10-29T09:15:20Z",
            "severity": "HIGH",
            "metadata": {
                "detected_face_count": 2,
                "frame_number": 700
            },
            "confidence": 0.82,
        },

        {
            "event_type": "CAMERA_UNAVAILABLE",
            "timestamp": "2026-10-29T09:15:28Z",
            "severity": "MEDIUM",
            "metadata": {
                "reason": "mock camera timeout"
            },
            "confidence": None,
        },
    ]

    recorded = []

    for item in examples:

        event = events.record_event(
            candidate_id="cand-demo-001",
            session_id="sess-demo-001",
            event_type=item["event_type"],
            severity=item["severity"],
            source="mock-monitor",
            timestamp=item["timestamp"],
            metadata=item["metadata"],
            confidence=item["confidence"],
        )

        recorded.append(event)

        print(
            f"Stored {event['event_type']:<20} "
            f"session={event['session_id']} "
            f"event_id={event['event_id']}"
        )

        logger.info(
            "Manual mock event recorded",
            extra={
                "session_id": event["session_id"],
                "event_id": event["event_id"]
            }
        )

    

    print("\n=== EVENTS IN CHRONOLOGICAL ORDER ===")

    ordered = events.list_events("sess-demo-001")

    for event in ordered:

        print(
            f"seq={event.sequence_number} | "
            f"{event.timestamp} | "
            f"{event.event_type:<20} | "
            f"severity={event.severity} | "
            f"id={event.event_id}"
        )

    print(
        f"\nRetrieved {len(ordered)} events "
        f"for sess-demo-001"
    )

    

    audit_record = audit.record_action(
        actor_id="invigilator-demo-001",
        action="REVIEW_SESSION",
        target_type="EXAM_SESSION",
        target_id="sess-demo-001",
        details={
            "note": "Demo review started; no misconduct conclusion"
        },
    )

    logger.info(
        "Audit action recorded: id=%s action=%s",
        audit_record.audit_id,
        audit_record.action
    )

    print("\n=== AUDIT TRAIL ===")

    audit_records = audit.list_records(
        target_id="sess-demo-001"
    )

    print(
        json.dumps(
            audit_records,
            indent=2,
            ensure_ascii=False
        )
    )



    summary = summarize_integrity(ordered)

    print("\n=== INTEGRITY SUMMARY ===")

    print(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False
        )
    )

    logger.info(
        "ExamGuard demo completed",
        extra={
            "session_id": "sess-demo-001",
            "event_id": None
        }
    )

    print("\n=== DEMO COMPLETED ===")

    print(f"Event data : {DATA / 'events.jsonl'}")
    print(f"Audit data : {DATA / 'audit.jsonl'}")
    print(f"Log file   : {LOGS / 'examguard.log'}")




def main() -> None:

    parser = argparse.ArgumentParser(
        description="ExamGuard Sprint 2 Team 3 Demo"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="clear previous event and audit data"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable DEBUG logging"
    )

    args = parser.parse_args()

    run_demo(
        reset=args.reset,
        debug=args.debug
    )


if __name__ == "__main__":
    main()
