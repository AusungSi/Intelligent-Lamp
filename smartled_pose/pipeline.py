from __future__ import annotations

import time

from .event_manager import EventManager
from .feature_extractor import extract_features
from .inference import UltralyticsPoseEngine
from .rules import RuleEngine
from .target_selector import TargetSelector
from .temporal import LabelSmoother
from .types import PipelineSnapshot, PoseFeatures, PostureOutput, ReferenceFeatures, ROI


class PosturePipeline:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.use_roi = config.get("selection", {}).get("use_roi", True)
        self.roi = self._build_roi(config["roi"], config["camera"]) if self.use_roi else None
        self.reference = ReferenceFeatures(
            shoulder_width_px=config.get("reference", {}).get("shoulder_width_px"),
            bbox_area_ratio=config.get("reference", {}).get("bbox_area_ratio"),
            head_shoulder_distance_ratio=config.get("reference", {}).get("head_shoulder_distance_ratio"),
            torso_angle_deg=config.get("reference", {}).get("torso_angle_deg"),
            head_tilt_deg=config.get("reference", {}).get("head_tilt_deg"),
        )
        inference_cfg = config["inference"]
        self.engine = UltralyticsPoseEngine(
            model_name=inference_cfg["model"],
            imgsz=inference_cfg["imgsz"],
            conf=inference_cfg["conf"],
            iou=inference_cfg["iou"],
            verbose=inference_cfg.get("verbose", False),
        )
        selection_cfg = config["selection"]
        self.target_selector = TargetSelector(
            roi=self.roi,
            hold_last_seconds=selection_cfg["hold_last_seconds"],
            kp_confidence=selection_cfg["kp_confidence"],
        )
        self.rule_engine = RuleEngine(config=config, reference=self.reference)
        self.label_smoother = LabelSmoother(window_seconds=config["rules"]["label_window_seconds"])
        self.event_manager = EventManager()
        self._last_frame_time = None

    @staticmethod
    def _build_roi(roi_cfg: dict, camera_cfg: dict) -> ROI:
        return ROI(
            x=roi_cfg["x"] * camera_cfg["width"],
            y=roi_cfg["y"] * camera_cfg["height"],
            w=roi_cfg["w"] * camera_cfg["width"],
            h=roi_cfg["h"] * camera_cfg["height"],
        )

    def process_frame(self, frame, timestamp: float | None = None) -> PipelineSnapshot:
        ts = timestamp if timestamp is not None else time.time()
        frame_height, frame_width = frame.shape[:2]
        if self.use_roi and (frame_width, frame_height) != (self.config["camera"]["width"], self.config["camera"]["height"]):
            self.roi = self._build_roi(
                self.config["roi"],
                {"width": frame_width, "height": frame_height},
            )

        detections = self.engine.infer(frame)
        target = self.target_selector.select(detections, frame_width, frame_height, ts)
        features: PoseFeatures | None = None
        if target is not None:
            features = extract_features(
                target,
                frame_width=frame_width,
                frame_height=frame_height,
                roi=self.roi,
                kp_confidence=self.config["selection"]["kp_confidence"],
            )

        presence, distance, raw_posture, event_state = self.rule_engine.evaluate(
            timestamp=ts,
            features=features,
            detection_found=target is not None,
        )
        posture = self.label_smoother.update(ts, raw_posture)

        fps = 0.0
        if self._last_frame_time is not None and ts > self._last_frame_time:
            fps = 1.0 / (ts - self._last_frame_time)
        self._last_frame_time = ts

        metrics = {
            "fps": fps,
            "pose_conf": features.pose_conf if features else 0.0,
            "bbox_area_ratio": features.bbox_area_ratio if features else 0.0,
            "head_tilt_deg": features.head_tilt_deg if features else 0.0,
            "torso_tilt_deg": features.torso_tilt_deg if features else 0.0,
            "kp_valid_ratio": features.kp_valid_ratio if features else 0.0,
            "roi_overlap": features.roi_overlap if features else 0.0,
        }

        output = PostureOutput(
            timestamp=ts,
            presence_state=presence,
            distance_level=distance,
            posture_label=posture,
            raw_distance_level=distance,
            raw_posture_label=raw_posture,
            event_state=event_state,
            metrics=metrics,
            detection=target,
            features=features,
        )
        self.event_manager.append(output)
        return PipelineSnapshot(output=output, events=self.event_manager.records)
