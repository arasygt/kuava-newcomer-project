"""OpenCV tracking of a user-selected target."""
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
# Frames wider than this are downscaled before tracking (boxes are scaled back)
TRACK_MAX_WIDTH = 640


@dataclass
class TrackRun:
    tracker: str
    start_frame: int
    states: list[FrameState] = field(default_factory=list)
    elapsed_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tracker": self.tracker,
            "start_frame": self.start_frame,
            "frames_processed": len(self.states),
            "elapsed_s": round(self.elapsed_s, 3),
        }


def validate_init_box(box: Box, width: int, height: int) -> None:
    if box.x < 0 or box.y < 0 or box.x + box.w > width or box.y + box.h > height:
        raise ValueError("The selected box must lie inside the video frame.")
    if box.w < 4 or box.h < 4:
        raise ValueError("The selected box is too small (minimum 4x4 pixels).")


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
    """Track from `start_frame` (where the target is `init_box`) to the end of the video."""
    tracker = tracker_factory() if tracker_factory else make_tracker(tracker_name)
    run = TrackRun(tracker=tracker_name, start_frame=start_frame)
    t0 = time.perf_counter()

    cap = open_at(path, start_frame)
    try:
        ok, frame = cap.read()
        if not ok:
            raise IndexError(f"Frame {start_frame} is beyond the end of the video")
        height, width = frame.shape[:2]
        validate_init_box(init_box, width, height)
        scale = min(1.0, max_width / width)

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

        index = start_frame
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            index += 1
            found, raw = tracker.update(prep(frame))
            if found and raw is not None:
                raw = tuple(v / scale for v in raw)
            if not found or raw is None or raw[2] <= 0 or raw[3] <= 0:
                run.states.append(FrameState(index, LOST, None))
                continue
            box = Box(round(raw[0], 1), round(raw[1], 1), round(raw[2], 1), round(raw[3], 1))
            run.states.append(FrameState(index, TRACKED, box))
    finally:
        cap.release()

    run.elapsed_s = time.perf_counter() - t0
    return run
