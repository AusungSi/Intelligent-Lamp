from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Keypoint:
    x: float
    y: float
    conf: float


@dataclass(slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


@dataclass(slots=True)
class PoseDetection:
    bbox: BoundingBox
    keypoints: list[Keypoint]
    score: float


@dataclass(slots=True)
class ROI:
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h


@dataclass(slots=True)
class ReferenceFeatures:
    shoulder_width_px: float | None = None
    bbox_area_ratio: float | None = None
    head_shoulder_distance_ratio: float | None = None
    torso_angle_deg: float | None = None
    head_tilt_deg: float | None = None


@dataclass(slots=True)
class PoseFeatures:
    bbox_area_ratio: float = 0.0
    shoulder_width_px: float = 0.0
    nose_to_shoulder_center_y: float = 0.0
    head_shoulder_distance_ratio: float = 0.0
    neck_angle_deg: float = 0.0
    torso_tilt_deg: float = 0.0
    head_tilt_deg: float = 0.0
    kp_valid_ratio: float = 0.0
    roi_overlap: float = 0.0
    center_in_roi: bool = False
    shoulders_in_roi: bool = False
    pose_conf: float = 0.0


@dataclass(slots=True)
class PostureOutput:
    timestamp: float
    presence_state: str
    distance_level: str
    posture_label: str
    raw_distance_level: str
    raw_posture_label: str
    event_state: str
    metrics: dict[str, float]
    detection: PoseDetection | None = None
    features: PoseFeatures | None = None


@dataclass(slots=True)
class EventRecord:
    timestamp: float
    presence_state: str
    distance_level: str
    posture_label: str
    raw_distance_level: str
    raw_posture_label: str
    event_state: str
    metrics: dict[str, float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "presence_state": self.presence_state,
            "distance_level": self.distance_level,
            "posture_label": self.posture_label,
            "raw_distance_level": self.raw_distance_level,
            "raw_posture_label": self.raw_posture_label,
            "event_state": self.event_state,
            "metrics": dict(self.metrics),
        }


@dataclass(slots=True)
class PipelineSnapshot:
    output: PostureOutput
    events: list[EventRecord] = field(default_factory=list)
