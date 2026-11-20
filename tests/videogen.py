"""Generates small synthetic MP4 videos with a known ground-truth target path.

Videos are created at test time in a temp folder, so no video is committed.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np


def _background(width: int, height: int, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.integers(0, 255, (height // 8 + 1, width // 8 + 1), dtype=np.uint8)
    bg = cv2.resize(noise, (width, height), interpolation=cv2.INTER_CUBIC)
    bg = cv2.GaussianBlur(bg, (0, 0), 3)
    bg = (bg * 0.35 + 40).astype(np.uint8)
    return cv2.cvtColor(bg, cv2.COLOR_GRAY2BGR)


def _target(size: int) -> np.ndarray:
    """Checkerboard patch with a red border: easy, high-contrast texture to track."""
    cells = 4
    tile = np.indices((cells, cells)).sum(axis=0) % 2
    patch = cv2.resize((tile * 255).astype(np.uint8), (size, size), interpolation=cv2.INTER_NEAREST)
    patch = cv2.cvtColor(patch, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(patch, (0, 0), (size - 1, size - 1), (0, 0, 255), max(2, size // 12))
    return patch


def linear_path(n_frames: int, width: int, height: int, size: int,
                x0: float = 0.05, x1: float = 0.85) -> list[tuple[int, int, int, int]]:
    """Target moves left to right along the vertical centre line."""
    y = (height - size) // 2
    xs = np.linspace(x0 * width, x1 * width - size, n_frames)
    return [(int(round(x)), y, size, size) for x in xs]


def write_video(path: Path, boxes: list, width: int = 320, height: int = 240, fps: int = 25,
                size: int = 40, codec: str = "libx264", visible: list | None = None) -> Path:
    """Write a video where frame i shows the target at boxes[i] (if visible[i])."""
    bg = _background(width, height)
    patch = _target(size)
    writer = imageio_ffmpeg.write_frames(
        str(path), (width, height), fps=fps, codec=codec, pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p", macro_block_size=1, quality=8,
        output_params=["-g", str(fps)], ffmpeg_log_level="error",
    )
    writer.send(None)
    for i, (x, y, w, h) in enumerate(boxes):
        frame = bg.copy()
        if visible is None or visible[i]:
            frame[y:y + h, x:x + w] = patch
        writer.send(np.ascontiguousarray(frame[:, :, ::-1]))
    writer.close()
    return path


def moving_target_video(path: Path, n_frames: int = 75, width: int = 320, height: int = 240,
                        fps: int = 25, size: int = 40, codec: str = "libx264"):
    boxes = linear_path(n_frames, width, height, size)
    write_video(path, boxes, width, height, fps, size, codec)
    return path, boxes


def vanishing_target_video(path: Path, n_frames: int = 75, hidden: range = range(30, 40),
                           width: int = 320, height: int = 240, fps: int = 25, size: int = 40):
    """Target disappears for the frames in `hidden`, then reappears on its path."""
    boxes = linear_path(n_frames, width, height, size)
    visible = [i not in hidden for i in range(n_frames)]
    write_video(path, boxes, width, height, fps, size, visible=visible)
    return path, boxes
