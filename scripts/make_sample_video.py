"""Create a small synthetic H.264 demo video (target crosses the frame, hides, reappears).

Usage: python scripts/make_sample_video.py [output.mp4]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests.videogen import linear_path, write_video  # noqa: E402


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/sample.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height, fps, size, n = 1280, 720, 30, 80, 300  # 10 s, 720p
    # There and back again, so the target enters and leaves the lock zone twice
    forward = linear_path(n // 2, width, height, size, 0.03, 0.97)
    boxes = forward + forward[::-1]
    visible = [not (170 <= i < 185) for i in range(n)]  # hidden for half a second
    write_video(out, boxes, width, height, fps, size, visible=visible)
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB, {n} frames, {width}x{height} @ {fps} fps)")


if __name__ == "__main__":
    main()
