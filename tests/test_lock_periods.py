"""US-3: lock-zone logic tested with generated box sequences with known answers.

Expected values are built from the way each sequence is constructed (run lengths),
never from running the implementation.
"""
import random

import pytest

from app.lock import Box, is_inside, lock_periods
from tests.sequences import FPS, ZONE, build


def expected_periods(runs):
    """Known answer: every I-run is exactly one period (callers never put two I-runs side by side)."""
    out, frame = [], 0
    for kind, length in runs:
        if kind == "I":
            out.append((frame, frame + length - 1))
        frame += length
    return out


# ---------- is_inside: boundary triples (L, L - 1px, L + 1px) ----------
@pytest.mark.parametrize("box, inside", [
    (Box(100, 100, 200, 100), True),     # exactly equal to the zone -> inside (borders inclusive)
    (Box(101, 101, 198, 98), True),      # 1 px inside every edge
    (Box(99, 120, 40, 40), False),       # 1 px past the left edge
    (Box(261, 120, 40, 40), False),      # right edge at 301 -> 1 px past
    (Box(260, 120, 40, 40), True),       # right edge exactly at 300
    (Box(150, 99, 40, 40), False),       # 1 px past the top edge
    (Box(150, 161, 40, 40), False),      # bottom at 201 -> 1 px past
    (Box(150, 160, 40, 40), True),       # bottom exactly at 200
    (Box(150, 160, 40, 40.001), False),  # bottom 0.001 px past (float epsilon)
])
def test_box_inside_zone_boundaries(box, inside):
    assert is_inside(box, ZONE) is inside


def test_missing_box_is_never_inside():
    assert is_inside(None, ZONE) is False


def test_box_rejects_zero_or_negative_size():
    with pytest.raises(ValueError):
        Box(0, 0, 0, 10)
    with pytest.raises(ValueError):
        Box(0, 0, 10, -1)


# ---------- lock periods ----------
def test_single_period_frames_and_times():
    states = build([("O", 2), ("I", 3), ("O", 5)])
    [p] = lock_periods(states, ZONE, FPS)
    assert (p.start_frame, p.end_frame, p.frames) == (2, 4, 3)
    assert p.start_time == pytest.approx(2 / 25)
    assert p.end_time == pytest.approx(5 / 25)
    assert p.duration == pytest.approx(3 / 25)


def test_multiple_periods_are_reported_separately():
    runs = [("I", 4), ("O", 2), ("I", 10), ("O", 1), ("I", 1)]
    periods = lock_periods(build(runs), ZONE, FPS)
    assert [(p.start_frame, p.end_frame) for p in periods] == [(0, 3), (6, 15), (17, 17)]


def test_single_frame_lock_lasts_one_frame_period():
    [p] = lock_periods(build([("O", 3), ("I", 1), ("O", 3)]), ZONE, 30.0)
    assert p.duration == pytest.approx(1 / 30)


def test_lost_frame_breaks_a_lock_period():
    periods = lock_periods(build([("I", 5), ("L", 1), ("I", 5)]), ZONE, FPS)
    assert [(p.start_frame, p.end_frame) for p in periods] == [(0, 4), (6, 10)]


def test_untracked_frames_are_never_locked():
    assert lock_periods(build([("U", 10)]), ZONE, FPS) == []
    periods = lock_periods(build([("I", 3), ("U", 4), ("I", 2)]), ZONE, FPS)
    assert [(p.start_frame, p.end_frame) for p in periods] == [(0, 2), (7, 8)]


def test_whole_video_locked_is_one_period():
    [p] = lock_periods(build([("I", 750)]), ZONE, FPS)
    assert (p.start_frame, p.end_frame) == (0, 749)
    assert p.duration == pytest.approx(30.0)


def test_empty_sequence_has_no_periods():
    assert lock_periods([], ZONE, FPS) == []


@pytest.mark.parametrize("fps", [0, -25])
def test_non_positive_fps_is_rejected(fps):
    with pytest.raises(ValueError):
        lock_periods(build([("I", 3)]), ZONE, fps)


@pytest.mark.parametrize("seed", range(20))
def test_random_generated_sequences_match_known_answer(seed):
    rng = random.Random(seed)
    runs, prev = [], None
    for _ in range(rng.randint(1, 15)):
        kind = rng.choice([k for k in "IOLU" if k != prev] if prev == "I" else "IOLU")
        runs.append((kind, rng.randint(1, 40)))
        prev = kind
    # Merge adjacent non-I runs is unnecessary: they never create locks.
    periods = lock_periods(build(runs), ZONE, FPS)
    assert [(p.start_frame, p.end_frame) for p in periods] == expected_periods(runs)


def test_analyse_reports_periods_and_totals():
    from app.lock import analyse
    result = analyse(build([("I", 25), ("O", 25), ("I", 50)]), ZONE, FPS)
    assert [(p["start_frame"], p["end_frame"]) for p in result["periods"]] == [(0, 24), (50, 99)]
    assert result["total_locked_frames"] == 75
    assert result["total_locked_time"] == pytest.approx(3.0)
    assert result["zone"] == {"x": 100, "y": 100, "w": 200, "h": 100}
