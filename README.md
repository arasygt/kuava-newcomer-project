# Target-Lock Video Tracker

KUAVA newcomer task — **Project B**. A local web app that tracks a target in drone video with an OpenCV tracker and measures how long it stays inside a lock zone, inspired by the lock-on task of the TEKNOFEST Fighter UAV competition.

![pipeline](https://img.shields.io/badge/pipeline-requirements%20→%20architecture%20→%20red%20→%20green-35d0ba)

## Features

| Requirement | Where |
|---|---|
| Upload an MP4 (H.264) and draw a box around the target on the first frame | US-1 |
| Track the target through the video with an OpenCV tracker (KCF default, CSRT, MIL) and show its box on every frame | US-2 |
| Define a lock zone; the target is locked while its box is fully inside the zone; every continuous lock period is reported | US-3 |
| Timeline of locked / unlocked / lost / not-tracked periods, longest lock highlighted | US-4 |
| Detect lost tracking (tracker failure, or box area change > 50% between two frames) and re-select the target | US-5 |

Invalid input (wrong extension, non-H.264 codec, corrupt/empty/truncated file, box or zone outside the frame, bad frame numbers…) always produces a clear message and never crashes the app.

## Setup

Requires **Python 3.10+** (developed with 3.12 on Windows). No FFmpeg install is needed.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

> Use a fresh virtual environment: `opencv-python`, `opencv-python-headless` and `opencv-contrib-python-headless` must not be installed side by side, and the CSRT/KCF trackers come from the contrib package.

## Run (one command)

```bash
python run.py
```

The app opens at <http://127.0.0.1:8000>. Options: `--port 8080`, `--no-browser`.

No sample video at hand? Generate a small synthetic 10 s 720p clip (≈2.5 MB, not committed):

```bash
python scripts/make_sample_video.py data/sample.mp4
```

### How to use

1. **Upload** an `.mp4` (drag & drop or click).
2. **Draw a box** around the target on frame 0, choose a tracker, press **Start tracking**.
3. **Review**: the box is drawn over the video on every frame (green = locked, yellow = tracked but outside the zone). The dashed rectangle is the lock zone — press **Draw lock zone** to drag a new one, **Default zone** to reset it.
4. The side panel lists every lock period (click a row to jump there) with the **longest lock** starred; the timeline at the bottom shows all states (click to seek).
5. If tracking is lost, a banner names the frame and the reason. Press **Re-select target**, step to a frame where the target is visible (−10/−1/+1/+10 or type a frame number), draw a new box and continue. **Re-select at this frame** does the same from any frame.

## Tests (one command)

```bash
python -m pytest
```

149 tests + 1 performance test. All test videos are generated at test time in a temp folder (`tests/videogen.py`), so no video is stored in the repository. Skip the ~15 s performance test with `python -m pytest -m "not perf"`.

| File | Covers |
|---|---|
| `test_video.py`, `test_api_upload.py` | US-1 validation, metadata, exact frame access, upload API |
| `test_tracking_core.py`, `test_api_tracking.py` | US-2 tracking on every frame (IoU ≥ 0.5 vs ground truth), input validation, 409 on concurrent runs |
| `test_performance.py` | NFR: 30 s 720p video tracked in < 60 s |
| `test_lock_periods.py`, `test_api_lock.py` | US-3 inside-zone boundaries, lock periods from generated sequences with known answers |
| `test_timeline.py`, `test_api_timeline.py` | US-4 timeline segments, longest lock and ties |
| `test_loss.py`, `test_api_lost.py` | US-5 loss rules (exactly ±50% vs just over), failure stop, re-selection |
| `test_robustness.py` | Final-review fixes: MIL minimum box (no freeze), non-finite input, stale-upload cleanup |

## Definitions

- **Locked frame**: the tracker produced a box on that frame **and** the whole box is inside the lock zone (`box.x ≥ zone.x`, `box.y ≥ zone.y`, `box.x+box.w ≤ zone.x+zone.w`, `box.y+box.h ≤ zone.y+zone.h`; touching the border counts as inside). Lost and not-tracked frames are never locked.
- **Lock period**: a maximal run of consecutive locked frames. `start = first_frame / fps`, `end = (last_frame + 1) / fps`, `duration = frames / fps` (a single locked frame lasts 1/fps s). No minimum duration.
- **Longest lock**: the period with the most frames; on a tie, the earliest.
- **Default lock zone**: x from 25% to 75% of the width, y from 10% to 90% of the height.
- **Tracking lost** on frame t: the tracker reports failure (or a box with zero/negative size), **or** `|A_t − A_{t−1}| / A_{t−1} > 0.5` where A is the box area. Exactly 50% is still tracked. Tracking stops at the lost frame; later frames stay "not tracked" until the user re-selects. KCF and MIL keep a fixed box size, so with them only the failure rule can trigger; the area rule fires with CSRT.
- **Minimum box**: 4×4 px for KCF and CSRT, 8×8 px for MIL (MIL freezes on smaller boxes).

### Known limitations

- Uploads are kept only while the server runs; they are deleted from `data/uploads/` the next time it starts.
- Frame ↔ time mapping assumes a constant frame rate (normal for drone footage; variable-frame-rate phone videos may be slightly off).
- Stepping to a late frame in the re-select view decodes from the start for exactness (≈ 3 s near the end of a 30 s 720p clip).

## Architecture

```
app/
  main.py      FastAPI routes + static UI, error handling (400/404/409/413/500 with messages)
  video.py     MP4/H.264 validation (ftyp + FourCC + first-frame decode), frame-exact reads
  tracking.py  OpenCV trackers (KCF/CSRT/MIL), 640 px tracking width, loss detection
  lock.py      pure lock-zone logic: periods, timeline, longest lock
  store.py     in-memory video sessions (uploads in data/uploads/, git-ignored)
  static/      index.html, app.js (canvas overlay on <video>, timeline), style.css
tests/         pytest suite + synthetic video generator
docs/          design, architecture, implementation log, approval log
```

Why Python + FastAPI + vanilla JS, why KCF is the default tracker (CSRT ≈ 40–50 ms/frame on a 2-core laptop would endanger the 60 s budget; KCF does 900 frames of 720p in ≈ 10 s) and the other decisions are explained with benefit/drawback tables in [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md).

## Development process

Every feature went through the agentic skill pipeline (skills in `.claude/skills/`):
requirements ([DESIGN.md](docs/design/DESIGN.md)) → Gate 1 → architecture ([ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)) → Gate 2 → implementation one story at a time, red phase then green phase ([IMPLEMENTATION_LOG.md](docs/implementation/IMPLEMENTATION_LOG.md)). Approvals are recorded in [docs/APPROVAL_LOG.md](docs/APPROVAL_LOG.md); open questions I had to research are in [LEARNING.md](LEARNING.md).
