"""NFR-1: a 30-second 720p video is processed in less than 60 seconds on a laptop CPU."""
import time

import pytest

from app.lock import Box
from app.tracking import DEFAULT_TRACKER, track_video
from tests.videogen import linear_path, write_video

BUDGET_S = 60.0


@pytest.mark.perf
def test_30s_720p_video_tracks_within_budget(video_dir):
    fps, n = 30, 900
    boxes = linear_path(n, 1280, 720, 90)
    path = write_video(video_dir / "perf_720p.mp4", boxes, 1280, 720, fps, 90)
    t0 = time.perf_counter()
    run = track_video(path, 0, Box(*boxes[0]), DEFAULT_TRACKER)
    elapsed = time.perf_counter() - t0
    print(f"\n{DEFAULT_TRACKER}: {n} frames of 1280x720 in {elapsed:.1f} s")
    assert len(run.states) == n
    assert all(s.status == "tracked" for s in run.states)
    assert elapsed < BUDGET_S
