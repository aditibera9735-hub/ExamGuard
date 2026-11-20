
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from .audit_service import AuditService
from .event_service import EventService
from .scoring_engine import ScoringEngine
from .storage import JsonlStore


class ScoringService:

    def __init__(
        self,
        event_service: EventService,
        scores_path: str | Path = "data/scores.jsonl",
        audit_service: AuditService | None = None,
        scoring_engine: ScoringEngine | None = None,
    ):
        self.event_service = event_service
        self.store = JsonlStore(scores_path)
        self.audit_service = audit_service
        self.engine = scoring_engine or ScoringEngine()

    def _check_access(
        self,
        actor_id: str,
        owner_id: str,
        role: str,
        score_id: str,
    ) -> bool:

        if not all(
            isinstance(value, str) and value.strip()
            for value in (actor_id, owner_id, role, score_id)
        ):
            raise ValueError("Actor, owner, role and score IDs are required")

        allowed = (
            actor_id == owner_id
            or role == "invigilator"
        )

        if self.audit_service is not None:
            self.audit_service.record_action(
                actor_id=actor_id,
                action="SCORE_ACCESS",
                target_type="EXAM_SCORE",
                target_id=score_id,
                outcome="SUCCESS" if allowed else "DENIED",
                details={
                    "owner_id": owner_id,
                    "role": role,
                },
            )

        return allowed

    def calculate_and_store(
        self,
        session_id: str,
        actor_id: str,
        role: str = "candidate",
    ) -> dict[str, Any]:

        events = self.event_service.get_session_events(session_id)

        if not events:
            raise ValueError("No events found for this session")

        candidate_ids = {
            event.candidate_id for event in events
        }

        if len(candidate_ids) != 1:
            raise ValueError(
                "Session events must belong to one candidate"
            )

        owner_id = next(iter(candidate_ids))

        score_id = str(uuid4())

        if not self._check_access(
            actor_id, owner_id, role, score_id
        ):
            raise PermissionError("Access denied")

        result = self.engine.calculate_score(events)

        record = {
            "score_id": score_id,
            "candidate_id": owner_id,
            "session_id": session_id,
            "calculation_type": "INITIAL",
            **result,
        }

        self.store.append(record)

        if self.audit_service is not None:
            self.audit_service.record_action(
                actor_id=actor_id,
                action="SCORE_CALCULATED",
                target_type="EXAM_SCORE",
                target_id=score_id,
                details={
                    "session_id": session_id,
                    "scoring_version": result["scoring_version"],
                    "score": result["score"],
                },
            )

        return record

    def get_score(
        self,
        session_id: str,
        actor_id: str,
        role: str = "candidate",
    ) -> dict[str, Any] | None:

        records = [
            row for row in self.store.read_all()
            if row.get("session_id") == session_id
        ]

        if not records:
            return None

        records.sort(
            key=lambda row: (
                row.get("calculated_at", ""),
                row.get("score_id", ""),
            )
        )

        latest = records[-1]

        if not self._check_access(
            actor_id,
            latest.get("candidate_id"),
            role,
            latest.get("score_id"),
        ):
            raise PermissionError("Access denied")

        return latest

    def recalculate(
        self,
        session_id: str,
        actor_id: str,
        role: str = "invigilator",
    ) -> dict[str, Any]:

        records = [
            row for row in self.store.read_all()
            if row.get("session_id") == session_id
        ]

        if not records:
            raise ValueError("No previous score found for this session")

        latest = max(
            records,
            key=lambda row: (
                row.get("calculated_at", ""),
                row.get("score_id", ""),
            ),
        )

        owner_id = latest.get("candidate_id")
        score_id = str(uuid4())

        if not self._check_access(
            actor_id, owner_id, role, score_id
        ):
            raise PermissionError("Access denied")

        events = self.event_service.get_session_events(session_id)

        if not events:
            raise ValueError("No events found for this session")

        current_candidate_ids = {
            event.candidate_id for event in events
        }

        if current_candidate_ids != {owner_id}:
            raise ValueError("Session ownership mismatch")

        result = self.engine.calculate_score(events)

        record = {
            "score_id": score_id,
            "candidate_id": owner_id,
            "session_id": session_id,
            "calculation_type": "RECALCULATION",
            **result,
        }

        self.store.append(record)

        if self.audit_service is not None:
            self.audit_service.record_action(
                actor_id=actor_id,
                action="SCORE_RECALCULATED",
                target_type="EXAM_SCORE",
                target_id=score_id,
                details={
                    "session_id": session_id,
                    "scoring_version": result["scoring_version"],
                    "score": result["score"],
                },
            )

        return record

