
from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Any

from .audit_service import AuditService


class EvidenceService:

    def __init__(
        self,
        evidence_dir: str | Path = "data/evidence",
        max_file_size: int = 10 * 1024 * 1024,
        audit_service: AuditService | None = None,
    ):
        self.evidence_dir = Path(evidence_dir).resolve()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.audit_service = audit_service

    def validate_evidence(
        self,
        relative_path: str,
        expected_sha256: str | None = None,
    ) -> dict[str, Any]:

        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Evidence path is required")

        requested_path = Path(relative_path)

        if requested_path.is_absolute():
            raise ValueError("Absolute evidence paths are not allowed")

        if ".." in requested_path.parts:
            raise ValueError("Path traversal is not allowed")

        file_path = (self.evidence_dir / requested_path).resolve()

        try:
            file_path.relative_to(self.evidence_dir)
        except ValueError:
            raise ValueError(
                "Evidence path is outside the evidence directory"
            )

        if not file_path.is_file():
            raise ValueError("Evidence file does not exist")

        file_size = file_path.stat().st_size

        if file_size > self.max_file_size:
            raise ValueError("Evidence file exceeds the maximum size")

        sha256_hash = hashlib.sha256()

        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(8192), b""):
                sha256_hash.update(chunk)

        actual_sha256 = sha256_hash.hexdigest()

        if expected_sha256 is not None:

            if not isinstance(expected_sha256, str):
                raise ValueError("Invalid expected SHA-256 hash")

            if not hmac.compare_digest(
                actual_sha256.lower(),
                expected_sha256.lower()
            ):
                raise ValueError("Evidence SHA-256 hash mismatch")

        return {
            "valid": True,
            "file_name": file_path.name,
            "file_size": file_size,
            "sha256": actual_sha256,
        }

    def check_access(
        self,
        actor_id: str,
        owner_id: str,
        evidence_id: str,
        *,
        role: str = "candidate",
    ) -> bool:

        if not all(
            isinstance(value, str) and value.strip()
            for value in (actor_id, owner_id, evidence_id)
        ):
            raise ValueError(
                "Actor, owner and evidence IDs are required"
            )

        allowed = (
            actor_id == owner_id
            or role == "invigilator"
        )

        if self.audit_service is not None:

            self.audit_service.record_action(
                actor_id=actor_id,
                action="EVIDENCE_ACCESS",
                target_type="EVIDENCE",
                target_id=evidence_id,
                outcome="SUCCESS" if allowed else "DENIED",
                details={
                    "owner_id": owner_id,
                    "role": role,
                },
            )

        return allowed
