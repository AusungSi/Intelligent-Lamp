from flask import Blueprint, current_app, request

from backend.services import camera_store, telemetry_service
from backend.utils.response import error, ok


device_api = Blueprint("device_api", __name__)


def _device_auth_failed():
    token = request.headers.get("X-Device-Token")
    return token != current_app.config["DEVICE_TOKEN"]


@device_api.before_request
def verify_device_token():
    if _device_auth_failed():
        return error("Unauthorized device token", 401)
    return None


@device_api.post("/telemetry")
def receive_telemetry():
    payload = request.get_json(silent=True) or {}
    if not payload.get("device_id"):
        return error("device_id is required")
    result = telemetry_service.save_telemetry(payload)
    return ok({"message": "telemetry stored", **result}, 201)


@device_api.post("/events")
def receive_event():
    payload = request.get_json(silent=True) or {}
    if not payload.get("device_id") or not payload.get("event_type"):
        return error("device_id and event_type are required")
    event_id = telemetry_service.save_event(payload)
    return ok({"message": "event stored", "event_id": event_id}, 201)


@device_api.post("/events/<int:event_id>/snapshot")
def upload_event_snapshot(event_id):
    jpeg_bytes = request.get_data()
    if not jpeg_bytes:
        return error("empty snapshot body")
    if not telemetry_service.attach_event_snapshot(event_id, jpeg_bytes):
        return error("failed to attach snapshot", 404)
    return ok({"message": "snapshot stored"}, 201)


@device_api.post("/heartbeat")
def receive_heartbeat():
    payload = request.get_json(silent=True) or {}
    if not payload.get("device_id"):
        return error("device_id is required")
    telemetry_service.save_heartbeat(payload)
    return ok({"message": "heartbeat stored"}, 201)


@device_api.post("/camera/frame")
def receive_camera_frame():
    device_id = request.headers.get("X-Device-Id") or request.args.get("device_id") or "unknown"
    timestamp = request.args.get("timestamp", type=int)
    frame = request.get_data()
    if not frame:
        return error("empty frame body")
    camera_store.update_frame(device_id, frame, timestamp)
    return ok({"message": "frame stored"})


@device_api.get("/config")
def device_config():
    return ok(
        {
            "settings": {
                "distance_warning_mm": 350,
                "distance_presence_mm": 1200,
                "light_low_lux": 150,
                "temperature_high_c": 30,
                "humidity_high_percent": 75,
                "leave_grace_seconds": 15,
                "snapshot_enabled": True,
                "snapshot_event_types": ["distance_too_close", "presence_away"],
            },
            "features": {
                "backend_lamp_control": True,
                "backend_pose_detection": True,
            },
        }
    )


