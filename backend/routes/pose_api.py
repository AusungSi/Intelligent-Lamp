from flask import Blueprint, current_app, request

from backend.services import pose_service, telemetry_service
from backend.utils.response import error, ok


pose_api = Blueprint("pose_api", __name__)


def _device_auth_failed():
    token = request.headers.get("X-Device-Token")
    return token != current_app.config["DEVICE_TOKEN"]


@pose_api.post("/analyze/latest-frame")
def analyze_latest_frame():
    return ok({"pose": pose_service.analyze_latest_frame()}, 201)


@pose_api.post("/result")
def save_pose_result():
    if _device_auth_failed():
        return error("Unauthorized device token", 401)

    payload = request.get_json(silent=True) or {}
    if not payload.get("pose_state"):
        return error("pose_state is required")
    return ok({"pose": telemetry_service.save_pose_result(payload)}, 201)


@pose_api.get("/latest")
def latest_pose():
    return ok({"pose": telemetry_service.get_latest_pose()})


@pose_api.get("/history")
def pose_history():
    limit = request.args.get("limit", default=100, type=int)
    return ok({"items": telemetry_service.get_pose_history(limit)})


@pose_api.get("/config")
def pose_config():
    return ok({"pose": pose_service.get_config()})


@pose_api.put("/config")
def update_pose_config():
    payload = request.get_json(silent=True) or {}
    return ok({"pose": pose_service.update_config(payload)})


@pose_api.get("/docs")
def pose_docs():
    return ok(
        {
            "integration": "Backend-only pose detection. Replace backend.services.pose_service.analyze_latest_frame internals with the selected model.",
            "states": [
                "unknown",
                "normal",
                "head_down",
                "leaning_left",
                "leaning_right",
                "too_close",
                "absent",
                "multi_person",
                "low_confidence",
            ],
            "record_shape": {
                "device_id": "camera source device id",
                "timestamp": "unix seconds",
                "provider": "backend detector name",
                "pose_state": "one of states",
                "confidence": "0..1",
                "keypoints": [{"name": "nose", "x": 0.5, "y": 0.2, "score": 0.9}],
                "risk_labels": ["bad_posture"],
            },
        }
    )
