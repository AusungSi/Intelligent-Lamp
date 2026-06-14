from __future__ import annotations

from collections import Counter, deque


class LabelSmoother:
    def __init__(self, window_seconds: float) -> None:
        self.window_seconds = window_seconds
        self.buffer: deque[tuple[float, str]] = deque()

    def update(self, timestamp: float, label: str) -> str:
        self.buffer.append((timestamp, label))
        cutoff = timestamp - self.window_seconds
        while self.buffer and self.buffer[0][0] < cutoff:
            self.buffer.popleft()
        counts = Counter(item[1] for item in self.buffer)
        return counts.most_common(1)[0][0]
