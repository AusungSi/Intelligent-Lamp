from __future__ import annotations

from typing import Any

from .types import BoundingBox, Keypoint, PoseDetection


class UltralyticsPoseEngine:
    def __init__(self, model_name: str, imgsz: int, conf: float, iou: float, verbose: bool = False) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "Ultralytics is not installed. Run `python -m pip install -r requirements.txt` first."
            ) from exc
        self._model = YOLO(model_name)
        self._imgsz = imgsz
        self._conf = conf
        self._iou = iou
        self._verbose = verbose

    def infer(self, frame: Any) -> list[PoseDetection]:
        results = self._model.predict(
            source=frame,
            imgsz=self._imgsz,
            conf=self._conf,
            iou=self._iou,
            verbose=self._verbose,
        )
        if not results:
            return []
        result = results[0]
        boxes = result.boxes
        keypoints = result.keypoints
        if boxes is None or keypoints is None:
            return []

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        kxy = keypoints.xy.cpu().numpy()
        kconf = keypoints.conf.cpu().numpy()

        detections: list[PoseDetection] = []
        for box_xyxy, box_conf, pose_xy, pose_conf in zip(xyxy, confs, kxy, kconf):
            bbox = BoundingBox(
                x1=float(box_xyxy[0]),
                y1=float(box_xyxy[1]),
                x2=float(box_xyxy[2]),
                y2=float(box_xyxy[3]),
                conf=float(box_conf),
            )
            points = [Keypoint(x=float(x), y=float(y), conf=float(c)) for (x, y), c in zip(pose_xy, pose_conf)]
            detections.append(PoseDetection(bbox=bbox, keypoints=points, score=float(box_conf)))
        return detections
