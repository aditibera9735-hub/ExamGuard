from datetime import datetime, timezone

from examguard.face_event_adapter import FaceEventAdapter


class CVResultAdapter:
    """
    Converts Computer Vision detection results into
    normalized face-monitoring events.
    """

    def __init__(self, absence_threshold_seconds=5):
        self.face_adapter = FaceEventAdapter(
            absence_threshold_seconds=absence_threshold_seconds
        )

    def process_cv_result(self, result):
        """
        Expected input format:

        {
            "face_detected": True,
            "detection_available": True,
            "confidence": 0.98,
            "timestamp": datetime.now(timezone.utc)
        }
        """

        if not isinstance(result, dict):
            raise ValueError("CV result must be a dictionary")

        if "detection_available" not in result:
            raise ValueError("detection_available field is required")

        detection_available = result["detection_available"]

        if not isinstance(detection_available, bool):
            raise ValueError("detection_available must be True or False")

        timestamp = result.get(
            "timestamp",
            datetime.now(timezone.utc)
        )

        if not isinstance(timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")

        if timestamp.tzinfo is None:
            raise ValueError("timestamp must include a timezone")

        if not detection_available:
            state = "DETECTION_FAILURE"
            confidence = None

        else:
            if "face_detected" not in result:
                raise ValueError(
                    "face_detected is required when detection is available"
                )

            face_detected = result["face_detected"]

            if not isinstance(face_detected, bool):
                raise ValueError("face_detected must be True or False")

            if face_detected:
                state = "FACE_PRESENT"
            else:
                state = "FACE_ABSENT"

            confidence = result.get("confidence")

        return self.face_adapter.process_observation(
            state=state,
            confidence=confidence,
            timestamp=timestamp
        )

    def get_events(self):
        """Return all completed events."""
        return self.face_adapter.get_events()

    def finish_session(self, timestamp=None):
        """Finish monitoring and close the last event."""
        return self.face_adapter.finish_session(timestamp)