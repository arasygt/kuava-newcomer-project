"""OpenCV tracking with lost-track detection."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import cv2

from .lock import LOST, TRACKED, Box, FrameState
from .video import open_at

TRACKERS: dict[str, Callable[[], object]] = {
    "CSRT": cv2.TrackerCSRT_create,
    "KCF": cv2.TrackerKCF_create,
    "MIL": cv2.TrackerMIL_create,
}
# KCF is the default because it meets the 30 s / 720p < 60 s budget on a laptop CPU;
# CSRT is more accurate and handles scale but is ~10x slower (see ARCHITECTURE.md).
DEFAULT_TRACKER = "KCF"

# Tracking is lost when the box area changes by MORE than this fraction between two frames
AREA_CHANGE_LIMIT = 0.5
# Frames wider than this are downscaled before tracking (boxes are scaled back)
TRACK_MAX_WIDTH = 640
# Downscaling never shrinks the target box below this many pixels (IQ-9)
MIN_TRACKED_PX = 8
# MIL never returns on boxes of ~4 px or less, so it needs a larger selection (IQ-9)
MIL_MIN_BOX = 8

REASON_FAILURE = "tracker_failure"
REASON_AREA = "area_change"


def area_change_exceeded(prev: Box, cur: Box, limit: float = AREA_CHANGE_LIMIT) -> bool:
    """|A_cur - A_prev| / A_prev > limit. Exactly 50% is still accepted."""
    return abs(cur.area - prev.area) / prev.area > limit


def detect_loss(ok: bool, raw_box, prev: Box) -> tuple[Optional[str], Optional[Box]]:
    """Return (reason, box). reason is None when tracking is still valid."""
    if not ok or raw_box is None:
        return REASON_FAILURE, None
    x, y, w, h = (float(v) for v in raw_box)
    if w <= 0 or h <= 0:
        return REASON_FAILURE, None
    box = Box(x, y, w, h)
    if area_change_exceeded(prev, box):
        return REASON_AREA, None
    return None, box


@dataclass
class TrackRun:
    tracker: str
    start_frame: int
    states: list[FrameState] = field(default_factory=list)
    lost_frame: Optional[int] = None
    lost_reason: Optional[str] = None
    elapsed_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tracker": self.tracker,
            "start_frame": self.start_frame,
            "frames_processed": len(self.states),
            "lost_frame": self.lost_frame,
            "lost_reason": self.lost_reason,
            "elapsed_s": round(self.elapsed_s, 3),
        }


def validate_init_box(box: Box, width: int, height: int, tracker_name: str = DEFAULT_TRACKER) -> None:
    if box.x < 0 or box.y < 0 or box.x + box.w > width or box.y + box.h > height:
        raise ValueError("The selected box must lie inside the video frame.")
    if box.w < 4 or box.h < 4:
        raise ValueError("The selected box is too small (minimum 4x4 pixels).")
    if tracker_name == "MIL" and (box.w < MIL_MIN_BOX or box.h < MIL_MIN_BOX):
        raise ValueError(
            f"The MIL tracker needs a box of at least {MIL_MIN_BOX}x{MIL_MIN_BOX} pixels. "
            "Draw a larger box or choose KCF or CSRT."
        )


def tracking_scale(frame_width: int, box: Box, max_width: int = TRACK_MAX_WIDTH) -> float:
    """Downscale factor for tracking: fit max_width, but keep the box >= MIN_TRACKED_PX."""
    scale = min(1.0, max_width / frame_width)
    keep_box = MIN_TRACKED_PX / min(box.w, box.h)
    return min(1.0, max(scale, keep_box))


def make_tracker(name: str):
    if name not in TRACKERS:
        raise ValueError(f"Unknown tracker '{name}'. Choose one of: {', '.join(TRACKERS)}.")
    return TRACKERS[name]()


def track_video(
    path: str | Path,
    start_frame: int,
    init_box: Box,
    tracker_name: str = DEFAULT_TRACKER,
    max_width: int = TRACK_MAX_WIDTH,
    tracker_factory: Optional[Callable[[], object]] = None,
) -> TrackRun:
    """Track from `start_frame` (where the target is `init_box`) until the end or a loss.

    The loss frame is recorded with status LOST and processing stops there so the
    user can re-select the target on exactly that frame.
    """
    tracker = tracker_factory() if tracker_factory else make_tracker(tracker_name)
    run = TrackRun(tracker=tracker_name, start_frame=start_frame)
    t0 = time.perf_counter()

    cap = open_at(path, start_frame)
    try:
        ok, frame = cap.read()
        if not ok:
            raise IndexError(f"Frame {start_frame} is beyond the end of the video")
        height, width = frame.shape[:2]
        validate_init_box(init_box, width, height, tracker_name)
        scale = tracking_scale(width, init_box, max_width)

        def prep(img):
            return img if scale == 1.0 else cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        scaled = (
            int(round(init_box.x * scale)),
            int(round(init_box.y * scale)),
            max(1, int(round(init_box.w * scale))),
            max(1, int(round(init_box.h * scale))),
        )
        tracker.init(prep(frame), scaled)
        run.states.append(FrameState(start_frame, TRACKED, init_box))
        prev = init_box

        index = start_frame
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            index += 1
            found, raw = tracker.update(prep(frame))
            if found and raw is not None:
                raw = tuple(v / scale for v in raw)
            reason, box = detect_loss(found, raw, prev)
            if reason:
                run.states.append(FrameState(index, LOST, None))
                run.lost_frame, run.lost_reason = index, reason
                break
            box = Box(round(box.x, 1), round(box.y, 1), round(box.w, 1), round(box.h, 1))
            run.states.append(FrameState(index, TRACKED, box))
            prev = box
    finally:
        cap.release()

    run.elapsed_s = time.perf_counter() - t0
    return run
