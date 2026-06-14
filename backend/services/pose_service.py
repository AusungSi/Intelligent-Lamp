import json
import time

from backend.services import camera_store, telemetry_service
from backend.services.db import execute, fetch_one


DEFAULT_CONFIG = {
    "enabled": False,
    "provider": "backend_latest_frame",
    "analyze_interval_seconds": 2,
    "min_confidence": 0.65,
}


def get_config():
    row = fetch_one("SELECT * FROM lamp_policies WHERE name = 'pose' LIMIT 1")
    if not row:
        policy_id = execute(
            """
            INSERT INTO lamp_policies (name, enabled, config_json)
            VALUES ('pose', 0, ?)
            """,
            (json.dumps(DEFAULT_CONFIG),),
        )
        row = fetch_one("SELECT * FROM lamp_policies WHERE id = ?", (policy_id,))
    config = json.loads(row["config_json"]) if row.get("config_json") else {}
    return {"enabled": bool(row.get("enabled")), "config": {**DEFAULT_CONFIG, **config}}


def update_config(payload):
    current = get_config()
    config = {**current["config"], **(payload.get("config") or payload)}
    enabled = payload.get("enabled", current["enabled"])
    execute(
        """
        UPDATE lamp_policies
        SET enabled = ?, config_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE name = 'pose'
        """,
        (1 if enabled else 0, json.dumps(config),),
    )
    return get_config()


def analyze_latest_frame():
    frame, frame_timestamp, device_id = camera_store.get_latest_frame()
    if frame is None:
        payload = {
            "device_id": device_id,
            "timestamp": int(time.time()),
            "provider": "backend_latest_frame",
            "pose_state": "unknown",
            "confidence": 0,
            "risk_labels": ["no_frame"],
            "keypoints": [],
            "raw": {"message": "No camera frame available"},
        }
        return telemetry_service.save_pose_result(payload)

    # Placeholder for a backend-only pose detector. The integration point is here:
    # decode frame bytes, run the model, then fill pose_state/confidence/keypoints.
    payload = {
        "device_id": device_id,
        "timestamp": int(frame_timestamp or time.time()),
        "provider": "backend_latest_frame",
        "pose_state": "low_confidence",
        "confidence": 0,
        "risk_labels": ["pose_detector_not_configured"],
        "keypoints": [],
        "raw": {"frame_bytes": len(frame)},
    }
    return telemetry_service.save_pose_result(payload)
