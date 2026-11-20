
import logging
from pathlib import Path
from uuid import uuid4

from flask import Flask, render_template, request, jsonify

from examguard.event_service import EventService
from examguard.audit_service import AuditService
from examguard.evidence_service import EvidenceService
from examguard.scoring_service import ScoringService


app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EVIDENCE_DIR = DATA_DIR / "evidence"

DATA_DIR.mkdir(exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("examguard")

event_service = EventService(
    events_path=str(DATA_DIR / "events.jsonl"),
    logger=logger
)

audit_service = AuditService(
    audit_path=DATA_DIR / "audit.jsonl"
)

evidence_service = EvidenceService(
    evidence_dir=EVIDENCE_DIR,
    audit_service=audit_service
)

# Sprint 5: Scoring Service
scoring_service = ScoringService(
    event_service=event_service,
    scores_path=DATA_DIR / "scores.jsonl",
    audit_service=audit_service
)

BROWSER_EVENT_TYPES = {
    "TAB_HIDDEN",
    "FOCUS_LOST",
    "FULLSCREEN_EXIT"
}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "success",
        "message": "Smart Examination Monitoring Platform is running"
    })


# --------------------------------------------------
# EVENT APIs
# --------------------------------------------------

@app.route("/api/events", methods=["GET"])
def get_events():
    session_id = request.args.get("session_id")

    if not session_id:
        return jsonify({
            "status": "error",
            "message": "session_id is required"
        }), 400

    events = event_service.get_session_events(session_id)

    return jsonify({
        "status": "success",
        "count": len(events),
        "events": [event.to_dict() for event in events]
    }), 200


@app.route("/api/browser-events", methods=["POST"])
def receive_browser_event():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid JSON data"
        }), 400

    required_fields = ["candidate_id", "session_id", "event_type"]

    if any(not data.get(field) for field in required_fields):
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

    event_type = data["event_type"]

    if event_type not in BROWSER_EVENT_TYPES:
        return jsonify({
            "status": "error",
            "message": "Unsupported browser event type"
        }), 400

    metadata = data.get("metadata", {})

    if not isinstance(metadata, dict):
        return jsonify({
            "status": "error",
            "message": "Metadata must be an object"
        }), 400

    event = event_service.record_event(
        candidate_id=data["candidate_id"],
        session_id=data["session_id"],
        event_type=event_type,
        severity="MEDIUM",
        source="browser",
        metadata=metadata,
        timestamp=data.get("timestamp")
    )

    audit_service.record_action(
        actor_id=data["candidate_id"],
        action="BROWSER_EVENT_RECORDED",
        target_type="INTEGRITY_EVENT",
        target_id=event["event_id"],
        details={
            "session_id": data["session_id"],
            "event_type": event_type,
            "source": "browser"
        }
    )

    return jsonify({
        "status": "success",
        "message": "Browser event recorded",
        "event": event
    }), 201


# --------------------------------------------------
# EVIDENCE APIs
# --------------------------------------------------

@app.route("/api/evidence/upload", methods=["POST"])
def upload_evidence():

    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "message": "No file uploaded"
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "message": "Filename is required"
        }), 400

    safe_name = Path(uploaded_file.filename).name

    if safe_name in ("", ".", ".."):
        return jsonify({
            "status": "error",
            "message": "Invalid filename"
        }), 400

    evidence_id = str(uuid4())
    stored_name = evidence_id + "_" + safe_name

    try:
        uploaded_file.save(EVIDENCE_DIR / stored_name)

        result = evidence_service.validate_evidence(stored_name)

        audit_service.record_action(
            actor_id="SYSTEM",
            action="EVIDENCE_UPLOADED",
            target_type="EVIDENCE",
            target_id=evidence_id,
            details={
                "file_name": safe_name,
                "sha256": result["sha256"]
            }
        )

        return jsonify({
            "status": "success",
            "message": "Evidence uploaded and validated",
            "evidence_id": evidence_id,
            "evidence": result
        }), 201

    except (ValueError, OSError) as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


@app.route("/api/evidence/validate", methods=["POST"])
def validate_evidence():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid JSON data"
        }), 400

    relative_path = data.get("file_name")
    expected_sha256 = data.get("sha256")

    try:
        result = evidence_service.validate_evidence(
            relative_path=relative_path,
            expected_sha256=expected_sha256
        )

        return jsonify({
            "status": "success",
            "message": "Evidence validation successful",
            "evidence": result
        }), 200

    except (ValueError, OSError) as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


@app.route("/api/evidence/access", methods=["POST"])
def check_evidence_access():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid JSON data"
        }), 400

    actor_id = data.get("actor_id")
    owner_id = data.get("owner_id")
    evidence_id = data.get("evidence_id")
    role = data.get("role", "candidate")

    try:
        allowed = evidence_service.check_access(
            actor_id=actor_id,
            owner_id=owner_id,
            evidence_id=evidence_id,
            role=role
        )

        if not allowed:
            return jsonify({
                "status": "error",
                "message": "Access denied"
            }), 403

        return jsonify({
            "status": "success",
            "message": "Evidence access granted",
            "evidence_id": evidence_id
        }), 200

    except ValueError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


# --------------------------------------------------
# SPRINT 5: SCORING APIs
# --------------------------------------------------

@app.route("/api/scores/calculate", methods=["POST"])
def calculate_score():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid JSON data"
        }), 400

    session_id = data.get("session_id")
    actor_id = data.get("actor_id")
    role = data.get("role", "candidate")

    if not session_id or not actor_id:
        return jsonify({
            "status": "error",
            "message": "session_id and actor_id are required"
        }), 400

    try:
        result = scoring_service.calculate_and_store(
            session_id=session_id,
            actor_id=actor_id,
            role=role
        )

        return jsonify({
            "status": "success",
            "message": "Integrity score calculated and stored",
            "score": result
        }), 201

    except PermissionError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 403

    except ValueError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


@app.route("/api/scores/<session_id>", methods=["GET"])
def retrieve_score(session_id):

    actor_id = request.args.get("actor_id")
    role = request.args.get("role", "candidate")

    if not actor_id:
        return jsonify({
            "status": "error",
            "message": "actor_id is required"
        }), 400

    try:
        result = scoring_service.get_score(
            session_id=session_id,
            actor_id=actor_id,
            role=role
        )

        if result is None:
            return jsonify({
                "status": "error",
                "message": "No score found for this session"
            }), 404

        return jsonify({
            "status": "success",
            "message": "Score retrieved successfully",
            "score": result
        }), 200

    except PermissionError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 403

    except ValueError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


@app.route("/api/scores/<session_id>/recalculate", methods=["POST"])
def recalculate_score(session_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid JSON data"
        }), 400

    actor_id = data.get("actor_id")
    role = data.get("role", "invigilator")

    if not actor_id:
        return jsonify({
            "status": "error",
            "message": "actor_id is required"
        }), 400

    try:
        result = scoring_service.recalculate(
            session_id=session_id,
            actor_id=actor_id,
            role=role
        )

        return jsonify({
            "status": "success",
            "message": "Score recalculated successfully",
            "score": result
        }), 200

    except PermissionError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 403

    except ValueError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


if __name__ == "__main__":
    app.run(debug=True)
