"""US-1: video validation and exact frame access."""
import cv2
import numpy as np
import pytest

from app.video import VideoValidationError, check_extension, probe, read_frame
from tests.videogen import moving_target_video


def test_valid_h264_mp4_reports_metadata(moving_video):
    path, _ = moving_video
    info = probe(path)
    assert (info.width, info.height, info.fps, info.frame_count) == (320, 240, 25.0, 75)
    assert info.duration == pytest.approx(3.0)
    assert info.codec.lower() in {"h264", "avc1"}


def test_mpeg4_codec_in_mp4_container_is_rejected(video_dir):
    path, _ = moving_target_video(video_dir / "mpeg4.mp4", n_frames=10, codec="mpeg4")
    with pytest.raises(VideoValidationError, match="Only H.264"):
        probe(path)


def test_non_video_file_named_mp4_is_rejected(tmp_path):
    path = tmp_path / "fake.mp4"
    path.write_bytes(b"this is definitely not a video" * 100)
    with pytest.raises(VideoValidationError, match="not a valid MP4"):
        probe(path)


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "empty.mp4"
    path.write_bytes(b"")
    with pytest.raises(VideoValidationError, match="empty"):
        probe(path)


def test_truncated_mp4_is_rejected(moving_video, tmp_path):
    src, _ = moving_video
    path = tmp_path / "truncated.mp4"
    path.write_bytes(src.read_bytes()[:2048])  # header present, frame data missing
    with pytest.raises(VideoValidationError):
        probe(path)


@pytest.mark.parametrize("name", ["clip.avi", "clip.mov", "clip.mp4.txt", "clip", "", None])
def test_non_mp4_extensions_are_rejected(name):
    with pytest.raises(VideoValidationError, match=r"\.mp4"):
        check_extension(name)


@pytest.mark.parametrize("name", ["clip.mp4", "CLIP.MP4"])
def test_mp4_extension_is_accepted_case_insensitively(name):
    check_extension(name)  # raising would fail the test; acceptance is the contract


def test_read_frame_returns_the_exact_requested_frame(moving_video):
    path, boxes = moving_video
    cap = cv2.VideoCapture(str(path))
    for _ in range(40):
        cap.read()
    _, expected = cap.read()  # frame 40 via plain sequential decode
    cap.release()
    frame = read_frame(path, 40)
    assert np.array_equal(frame, expected)
    # The target's red border is at the ground-truth position of frame 40
    x, y, w, h = boxes[40]
    b, g, r = frame[y + h // 2, x + 1].astype(int)
    assert r > 150 and g < 100 and b < 100


@pytest.mark.parametrize("index", [75, 1000, -1])
def test_read_frame_out_of_range_raises(moving_video, index):
    path, _ = moving_video
    with pytest.raises(IndexError):
        read_frame(path, index)


def test_last_frame_is_readable(moving_video):
    path, _ = moving_video
    assert read_frame(path, 74).shape == (240, 320, 3)
