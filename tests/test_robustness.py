"""Fixes found in the final review: MIL freeze on tiny boxes, NaN/Infinity input, stale uploads."""
import threading

import pytest

from app.lock import Box
from app.main import create_app
from app import tracking
from app.tracking import track_video
from tests.conftest import track
from tests.videogen import linear_path, write_video


def finishes_within(fn, seconds):
    """Run fn in a daemon thread; return (finished, result_or_exception)."""
    out = {}

    def run():
        try:
            out["r"] = fn()
        except Exception as e:  # noqa: BLE001 - the test inspects it
            out["r"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(seconds)
    return not t.is_alive(), out.get("r")


@pytest.fixture(scope="module")
def video_720p(tmp_path_factory):
    path = tmp_path_factory.mktemp("v720") / "small_target_720p.mp4"
    return write_video(path, linear_path(15, 1280, 720, 40), 1280, 720, 25, 40)


# ---------- IQ-9: MIL needs a box of at least 8x8 px ----------

@pytest.mark.parametrize("size, ok", [(7.9, False), (8, True), (8.1, True)])
def test_mil_minimum_box_boundaries(moving_video, size, ok):
    run = lambda: track_video(moving_video[0], 0, Box(100, 100, size, size), "MIL")  # noqa: E731
    finished, result = finishes_within(run, 30)
    assert finished, "MIL tracking did not finish (frozen)"
    if ok:
        assert not isinstance(result, Exception), result
        assert result.states
    else:
        assert isinstance(result, ValueError) and "8x8" in str(result)


def test_kcf_and_csrt_keep_the_4x4_minimum(moving_video):
    for name in ("KCF", "CSRT"):
        assert track_video(moving_video[0], 0, Box(100, 100, 4, 4), name).states


def test_api_refuses_small_mil_box_quickly(client, uploaded):
    finished, res = finishes_within(lambda: track(client, uploaded["id"], 0, (100, 100, 4, 4), "MIL"), 30)
    assert finished, "MIL request never returned"
    assert res.status_code == 400
    assert "MIL" in res.json()["detail"] and "8x8" in res.json()["detail"]


# ---------- the tracked box never shrinks below MIN_TRACKED_PX ----------

@pytest.mark.parametrize("frame_w, box_side, expected", [
    (1280, 80, 0.5),    # normal case: downscale to 640 px wide
    (1280, 10, 0.8),    # 10 px * 0.8 = 8 px -> limited downscale
    (1280, 4, 1.0),     # would need upscaling -> keep full resolution
    (320, 40, 1.0),     # already narrow -> no scaling
])
def test_tracking_scale_keeps_box_large_enough(frame_w, box_side, expected):
    assert tracking.MIN_TRACKED_PX == 8
    assert tracking.tracking_scale(frame_w, Box(0, 0, box_side, box_side)) == pytest.approx(expected)


def test_mil_with_small_box_on_720p_finishes(video_720p):
    # 8x8 on 1280x720 used to become 4x4 after downscaling and froze MIL
    finished, result = finishes_within(lambda: track_video(video_720p, 0, Box(100, 340, 8, 8), "MIL"), 60)
    assert finished, "MIL froze on a small box in a 720p video"
    assert not isinstance(result, Exception), result


# ---------- NaN / Infinity are refused with a clear 400 ----------

@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_box_values_give_clear_error(client, uploaded, bad):
    body = '{"start_frame": 0, "box": {"x": %s, "y": 10, "w": 40, "h": 40}}' % bad
    res = client.post(f"/api/videos/{uploaded['id']}/track", content=body,
                      headers={"content-type": "application/json"})
    assert res.status_code == 400
    assert "box.x" in res.json()["detail"] and "finite" in res.json()["detail"]


def test_non_finite_zone_gives_clear_error(client, uploaded):
    res = client.post(f"/api/videos/{uploaded['id']}/analysis",
                      content='{"zone": {"x": NaN, "y": 0, "w": 10, "h": 10}}',
                      headers={"content-type": "application/json"})
    assert res.status_code == 400
    assert "zone.x" in res.json()["detail"] and "finite" in res.json()["detail"]


# ---------- uploads from a previous run are removed at start-up ----------

def test_stale_uploads_are_removed_on_startup(tmp_path):
    up = tmp_path / "uploads"
    up.mkdir()
    (up / "0123abcd.mp4").write_bytes(b"old upload")
    (up / "notes.txt").write_text("not ours")
    create_app(upload_dir=up)
    assert not (up / "0123abcd.mp4").exists()
    assert (up / "notes.txt").exists()   # only our .mp4 uploads are deleted
