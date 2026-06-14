import ujson


DEFAULT_CONFIG = {
    "device_id": "esp32-study-lamp-01",
    "backend_host": "192.168.1.100",
    "backend_port": 5000,
    "device_token": "change-me",
    "telemetry_interval_seconds": 1,
    "heartbeat_interval_seconds": 5,
    "config_refresh_seconds": 60,
    "camera_enabled": True,
    "camera_frame_interval_ms": 300,
    "camera_framesize": "QVGA",
    "camera_vflip": 1,
    "camera_brightness": 1,
    "local_camera_stream_enabled": True,
    "local_camera_stream_port": 80,
    "local_camera_frame_interval_ms": 120,
    "connect_timeout_seconds": 10,
    "lamp_brightness_pin": None,
    "lamp_warm_pin": None,
    "lamp_cool_pin": None,
}


def load_config(path="secrets.json"):
    config = DEFAULT_CONFIG.copy()
    try:
        with open(path, "r") as fp:
            file_config = ujson.load(fp)
    except OSError:
        raise RuntimeError(
            "Missing secrets.json. Copy secrets.example.json to secrets.json and fill it in."
        )

    for key, value in file_config.items():
        config[key] = value

    if not config.get("wifi_ssid") or not config.get("wifi_password"):
        raise RuntimeError("wifi_ssid and wifi_password must be set in secrets.json")

    return config

