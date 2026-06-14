SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sensor_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    temperature REAL,
    humidity REAL,
    lux REAL,
    distance_mm INTEGER,
    temperature_timestamp INTEGER,
    humidity_timestamp INTEGER,
    lux_timestamp INTEGER,
    distance_timestamp INTEGER,
    presence_state TEXT,
    distance_level TEXT,
    env_label TEXT,
    study_state TEXT,
    study_duration INTEGER,
    session_started_at INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    presence_state TEXT,
    distance_level TEXT,
    study_state TEXT,
    extra_json TEXT,
    snapshot_path TEXT,
    has_snapshot INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS heartbeats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    ip TEXT,
    study_state TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    duration_seconds INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    leave_count INTEGER DEFAULT 0,
    summary_text TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mijia_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    auth_path TEXT NOT NULL,
    login_status TEXT NOT NULL DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_verified_at INTEGER
);

CREATE TABLE IF NOT EXISTS lamp_bindings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    did TEXT NOT NULL,
    name TEXT,
    model TEXT,
    room_name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    capability_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lamp_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    binding_id INTEGER NOT NULL,
    power INTEGER,
    brightness INTEGER,
    color_temperature INTEGER,
    mode TEXT NOT NULL DEFAULT 'auto',
    online INTEGER,
    source TEXT,
    raw_prop_json TEXT,
    manual_override_until INTEGER DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lamp_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    binding_id INTEGER,
    command_type TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    payload_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    reason TEXT,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    executed_at INTEGER
);

CREATE TABLE IF NOT EXISTS lamp_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    config_json TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS derived_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    presence_state TEXT,
    distance_level TEXT,
    env_labels_json TEXT,
    pose_state TEXT,
    study_state TEXT,
    recommended_action_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pose_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    timestamp INTEGER NOT NULL,
    provider TEXT,
    pose_state TEXT,
    confidence REAL,
    keypoints_json TEXT,
    risk_labels_json TEXT,
    raw_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

"""

