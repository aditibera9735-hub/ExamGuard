
from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import IntegrityEvent, parse_timestamp
from .storage import JsonlStore


class EventService:

    def __init__(self, events_path: str | Path, logger):
        self.store = JsonlStore(events_path)
        self.logger = logger

    def record_event(
        self,
        candidate_id: str,
        session_id: str,
        event_type: str,
        *,
        severity: str = "MEDIUM",
        source: str = "mock-monitor",
        metadata: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
        confidence: float | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:

        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")

        session_id = session_id.strip()

        event_metadata = metadata or {}
        incident_id = event_metadata.get("incident_id")

        all_events = self.store.read_all()

        for row in all_events:
            if (
                row.get("session_id") != session_id
                or row.get("candidate_id") != candidate_id
                or row.get("event_type") != event_type
                or row.get("source") != source
            ):
                continue

            old_metadata = row.get("metadata") or {}
            old_incident_id = old_metadata.get("incident_id")

            # If incident_id is available, use it for deduplication.
            if incident_id:
                if old_incident_id == incident_id:
                    self.logger.info(
                        "Duplicate event ignored",
                        extra={
                            "session_id": session_id,
                            "event_id": row["event_id"],
                        }
                    )
                    return row

            # For events without incident_id, use a 5-second fallback.
            elif not old_incident_id and timestamp:
                old_time = parse_timestamp(row["timestamp"])
                new_time = parse_timestamp(timestamp)

                time_difference = abs(
                    (new_time - old_time).total_seconds()
                )

                if time_difference <= 5:
                    self.logger.info(
                        "Duplicate event ignored",
                        extra={
                            "session_id": session_id,
                            "event_id": row["event_id"],
                        }
                    )
                    return row

        # Generate the next sequence number.
        existing = [
            row for row in all_events
            if row.get("session_id") == session_id
        ]

        next_sequence = max(
            (int(row.get("sequence_number", 0)) for row in existing),
            default=0
        ) + 1

        event = IntegrityEvent.create(
            candidate_id=candidate_id,
            session_id=session_id,
            event_type=event_type,
            severity=severity,
            source=source,
            metadata=metadata,
            evidence=evidence,
            confidence=confidence,
            timestamp=timestamp,
            sequence_number=next_sequence,
        )

        event.validate_and_normalize()

        self.store.append(event.to_dict())

        self.logger.info(
            "Exam event stored",
            extra={
                "session_id": event.session_id,
                "event_id": event.event_id,
            }
        )

        return event.to_dict()

    def get_session_events(
        self,
        session_id: str
    ) -> list[IntegrityEvent]:

        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")

        sid = session_id.strip()

        events = [
            IntegrityEvent.from_dict(row)
            for row in self.store.read_all()
            if row.get("session_id") == sid
        ]

        events = sorted(
            events,
            key=lambda event: (
                parse_timestamp(event.timestamp),
                event.sequence_number,
                event.event_id,
            ),
        )

        self.logger.info(
            "Session events retrieved",
            extra={
                "session_id": sid,
                "event_id": None,
            }
        )

        return events

    def list_events(
        self,
        session_id: str | None = None
    ) -> list[IntegrityEvent]:

        if session_id is not None:
            return self.get_session_events(session_id)

        events = [
            IntegrityEvent.from_dict(row)
            for row in self.store.read_all()
        ]

        return sorted(
            events,
            key=lambda event: (
                parse_timestamp(event.timestamp),
                event.sequence_number,
                event.event_id,
            ),
        )

    def get_event(
        self,
        event_id: str
    ) -> IntegrityEvent | None:

        for row in self.store.read_all():

            if row.get("event_id") == event_id:

                event = IntegrityEvent.from_dict(row)

                self.logger.info(
                    "Exam event retrieved",
                    extra={
                        "session_id": event.session_id,
                        "event_id": event.event_id,
                    }
                )

                return event

        self.logger.warning(
            "Exam event not found",
            extra={
                "session_id": None,
                "event_id": event_id,
            }
        )

        return None
