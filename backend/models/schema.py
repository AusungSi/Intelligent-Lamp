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

"""

