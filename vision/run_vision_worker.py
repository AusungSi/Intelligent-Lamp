from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from smartled_pose import PosturePipeline, load_config
from smartled_pose.config import load_reference, merge_reference
from smartled_pose.posture_classifier import (
    STATE_TEXT,
    StateClassifierDecision,
    apply_side_view_overrides,
    extract_side_features,
    state_classifier,
)


DEFAULT_CAMERA_PROFILES: dict[str, dict[str, str]] = {
    "phone": {
        "source": "0",
        "source_id": "phone-camera",
        "capture_backend": "dshow",
    },
    "board": {
        "source": "",
        "source_id": "esp32-camera",
        "capture_backend": "auto",
    },
}


def parse_source(source: str):
    if source.isdigit():
        return int(source)
    return source


def load_camera_profiles(path: str | Path) -> dict[str, dict[str, str]]:
    profiles = {name: values.copy() for name, values in DEFAULT_CAMERA_PROFILES.items()}
    profile_path = Path(path)
    if not profile_path.exists():
        return profiles

    with profile_path.open("r", encoding="utf-8") as fp:
        loaded = json.load(fp)
    if not isinstance(loaded, dict):
        raise ValueError(f"Camera profile file must contain a JSON object: {profile_path}")

    for name, values in loaded.items():
        if not isinstance(values, dict):
            continue
        profile = profiles.setdefault(str(name), {})
        for key in ("source", "source_id", "capture_backend"):
            if key in values:
                profile[key] = str(values[key])
    return profiles


def resolve_camera_options(args) -> tuple[str, str, str, str]:
    profiles = load_camera_profiles(args.camera_profiles)
    profile_name = args.camera_profile or os.environ.get("SMARTLAMP_CAMERA_PROFILE") or "phone"
    profile = profiles.get(profile_name, {})

    source = (
        args.source
        or os.environ.get("SMARTLAMP_CAMERA_SOURCE")
        or (os.environ.get("SMARTLAMP_BOARD_CAMERA_URL") if profile_name == "board" else None)
        or profile.get("source")
        or ""
    )
    source_id = (
        args.source_id
        or os.environ.get("SMARTLAMP_SOURCE_ID")
        or profile.get("source_id")
        or f"{profile_name}-camera"
    )
    capture_backend = (
        args.capture_backend
        or os.environ.get("SMARTLAMP_CAPTURE_BACKEND")
        or profile.get("capture_backend")
        or "auto"
    )

    if not source:
        raise RuntimeError(
            "Camera source is empty. For board mode, pass a stream URL such as "
            "`run_vision.cmd board http://192.168.1.50/stream` or set SMARTLAMP_BOARD_CAMERA_URL."
        )
    return profile_name, source, source_id, capture_backend.lower()


def create_capture(source: str, capture_backend: str):
    parsed_source = parse_source(str(source))
    backend_codes = {
        "auto": None,
        "any": cv2.CAP_ANY,
        "dshow": cv2.CAP_DSHOW,
        "directshow": cv2.CAP_DSHOW,
        "msmf": cv2.CAP_MSMF,
    }
    if capture_backend not in backend_codes:
        raise ValueError(f"Unsupported capture backend: {capture_backend}")
    backend_code = backend_codes[capture_backend]
    if backend_code is None:
        return cv2.VideoCapture(parsed_source)
    return cv2.VideoCapture(parsed_source, backend_code)


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    try:
        if hasattr(value, "item"):
            return value.item()
    except Exception:
        pass
    return value


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float = 2.0) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        response.read()


