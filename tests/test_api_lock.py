"""US-3: lock zone and the list of continuous lock periods, through the API."""
import pytest

from tests.conftest import set_states, track

ZONE = {"x": 80, "y": 24, "w": 160, "h": 192}


def test_analysis_reports_every_lock_period(client, uploaded):
    set_states(client, uploaded["id"], "O" * 10 + "I" * 20 + "O" * 5 + "I" * 30 + "L" + "U" * 9)
    res = client.post(f"/api/videos/{uploaded['id']}/analysis", json={"zone": ZONE})
    assert res.status_code == 200
    body = res.json()
    assert [(p["start_frame"], p["end_frame"]) for p in body["periods"]] == [(10, 29), (35, 64)]
    assert body["periods"][0]["duration"] == pytest.approx(20 / 25)
    assert body["periods"][1]["start_time"] == pytest.approx(35 / 25)
    assert body["total_locked_time"] == pytest.approx(2.0)


def test_analysis_changes_when_zone_changes(client, uploaded):
    set_states(client, uploaded["id"], "I" * 75)
    small = {"x": 0, "y": 0, "w": 50, "h": 50}  # the box at (150,100) is outside this zone
    body = client.post(f"/api/videos/{uploaded['id']}/analysis", json={"zone": small}).json()
    assert body["periods"] == []
    assert body["total_locked_frames"] == 0


@pytest.mark.parametrize("zone", [
    {"x": -1, "y": 0, "w": 100, "h": 100},
    {"x": 0, "y": 0, "w": 321, "h": 100},
    {"x": 0, "y": 0, "w": 0, "h": 100},
    {"x": 0, "y": 0, "w": 100},
])
def test_invalid_zone_gives_clear_error(client, uploaded, zone):
    res = client.post(f"/api/videos/{uploaded['id']}/analysis", json={"zone": zone})
    assert res.status_code == 400
    assert res.json()["detail"]


def test_zone_equal_to_full_frame_is_accepted(client, uploaded):
    res = client.post(f"/api/videos/{uploaded['id']}/analysis", json={"zone": {"x": 0, "y": 0, "w": 320, "h": 240}})
    assert res.status_code == 200


def test_analysis_unknown_video_is_404(client):
    assert client.post("/api/videos/nope/analysis", json={"zone": ZONE}).status_code == 404


def test_end_to_end_lock_period_matches_ground_truth(client, uploaded, moving_video):
    truth = moving_video[1]
    track(client, uploaded["id"], 0, truth[0])
    body = client.post(f"/api/videos/{uploaded['id']}/analysis", json={"zone": ZONE}).json()
    # Ground truth: frames whose true box lies fully inside the zone (x 80..240)
    expected = [i for i, (x, y, w, h) in enumerate(truth) if x >= 80 and x + w <= 240]
    [period] = body["periods"]
    assert abs(period["start_frame"] - expected[0]) <= 2
    assert abs(period["end_frame"] - expected[-1]) <= 2
