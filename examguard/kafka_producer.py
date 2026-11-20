
"""Publish ExamGuard events to Kafka."""

import json
import os
from typing import Any, Iterable

from kafka import KafkaProducer
from kafka.errors import KafkaError

from .models import IntegrityEvent

BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
)
TOPIC = os.getenv("KAFKA_TOPIC", "exam-events")


def publish_integrity_events(
    events: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:

    validated_events = [
        IntegrityEvent.from_dict(event).to_dict()
        for event in events
    ]

    if not validated_events:
        print("No events to publish.")
        return []

    producer = None

    try:
        producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda value: json.dumps(
                value
            ).encode("utf-8"),
            acks="all",
            retries=3,
        )

        for event in validated_events:
            metadata = producer.send(
                TOPIC,
                value=event,
                key=event["session_id"].encode("utf-8"),
            ).get(timeout=15)

            print(
                f"Event sent successfully: "
                f"{metadata.topic} | "
                f"Partition: {metadata.partition} | "
                f"Offset: {metadata.offset}"
            )

        return validated_events

    except KafkaError as exc:
        raise RuntimeError(
            f"Kafka publishing failed: {exc}"
        ) from exc

    finally:
        if producer is not None:
            producer.flush()
            producer.close()


def publish_cv_events(
    observations: Iterable[dict[str, Any]],
    *,
    candidate_id: str,
    session_id: str,
) -> list[dict[str, Any]]:

    severity_by_type = {
        "FACE_PRESENT": "INFO",
        "FACE_ABSENT": "MEDIUM",
        "DETECTION_FAILURE": "LOW",
    }

    normalized_events = []

    for sequence_number, observation in enumerate(
        observations, start=1
    ):
        event_type = observation["event_type"]
        end_time = observation["end_time"]

        metadata = {
            "start_time": observation["start_time"],
            "end_time": end_time,
            "duration_seconds": observation["duration_seconds"],
            "observation_status": observation["observation_status"],
            "adapter": "FaceEventAdapter",
        }

        event = IntegrityEvent.create(
            candidate_id=candidate_id,
            session_id=session_id,
            event_type=event_type,
            timestamp=end_time,
            sequence_number=sequence_number,
            severity=severity_by_type.get(
                event_type, "MEDIUM"
            ),
            source="computer-vision",
            metadata=metadata,
            confidence=observation["confidence"],
        ).to_dict()

        normalized_events.append(event)

    return publish_integrity_events(normalized_events)


def main():
    event = IntegrityEvent.create(
        candidate_id="candidate-demo-001",
        session_id="session-demo-001",
        event_type="FACE_ABSENT",
        severity="MEDIUM",
        source="mock-monitor",
        metadata={
            "duration_seconds": 5,
            "note": "Kafka integration test"
        },
        evidence={
            "available": False,
            "evidence_id": None,
            "sha256": None
        },
        confidence=0.91,
    ).to_dict()

    publish_integrity_events([event])
    print(json.dumps(event, indent=2))


if __name__ == "__main__":
    main()
