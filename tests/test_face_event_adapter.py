import unittest
from datetime import datetime, timedelta, timezone

from examguard.face_event_adapter import FaceEventAdapter


class FaceEventAdapterTests(unittest.TestCase):

    def setUp(self):
        self.monitor = FaceEventAdapter(
            absence_threshold_seconds=5
        )

        self.start = datetime(
            2026, 11, 3, 10, 0, 0,
            tzinfo=timezone.utc
        )

    def test_face_present_event(self):
        self.monitor.process_observation(
            "FACE_PRESENT",
            confidence=0.98,
            timestamp=self.start
        )

        event = self.monitor.finish_session(
            self.start + timedelta(seconds=3)
        )

        self.assertEqual(event["event_type"], "FACE_PRESENT")
        self.assertEqual(event["duration_seconds"], 3)
        self.assertEqual(event["confidence"], 0.98)
        self.assertEqual(
            event["observation_status"], "CONFIRMED"
        )

    def test_absence_threshold(self):
        self.monitor.process_observation(
            "FACE_PRESENT", 0.98, self.start
        )

        self.monitor.process_observation(
            "FACE_ABSENT", None,
            self.start + timedelta(seconds=1)
        )

        result = self.monitor.process_observation(
            "FACE_ABSENT", None,
            self.start + timedelta(seconds=6)
        )

        self.assertEqual(result["event_type"], "FACE_PRESENT")

        absence_event = self.monitor.finish_session(
            self.start + timedelta(seconds=8)
        )

        self.assertEqual(
            absence_event["event_type"], "FACE_ABSENT"
        )
        self.assertEqual(
            absence_event["duration_seconds"], 7
        )

    def test_short_absence_does_not_create_event(self):
        self.monitor.process_observation(
            "FACE_PRESENT", 0.97, self.start
        )

        self.monitor.process_observation(
            "FACE_ABSENT", None,
            self.start + timedelta(seconds=1)
        )

        result = self.monitor.process_observation(
            "FACE_PRESENT", 0.96,
            self.start + timedelta(seconds=3)
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.monitor.get_events()), 0)

    def test_detection_failure_is_uncertain(self):
        self.monitor.process_observation(
            "FACE_PRESENT", 0.98, self.start
        )

        self.monitor.process_observation(
            "DETECTION_FAILURE", None,
            self.start + timedelta(seconds=2)
        )

        event = self.monitor.finish_session(
            self.start + timedelta(seconds=5)
        )

        self.assertEqual(
            event["event_type"], "DETECTION_FAILURE"
        )
        self.assertEqual(
            event["observation_status"], "UNCERTAIN"
        )

    def test_repeated_observations_do_not_duplicate_events(self):
        self.monitor.process_observation(
            "FACE_PRESENT", 0.98, self.start
        )

        for seconds in range(1, 10):
            result = self.monitor.process_observation(
                "FACE_PRESENT", 0.97,
                self.start + timedelta(seconds=seconds)
            )

            self.assertIsNone(result)

        self.assertEqual(len(self.monitor.get_events()), 0)

        self.monitor.finish_session(
            self.start + timedelta(seconds=10)
        )

        self.assertEqual(len(self.monitor.get_events()), 1)

    def test_invalid_confidence_is_rejected(self):
        with self.assertRaises(ValueError):
            self.monitor.process_observation(
                "FACE_PRESENT", 1.5, self.start
            )

    def test_invalid_state_is_rejected(self):
        with self.assertRaises(ValueError):
            self.monitor.process_observation(
                "UNKNOWN_STATE", None, self.start
            )

    def test_timezone_is_required(self):
        naive_time = datetime(2026, 11, 3, 10, 0, 0)

        with self.assertRaises(ValueError):
            self.monitor.process_observation(
                "FACE_PRESENT", 0.98, naive_time
            )

    def test_session_can_finish(self):
        self.monitor.process_observation(
            "FACE_PRESENT", 0.99, self.start
        )

        event = self.monitor.finish_session(
            self.start + timedelta(seconds=5)
        )

        self.assertEqual(event["duration_seconds"], 5)
        self.assertIsNone(self.monitor.current_state)


if __name__ == "__main__":
    unittest.main()