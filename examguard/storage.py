
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonlStore:

    def __init__(
        self,
        path: str | Path = "data/events.jsonl"
    ):
        self.path = Path(path)

        
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        
        self.path.touch(exist_ok=True)

    def append(self, record: dict[str, Any]) -> None:
        """Append one JSON object as a single line."""

        if not isinstance(record, dict):
            raise ValueError("record must be a dictionary/object")

        with self.path.open("a", encoding="utf-8") as handle:

            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":")
                ) + "\n"
            )

    def read_all(self) -> list[dict[str, Any]]:
        """Read and validate all JSON records."""

        records: list[dict[str, Any]] = []

        if not self.path.exists():
            return records

        with self.path.open("r", encoding="utf-8") as handle:

            for line_number, line in enumerate(handle, start=1):

                if not line.strip():
                    continue

                try:
                    value = json.loads(line)

                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON at {self.path}:{line_number}"
                    ) from exc

                if not isinstance(value, dict):
                    raise ValueError(
                        f"Expected JSON object at {self.path}:{line_number}"
                    )

                records.append(value)

        return records

    def list_all(self) -> list[dict[str, Any]]:
        """Return all stored events."""

        return self.read_all()

    def list_by_session(
        self,
        session_id: str
    ) -> list[dict[str, Any]]:
        """Return events belonging to a specific session."""

        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError(
                "session_id must be a non-empty string"
            )

        sid = session_id.strip()

        events = [
            event
            for event in self.read_all()
            if event.get("session_id") == sid
        ]

        return sorted(
            events,
            key=lambda event: (
                event.get("timestamp", ""),
                event.get("sequence_number", 0),
                event.get("event_id", ""),
            )
        )

    def reset(self) -> None:
        """Remove all stored events."""

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.path.write_text(
            "",
            encoding="utf-8"
        )
