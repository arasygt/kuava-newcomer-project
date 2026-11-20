# Approval Log

> Single file shared by the **entire pipeline** (`requirement-analysis`, `solution-architect`, and any future stage). Exactly **one active entry** exists at a time, regardless of which stage/skill created it, with status `Pending Approval`. Update it in place as decisions accumulate during a session — never create a second pending entry. Once a human operator explicitly sets it to `Approved` or `Rejected` and the associated commit/PR lands, move it to History below and leave the active slot empty for the next stage to use.

## Active Entry

_No active entry — the next stage will open one._

---

## History

<!-- Closed (Approved/Rejected) entries, most recent first. -->

### Solution Architecture — US-2 target tracking

- **Status**: Approved
- **Stage**: Solution Architecture
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/architecture/ARCHITECTURE.md (input: Requirement Analysis — US-2, approved 2026-11-21)
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - KCF default tracker (CSRT ≈ 40–50 ms/frame on the 2-core dev laptop would endanger the 60 s budget)
  - Frames wider than 640 px are downscaled for tracking; boxes scaled back to original pixels
  - Synchronous POST /track in the thread pool; 409 for a second run on the same video
  - Browser maps time to frame with requestVideoFrameCallback; seeks to mid-frame
  - Entities: Box, FrameState, TrackRun
- **Open Questions Resolved This Session**:
  - AQ-5 — synchronous request, per-video lock (409)
  - AQ-6 — KCF default
  - AQ-7 — downscale to max 640 px width
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Requirement Analysis — US-2 target tracking

- **Status**: Approved
- **Stage**: Requirement Analysis
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/design/DESIGN.md
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - US-2: track the target with an OpenCV tracker and show its box on every frame
  - NFR: 30 s 720p video processed in < 60 s on a laptop CPU
  - Rejection scenarios: box outside frame / too small, bad start frame, unknown tracker, concurrent run
  - Out of scope this round: lock zone, timeline, loss handling
- **Open Questions Resolved This Session**:
  - OQ-6 — user chooses CSRT, KCF or MIL; default decided in architecture
  - OQ-7 — track once on the server, draw stored boxes over the normal player
  - OQ-8 — canvas overlay with frame counter and time, synced to playback and seeking
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Implementation — US-1 Upload a video and select the target

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md, docs/design/DESIGN.md, docs/architecture/ARCHITECTURE.md
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - US-1 implemented on `feature/video-upload-target-selection`
  - Red: collection aborted — ImportError while loading conftest (ModuleNotFoundError: No module named 'app')
  - Green: 30 passed, 1 warning in 6.73s
- **Open Questions Resolved This Session**:
  - IQ-1 — Generate them at test time with imageio-ffmpeg (bundled FFmpeg with libx264) into pytest's temp folder (`tests/videogen.py`).
  - IQ-2 — No. A custom handler returns HTTP 400 with one readable sentence, e.g. `Invalid request — file: Field required`.
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Solution Architecture — US-1 video upload and target selection

- **Status**: Approved
- **Stage**: Solution Architecture
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/architecture/ARCHITECTURE.md (input: Requirement Analysis — US-1, approved 2026-11-21)
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - Python 3.12 + FastAPI + vanilla JS (no build step, one-command run)
  - H.264 check = ftyp magic + OpenCV FourCC + first-frame decode
  - Uploads in git-ignored data/uploads/, results in memory
  - Frame-exact access by sequential grab() instead of seeking
  - Entities: VideoInfo, VideoSession
- **Open Questions Resolved This Session**:
  - AQ-1 — Python + FastAPI + vanilla JS
  - AQ-2 — no persistence across restarts
  - AQ-3 — sequential grab() for exact frames
  - AQ-4 — ftyp + FourCC + decode, no FFmpeg needed
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Requirement Analysis — US-1 video upload and target selection

- **Status**: Approved
- **Stage**: Requirement Analysis
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/design/DESIGN.md
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - US-1: upload an MP4 (H.264) and draw the target box on the first frame
  - Rejection scenarios: wrong extension, wrong codec, empty/corrupt/truncated file, > 500 MB, box too small, box outside frame
  - Out of scope this round: tracking, lock zone, timeline, loss handling
- **Open Questions Resolved This Session**:
  - OQ-1 — only .mp4 with an H.264 stream; everything else rejected with a message
  - OQ-2 — 500 MB upload limit
  - OQ-3 — first frame only in this round; other frames come with US-5
  - OQ-4 — minimum box 4×4 px
  - OQ-5 — box must stay inside the frame; UI clamps the drag
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

