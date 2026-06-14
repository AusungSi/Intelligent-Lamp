from __future__ import annotations

from .geometry import angle_between, angle_from_vertical, angle_three_points, bbox_iou_with_roi, distance, midpoint, point_in_roi
from .types import Keypoint, PoseDetection, PoseFeatures, ROI


NOSE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_HIP = 11
RIGHT_HIP = 12


def _valid(kp: Keypoint | None, min_conf: float) -> bool:
    return kp is not None and kp.conf >= min_conf


def _safe_get(keypoints: list[Keypoint], index: int) -> Keypoint | None:
    if 0 <= index < len(keypoints):
        return keypoints[index]
    return None


def extract_features(
    detection: PoseDetection,
    frame_width: int,
    frame_height: int,
    roi: ROI | None,
    kp_confidence: float,
) -> PoseFeatures:
    keypoints = detection.keypoints
    valid_count = sum(1 for kp in keypoints if kp.conf >= kp_confidence)
    bbox_area_ratio = detection.bbox.area / float(max(1, frame_width * frame_height))
    roi_overlap = bbox_iou_with_roi(detection.bbox, roi) if roi else 1.0
    center_in_roi = point_in_roi(detection.bbox.center, roi) if roi else True

    left_shoulder = _safe_get(keypoints, LEFT_SHOULDER)
    right_shoulder = _safe_get(keypoints, RIGHT_SHOULDER)
    left_hip = _safe_get(keypoints, LEFT_HIP)
    right_hip = _safe_get(keypoints, RIGHT_HIP)
    nose = _safe_get(keypoints, NOSE)
    left_eye = _safe_get(keypoints, LEFT_EYE)
    right_eye = _safe_get(keypoints, RIGHT_EYE)
    left_ear = _safe_get(keypoints, LEFT_EAR)
    right_ear = _safe_get(keypoints, RIGHT_EAR)

    shoulder_width = 0.0
    shoulder_center = None
    shoulders_in_roi = True if roi is None else False
    if _valid(left_shoulder, kp_confidence) and _valid(right_shoulder, kp_confidence):
        shoulder_width = distance(left_shoulder, right_shoulder)
        shoulder_center = midpoint(left_shoulder, right_shoulder)
        if roi is not None:
            shoulders_in_roi = point_in_roi((left_shoulder.x, left_shoulder.y), roi) and point_in_roi(
                (right_shoulder.x, right_shoulder.y), roi
            )

    torso_tilt_deg = 0.0
    if shoulder_center and _valid(left_hip, kp_confidence) and _valid(right_hip, kp_confidence):
        hip_center = midpoint(left_hip, right_hip)
        torso_tilt_deg = angle_from_vertical(hip_center.x - shoulder_center.x, hip_center.y - shoulder_center.y)

    head_tilt_deg = 0.0
    if _valid(left_eye, kp_confidence) and _valid(right_eye, kp_confidence):
        head_tilt_deg = angle_between(left_eye, right_eye)
    elif _valid(left_ear, kp_confidence) and _valid(right_ear, kp_confidence):
        head_tilt_deg = angle_between(left_ear, right_ear)

    nose_to_shoulder_center_y = 0.0
    head_shoulder_distance_ratio = 0.0
    if shoulder_center and _valid(nose, kp_confidence):
        nose_to_shoulder_center_y = max(0.0, nose.y - shoulder_center.y)
        if shoulder_width > 0:
            head_distance = distance(nose, shoulder_center)
            head_shoulder_distance_ratio = head_distance / shoulder_width

    neck_angle_deg = 0.0
    if shoulder_center and _valid(nose, kp_confidence) and _valid(left_hip, kp_confidence) and _valid(right_hip, kp_confidence):
        hip_center = midpoint(left_hip, right_hip)
        neck_angle_deg = angle_three_points(nose, shoulder_center, hip_center)

    return PoseFeatures(
        bbox_area_ratio=bbox_area_ratio,
        shoulder_width_px=shoulder_width,
        nose_to_shoulder_center_y=nose_to_shoulder_center_y,
        head_shoulder_distance_ratio=head_shoulder_distance_ratio,
        neck_angle_deg=neck_angle_deg,
        torso_tilt_deg=torso_tilt_deg,
        head_tilt_deg=head_tilt_deg,
        kp_valid_ratio=valid_count / float(max(1, len(keypoints))),
        roi_overlap=roi_overlap,
        center_in_roi=center_in_roi,
        shoulders_in_roi=shoulders_in_roi,
        pose_conf=detection.score,
    )
