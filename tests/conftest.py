import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.main import create_app  # noqa: E402
from tests.videogen import moving_target_video  # noqa: E402


@pytest.fixture(scope="session")
def video_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("videos")


@pytest.fixture(scope="session")
def moving_video(video_dir):
    """75-frame 320x240 25 fps H.264 video; returns (path, ground-truth boxes)."""
    return moving_target_video(video_dir / "moving.mp4")


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(upload_dir=tmp_path / "uploads"))


@pytest.fixture()
def uploaded(client, moving_video):
    res = upload(client, moving_video[0])
    assert res.status_code == 200
    return res.json()


def upload(client, path, name=None):
    with open(path, "rb") as f:
        return client.post("/api/videos", files={"file": (name or Path(path).name, f, "video/mp4")})


def track(client, vid, frame, box, tracker="KCF"):
    x, y, w, h = box
    return client.post(f"/api/videos/{vid}/track",
                       json={"start_frame": frame, "box": {"x": x, "y": y, "w": w, "h": h}, "tracker": tracker})


def set_states(client, vid, kinds):
    """Inject a known per-frame sequence: I = inside zone, O = outside, L = lost, U = untracked."""
    from app.lock import LOST, TRACKED, UNTRACKED, Box, FrameState
    session = client.app.state.store.get(vid)
    boxes = {"I": Box(150, 100, 20, 20), "O": Box(5, 5, 20, 20)}
    session.states = [
        FrameState(i, TRACKED, boxes[k]) if k in boxes else FrameState(i, LOST if k == "L" else UNTRACKED)
        for i, k in enumerate(kinds)
    ]
