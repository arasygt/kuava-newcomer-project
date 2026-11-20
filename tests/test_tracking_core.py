"""US-2: track the target through the video with an OpenCV tracker."""
import pytest

from app.lock import TRACKED, Box
from app.tracking import track_video


def iou(a: Box, b) -> float:
    bx, by, bw, bh = b
    ix = max(0.0, min(a.x + a.w, bx + bw) - max(a.x, bx))
    iy = max(0.0, min(a.y + a.h, by + bh) - max(a.y, by))
    inter = ix * iy
    return inter / (a.w * a.h + bw * bh - inter)


@pytest.mark.parametrize("tracker", ["KCF", "CSRT"])
def test_tracker_follows_target_on_every_frame(moving_video, tracker):
    path, truth = moving_video
    run = track_video(path, 0, Box(*truth[0]), tracker)
    assert [s.frame for s in run.states] == list(range(75))
    assert all(s.status == TRACKED for s in run.states)
    worst = min(iou(s.box, truth[s.frame]) for s in run.states)
    assert worst >= 0.5, f"{tracker} drifted: worst IoU {worst:.2f}"


def test_tracking_can_start_mid_video(moving_video):
    path, truth = moving_video
    run = track_video(path, 30, Box(*truth[30]), "KCF")
    assert run.states[0].frame == 30 and run.states[-1].frame == 74
    assert iou(run.states[-1].box, truth[74]) >= 0.5


def test_downscaled_tracking_returns_boxes_in_original_pixels(moving_video):
    path, truth = moving_video
    run = track_video(path, 0, Box(*truth[0]), "KCF", max_width=160)  # tracks at half size
    assert iou(run.states[40].box, truth[40]) >= 0.5


@pytest.mark.parametrize("box", [
    Box(-1, 10, 40, 40),      # 1 px left of the frame
    Box(281, 10, 40, 40),     # right edge 321 > width 320
    Box(10, 201, 40, 40),     # bottom edge 241 > height 240
])
def test_init_box_outside_frame_is_rejected(moving_video, box):
    with pytest.raises(ValueError, match="inside the video frame"):
        track_video(moving_video[0], 0, box, "KCF")


def test_init_box_touching_frame_edges_is_accepted(moving_video):
    run = track_video(moving_video[0], 0, Box(280, 200, 40, 40), "KCF")
    assert run.states[0].box == Box(280, 200, 40, 40)


@pytest.mark.parametrize("w, h, ok", [(4, 4, True), (3.9, 4, False), (4, 3, False)])
def test_init_box_minimum_size(moving_video, w, h, ok):
    if ok:
        assert track_video(moving_video[0], 0, Box(100, 100, w, h), "KCF").states
    else:
        with pytest.raises(ValueError, match="too small"):
            track_video(moving_video[0], 0, Box(100, 100, w, h), "KCF")


def test_unknown_tracker_is_rejected(moving_video):
    with pytest.raises(ValueError, match="Unknown tracker"):
        track_video(moving_video[0], 0, Box(10, 10, 40, 40), "BOOSTING")


def test_start_frame_past_end_is_rejected(moving_video):
    with pytest.raises(IndexError):
        track_video(moving_video[0], 75, Box(10, 10, 40, 40), "KCF")
