from __future__ import annotations

import math

from .types import BoundingBox, Keypoint, ROI


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def point_in_roi(point: tuple[float, float], roi: ROI) -> bool:
    x, y = point
    return roi.x <= x <= roi.x2 and roi.y <= y <= roi.y2


def bbox_iou_with_roi(box: BoundingBox, roi: ROI) -> float:
    inter_x1 = max(box.x1, roi.x)
    inter_y1 = max(box.y1, roi.y)
    inter_x2 = min(box.x2, roi.x2)
    inter_y2 = min(box.y2, roi.y2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if box.area <= 0.0:
        return 0.0
    return inter_area / box.area


def distance(a: Keypoint, b: Keypoint) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def angle_from_vertical(dx: float, dy: float) -> float:
    if dx == 0.0 and dy == 0.0:
        return 0.0
    return math.degrees(math.atan2(dx, dy))


def angle_between(a: Keypoint, b: Keypoint) -> float:
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x))


def midpoint(a: Keypoint, b: Keypoint) -> Keypoint:
    return Keypoint(x=(a.x + b.x) / 2.0, y=(a.y + b.y) / 2.0, conf=min(a.conf, b.conf))


def angle_three_points(a: Keypoint, b: Keypoint, c: Keypoint) -> float:
    """Calculate angle at point b formed by points a-b-c in degrees."""
    ba_x, ba_y = a.x - b.x, a.y - b.y
    bc_x, bc_y = c.x - b.x, c.y - b.y

    dot = ba_x * bc_x + ba_y * bc_y
    cross = ba_x * bc_y - ba_y * bc_x

    angle = math.degrees(math.atan2(cross, dot))
    return abs(angle)
