"""US-4: timeline segments and longest lock, tested with generated sequences with known answers."""
import pytest

from app.lock import analyse, lock_periods, longest_period, timeline
from tests.sequences import FPS, ZONE, build


def test_longest_period_is_selected():
    periods = lock_periods(build([("I", 3), ("O", 1), ("I", 9), ("O", 1), ("I", 4)]), ZONE, FPS)
    longest = longest_period(periods)
    assert (longest.start_frame, longest.end_frame) == (4, 12)
    assert longest.duration == pytest.approx(9 / 25)


@pytest.mark.parametrize("second_len, expected_start", [
    (4, 2),   # second period 1 frame shorter -> first wins
    (5, 2),   # equal length -> tie goes to the earliest
    (6, 8),   # second period 1 frame longer -> second wins
])
def test_longest_boundaries(second_len, expected_start):
    periods = lock_periods(build([("O", 2), ("I", 5), ("O", 1), ("I", second_len)]), ZONE, FPS)
    assert longest_period(periods).start_frame == expected_start


def test_no_lock_means_no_longest():
    assert longest_period([]) is None
    result = analyse(build([("O", 10)]), ZONE, FPS)
    assert result["longest"] is None
    assert result["periods"] == []


def test_timeline_segments_cover_every_frame_in_order():
    states = build([("U", 2), ("O", 3), ("I", 4), ("L", 1), ("U", 2)])
    segs = timeline(states, ZONE)
    assert [(s.state, s.start_frame, s.end_frame) for s in segs] == [
        ("untracked", 0, 1), ("unlocked", 2, 4), ("locked", 5, 8), ("lost", 9, 9), ("untracked", 10, 11),
    ]


def test_empty_sequence_has_empty_timeline():
    assert timeline([], ZONE) == []


def test_analyse_reports_longest_and_timeline_times():
    result = analyse(build([("I", 25), ("O", 25), ("I", 50)]), ZONE, FPS)
    assert result["longest"]["start_frame"] == 50
    assert result["longest"]["duration"] == pytest.approx(2.0)
    assert result["timeline"][1] == {"state": "unlocked", "start_frame": 25, "end_frame": 49,
                                     "start_time": 1.0, "end_time": 2.0}