def post_frame(url: str, frame, headers: dict[str, str], timeout: float = 2.0) -> None:
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not ok:
        return
    request = Request(
        url,
        data=encoded.tobytes(),
        headers={"Content-Type": "image/jpeg", **headers},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        response.read()


def predict_state(snapshot, frame, pipeline, classifier) -> tuple[StateClassifierDecision, dict[str, float] | None]:
    if snapshot.output.presence_state == "absent":
        return (
            StateClassifierDecision(
                label="absent",
                text=STATE_TEXT["absent"],
                confidence=1.0,
                model_name=classifier.model_name,
            ),
            None,
        )

    features = extract_side_features(
        snapshot.output,
        reference=pipeline.reference,
        frame_width=frame.shape[1],
        frame_height=frame.shape[0],
    )
    if not features:
        return (
            StateClassifierDecision(
                label="ignore",
                text=STATE_TEXT["ignore"],
                confidence=0.0,
                model_name=classifier.model_name,
            ),
            None,
        )
    return apply_side_view_overrides(classifier.predict(features), features), features


def draw_worker_overlay(frame, decision: StateClassifierDecision, fps: float) -> None:
    color = (40, 200, 80)
    if decision.label.endswith("abnormal"):
        color = (40, 80, 240)
    elif decision.label in {"absent", "ignore"}:
        color = (180, 180, 180)

    lines = [
        f"state: {decision.label}",
        f"confidence: {decision.confidence:.2f}",
        f"model: {decision.model_name}",
        f"fps: {fps:.1f}",
    ]
    x, y = 24, 36
    for index, line in enumerate(lines):
        yy = y + index * 34
        cv2.putText(frame, line, (x, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, line, (x, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2, cv2.LINE_AA)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SmartLED visual posture worker and report state to StudyPilot backend.")
    parser.add_argument("--backend-url", default="http://127.0.0.1:5000", help="StudyPilot backend base URL.")
    parser.add_argument("--vision-token", default="change-me", help="Deprecated alias kept for old scripts.")
    parser.add_argument("--device-token", default="change-me", help="Token for optional /api/device/camera/frame upload.")
    parser.add_argument("--camera-profile", default=None, help="Camera profile name, for example phone or board.")
    parser.add_argument("--camera-profiles", default="vision/camera_sources.json", help="Optional JSON file for camera profiles.")
    parser.add_argument("--source-id", default=None, help="Source ID saved with vision records.")
    parser.add_argument("--source", default=None, help="Camera index, video path, or MJPEG stream URL.")
    parser.add_argument("--capture-backend", default=None, help="OpenCV backend: auto, dshow, msmf, or any.")
    parser.add_argument("--config", default="configs/relaxed.yaml", help="Pose runtime config.")
    parser.add_argument("--reference", default="vision/reference.json", help="Calibration reference JSON.")
    parser.add_argument("--state-samples-dir", default="output/state_classifier_1s_feedback", help="Seven-state sample directory.")
    parser.add_argument("--post-interval", type=float, default=0.5, help="Seconds between vision state posts.")
    parser.add_argument("--frame-interval", type=float, default=0.2, help="Seconds between camera frame uploads.")
    parser.add_argument("--no-frame-upload", action="store_true", help="Do not upload frames to backend camera stream.")
    parser.add_argument("--preview", action="store_true", help="Show local OpenCV preview window.")
    args = parser.parse_args()

    camera_profile, camera_source, source_id, capture_backend = resolve_camera_options(args)
    config = merge_reference(load_config(args.config), load_reference(args.reference))
    pipeline = PosturePipeline(config)
    classifier = state_classifier(args.state_samples_dir)

    capture = create_capture(camera_source, capture_backend)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, config["camera"]["width"])
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config["camera"]["height"])
    capture.set(cv2.CAP_PROP_FPS, config["camera"]["fps"])
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video source: {camera_source}")

    backend_url = args.backend_url.rstrip("/")
    state_url = f"{backend_url}/api/pose/result"
    frame_url = f"{backend_url}/api/device/camera/frame?device_id={source_id}"
    pose_headers = {"X-Device-Token": args.device_token}
    frame_headers = {"X-Device-Token": args.device_token, "X-Device-Id": source_id}

    print(
        "Vision worker started: "
        f"profile={camera_profile}, source={camera_source}, source_id={source_id}, "
        f"capture_backend={capture_backend}, backend={backend_url}, model={classifier.model_name}"
    )
    last_post_at = 0.0
    last_frame_at = 0.0
    last_error_at = 0.0

    while True:
        ok, frame = capture.read()
        if not ok:
            break

        now = time.time()
        snapshot = pipeline.process_frame(frame, timestamp=now)
        decision, features = predict_state(snapshot, frame, pipeline, classifier)

        display = frame.copy()
        draw_worker_overlay(display, decision, snapshot.output.metrics.get("fps", 0.0))

        if now - last_post_at >= args.post_interval:
            risk_labels = []
            if decision.label.endswith("abnormal"):
                risk_labels.append("bad_posture")
            if decision.label == "absent":
                risk_labels.append("absent")
            if decision.label == "ignore":
                risk_labels.append("ignore")

            payload = {
                "device_id": source_id,
                "timestamp": int(now),
                "provider": "smartled_yolo_state7",
                "pose_state": decision.label,
                "confidence": decision.confidence,
                "risk_labels": risk_labels,
                "keypoints": [],
                "raw": {
                    "mode": "state7",
                    "state_text": decision.text,
                    "presence_state": snapshot.output.presence_state,
                    "event_state": snapshot.output.event_state,
                    "raw_distance_level": snapshot.output.raw_distance_level,
                    "raw_posture_label": snapshot.output.raw_posture_label,
                    **json_ready(snapshot.output.metrics),
                    "model": decision.model_name,
                    "features": json_ready(features or {}),
                },
            }
            try:
                post_json(state_url, payload, pose_headers)
                last_post_at = now
            except (OSError, URLError) as exc:
                if now - last_error_at >= 5:
                    print("Vision state upload failed:", exc)
                    last_error_at = now

        if not args.no_frame_upload and now - last_frame_at >= args.frame_interval:
            try:
                post_frame(f"{frame_url}&timestamp={int(now)}", display, frame_headers)
                last_frame_at = now
            except (OSError, URLError) as exc:
                if now - last_error_at >= 5:
                    print("Frame upload failed:", exc)
                    last_error_at = now

        if args.preview:
            cv2.imshow("StudyPilot Vision Worker", display)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break

    capture.release()
    if args.preview:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
