import json
import time

from backend.services import snapshot_store, summary_service
from backend.services import policy_engine, state_engine
from backend.services.db import execute, fetch_all, fetch_one

DEFAULT_SNAPSHOT_EVENT_TYPES = frozenset({"distance_too_close", "presence_away"})
MAX_DEVICE_CLOCK_DRIFT_SECONDS = 24 * 60 * 60
LEAVE_GRACE_SECONDS = 15
POSTURE_WINDOW_SECONDS = 10
POSTURE_MIN_ABNORMAL_RATIO = 0.6
POSTURE_MIN_SAMPLES = 5
POSTURE_EVENT_COOLDOWN_SECONDS = 60
POSTURE_EVENT_RULES = {
    "reading_abnormal": {
        "event_type": "posture_reading_abnormal",
        "message": "看书姿势不正确",
    },
    "computer_abnormal": {
        "event_type": "posture_computer_abnormal",
        "message": "使用电脑姿势不正确",
    },
}


def _snapshot_event_types():
    return DEFAULT_SNAPSHOT_EVENT_TYPES


def _normalize_device_timestamps(payload, timestamp_fields):
    normalized = dict(payload)
    now = int(time.time())
    raw_timestamp = normalized.get("timestamp")

    try:
        timestamp = int(raw_timestamp)
    except (TypeError, ValueError):
        normalized["timestamp"] = now
        return normalized

    if abs(now - timestamp) <= MAX_DEVICE_CLOCK_DRIFT_SECONDS:
        return normalized

    offset = now - timestamp
    for field in timestamp_fields:
        value = normalized.get(field)
        if value in (None, 0):
            continue
        try:
            normalized[field] = int(value) + offset
        except (TypeError, ValueError):
            normalized[field] = now
    normalized["timestamp"] = now
    return normalized


def save_telemetry(payload):
    payload = _normalize_device_timestamps(
        payload,
        (
            "timestamp",
            "temperature_timestamp",
            "humidity_timestamp",
            "lux_timestamp",
            "distance_timestamp",
            "session_started_at",
        ),
    )
    env_label = payload.get("env_label") or []
    execute(
        """
        INSERT INTO sensor_records (
            device_id, timestamp, temperature, humidity, lux, distance_mm,
            temperature_timestamp, humidity_timestamp, lux_timestamp, distance_timestamp,
            presence_state, distance_level, env_label, study_state, study_duration, session_started_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("device_id"),
            payload.get("timestamp", int(time.time())),
            payload.get("temperature"),
            payload.get("humidity"),
            payload.get("lux"),
            payload.get("distance_mm"),
            payload.get("temperature_timestamp"),
            payload.get("humidity_timestamp"),
            payload.get("lux_timestamp"),
            payload.get("distance_timestamp"),
            payload.get("presence_state"),
            payload.get("distance_level"),
            json.dumps(env_label),
            payload.get("study_state"),
            payload.get("study_duration", 0),
            payload.get("session_started_at", 0),
        ),
    )
    derived_state = state_engine.derive_state(payload, get_latest_pose())
    sync_session_from_derived(payload, derived_state)
    lamp_action = policy_engine.maybe_execute(derived_state, payload)
    state_engine.save_derived_state(derived_state, lamp_action.get("action"))
    maybe_emit_posture_warning(derived_state)
    return {"derived_state": derived_state, "lamp_action": lamp_action}


def save_event(payload):
    payload = _normalize_device_timestamps(payload, ("timestamp",))
    event_id = execute(
        """
        INSERT INTO events (
            device_id, timestamp, event_type, level, message, presence_state, distance_level, study_state, extra_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("device_id"),
            payload.get("timestamp", int(time.time())),
            payload.get("event_type"),
            payload.get("level", "info"),
            payload.get("message", ""),
            payload.get("presence_state"),
            payload.get("distance_level"),
            payload.get("study_state"),
            json.dumps(payload.get("extra") or {}),
        ),
    )
    sync_session_from_event(payload)
    return event_id


