"""US-4: timeline of locked / unlocked periods and the longest lock, through the API."""
import pytest

from tests.conftest import set_states

ZONE = {"x": 80, "y": 24, "w": 160, "h": 192}


def analyse(client, vid):
    return client.post(f"/api/videos/{vid}/analysis", json={"zone": ZONE}).json()


def test_timeline_and_longest_lock(client, uploaded):
    set_states(client, uploaded["id"], "O" * 10 + "I" * 20 + "O" * 5 + "I" * 30 + "L" + "U" * 9)
    body = analyse(client, uploaded["id"])
    assert body["longest"]["start_frame"] == 35 and body["longest"]["end_frame"] == 64
    assert body["longest"]["duration"] == pytest.approx(1.2)
    assert [(s["state"], s["start_frame"], s["end_frame"]) for s in body["timeline"]] == [
        ("unlocked", 0, 9), ("locked", 10, 29), ("unlocked", 30, 34),
        ("locked", 35, 64), ("lost", 65, 65), ("untracked", 66, 74),
    ]


def test_timeline_covers_whole_video_before_tracking(client, uploaded):
    body = analyse(client, uploaded["id"])
    assert body["timeline"] == [{"state": "untracked", "start_frame": 0, "end_frame": 74,
                                 "start_time": 0.0, "end_time": 3.0}]
    assert body["longest"] is None


def test_no_lock_means_no_longest(client, uploaded):
    set_states(client, uploaded["id"], "O" * 75)
    assert analyse(client, uploaded["id"])["longest"] is None
