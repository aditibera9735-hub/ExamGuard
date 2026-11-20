"""Read and validate ExamGuard events from Kafka and save received events."""
from __future__ import annotations

import json
import os
from pathlib import Path

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from .models import IntegrityEvent
from .storage import JsonlStore

ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "exam-events")
OUTPUT = ROOT / "data" / "kafka_received_events.jsonl"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id="examguard-team3-consumer",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    store = JsonlStore(OUTPUT)
    print(f"Listening on topic '{TOPIC}' at {BOOTSTRAP_SERVERS}")
    print(f"Validated events will be saved to: {OUTPUT}")
    print("Stop with Ctrl+C.")

    try:
        for message in consumer:
            try:
                event = IntegrityEvent.from_dict(message.value).to_dict()
                store.append(event)
                print(
                    f"Received and saved: {event['event_type']} | "
                    f"severity={event['severity']} | "
                    f"session={event['session_id']} | "
                    f"offset={message.offset}"
                )
            except (ValueError, TypeError, KeyError) as exc:
                print(f"Skipped invalid event message: {exc}")
    except KeyboardInterrupt:
        print("\nConsumer stopped.")
    except KafkaError as exc:
        raise SystemExit(f"Kafka consumer error: {exc}") from exc
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
