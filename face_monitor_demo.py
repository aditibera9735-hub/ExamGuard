
"""Simulate face observations and optionally publish them to Kafka."""

import argparse
from datetime import datetime, timedelta, timezone

from examguard.face_event_adapter import FaceEventAdapter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kafka",
        action="store_true",
        help="Publish CV events to Kafka"
    )
    args = parser.parse_args()

    monitor = FaceEventAdapter(absence_threshold_seconds=5)
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

    for state, confidence, seconds in observations:
        timestamp = start + timedelta(seconds=seconds)

        result = monitor.process_observation(
            state=state,
            confidence=confidence,
            timestamp=timestamp
        )

        if result:
            print("\nEvent generated:")
            print(result)

    
    final_event = monitor.finish_session(
        timestamp=start + timedelta(seconds=15)
    )

    if final_event:
        print("\nFinal session event:")
        print(final_event)

    events = monitor.get_events()

    print("\nCompleted events:")
    for event in events:
        print(event)

    if args.kafka:
        from examguard.kafka_producer import publish_cv_events

        session_id = "session-cv-demo-" + start.strftime(
            "%Y%m%dT%H%M%S"
        )

        print("\nPublishing CV events to Kafka...")

        published = publish_cv_events(
            events,
            candidate_id="candidate-demo-001",
            session_id=session_id
        )

        print(
            f"Successfully published {len(published)} events."
        )
    else:
        print("\nKafka publishing skipped. Use --kafka to enable it.")


if __name__ == "__main__":
    main()