def attach_event_snapshot(event_id, jpeg_bytes):
    event = fetch_one("SELECT * FROM events WHERE id = ?", (event_id,))
    if event is None:
        return False
    if event.get("event_type") not in _snapshot_event_types():
        return False

    snapshot_path = snapshot_store.save_event_snapshot(event_id, jpeg_bytes)
    execute(
        """
        UPDATE events
        SET snapshot_path = ?, has_snapshot = 1
        WHERE id = ?
        """,
        (snapshot_path, event_id),
    )
    return True


def save_heartbeat(payload):
    payload = _normalize_device_timestamps(payload, ("timestamp",))
    execute(
        """
        INSERT INTO heartbeats (device_id, timestamp, ip, study_state)
        VALUES (?, ?, ?, ?)
        """,
        (
            payload.get("device_id"),
            payload.get("timestamp", int(time.time())),
            payload.get("ip"),
            payload.get("study_state"),
        ),
    )


def sync_session_from_derived(payload, derived_state):
    device_id = derived_state.get("device_id") or payload.get("device_id")
    active = get_active_session(device_id)
    presence_state = derived_state.get("presence_state")
    timestamp = int(derived_state.get("timestamp") or payload.get("timestamp") or time.time())

    if presence_state == "present":
        if active is None:
            execute(
                """
                INSERT INTO study_sessions (device_id, started_at, status)
                VALUES (?, ?, 'active')
                """,
                (device_id, timestamp),
            )
        return

    if active is None or presence_state != "away":
        return

    if _latest_derived_presence(device_id) == "present":
        execute(
            """
            UPDATE study_sessions
            SET leave_count = leave_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (active["id"],),
        )

    last_present_at = _latest_present_timestamp(device_id)
    if last_present_at is None:
        last_present_at = int(active.get("started_at") or timestamp)
    if timestamp - last_present_at >= LEAVE_GRACE_SECONDS:
        close_active_session(device_id, timestamp)


def sync_session_from_event(payload):
    device_id = payload.get("device_id")
    event_type = payload.get("event_type")
    active = get_active_session(device_id)

    if active is None:
        return

    if event_type in (
        "distance_too_close",
        "environment_changed",
        "posture_reading_abnormal",
        "posture_computer_abnormal",
    ):
        execute(
            """
            UPDATE study_sessions
            SET warning_count = warning_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (active["id"],),
        )


def maybe_emit_posture_warning(derived_state):
    device_id = derived_state.get("device_id")
    timestamp = int(derived_state.get("timestamp") or time.time())
    pose_state = derived_state.get("pose_state")
    rule = POSTURE_EVENT_RULES.get(pose_state)
    if not device_id or not rule:
        return None

    stats = _posture_window_stats(device_id, pose_state, timestamp)
    if stats["total"] < POSTURE_MIN_SAMPLES or stats["ratio"] < POSTURE_MIN_ABNORMAL_RATIO:
        return None

    event_type = rule["event_type"]
    if _recent_event_exists(device_id, event_type, timestamp, POSTURE_EVENT_COOLDOWN_SECONDS):
        return None

    event = {
        "device_id": device_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "level": "warning",
        "message": rule["message"],
        "presence_state": derived_state.get("presence_state"),
        "distance_level": derived_state.get("distance_level"),
        "study_state": derived_state.get("study_state"),
        "extra": {
            "pose_state": pose_state,
            "window_seconds": POSTURE_WINDOW_SECONDS,
            "sample_count": stats["total"],
            "abnormal_count": stats["abnormal"],
            "abnormal_ratio": round(stats["ratio"], 3),
        },
    }
    return save_event(event)


