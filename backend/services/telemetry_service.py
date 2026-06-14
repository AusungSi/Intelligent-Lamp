import json
import time

from backend.services import snapshot_store, summary_service
from backend.services import policy_engine, state_engine
from backend.services.db import execute, fetch_all, fetch_one

DEFAULT_SNAPSHOT_EVENT_TYPES = frozenset({"distance_too_close", "presence_away"})


def _snapshot_event_types():
    return DEFAULT_SNAPSHOT_EVENT_TYPES


def save_telemetry(payload):
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
    sync_session_from_telemetry(payload)
    derived_state = state_engine.derive_state(payload, get_latest_pose())
    lamp_action = policy_engine.maybe_execute(derived_state, payload)
    state_engine.save_derived_state(derived_state, lamp_action.get("action"))
    return {"derived_state": derived_state, "lamp_action": lamp_action}


def save_event(payload):
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


def sync_session_from_telemetry(payload):
    device_id = payload.get("device_id")
    active = get_active_session(device_id)
    session_started_at = payload.get("session_started_at") or 0
    study_state = payload.get("study_state")
    study_duration = int(payload.get("study_duration") or 0)

    if session_started_at and active is None:
        execute(
            """
            INSERT INTO study_sessions (device_id, started_at, status)
            VALUES (?, ?, 'active')
            """,
            (device_id, session_started_at),
        )
        active = get_active_session(device_id)

    if active and study_state == "idle" and study_duration == 0 and payload.get("presence_state") == "away":
        close_active_session(device_id, payload.get("timestamp", int(time.time())))


def sync_session_from_event(payload):
    device_id = payload.get("device_id")
    event_type = payload.get("event_type")
    active = get_active_session(device_id)

    if event_type == "study_started" and active is None:
        execute(
            """
            INSERT INTO study_sessions (device_id, started_at, status)
            VALUES (?, ?, 'active')
            """,
            (device_id, payload.get("timestamp", int(time.time()))),
        )
        return

    if active is None:
        return

    if event_type in ("distance_too_close", "environment_changed"):
        execute(
            """
            UPDATE study_sessions
            SET warning_count = warning_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (active["id"],),
        )
    elif event_type == "presence_away":
        execute(
            """
            UPDATE study_sessions
            SET leave_count = leave_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (active["id"],),
        )
    elif event_type == "study_finished":
        close_active_session(
            device_id,
            payload.get("timestamp", int(time.time())),
            int((payload.get("extra") or {}).get("study_duration", 0)),
        )


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
