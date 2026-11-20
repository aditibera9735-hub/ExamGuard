import unittest
from datetime import datetime, timedelta, timezone

from examguard.cv_result_adapter import CVResultAdapter


class CVResultAdapterTests(unittest.TestCase):

    def setUp(self):
        self.monitor = CVResultAdapter(
            absence_threshold_seconds=5
        )

        self.start = datetime(
            2026, 11, 3, 10, 0, 0,
            tzinfo=timezone.utc
        )

    def test_face_detected(self):
        result = {
            "face_detected": True,
            "detection_available": True,
            "confidence": 0.98,
            "timestamp": self.start
        }

        event = self.monitor.process_cv_result(result)

        self.assertIsNone(event)
        
        final_event = self.monitor.finish_session(
            self.start + timedelta(seconds=3)
        )

        self.assertEqual(
            final_event["event_type"], "FACE_PRESENT"
        )
        self.assertEqual(final_event["confidence"], 0.98)
        self.assertEqual(
            final_event["observation_status"], "CONFIRMED"
        )

    def test_face_absent_after_threshold(self):
        present = {
            "face_detected": True,
            "detection_available": True,
            "confidence": 0.98,
            "timestamp": self.start
        }

        absent1 = {
            "face_detected": False,
            "detection_available": True,
            "confidence": None,
            "timestamp": self.start + timedelta(seconds=1)
        }

        absent2 = {
            "face_detected": False,
            "detection_available": True,
            "confidence": None,
            "timestamp": self.start + timedelta(seconds=6)
        }

        self.monitor.process_cv_result(present)
        self.monitor.process_cv_result(absent1)

        event = self.monitor.process_cv_result(absent2)

        self.assertEqual(
            event["event_type"], "FACE_PRESENT"
        )

        final_event = self.monitor.finish_session(
            self.start + timedelta(seconds=8)
        )

        self.assertEqual(
            final_event["event_type"], "FACE_ABSENT"
        )
        self.assertEqual(
            final_event["observation_status"], "CONFIRMED"
        )

    def test_detection_unavailable(self):
        result = {
            "face_detected": False,
            "detection_available": False,
            "confidence": None,
            "timestamp": self.start
        }

        self.monitor.process_cv_result(result)

        event = self.monitor.finish_session(
            self.start + timedelta(seconds=3)
        )

        self.assertEqual(
            event["event_type"], "DETECTION_FAILURE"
        )
        self.assertEqual(
            event["observation_status"], "UNCERTAIN"
        )

    def test_missing_detection_available(self):
        result = {
            "face_detected": True,
            "confidence": 0.98,
            "timestamp": self.start
        }

        with self.assertRaises(ValueError):
            self.monitor.process_cv_result(result)

    def test_invalid_detection_available(self):
        result = {
            "face_detected": True,
            "detection_available": "yes",
            "confidence": 0.98,
            "timestamp": self.start
        }

        with self.assertRaises(ValueError):
            self.monitor.process_cv_result(result)

    def test_missing_face_detected(self):
        result = {
            "detection_available": True,
            "confidence": 0.98,
            "timestamp": self.start
        }

        with self.assertRaises(ValueError):
            self.monitor.process_cv_result(result)

    def test_invalid_face_detected(self):
        result = {
            "face_detected": "yes",
            "detection_available": True,
            "confidence": 0.98,
            "timestamp": self.start
        }

        with self.assertRaises(ValueError):
            self.monitor.process_cv_result(result)

    def test_invalid_input_type(self):
        with self.assertRaises(ValueError):
            self.monitor.process_cv_result("invalid")

    def test_timezone_required(self):
        result = {
            "face_detected": True,
            "detection_available": True,
            "confidence": 0.98,
            "timestamp": datetime(2026, 11, 3, 10, 0, 0)
        }

        with self.assertRaises(ValueError):
            self.monitor.process_cv_result(result)


if __name__ == "__main__":
    unittest.main()