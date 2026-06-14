from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_reference(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def merge_reference(config: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(config)
    if reference:
        merged.setdefault("reference", {})
        merged["reference"].update(reference)
    return merged
