
from datetime import datetime, timezone


class FaceEventAdapter:
    """Convert face-monitoring observations into normalized events."""

    def __init__(self, absence_threshold_seconds=5):
        if absence_threshold_seconds < 0:
            raise ValueError("Threshold cannot be negative")

        self.absence_threshold_seconds = absence_threshold_seconds
        self.current_state = None
        self.state_started_at = None
        self.absence_started_at = None
        self.last_confidence = None
        self.events = []

    def process_observation(
        self, state, confidence=None, timestamp=None
    ):
        allowed_states = {
            "FACE_PRESENT",
            "FACE_ABSENT",
            "DETECTION_FAILURE",
        }

        if state not in allowed_states:
            raise ValueError(f"Unsupported state: {state}")

        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")

        timestamp = timestamp or datetime.now(timezone.utc)

        if timestamp.tzinfo is None:
            raise ValueError("Timestamp must include a timezone")

        # Require sustained absence before confirming it.
        if state == "FACE_ABSENT":
            if self.absence_started_at is None:
                self.absence_started_at = timestamp

            elapsed = (
                timestamp - self.absence_started_at
            ).total_seconds()

            if elapsed < self.absence_threshold_seconds:
                return None

            # Record the actual beginning of the absence,
            # not the later time when the threshold was reached.
            transition_time = self.absence_started_at

        else:
            transition_time = timestamp

        # Repeated observations do not create duplicate events.
        if state == self.current_state:
            if confidence is not None:
                self.last_confidence = confidence

            if state != "FACE_ABSENT":
                self.absence_started_at = None

            return None

        completed_event = None

        # Close the previous state at the transition time.
        if self.current_state is not None:
            duration = (
                transition_time - self.state_started_at
            ).total_seconds()

            completed_event = {
                "event_type": self.current_state,
                "start_time": self.state_started_at.isoformat(),
                "end_time": transition_time.isoformat(),
                "duration_seconds": round(max(0, duration), 2),
                "confidence": self.last_confidence,
                "observation_status": (
                    "UNCERTAIN"
                    if self.current_state == "DETECTION_FAILURE"
                    else "CONFIRMED"
                ),
            }

            self.events.append(completed_event)

        self.current_state = state
        self.state_started_at = transition_time
        self.last_confidence = confidence

        if state != "FACE_ABSENT":
            self.absence_started_at = None

        return completed_event

    def get_events(self):
        """Return completed events."""
        return list(self.events)

    def finish_session(self, timestamp=None):
        """Close the current event when monitoring stops."""
        if self.current_state is None:
            return None

        timestamp = timestamp or datetime.now(timezone.utc)

        if timestamp.tzinfo is None:
            raise ValueError("Timestamp must include a timezone")

        duration = (
            timestamp - self.state_started_at
        ).total_seconds()

        event = {
            "event_type": self.current_state,
            "start_time": self.state_started_at.isoformat(),
            "end_time": timestamp.isoformat(),
            "duration_seconds": round(max(0, duration), 2),
            "confidence": self.last_confidence,
            "observation_status": (
                "UNCERTAIN"
                if self.current_state == "DETECTION_FAILURE"
                else "CONFIRMED"
            ),
        }

        self.events.append(event)
        self.current_state = None
        self.state_started_at = None
        self.absence_started_at = None
        self.last_confidence = None

        return event
