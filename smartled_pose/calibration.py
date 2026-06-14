from __future__ import annotations

import json
from pathlib import Path

from .types import PoseFeatures, ReferenceFeatures


class ReferenceCalibrator:
    def __init__(self) -> None:
        self.shoulder_width_samples: list[float] = []
        self.bbox_area_samples: list[float] = []
        self.head_shoulder_distance_ratio_samples: list[float] = []
        self.torso_angle_samples: list[float] = []
        self.head_tilt_samples: list[float] = []

    def add(self, features: PoseFeatures) -> None:
        if features.shoulder_width_px > 0:
            self.shoulder_width_samples.append(features.shoulder_width_px)
        if features.bbox_area_ratio > 0:
            self.bbox_area_samples.append(features.bbox_area_ratio)
        if features.head_shoulder_distance_ratio > 0:
            self.head_shoulder_distance_ratio_samples.append(features.head_shoulder_distance_ratio)
        if features.torso_tilt_deg != 0.0:
            self.torso_angle_samples.append(features.torso_tilt_deg)
        if features.head_tilt_deg != 0.0:
            self.head_tilt_samples.append(features.head_tilt_deg)

    def build(self) -> ReferenceFeatures:
        shoulder = (
            sum(self.shoulder_width_samples) / len(self.shoulder_width_samples) if self.shoulder_width_samples else None
        )
        bbox = sum(self.bbox_area_samples) / len(self.bbox_area_samples) if self.bbox_area_samples else None
        head_shoulder_ratio = (
            sum(self.head_shoulder_distance_ratio_samples) / len(self.head_shoulder_distance_ratio_samples)
            if self.head_shoulder_distance_ratio_samples
            else None
        )
        torso_angle = (
            sum(self.torso_angle_samples) / len(self.torso_angle_samples) if self.torso_angle_samples else None
        )
        head_tilt = sum(self.head_tilt_samples) / len(self.head_tilt_samples) if self.head_tilt_samples else None
        return ReferenceFeatures(
            shoulder_width_px=shoulder,
            bbox_area_ratio=bbox,
            head_shoulder_distance_ratio=head_shoulder_ratio,
            torso_angle_deg=torso_angle,
            head_tilt_deg=head_tilt,
        )

    def save(self, path: str | Path) -> ReferenceFeatures:
        reference = self.build()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as fh:
            json.dump(
                {
                    "shoulder_width_px": reference.shoulder_width_px,
                    "bbox_area_ratio": reference.bbox_area_ratio,
                    "head_shoulder_distance_ratio": reference.head_shoulder_distance_ratio,
                    "torso_angle_deg": reference.torso_angle_deg,
                    "head_tilt_deg": reference.head_tilt_deg,
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )
        return reference
