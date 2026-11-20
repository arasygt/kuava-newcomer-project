"""US-5: tracking is lost on tracker failure or a >50% box-area change between two frames."""
import pytest

from app.lock import LOST, TRACKED, Box
from app.tracking import (REASON_AREA, REASON_FAILURE, area_change_exceeded, detect_loss,
                          track_video)
from tests.videogen import vanishing_target_video


class ScriptedTracker:
    """Stands in for the OpenCV tracker (an external library boundary) with fixed outputs."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.init_args = None

    def init(self, frame, box):
        self.init_args = box

    def update(self, frame):
        # The last scripted output repeats for the rest of the video
        return self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]


@pytest.mark.parametrize("cur_area, lost", [
    (150.0, False),     # exactly +50% -> still tracked
    (150.01, True),     # just above +50%
    (149.99, False),
    (50.0, False),      # exactly -50%
    (49.99, True),      # just below -50%
    (100.0, False),     # unchanged
])
def test_area_change_limit_boundaries(cur_area, lost):
    prev = Box(0, 0, 10, 10)               # area 100
    cur = Box(0, 0, cur_area / 10, 10)
    assert area_change_exceeded(prev, cur) is lost


def test_tracker_failure_flag_means_lost():
    assert detect_loss(False, (1, 1, 10, 10), Box(1, 1, 10, 10)) == (REASON_FAILURE, None)


@pytest.mark.parametrize("raw", [(5, 5, 0, 10), (5, 5, 10, 0), (5, 5, -3, 10), None])
def test_degenerate_box_means_lost(raw):
    assert detect_loss(True, raw, Box(1, 1, 10, 10))[0] == REASON_FAILURE


def test_valid_update_is_not_lost():
    reason, box = detect_loss(True, (2, 3, 11, 10), Box(1, 1, 10, 10))  # +10% area
    assert reason is None and box == Box(2, 3, 11, 10)


def test_run_stops_at_first_tracker_failure(moving_video):
    path, truth = moving_video
    x, y, w, h = truth[0]
    outputs = [(True, (x, y, w, h))] * 9 + [(False, None)] + [(True, (x, y, w, h))] * 100
    run = track_video(path, 0, Box(x, y, w, h), "KCF", tracker_factory=lambda: ScriptedTracker(outputs))
    assert run.lost_frame == 10 and run.lost_reason == REASON_FAILURE
    assert len(run.states) == 11
    assert run.states[-1].status == LOST and run.states[-1].box is None
    assert all(s.status == TRACKED for s in run.states[:-1])


def test_run_stops_when_area_jumps_more_than_half(moving_video):
    path, truth = moving_video
    x, y, w, h = truth[0]          # 40x40 -> area 1600
    outputs = [(True, (x, y, 40, 40))] * 4 + [(True, (x, y, 40, 60))] + [(True, (x, y, 40, 61))]
    run = track_video(path, 0, Box(x, y, w, h), "KCF", tracker_factory=lambda: ScriptedTracker(outputs))
    # +50% (2400) at frame 5 is allowed; frame 6 grows only +1.7% vs frame 5 -> never lost
    assert run.lost_frame is None
    assert run.states[6].box == Box(x, y, 40, 61)
    outputs = [(True, (x, y, 40, 40))] * 4 + [(True, (x, y, 40, 61))]
    run = track_video(path, 0, Box(x, y, w, h), "KCF", tracker_factory=lambda: ScriptedTracker(outputs))
    assert run.lost_frame == 5 and run.lost_reason == REASON_AREA


def test_real_tracker_reports_loss_when_target_disappears(video_dir):
    path, truth = vanishing_target_video(video_dir / "vanish.mp4")
    run = track_video(path, 0, Box(*truth[0]), "KCF")
    assert run.lost_frame is not None
    assert 30 <= run.lost_frame <= 40  # target hidden from frame 30 to 39
