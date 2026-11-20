"""Lock-zone logic: decides which frames are "locked" and groups them into periods.

Pure Python with no OpenCV dependency so it can be tested with generated box
sequences that have known answers (see tests/test_lock_periods.py).

Definitions (see docs/architecture/ARCHITECTURE.md, Entity: LockPeriod):
- A frame is LOCKED when tracking succeeded on it AND the whole target box lies
  inside the lock zone (edges touching the zone border count as inside).
- A lock period is a maximal run of consecutive locked frames.
- Duration of a period = number of frames / fps (a 1-frame lock lasts 1/fps s).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

# Per-frame tracking status values
TRACKED = "tracked"      # tracker produced a valid box for this frame
LOST = "lost"            # tracking was lost on this frame (no box)
UNTRACKED = "untracked"  # frame not processed (before first selection / after loss)

# Timeline segment states
LOCKED = "locked"
UNLOCKED = "unlocked"


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


# The lock zone is also a rectangle in video pixels.
Zone = Box


@dataclass(frozen=True)
class FrameState:
    frame: int
    status: str
    box: Optional[Box] = None


@dataclass(frozen=True)
class LockPeriod:
    start_frame: int  # first locked frame (inclusive)
    end_frame: int    # last locked frame (inclusive)
    fps: float

    @property
    def frames(self) -> int:
        return self.end_frame - self.start_frame + 1

    @property
    def start_time(self) -> float:
        return self.start_frame / self.fps

    @property
    def end_time(self) -> float:
        # End of the last locked frame's display interval
        return (self.end_frame + 1) / self.fps

    @property
    def duration(self) -> float:
        return self.frames / self.fps

    def to_dict(self) -> dict:
        return {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "frames": self.frames,
            "start_time": round(self.start_time, 4),
            "end_time": round(self.end_time, 4),
            "duration": round(self.duration, 4),
        }


def is_inside(box: Optional[Box], zone: Zone) -> bool:
    """True when the whole box lies inside the zone (borders inclusive)."""
    if box is None:
        return False
    return (
        box.x >= zone.x
        and box.y >= zone.y
        and box.x + box.w <= zone.x + zone.w
        and box.y + box.h <= zone.y + zone.h
    )


def frame_state(state: FrameState, zone: Zone) -> str:
    if state.status == TRACKED:
        return LOCKED if is_inside(state.box, zone) else UNLOCKED
    return state.status  # LOST or UNTRACKED


def lock_periods(states: Sequence[FrameState], zone: Zone, fps: float) -> list[LockPeriod]:
    if fps <= 0:
        raise ValueError("fps must be positive")
    periods: list[LockPeriod] = []
    start: Optional[int] = None
    prev_frame: Optional[int] = None
    for s in states:
        locked = frame_state(s, zone) == LOCKED
        if locked and start is not None and prev_frame == s.frame - 1:
            prev_frame = s.frame
            continue
        if start is not None:
            periods.append(LockPeriod(start, prev_frame, fps))
            start = None
        if locked:
            start = prev_frame = s.frame
    if start is not None:
        periods.append(LockPeriod(start, prev_frame, fps))
    return periods


def analyse(states: Sequence[FrameState], zone: Zone, fps: float) -> dict:
    periods = lock_periods(states, zone, fps)
    locked_frames = sum(p.frames for p in periods)
    return {
        "zone": zone.to_dict(),
        "periods": [p.to_dict() for p in periods],
        "total_locked_frames": locked_frames,
        "total_locked_time": round(locked_frames / fps, 4),
    }
