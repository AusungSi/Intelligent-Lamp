from __future__ import annotations

import json
from pathlib import Path

from .types import EventRecord, PostureOutput


class EventManager:
    def __init__(self) -> None:
        self._records: list[EventRecord] = []

    @property
    def records(self) -> list[EventRecord]:
        return list(self._records)

    def append(self, output: PostureOutput) -> None:
        self._records.append(
            EventRecord(
                timestamp=output.timestamp,
                presence_state=output.presence_state,
                distance_level=output.distance_level,
                posture_label=output.posture_label,
                raw_distance_level=output.raw_distance_level,
                raw_posture_label=output.raw_posture_label,
                event_state=output.event_state,
                metrics=output.metrics,
            )
        )

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.as_dict() for item in self._records]
        with target.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
