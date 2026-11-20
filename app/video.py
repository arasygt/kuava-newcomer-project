"""Video validation, metadata probing and exact frame access."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np

# FourCC codes OpenCV/FFmpeg reports for H.264 streams in an MP4 container
H264_FOURCCS = {"avc1", "avc3", "h264", "x264"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024


class VideoValidationError(ValueError):
    """Raised with a user-facing message when an uploaded file is not usable."""


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    frame_count: int
    duration: float
    codec: str

    def to_dict(self) -> dict:
        return asdict(self)


def _fourcc_to_str(value: float) -> str:
    code = int(value)
    return "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4)).strip("\x00 ")


def check_extension(filename: str | None) -> None:
    if not filename or not filename.lower().endswith(".mp4"):
        raise VideoValidationError("Only .mp4 files are supported. Please upload an MP4 (H.264) video.")


def probe(path: str | Path) -> VideoInfo:
    """Validate that `path` is a decodable H.264 MP4 and return its metadata."""
    path = Path(path)
    size = path.stat().st_size if path.exists() else 0
    if size == 0:
        raise VideoValidationError("The uploaded file is empty.")

    # Every MP4 starts with a box whose type at bytes 4..8 is 'ftyp'
    with path.open("rb") as f:
        header = f.read(12)
    if len(header) < 8 or header[4:8] != b"ftyp":
        raise VideoValidationError("The file is not a valid MP4 container.")

    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise VideoValidationError("The video could not be opened or decoded.")
        codec = _fourcc_to_str(cap.get(cv2.CAP_PROP_FOURCC))
        if codec.lower() not in H264_FOURCCS:
            raise VideoValidationError(
                f"Unsupported video codec '{codec or 'unknown'}'. Only H.264 MP4 videos are supported."
            )
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ok, _ = cap.read()
        if not ok or fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
            raise VideoValidationError("The video has no readable frames.")
    finally:
        cap.release()

    return VideoInfo(width, height, round(fps, 4), frame_count, round(frame_count / fps, 4), codec)


def open_at(path: str | Path, index: int) -> cv2.VideoCapture:
    """Open the video positioned so the next read() returns frame `index`.

    Frames are skipped with grab() instead of CAP_PROP_POS_FRAMES because
    seeking in H.264 is not guaranteed to be frame-exact.
    """
    if index < 0:
        raise IndexError("Frame index must be >= 0")
    cap = cv2.VideoCapture(str(path))
    for _ in range(index):
        if not cap.grab():
            cap.release()
            raise IndexError(f"Frame {index} is beyond the end of the video")
    return cap


def read_frame(path: str | Path, index: int) -> np.ndarray:
    cap = open_at(path, index)
    try:
        ok, frame = cap.read()
    finally:
        cap.release()
    if not ok:
        raise IndexError(f"Frame {index} is beyond the end of the video")
    return frame
