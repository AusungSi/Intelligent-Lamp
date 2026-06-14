from __future__ import annotations

from dataclasses import dataclass

from .feature_extractor import extract_features
from .types import PoseDetection, ROI


@dataclass(slots=True)
class TargetSelectionState:
    last_target: PoseDetection | None = None
    last_seen_ts: float = 0.0


class TargetSelector:
    def __init__(self, roi: ROI | None, hold_last_seconds: float, kp_confidence: float) -> None:
        self.roi = roi
        self.hold_last_seconds = hold_last_seconds
        self.kp_confidence = kp_confidence
        self.state = TargetSelectionState()

    def select(
        self,
        detections: list[PoseDetection],
        frame_width: int,
        frame_height: int,
        timestamp: float,
    ) -> PoseDetection | None:
        if not detections:
            if self.state.last_target and (timestamp - self.state.last_seen_ts) <= self.hold_last_seconds:
                return self.state.last_target
            self.state.last_target = None
            return None

        scored: list[tuple[float, PoseDetection]] = []
        frame_area = float(max(1, frame_width * frame_height))
        for detection in detections:
            features = extract_features(detection, frame_width, frame_height, self.roi, self.kp_confidence)
            area_norm = detection.bbox.area / frame_area
            roi_bonus = (features.roi_overlap * 2.0) if self.roi is not None else 0.0
            score = roi_bonus + area_norm + detection.score
            scored.append((score, detection))

        scored.sort(key=lambda item: item[0], reverse=True)
        target = scored[0][1]
        self.state.last_target = target
        self.state.last_seen_ts = timestamp
        return target
