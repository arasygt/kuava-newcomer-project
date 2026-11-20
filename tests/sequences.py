"""Builds per-frame state sequences with known answers for the lock-logic tests."""
from app.lock import LOST, TRACKED, UNTRACKED, Box, FrameState

ZONE = Box(100, 100, 200, 100)          # x 100..300, y 100..200
INSIDE = Box(150, 120, 40, 40)
OUTSIDE = Box(10, 10, 40, 40)
FPS = 25.0


def build(runs):
    """runs: list of (kind, length) with kind in I (inside), O (outside), L (lost), U (untracked)."""
    states, frame = [], 0
    for kind, length in runs:
        for _ in range(length):
            if kind == "I":
                states.append(FrameState(frame, TRACKED, INSIDE))
            elif kind == "O":
                states.append(FrameState(frame, TRACKED, OUTSIDE))
            elif kind == "L":
                states.append(FrameState(frame, LOST))
            else:
                states.append(FrameState(frame, UNTRACKED))
            frame += 1
    return states
