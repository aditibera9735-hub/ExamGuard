
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import IntegrityEvent
from .scoring_config import (
    ScoringConfig,
    DEFAULT_SCORING_CONFIG,
)


class ScoringEngine:

    def __init__(
        self,
        config: ScoringConfig | None = None,
    ):
        self.config = config or DEFAULT_SCORING_CONFIG

        if not self.config.version.strip():
            raise ValueError("Scoring version is required")

        if (
            isinstance(self.config.maximum_score, bool)
            or not isinstance(self.config.maximum_score, int)
            or self.config.maximum_score < 0
        ):
            raise ValueError("Maximum score must be a non-negative integer")

        for event_type, rule in self.config.rules.items():
            if event_type != rule.event_type:
                raise ValueError("Rule key and event type must match")

            if (
                isinstance(rule.weight, bool)
                or not isinstance(rule.weight, int)
                or rule.weight < 0
            ):
                raise ValueError("Rule weight must be a non-negative integer")

            if not 0 <= rule.minimum_confidence <= 1:
                raise ValueError("Minimum confidence must be between 0 and 1")

    def calculate_score(
        self,
        events: list[IntegrityEvent],
    ) -> dict[str, Any]:

        if not isinstance(events, list):
            raise ValueError("Events must be provided as a list")

        validated_events = []

        for event in events:
            if not isinstance(event, IntegrityEvent):
                raise ValueError("Every item must be an IntegrityEvent")

            event.validate()
            validated_events.append(event)

        session_ids = {event.session_id for event in validated_events}

        if len(session_ids) > 1:
            raise ValueError("Events must belong to the same session")

        # Sort events to make the breakdown deterministic.
        validated_events.sort(
            key=lambda event: (
                event.timestamp,
                event.sequence_number,
                event.event_id,
            )
        )

        contributions = []
        skipped_events = []
        seen_events = {}

        raw_score = 0

        for event in validated_events:

            # Prevent duplicate event contributions.
            event_data = event.to_dict()

            if event.event_id in seen_events:

                if seen_events[event.event_id] != event_data:
                    raise ValueError(
                        "Conflicting events have the same event_id"
                    )

                skipped_events.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "reason": "Duplicate event ignored",
                })
                continue

            seen_events[event.event_id] = event_data

            rule = self.config.rules.get(event.event_type)

            # Events without a scoring rule do not add points.
            if rule is None:
                skipped_events.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "reason": "No scoring rule configured",
                })
                continue

            # Check evidence availability.
            if rule.requires_evidence:
                evidence = event.evidence

                if evidence.get("available") is not True:
                    skipped_events.append({
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "reason": "Required evidence is missing",
                    })
                    continue

            # Check detector confidence.
            if rule.minimum_confidence > 0:

                if event.confidence is None:
                    skipped_events.append({
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "reason": "Detection confidence is unavailable",
                    })
                    continue

                if event.confidence < rule.minimum_confidence:
                    skipped_events.append({
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "reason": "Detection confidence is below threshold",
                    })
                    continue

            points = rule.weight
            raw_score += points

            contributions.append({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "weight": rule.weight,
                "points": points,
                "explanation": rule.explanation,
                "confidence": event.confidence,
                "evidence_available": event.evidence.get(
                    "available", False
                ),
            })

        final_score = min(
            raw_score,
            self.config.maximum_score,
        )

        if final_score < 20:
            category = "LOW"
        elif final_score < 50:
            category = "MODERATE"
        else:
            category = "HIGH"

        return {
            "session_id": (
                validated_events[0].session_id
                if validated_events else None
            ),
            "score": final_score,
            "raw_score": raw_score,
            "maximum_score": self.config.maximum_score,
            "category": category,
            "scoring_version": self.config.version,
            "calculated_at": datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "event_count": len(validated_events),
            "scored_event_count": len(contributions),
            "contributions": contributions,
            "skipped_events": skipped_events,
            "human_review_required": final_score > 0,
            "decision_support_only": True,
            "automatic_decision": False,
            "notice": (
                "This score is a decision-support indicator only, "
                "not proof of misconduct. Human review is required "
                "before any decision."
            ),
        }
