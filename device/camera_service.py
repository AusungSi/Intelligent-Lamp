import time

try:
    import _thread
except ImportError:
    _thread = None

try:
    import camera
except ImportError:
    camera = None


CAM_PIN_PWDN = -1
CAM_PIN_RESET = -1
CAM_PIN_XCLK = 15
CAM_PIN_SIOD = 4
CAM_PIN_SIOC = 5

CAM_PIN_D7 = 16
CAM_PIN_D6 = 17
CAM_PIN_D5 = 18
CAM_PIN_D4 = 12
CAM_PIN_D3 = 10
CAM_PIN_D2 = 8
CAM_PIN_D1 = 9
CAM_PIN_D0 = 11

CAM_PIN_VSYNC = 6
CAM_PIN_HREF = 7
CAM_PIN_PCLK = 13

_camera_ready = False
_latest_frame = None
_latest_timestamp = 0
_lock = _thread.allocate_lock() if _thread else None


def _with_lock(callback):
    if _lock:
        _lock.acquire()
    try:
        return callback()
    finally:
        if _lock:
            _lock.release()


def _camera_framesize(config):
    if camera is None:
        return None

    size_name = str(config.get("camera_framesize", "QVGA")).upper()
    mapping = {
        "QVGA": getattr(camera, "FRAME_QVGA", getattr(camera, "FRAME_VGA", None)),
        "VGA": getattr(camera, "FRAME_VGA", None),
        "SVGA": getattr(camera, "FRAME_SVGA", getattr(camera, "FRAME_VGA", None)),
    }
    return mapping.get(size_name, mapping["QVGA"])


def init_camera(config):
    global _camera_ready

    if _camera_ready:
        return True

    if camera is None:
        print("camera module is missing")
        return False

    def _init():
        global _camera_ready
        try:
            try:
                camera.deinit()
            except Exception:
                pass

            camera.init(
                0,
                format=camera.JPEG,
                framesize=_camera_framesize(config),
                xclk_freq=camera.XCLK_20MHz,
                d0=CAM_PIN_D0,
                d1=CAM_PIN_D1,
                d2=CAM_PIN_D2,
                d3=CAM_PIN_D3,
                d4=CAM_PIN_D4,
                d5=CAM_PIN_D5,
                d6=CAM_PIN_D6,
                d7=CAM_PIN_D7,
                vsync=CAM_PIN_VSYNC,
                href=CAM_PIN_HREF,
                pclk=CAM_PIN_PCLK,
                xclk=CAM_PIN_XCLK,
                siod=CAM_PIN_SIOD,
                sioc=CAM_PIN_SIOC,
                reset=CAM_PIN_RESET,
                pwdn=CAM_PIN_PWDN,
            )

            try:
                sensor = camera.sensor
                sensor.set_vflip(sensor, int(config.get("camera_vflip", 1)))
                sensor.set_brightness(sensor, int(config.get("camera_brightness", 1)))
            except Exception:
                pass

            _camera_ready = True
            print("Camera initialized")
            return True
        except Exception as exc:
            _camera_ready = False
            print("Camera init failed:", exc)
            return False

    return _with_lock(_init)


def is_ready():
    return _camera_ready


def capture_frame():
    global _latest_frame, _latest_timestamp

    if not _camera_ready or camera is None:
        return None

    def _capture():
        global _latest_frame, _latest_timestamp
        frame = camera.capture()
        if frame:
            _latest_frame = frame
            _latest_timestamp = int(time.time())
        return frame

    return _with_lock(_capture)


def get_latest_frame():
    return _latest_frame, _latest_timestamp