def _posture_window_stats(device_id, pose_state, timestamp):
    rows = fetch_all(
        """
        SELECT pose_state FROM derived_states
        WHERE device_id = ?
          AND timestamp >= ?
          AND timestamp <= ?
          AND presence_state = 'present'
          AND pose_state IN (
            'calibration_normal',
            'computer_normal',
            'computer_abnormal',
            'reading_normal',
            'reading_abnormal'
          )
        ORDER BY timestamp DESC
        """,
        (device_id, timestamp - POSTURE_WINDOW_SECONDS + 1, timestamp),
    )
    total = len(rows)
    abnormal = sum(1 for row in rows if row.get("pose_state") == pose_state)
    ratio = abnormal / total if total else 0
    return {"total": total, "abnormal": abnormal, "ratio": ratio}


def _recent_event_exists(device_id, event_type, timestamp, cooldown_seconds):
    row = fetch_one(
        """
        SELECT id FROM events
        WHERE device_id = ?
          AND event_type = ?
          AND timestamp >= ?
        ORDER BY id DESC LIMIT 1
        """,
        (device_id, event_type, timestamp - cooldown_seconds),
    )
    return row is not None


def get_active_session(device_id):
    return fetch_one(
        """
        SELECT * FROM study_sessions
        WHERE device_id = ? AND status = 'active'
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (device_id,),
    )


def _latest_derived_presence(device_id):
    if not device_id:
        return None
    row = fetch_one(
        """
        SELECT presence_state FROM derived_states
        WHERE device_id = ?
        ORDER BY id DESC LIMIT 1
        """,
        (device_id,),
    )
    return row.get("presence_state") if row else None


def _latest_present_timestamp(device_id):
    if not device_id:
        return None
    row = fetch_one(
        """
        SELECT timestamp FROM derived_states
        WHERE device_id = ? AND presence_state = 'present'
        ORDER BY id DESC LIMIT 1
        """,
        (device_id,),
    )
    return int(row["timestamp"]) if row and row.get("timestamp") else None


def close_active_session(device_id, ended_at, duration_seconds=None):
    session = get_active_session(device_id)
    if session is None:
        return None

    if duration_seconds is None:
        duration_seconds = max(0, int(ended_at) - int(session["started_at"]))

    summary_text = summary_service.build_summary(
        {
            "started_at": session["started_at"],
            "ended_at": ended_at,
            "duration_seconds": duration_seconds,
        },
        session["warning_count"],
        session["leave_count"],
    )

    execute(
        """
        UPDATE study_sessions
        SET ended_at = ?, duration_seconds = ?, summary_text = ?, status = 'completed', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (ended_at, duration_seconds, summary_text, session["id"]),
    )
    return fetch_one("SELECT * FROM study_sessions WHERE id = ?", (session["id"],))


def _serialize_event(row):
    if row is None:
        return None

    event = dict(row)
    event["extra_json"] = json.loads(event["extra_json"]) if event.get("extra_json") else {}
    if event.get("has_snapshot") and event.get("event_type") in _snapshot_event_types():
        event["snapshot_url"] = f"/api/status/events/{event['id']}/snapshot.jpg"
    else:
        event["snapshot_url"] = None
    event.pop("snapshot_path", None)
    event.pop("has_snapshot", None)
    return event


def get_current_status():
    latest_telemetry = fetch_one(
        """
        SELECT * FROM sensor_records ORDER BY id DESC LIMIT 1
        """
    )
    latest_heartbeat = fetch_one(
        """
        SELECT * FROM heartbeats ORDER BY id DESC LIMIT 1
        """
    )
    latest_event = fetch_one(
        """
        SELECT * FROM events ORDER BY id DESC LIMIT 1
        """
    )

    if latest_telemetry and latest_telemetry.get("env_label"):
        latest_telemetry["env_label"] = json.loads(latest_telemetry["env_label"])

    return {
        "telemetry": latest_telemetry,
        "heartbeat": latest_heartbeat,
        "latest_event": _serialize_event(latest_event),
        "pose": get_latest_pose(),
        "derived_state": state_engine.get_latest_derived_state(),
    }


