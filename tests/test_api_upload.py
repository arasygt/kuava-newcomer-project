"""US-1: upload an MP4 (H.264) video and get the first frame to draw the target box on."""
import pytest

from tests.conftest import upload
from tests.videogen import moving_target_video


def test_upload_valid_video_returns_metadata(uploaded):
    assert (uploaded["width"], uploaded["height"], uploaded["frame_count"], uploaded["fps"]) == (320, 240, 75, 25.0)
    assert uploaded["filename"] == "moving.mp4"
    assert len(uploaded["id"]) == 32


def test_upload_wrong_extension_gives_clear_error(client, tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("hello")
    res = upload(client, p)
    assert res.status_code == 400
    assert "Only .mp4 files are supported" in res.json()["detail"]


def test_upload_non_h264_gives_clear_error(client, video_dir):
    path, _ = moving_target_video(video_dir / "api_mpeg4.mp4", n_frames=10, codec="mpeg4")
    res = upload(client, path)
    assert res.status_code == 400
    assert "Only H.264" in res.json()["detail"]


def test_upload_garbage_mp4_gives_clear_error(client, tmp_path):
    p = tmp_path / "broken.mp4"
    p.write_bytes(b"\x00" * 5000)
    res = upload(client, p)
    assert res.status_code == 400
    assert "not a valid MP4" in res.json()["detail"]


def test_upload_without_file_gives_clear_error(client):
    res = client.post("/api/videos")
    assert res.status_code == 400
    assert "file" in res.json()["detail"]


def test_rejected_upload_is_not_kept_on_disk(client, tmp_path):
    p = tmp_path / "broken.mp4"
    p.write_bytes(b"\x00" * 5000)
    upload(client, p)
    assert list(client.app.state.store.upload_dir.iterdir()) == []


def test_first_frame_is_served_as_jpeg(client, uploaded):
    res = client.get(f"/api/videos/{uploaded['id']}/frames/0")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    assert res.content[:2] == b"\xff\xd8"


@pytest.mark.parametrize("index, status", [(74, 200), (75, 400), (-1, 400)])
def test_frame_index_boundaries(client, uploaded, index, status):
    assert client.get(f"/api/videos/{uploaded['id']}/frames/{index}").status_code == status


def test_video_file_is_served_for_the_player(client, uploaded, moving_video):
    res = client.get(f"/api/videos/{uploaded['id']}/file")
    assert res.status_code == 200
    assert res.content == moving_video[0].read_bytes()


def test_unknown_video_id_is_404_with_message(client):
    res = client.get("/api/videos/doesnotexist")
    assert res.status_code == 404
    assert "upload" in res.json()["detail"]
    assert client.get("/api/videos/doesnotexist/frames/0").status_code == 404
