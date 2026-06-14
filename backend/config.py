import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "study_lamp.db"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
MIJIA_AUTH_DIR = DATA_DIR / "mijia"
MIJIA_AUTH_PATH = MIJIA_AUTH_DIR / "auth.json"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


class Config:
    SECRET_KEY = os.getenv("STUDYPILOT_SECRET_KEY", "studypilot-dev-key")
    DEVICE_TOKEN = os.getenv("STUDYPILOT_DEVICE_TOKEN", "change-me")
    DATABASE_PATH = str(DATABASE_PATH)
    SNAPSHOT_DIR = str(SNAPSHOT_DIR)
    MIJIA_AUTH_PATH = str(MIJIA_AUTH_PATH)
    MIJIA_AUTH_DIR = str(MIJIA_AUTH_DIR)
    FRONTEND_DIR = str(FRONTEND_DIR)
    CAMERA_STREAM_INTERVAL = float(os.getenv("STUDYPILOT_CAMERA_STREAM_INTERVAL", "0.2"))
    CAMERA_STALE_SECONDS = int(os.getenv("STUDYPILOT_CAMERA_STALE_SECONDS", "5"))
    LAMP_COMMAND_DEBOUNCE_SECONDS = int(os.getenv("STUDYPILOT_LAMP_COMMAND_DEBOUNCE_SECONDS", "10"))

