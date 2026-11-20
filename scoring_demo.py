
import json
import logging
import tempfile
from pathlib import Path

from examguard.event_service import EventService
from examguard.scoring_service import ScoringService


def main():

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("scoring-demo")

    candidate_id = "DEMO-STUDENT-001"
    session_id = "DEMO-SESSION-001"

    # Temporary storage protects your existing project data.
    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        event_service = EventService(
            events_path=temp_path / "demo_events.jsonl",
            logger=logger,
        )

        scoring_service = ScoringService(
            event_service=event_service,
            scores_path=temp_path / "demo_scores.jsonl",
        )

        print("\n========== EXAMGUARD SPRINT 5 DEMO ==========")

        # Event 1: Browser activity
        event_service.record_event(
            candidate_id=candidate_id,
            session_id=session_id,
            event_type="TAB_HIDDEN",
            source="browser-monitor",
            timestamp="2026-11-20T09:00:00Z",
            metadata={"description": "Exam tab became hidden"},
        )

        # Event 2: Face absence with simulated evidence
        event_service.record_event(
            candidate_id=candidate_id,
            session_id=session_id,
            event_type="FACE_ABSENT",
            source="computer-vision",
            timestamp="2026-11-20T09:00:10Z",
            confidence=0.95,
            evidence={
                "available": True,
                "evidence_id": "DEMO-EVIDENCE-001",
                "sha256": None,
                "demo": True,
            },
            metadata={"duration_seconds": 8},
        )

        # Event 3: Multiple faces with simulated evidence
        event_service.record_event(
            candidate_id=candidate_id,
            session_id=session_id,
            event_type="MULTIPLE_FACES",
            source="computer-vision",
            timestamp="2026-11-20T09:00:20Z",
            confidence=0.96,
            evidence={
                "available": True,
                "evidence_id": "DEMO-EVIDENCE-002",
                "sha256": None,
                "demo": True,
            },
            metadata={"face_count": 2},
        )

        print("\n1. EVENTS RECORDED")

        events = event_service.get_session_events(session_id)

        for event in events:
            print(
                event.event_type,
                "| Confidence:",
                event.confidence,
            )

        # Calculate score and save the result.
        print("\n2. CALCULATING SCORE")

        result = scoring_service.calculate_and_store(
            session_id=session_id,
            actor_id=candidate_id,
            role="candidate",
        )

        print("\n3. FINAL SCORE")
        print("Score:", result["score"])
        print("Raw score:", result["raw_score"])
        print("Category:", result["category"])
        print("Scoring version:", result["scoring_version"])
        print("Calculated at:", result["calculated_at"])

        print("\n4. SCORE CONTRIBUTIONS")

        for item in result["contributions"]:
            print(
                item["event_type"],
                "| Points:", item["points"],
                "| Explanation:", item["explanation"],
            )

        print("\n5. REVIEW INFORMATION")
        print(
            "Human review required:",
            result["human_review_required"],
        )
        print(
            "Automatic decision:",
            result["automatic_decision"],
        )
        print("Notice:", result["notice"])

        print("\n6. SCORE STORAGE")
        print("Score saved:", (temp_path / "demo_scores.jsonl").exists())

        print("\n========== DEMO COMPLETED ==========")


if __name__ == "__main__":
    main()
