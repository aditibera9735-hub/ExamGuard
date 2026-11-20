
from __future__ import annotations

import json
import logging
import tempfile
import unittest

from pathlib import Path

from examguard.audit_service import AuditService
from examguard.event_service import EventService
from examguard.integrity import summarize_integrity
from examguard.models import IntegrityEvent, parse_timestamp
from examguard.storage import JsonlStore
from examguard.synthetic_data import make_synthetic_events
from examguard.logging_config import JsonFormatter


class ExamGuardTests(unittest.TestCase):

    def setUp(self):

        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

        # Initialize JSONL storage
        self.store = JsonlStore(self.root / "events.jsonl")

        # Initialize logger
        self.logger = logging.getLogger("examguard.test")
        self.logger.handlers.clear()
        self.logger.addHandler(logging.NullHandler())
        self.logger.propagate = False

        # Initialize services
        self.events = EventService(
            self.root / "events.jsonl",
            self.logger
        )

        self.audit = AuditService(
            self.root / "audit.jsonl"
        )

    def tearDown(self):
        self.logger.handlers.clear()
        self.temp.cleanup()

    # ----------------------------------
    # EVENT CREATION AND STORAGE TESTS
    # ----------------------------------

    def test_event_is_saved_and_retrievable(self):

        event = self.events.record_event(
            "cand-1",
            "sess-1",
            "FACE_ABSENT"
        )

        found = self.events.get_event(event["event_id"])

        self.assertIsNotNone(found)
        self.assertEqual(found.event_type, "FACE_ABSENT")

    def test_sequence_increments_per_session(self):

        first = self.events.record_event(
            "cand-1", "sess-1", "FACE_PRESENT"
        )

        second = self.events.record_event(
            "cand-1", "sess-1", "FACE_ABSENT"
        )

        third = self.events.record_event(
            "cand-2", "sess-2", "FACE_PRESENT"
        )

        self.assertEqual(first["sequence_number"], 1)
        self.assertEqual(second["sequence_number"], 2)
        self.assertEqual(third["sequence_number"], 1)

    def test_event_ids_are_unique(self):

        saved = [
            self.events.record_event(
                event.candidate_id,
                event.session_id,
                event.event_type,
                timestamp=event.timestamp
            )
            for event in make_synthetic_events()
        ]

        ids = [event["event_id"] for event in saved]

        self.assertEqual(len(ids), len(set(ids)))

    # ----------------------------------
    # EVENT VALIDATION TESTS
    # ----------------------------------

    def test_invalid_event_type_rejected(self):

        with self.assertRaises(ValueError):

            IntegrityEvent.create(
                "cand-1",
                "sess-1",
                "MADE_UP_EVENT"
            )

    def test_confidence_range_checked(self):

        with self.assertRaises(ValueError):

            IntegrityEvent.create(
                "cand-1",
                "sess-1",
                "FACE_ABSENT",
                confidence=1.2
            )

    def test_timestamp_requires_timezone(self):

        with self.assertRaises(ValueError):

            parse_timestamp(
                "2026-10-29T09:15:00"
            )

    def test_timestamp_normalization(self):

        event = self.events.record_event(
            "c1",
            "s1",
            "FACE_ABSENT",
            timestamp="2026-10-29T14:45:08+05:30"
        )

        self.assertEqual(
            event["timestamp"],
            "2026-10-29T09:15:08Z"
        )

    def test_event_type_normalization(self):

        event = self.events.record_event(
            "c1",
            "s1",
            "face_absent"
        )

        self.assertEqual(
            event["event_type"],
            "FACE_ABSENT"
        )

    def test_missing_session_id_rejected(self):

        with self.assertRaises(ValueError):

            self.events.record_event(
                "c1",
                "",
                "FACE_PRESENT"
            )

    # ----------------------------------
    # EVENT RETRIEVAL TESTS
    # ----------------------------------

    def test_events_retrieved_by_session(self):

        self.events.record_event(
            "c1", "s1", "FACE_PRESENT"
        )

        self.events.record_event(
            "c2", "s2", "FACE_ABSENT"
        )

        found = self.events.get_session_events("s1")

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].session_id, "s1")

    def test_events_ordered_by_timestamp(self):

        self.events.record_event(
            "c", "s", "FACE_ABSENT",
            timestamp="2026-10-29T09:15:10Z"
        )

        self.events.record_event(
            "c", "s", "FACE_PRESENT",
            timestamp="2026-10-29T09:15:00Z"
        )

        ordered = self.events.list_events("s")

        self.assertEqual(
            ordered[0].event_type,
            "FACE_PRESENT"
        )

    def test_storage_lists_all_events(self):

        self.events.record_event(
            "c1", "s1", "FACE_PRESENT"
        )

        self.events.record_event(
            "c2", "s2", "FACE_ABSENT"
        )

        records = self.store.list_all()

        self.assertEqual(len(records), 2)

    def test_storage_lists_events_by_session(self):

        self.events.record_event(
            "c1", "s1", "FACE_PRESENT"
        )

        self.events.record_event(
            "c2", "s2", "FACE_ABSENT"
        )

        records = self.store.list_by_session("s1")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["session_id"], "s1")

    # ----------------------------------
    # AUDIT SERVICE TESTS
    # ----------------------------------

    def test_audit_record_stored_separately(self):

        record = self.audit.record_action(
            "invigilator-1",
            "OPEN_EVENT",
            "INTEGRITY_EVENT",
            "evt-1",
            details={"reason": "review"}
        )

        found = self.audit.list_records(
            target_id="evt-1"
        )

        self.assertEqual(len(found), 1)

        self.assertEqual(
            found[0]["audit_id"],
            record.audit_id
        )

    # ----------------------------------
    # INTEGRITY SCORING TESTS
    # ----------------------------------

    def test_score_has_explanation_and_is_capped(self):

        events = [
            IntegrityEvent.create("c", "s", "MULTIPLE_FACES"),
            IntegrityEvent.create("c", "s", "MULTIPLE_FACES"),
            IntegrityEvent.create("c", "s", "MULTIPLE_FACES"),
            IntegrityEvent.create("c", "s", "FACE_ABSENT"),
        ]

        summary = summarize_integrity(events)

        self.assertEqual(summary["score"], 70)
        self.assertEqual(summary["category"], "HIGH")
        self.assertEqual(len(summary["reasons"]), 4)

        self.assertTrue(
            summary["human_review_required"]
        )

    # ----------------------------------
    # SYNTHETIC DATA TESTS
    # ----------------------------------

    def test_synthetic_events_are_valid_model_instances(self):
        events = make_synthetic_events()

        self.assertEqual(len(events), 6)
        self.assertTrue(all(isinstance(event, IntegrityEvent) for event in events))
        self.assertTrue(all(event.sequence_number == 0 for event in events))
        self.assertEqual(events[0].event_type, "SESSION_STARTED")
        self.assertEqual(events[-1].event_type, "SESSION_ENDED")

    def test_synthetic_data_includes_failure_scenarios(self):

        types = {
            event.event_type
            for event in make_synthetic_events()
        }

        self.assertTrue(
            {
                "CAMERA_UNAVAILABLE",
                "MULTIPLE_FACES",
                "FACE_ABSENT"
            }.issubset(types)
        )

    # ----------------------------------
    # LOGGING TESTS
    # ----------------------------------

    def test_log_schema_has_session_and_event_ids(self):

        record = logging.LogRecord(
            "examguard",
            logging.WARNING,
            "",
            0,
            "warning",
            (),
            None
        )

        record.session_id = "s1"
        record.event_id = "evt-1"

        payload = json.loads(
            JsonFormatter().format(record)
        )

        self.assertEqual(payload["level"], "WARNING")
        self.assertEqual(payload["session_id"], "s1")
        self.assertEqual(payload["event_id"], "evt-1")

        self.assertIn("timestamp", payload)

    def test_logging_handles_exceptions(self):

        try:
            raise ValueError("Test exception")

        except ValueError:

            record = logging.LogRecord(
                "examguard",
                logging.ERROR,
                "",
                0,
                "Event processing failed",
                (),
                __import__("sys").exc_info()
            )

        payload = json.loads(
            JsonFormatter().format(record)
        )

        self.assertIn("exception", payload)
        self.assertIn(
            "Test exception",
            payload["exception"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
