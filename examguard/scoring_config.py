
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScoringRule:
    event_type: str
    weight: int
    explanation: str
    requires_evidence: bool = True
    minimum_confidence: float = 0.80


@dataclass(frozen=True)
class ScoringConfig:
    version: str = "1.0.0"
    maximum_score: int = 100
    rules: dict[str, ScoringRule] = field(
        default_factory=lambda: {
            "FACE_ABSENT": ScoringRule(
                event_type="FACE_ABSENT",
                weight=10,
                explanation="Face was absent during the examination.",
            ),
            "MULTIPLE_FACES": ScoringRule(
                event_type="MULTIPLE_FACES",
                weight=20,
                explanation="Multiple faces were detected.",
            ),
            "PHONE_DETECTED": ScoringRule(
                event_type="PHONE_DETECTED",
                weight=15,
                explanation="A phone was detected.",
            ),
            "LOOKING_AWAY": ScoringRule(
                event_type="LOOKING_AWAY",
                weight=5,
                explanation="Candidate was detected looking away.",
            ),
            "TAB_HIDDEN": ScoringRule(
                event_type="TAB_HIDDEN",
                weight=10,
                explanation="Examination tab became hidden.",
                requires_evidence=False,
                minimum_confidence=0.0,
            ),
            "FOCUS_LOST": ScoringRule(
                event_type="FOCUS_LOST",
                weight=5,
                explanation="Examination window lost focus.",
                requires_evidence=False,
                minimum_confidence=0.0,
            ),
            "FULLSCREEN_EXIT": ScoringRule(
                event_type="FULLSCREEN_EXIT",
                weight=5,
                explanation="Examination fullscreen mode was exited.",
                requires_evidence=False,
                minimum_confidence=0.0,
            ),
        }
    )


DEFAULT_SCORING_CONFIG = ScoringConfig()
