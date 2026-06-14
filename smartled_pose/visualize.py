from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .types import PostureOutput, ROI


PRESENCE_TEXT = {
    "absent": "未在位",
    "seated_candidate": "候选在位",
    "seated": "已在位",
}

DISTANCE_TEXT = {
    "normal": "正常",
    "near": "偏近",
    "too_close": "过近",
}

POSTURE_TEXT = {
    "normal": "正常",
    "head_down": "低头/过近",
    "leaning_left": "左歪",
    "leaning_right": "右歪",
}

EVENT_TEXT = {
    "none": "未触发",
    "warning_active": "已告警",
    "cooldown": "冷却中",
}


def _cn(mapping: dict[str, str], key: str) -> str:
    return mapping.get(key, key)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
    ]
    for candidate in font_candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _draw_chinese_lines(
    frame: Any,
    lines: list[str],
    start_x: int = 20,
    start_y: int = 18,
    line_gap: int = 28,
    fill: tuple[int, int, int] = (255, 255, 255),
) -> Any:
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    font = _load_font(24)
    for idx, text in enumerate(lines):
        draw.text((start_x, start_y + idx * line_gap), text, font=font, fill=fill)
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def draw_output(frame: Any, output: PostureOutput, roi: ROI | None, show_overlay: bool = True) -> Any:
    h, w = frame.shape[:2]

    if output.detection:
        box = output.detection.bbox
        color = (0, 200, 0) if output.event_state != "warning_active" else (0, 0, 255)
        cv2.rectangle(frame, (int(box.x1), int(box.y1)), (int(box.x2), int(box.y2)), color, 2)
        for kp in output.detection.keypoints:
            if kp.conf >= 0.3:
                cv2.circle(frame, (int(kp.x), int(kp.y)), 3, (255, 255, 0), -1)

    if show_overlay:
        overlay_lines = [
            f"在位状态: {_cn(PRESENCE_TEXT, output.presence_state)}",
            f"实时距离: {_cn(DISTANCE_TEXT, output.raw_distance_level)}",
            f"实时姿态: {_cn(POSTURE_TEXT, output.raw_posture_label)}",
            f"规则告警距离: {_cn(DISTANCE_TEXT, output.distance_level)}",
            f"规则告警姿态: {_cn(POSTURE_TEXT, output.posture_label)}",
            f"规则告警状态: {_cn(EVENT_TEXT, output.event_state)}",
            f"帧率: {output.metrics.get('fps', 0.0):.1f}",
            f"检测置信度: {output.metrics.get('pose_conf', 0.0):.2f}",
            f"人体框占比: {output.metrics.get('bbox_area_ratio', 0.0):.3f}",
            f"躯干倾角: {output.metrics.get('torso_tilt_deg', 0.0):.1f}",
            f"头部倾角: {output.metrics.get('head_tilt_deg', 0.0):.1f}",
        ]
        frame = _draw_chinese_lines(frame, overlay_lines)

    cv2.putText(frame, f"{w}x{h}", (w - 120, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return frame
