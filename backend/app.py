from flask import Flask, send_from_directory

from backend.config import Config
from backend.routes.camera_api import camera_api
from backend.routes.device_api import device_api
from backend.routes.lamp_api import lamp_api
from backend.routes.pose_api import pose_api
from backend.routes.status_api import status_api
from backend.routes.summary_api import summary_api
from backend.services.db import init_db


def create_app():
    app = Flask(
        __name__,
        static_folder=Config.FRONTEND_DIR,
        static_url_path="",
    )
    app.config.from_object(Config)

    init_db()

    app.register_blueprint(device_api, url_prefix="/api/device")
    app.register_blueprint(status_api, url_prefix="/api/status")
    app.register_blueprint(summary_api, url_prefix="/api/summaries")
    app.register_blueprint(camera_api, url_prefix="/api/camera")
    app.register_blueprint(lamp_api, url_prefix="/api/lamp")
    app.register_blueprint(pose_api, url_prefix="/api/pose")

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
