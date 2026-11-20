from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import AuditRecord
from .storage import JsonlStore


class AuditService:
    def __init__(self, audit_path: str | Path):
        self.store = JsonlStore(audit_path)

    def record_action(
        self,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: str,
        *,
        outcome: str = "SUCCESS",
        details: dict[str, Any] | None = None,
    ) -> AuditRecord:
        record = AuditRecord.create(
            actor_id, action, target_type, target_id,
            outcome=outcome, details=details,
        )
        self.store.append(record.to_dict())
        return record

    def list_records(self, target_id: str | None = None) -> list[dict[str, Any]]:
        records = self.store.read_all()
        if target_id:
            records = [row for row in records if row.get("target_id") == target_id]
        return records
