
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path


class JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:

        data = {
            "timestamp": datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),

            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),

            "session_id": getattr(record, "session_id", None),
            "event_id": getattr(record, "event_id", None),
        }

        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        return json.dumps(data, ensure_ascii=False)


def configure_logging(
    log_path: str | Path = "logs/examguard.log",
    level: int = logging.INFO,
) -> logging.Logger:

    
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    
    logger = logging.getLogger("examguard")
    logger.setLevel(level)

    
    logger.handlers.clear()
    logger.propagate = False

    
    formatter = JsonFormatter()

    
    file_handler = logging.FileHandler(
        path,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
