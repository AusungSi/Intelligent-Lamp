"""SmartLED posture detection package."""

from .config import load_config
from .pipeline import PosturePipeline

__all__ = ["PosturePipeline", "load_config"]