def get_telemetry_history(limit=120):
    rows = fetch_all(
        """
        SELECT * FROM sensor_records ORDER BY id DESC LIMIT ?
        """,
        (limit,),
    )
    for row in rows:
        row["env_label"] = json.loads(row["env_label"]) if row.get("env_label") else []
    return list(reversed(rows))


def get_events_total():
    total_row = fetch_one("SELECT COUNT(*) AS total FROM events")
    return int(total_row["total"]) if total_row else 0


def get_events(limit=50):
    rows = fetch_all(
        """
        SELECT * FROM events ORDER BY id DESC LIMIT ?
        """,
        (limit,),
    )
    return [_serialize_event(row) for row in rows]


def get_events_page(page=1, page_size=6):
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    offset = (page - 1) * page_size

    total_row = fetch_one("SELECT COUNT(*) AS total FROM events")
    total = int(total_row["total"]) if total_row else 0
    rows = fetch_all(
        """
        SELECT * FROM events ORDER BY id DESC LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    )

    return {
        "items": [_serialize_event(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_current_session():
    session = fetch_one(
        """
        SELECT * FROM study_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1
        """
    )
    if session and session.get("started_at"):
        session["duration_seconds"] = max(0, int(time.time()) - int(session["started_at"]))
    return session


def get_latest_summary():
    return fetch_one(
        """
        SELECT * FROM study_sessions
        WHERE status = 'completed'
        ORDER BY id DESC
        LIMIT 1
        """
    )


def get_today_summary():
    sessions = fetch_all(
        """
        SELECT * FROM study_sessions
        WHERE date(created_at) = date('now', 'localtime')
        ORDER BY started_at DESC
        """
    )
    total_duration = sum(int(item.get("duration_seconds") or 0) for item in sessions)
    total_warnings = sum(int(item.get("warning_count") or 0) for item in sessions)
    total_leaves = sum(int(item.get("leave_count") or 0) for item in sessions)
    return {
        "sessions": sessions,
        "total_duration_seconds": total_duration,
        "total_warning_count": total_warnings,
        "total_leave_count": total_leaves,
    }


def save_pose_result(payload):
    record_id = execute(
        """
        INSERT INTO pose_records (
            device_id, timestamp, provider, pose_state, confidence,
            keypoints_json, risk_labels_json, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("device_id"),
            payload.get("timestamp", int(time.time())),
            payload.get("provider", "backend_latest_frame"),
            payload.get("pose_state", "unknown"),
            payload.get("confidence", 0),
            json.dumps(payload.get("keypoints") or []),
            json.dumps(payload.get("risk_labels") or []),
            json.dumps(payload.get("raw") or {}),
        ),
    )
    return fetch_one("SELECT * FROM pose_records WHERE id = ?", (record_id,))


def get_latest_pose():
    row = fetch_one("SELECT * FROM pose_records ORDER BY id DESC LIMIT 1")
    if row:
        row["keypoints"] = json.loads(row["keypoints_json"]) if row.get("keypoints_json") else []
        row["risk_labels"] = json.loads(row["risk_labels_json"]) if row.get("risk_labels_json") else []
        row["raw"] = json.loads(row["raw_json"]) if row.get("raw_json") else {}
        row.pop("keypoints_json", None)
        row.pop("risk_labels_json", None)
        row.pop("raw_json", None)
    return row


def get_pose_history(limit=100):
    rows = fetch_all(
        """
        SELECT * FROM pose_records ORDER BY id DESC LIMIT ?
        """,
        (limit,),
    )
    items = []
    for row in rows:
        row["keypoints"] = json.loads(row["keypoints_json"]) if row.get("keypoints_json") else []
        row["risk_labels"] = json.loads(row["risk_labels_json"]) if row.get("risk_labels_json") else []
        row["raw"] = json.loads(row["raw_json"]) if row.get("raw_json") else {}
        row.pop("keypoints_json", None)
        row.pop("risk_labels_json", None)
        row.pop("raw_json", None)
        items.append(row)
    return list(reversed(items))
