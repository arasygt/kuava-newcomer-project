"""US-2: track the selected target with an OpenCV tracker and return a box for every frame."""
import pytest

from app.lock import TRACKED
from tests.conftest import track


def test_tracking_returns_a_box_for_every_frame(client, uploaded, moving_video):
    res = track(client, uploaded["id"], 0, moving_video[1][0])
    assert res.status_code == 200
    body = res.json()
    assert body["run"]["frames_processed"] == 75
    assert len(body["states"]) == 75
    assert all(s[0] == TRACKED and len(s) == 5 for s in body["states"])


def test_tracking_result_is_kept_on_the_video(client, uploaded, moving_video):
    track(client, uploaded["id"], 0, moving_video[1][0])
    states = client.get(f"/api/videos/{uploaded['id']}").json()["states"]
    assert len(states) == 75 and all(s[0] == TRACKED for s in states)


def test_tracker_list_endpoint(client):
    body = client.get("/api/trackers").json()
    assert set(body["trackers"]) == {"CSRT", "KCF", "MIL"}
    assert body["default"] == "KCF"


@pytest.mark.parametrize("payload, fragment", [
    ({"start_frame": 0, "box": {"x": 300, "y": 10, "w": 40, "h": 40}}, "inside the video frame"),
    ({"start_frame": 0, "box": {"x": 10, "y": 10, "w": 0, "h": 40}}, "box.w"),
    ({"start_frame": 0, "box": {"x": 10, "y": 10, "w": 2, "h": 2}}, "too small"),
    ({"start_frame": -1, "box": {"x": 10, "y": 10, "w": 40, "h": 40}}, "start_frame"),
    ({"start_frame": 75, "box": {"x": 10, "y": 10, "w": 40, "h": 40}}, "start_frame"),
    ({"start_frame": 0, "box": {"x": 10, "y": 10, "w": 40, "h": 40}, "tracker": "NOPE"}, "Unknown tracker"),
    ({"box": {"x": 10, "y": 10, "w": 40, "h": 40}}, "start_frame"),
])
def test_invalid_tracking_requests_give_clear_errors(client, uploaded, payload, fragment):
    res = client.post(f"/api/videos/{uploaded['id']}/track", json=payload)
    assert res.status_code == 400
    assert fragment in res.json()["detail"]


def test_tracking_unknown_video_is_404(client):
    res = track(client, "doesnotexist", 0, (1, 1, 9, 9))
    assert res.status_code == 404


def test_tracking_while_already_running_is_refused(client, uploaded):
    session = client.app.state.store.get(uploaded["id"])
    session.lock.acquire()
    try:
        res = track(client, uploaded["id"], 0, (10, 100, 40, 40))
        assert res.status_code == 409
        assert "already running" in res.json()["detail"]
    finally:
        session.lock.release()
