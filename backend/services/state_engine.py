import json
import time

from backend.services.db import execute, fetch_one


DEFAULT_THRESHOLDS = {
    "distance_warning_mm": 350,
    "distance_presence_mm": 1200,
    "light_low_lux": 150,
    "temperature_high_c": 30,
    "humidity_high_percent": 75,
}


def derive_state(payload, pose=None):
    now = int(payload.get("timestamp") or time.time())
    presence_state, distance_level = _classify_distance(payload.get("distance_mm"))
    env_labels = _classify_environment(payload)
    pose_state = (pose or {}).get("pose_state") or "unknown"

    study_state = "idle"
    if presence_state == "present":
        study_state = "warning" if distance_level == "too_close" or env_labels != ["normal"] else "studying"
    if pose_state not in ("unknown", "normal", "low_confidence") and presence_state == "present":
        study_state = "warning"

    return {
        "device_id": payload.get("device_id"),
        "timestamp": now,
        "presence_state": payload.get("presence_state") or presence_state,
        "distance_level": payload.get("distance_level") or distance_level,
        "env_labels": payload.get("env_label") or env_labels,
        "pose_state": pose_state,
        "study_state": payload.get("study_state") or study_state,
    }


def save_derived_state(state, recommended_action=None):
    state_id = execute(
        """
        INSERT INTO derived_states (
            device_id, timestamp, presence_state, distance_level, env_labels_json,
            pose_state, study_state, recommended_action_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            state.get("device_id"),
            state.get("timestamp"),
            state.get("presence_state"),
            state.get("distance_level"),
            json.dumps(state.get("env_labels") or [], ensure_ascii=False),
            state.get("pose_state"),
            state.get("study_state"),
            json.dumps(recommended_action or {}, ensure_ascii=False),
        ),
    )
    return fetch_one("SELECT * FROM derived_states WHERE id = ?", (state_id,))


def get_latest_derived_state():
    row = fetch_one("SELECT * FROM derived_states ORDER BY id DESC LIMIT 1")
    if row and row.get("env_labels_json"):
        row["env_labels"] = json.loads(row["env_labels_json"])
        row.pop("env_labels_json", None)
    if row and row.get("recommended_action_json"):
        row["recommended_action"] = json.loads(row["recommended_action_json"])
        row.pop("recommended_action_json", None)
    return row


def _classify_distance(distance_mm):
    if distance_mm is None:
        return "unknown", "unknown"
    distance = int(distance_mm)
    if distance <= DEFAULT_THRESHOLDS["distance_warning_mm"]:
        return "present", "too_close"
    if distance <= DEFAULT_THRESHOLDS["distance_presence_mm"]:
        return "present", "normal"
    return "away", "far"


def _classify_environment(payload):
    labels = []
    lux = payload.get("lux")
    temperature = payload.get("temperature")
    humidity = payload.get("humidity")
    if lux is not None and float(lux) < DEFAULT_THRESHOLDS["light_low_lux"]:
        labels.append("too_dark")
    if temperature is not None and float(temperature) > DEFAULT_THRESHOLDS["temperature_high_c"]:
        labels.append("too_hot")
    if humidity is not None and float(humidity) > DEFAULT_THRESHOLDS["humidity_high_percent"]:
        labels.append("too_humid")
    return labels or ["normal"]
