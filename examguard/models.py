
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4, UUID



EVENT_TYPES = {
    "FACE_PRESENT",
    "FACE_ABSENT",
    "MULTIPLE_FACES",
    "DETECTION_FAILURE",
    "CAMERA_UNAVAILABLE",
    "PERMISSION_DENIED",
    "PHONE_DETECTED",
    "LOOKING_AWAY",
    "SESSION_INTERRUPTED",
    "SESSION_STARTED",
    "SESSION_ENDED",

    
    "TAB_HIDDEN",
    "FOCUS_LOST",
    "FULLSCREEN_EXIT",

}

SEVERITIES = {
    "INFO",
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}



def utc_now() -> datetime:
    return datetime.now(timezone.utc)



def normalize_timestamp(value: str) -> str:

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "timestamp must be a non-empty ISO-8601 string"
        )

    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError:
        raise ValueError(
            "timestamp must be valid ISO-8601"
        ) from None

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            "timestamp must include a timezone, such as Z or +05:30"
        )

    return (
        parsed.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )



def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_timestamp(value).replace("Z", "+00:00")
    )


@dataclass
class IntegrityEvent:

    event_id: str
    schema_version: str
    candidate_id: str
    session_id: str
    event_type: str
    timestamp: str
    sequence_number: int
    severity: str
    source: str
    metadata: dict[str, Any]
    evidence: dict[str, Any]
    confidence: float | None = None

    @classmethod
    def create(
        cls,
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
        sequence_number: int = 0,
    ) -> IntegrityEvent:

        event = cls(
            event_id=f"evt-{uuid4().hex[:12]}",
            schema_version="1.0",
            candidate_id=candidate_id,
            session_id=session_id,
            event_type=event_type,
            timestamp=timestamp or utc_now().isoformat(),
            sequence_number=sequence_number,
            severity=severity,
            source=source,
            metadata=metadata if metadata is not None else {},
            evidence=evidence if evidence is not None else {
                "available": False,
                "evidence_id": None,
                "sha256": None,
            },
            confidence=confidence,
        )

        event.validate_and_normalize()
        return event

    def validate_and_normalize(self) -> IntegrityEvent:

        
        for field_name in (
            "event_id",
            "candidate_id",
            "session_id",
            "event_type",
            "source",
        ):

            value = getattr(self, field_name)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

            setattr(self, field_name, value.strip())

        
        self.event_type = self.event_type.upper()

        if self.event_type not in EVENT_TYPES:
            raise ValueError(
                f"Unsupported event_type: {self.event_type}"
            )

        
        if not isinstance(self.severity, str):
            raise ValueError("severity must be a string")

        self.severity = self.severity.strip().upper()

        if self.severity not in SEVERITIES:
            raise ValueError(
                f"severity must be one of {sorted(SEVERITIES)}"
            )

        
        if (
            isinstance(self.sequence_number, bool)
            or not isinstance(self.sequence_number, int)
            or self.sequence_number < 0
        ):
            raise ValueError(
                "sequence_number must be a non-negative integer"
            )

        
        self.timestamp = normalize_timestamp(self.timestamp)

        
        if self.metadata is None:
            self.metadata = {}

        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary/object")

        
        if self.evidence is None:
            self.evidence = {}

        if not isinstance(self.evidence, dict):
            raise ValueError("evidence must be a dictionary/object")

        
        if self.confidence is not None:

            if (
                isinstance(self.confidence, bool)
                or not isinstance(self.confidence, (int, float))
                or not 0 <= self.confidence <= 1
            ):
                raise ValueError(
                    "confidence must be null or a number from 0 to 1"
                )

        return self

    
    def validate(self) -> None:
        self.validate_and_normalize()

    def to_dict(self) -> dict[str, Any]:
        self.validate_and_normalize()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrityEvent:

        event = cls(**data)
        event.validate_and_normalize()
        return event


@dataclass
class AuditRecord:

    audit_id: str
    timestamp: str
    actor_id: str
    action: str
    target_type: str
    target_id: str
    outcome: str
    details: dict[str, Any]

    @classmethod
    def create(
        cls,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: str,
        *,
        outcome: str = "SUCCESS",
        details: dict[str, Any] | None = None,
    ) -> AuditRecord:

        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                actor_id,
                action,
                target_type,
                target_id,
                outcome,
            )
        ):
            raise ValueError(
                "actor_id, action, target_type, target_id and outcome are required"
            )

        if details is not None and not isinstance(details, dict):
            raise ValueError("details must be a dictionary/object")

        return cls(
            audit_id=f"audit-{uuid4().hex[:12]}",
            timestamp=utc_now().isoformat(
                timespec="seconds"
            ).replace("+00:00", "Z"),
            actor_id=actor_id.strip(),
            action=action.strip(),
            target_type=target_type.strip(),
            target_id=target_id.strip(),
            outcome=outcome.strip(),
            details=details if details is not None else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)



ExamEvent = IntegrityEvent
