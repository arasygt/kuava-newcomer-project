"""Per-frame tracking data shared by the tracker and the API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

# Per-frame tracking status values
TRACKED = "tracked"      # tracker produced a valid box for this frame
LOST = "lost"            # tracking was lost on this frame (no box)
UNTRACKED = "untracked"  # frame not processed (before first selection / after loss)


@dataclass(frozen=True)
class Box:
    """Axis-aligned box in original video pixels. (x, y) is the top-left corner."""
    x: float
    y: float
    w: float
    h: float

    def __post_init__(self) -> None:
        if self.w <= 0 or self.h <= 0:
            raise ValueError("Box width and height must be positive")

    @property
    def area(self) -> float:
        return self.w * self.h

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


@dataclass(frozen=True)
class FrameState:
    frame: int
    status: str
    box: Optional[Box] = None
