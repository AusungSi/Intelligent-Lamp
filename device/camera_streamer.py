import select
import socket
import time

try:
    import _thread
except ImportError:
    _thread = None

import camera_service
from http_client import post_jpeg, post_json
from net_utils import ensure_wifi, wifi_connected


HTML_PAGE = """<html><head><title>ESP32-S3 Camera</title></head>
<body>
<h1>ESP32-S3 Camera Stream</h1>
<img src="/stream" style="width:100%;max-width:720px;">
</body></html>"""


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except AttributeError:
        time.sleep(ms / 1000)


def _build_response(status, content_type, body):
    if isinstance(body, str):
        body = body.encode()
    headers = [
        "HTTP/1.1 {}".format(status),
        "Content-Type: {}".format(content_type),
        "Connection: close",
        "Content-Length: {}".format(len(body)),
        "",
        "",
    ]
    return "\r\n".join(headers).encode() + body


def _serve_stream(conn, frame_interval_ms):
    conn.sendall(b"HTTP/1.1 200 OK\r\n")
    conn.sendall(b"Content-Type: multipart/x-mixed-replace; boundary=frame\r\n")
    conn.sendall(b"Cache-Control: no-cache\r\n")
    conn.sendall(b"Pragma: no-cache\r\n\r\n")

    while True:
        frame = camera_service.capture_frame()
        if not frame:
            _sleep_ms(frame_interval_ms)
            continue
        conn.sendall(b"--frame\r\n")
        conn.sendall(b"Content-Type: image/jpeg\r\n")
        conn.sendall("Content-Length: {}\r\n\r\n".format(len(frame)).encode())
        conn.sendall(frame)
        conn.sendall(b"\r\n")
        _sleep_ms(frame_interval_ms)


def run_local_stream_server(config):
    if not config.get("local_camera_stream_enabled", False):
        return

    port = int(config.get("local_camera_stream_port", 80))
    frame_interval_ms = int(config.get("local_camera_frame_interval_ms", 120))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    sock.listen(2)
    print("Local camera stream listening on port", port)

    while True:
        conn = None
        try:
            readable, _, _ = select.select([sock], [], [], 0.1)
            if not readable:
                continue

            conn, _ = sock.accept()
            request = conn.recv(1024).decode("utf-8", "ignore")
            if "GET /stream" in request:
                _serve_stream(conn, frame_interval_ms)
            else:
                conn.sendall(_build_response("200 OK", "text/html; charset=utf-8", HTML_PAGE))
        except Exception as exc:
            print("Local camera stream error:", exc)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


def _report_camera_failure(config):
    try:
        post_json(
            config,
            "/api/device/events",
            {
                "device_id": config["device_id"],
                "event_type": "camera_init_failed",
                "level": "error",
                "message": "Camera initialization failed",
                "timestamp": int(time.time()),
            },
        )
    except Exception:
        pass


def run(config):
    if not config.get("camera_enabled", True):
        print("Camera streamer disabled in config")
        return

    if not camera_service.init_camera(config):
        _report_camera_failure(config)
        return

    if config.get("local_camera_stream_enabled", False):
        if _thread:
            _thread.start_new_thread(run_local_stream_server, (config,))
        else:
            print("Warning: _thread unavailable, local camera stream disabled")

    frame_interval_ms = int(config.get("camera_frame_interval_ms", 300))
    while True:
        try:
            if not wifi_connected():
                ensure_wifi(config)

            frame = camera_service.capture_frame()
            if not frame:
                _sleep_ms(frame_interval_ms)
                continue

            timestamp = int(time.time())
            status, _ = post_jpeg(
                config,
                "/api/device/camera/frame?timestamp={}".format(timestamp),
                frame,
                {"X-Frame-Timestamp": str(timestamp)},
            )
            if status not in (200, 201, 204):
                print("Camera frame upload failed:", status)
            _sleep_ms(frame_interval_ms)
        except Exception as exc:
            print("Camera loop error:", exc)
            _sleep_ms(500)
