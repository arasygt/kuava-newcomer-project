# Approval Log

> Single file shared by the **entire pipeline** (`requirement-analysis`, `solution-architect`, and any future stage). Exactly **one active entry** exists at a time, regardless of which stage/skill created it, with status `Pending Approval`. Update it in place as decisions accumulate during a session — never create a second pending entry. Once a human operator explicitly sets it to `Approved` or `Rejected` and the associated commit/PR lands, move it to History below and leave the active slot empty for the next stage to use.

## Active Entry

- **Status**: Pending Approval
- **Stage**: Implementation
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md, docs/design/DESIGN.md, docs/architecture/ARCHITECTURE.md
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - US-5 implemented on `feature/lost-tracking-reselect`
  - Red: 3 failed, 116 passed, 1 deselected, 1 warning, 1 error in 15.12s
  - Green: 135 passed, 1 warning in 59.78s
- **Open Questions Resolved This Session**:
  - IQ-7 — Use a scripted stand-in for the OpenCV tracker (the external library boundary) for exact frames, plus a real KCF run on a video where the target disappears (frames 30–39) with a range assertion.
  - IQ-8 — `HTMLImageElement.decode()` can stay pending while the tab is hidden. Replaced with `onload`/`onerror`, and stale frame loads are ignored.
- **Approved By**: 
- **Approval Date**: 

---

## History

<!-- Closed (Approved/Rejected) entries, most recent first. -->

### Solution Architecture — US-5 lost tracking and re-selection

- **Status**: Approved
- **Stage**: Solution Architecture
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/architecture/ARCHITECTURE.md (input: Requirement Analysis — US-5, approved 2026-11-21)
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - Loss rule in tracking.detect_loss; run stops at the loss frame
  - Session keeps states before the re-selection frame and replaces the rest
  - Consolidated system overview and NFR mapping added
  - Entity: LossRule
- **Open Questions Resolved This Session**:
  - AQ-11 — area ratio is scale-invariant; computed in original pixels vs previous tracked box
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Requirement Analysis — US-5 lost tracking and re-selection

- **Status**: Approved
- **Stage**: Requirement Analysis
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/design/DESIGN.md
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - US-5: detect lost tracking (tracker failure or > 50% area change) and let the user re-select
  - Rejection scenarios: non-numeric frame, out-of-range frame (clamped)
- **Open Questions Resolved This Session**:
  - OQ-16 — stop at the loss frame
  - OQ-17 — strictly > 50% vs the previous frame; exactly 50% still tracked
  - OQ-18 — re-select on any frame via frame stepping; earlier results kept
  - OQ-19 — lost frames are never locked
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Implementation — US-4 See a lock timeline and the longest lock

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md, docs/design/DESIGN.md, docs/architecture/ARCHITECTURE.md
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - US-4 implemented on `feature/lock-timeline`
  - Red: 3 failed, 105 passed, 1 deselected, 1 warning, 1 error in 13.14s
  - Green: 117 passed, 1 warning in 58.16s
- **Open Questions Resolved This Session**:
  - IQ-6 — No. `lock_periods()` is now derived from the `locked` timeline segments, so both always agree (refactor step; US-3 tests unchanged and still green).
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Implementation — US-3 Define a lock zone and report every lock period

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md, docs/design/DESIGN.md, docs/architecture/ARCHITECTURE.md
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - US-3 implemented on `feature/lock-zone-periods`
  - Red: 9 failed, 55 passed, 1 deselected, 1 warning, 1 error in 14.99s
  - Green: 106 passed, 1 warning in 54.14s
- **Open Questions Resolved This Session**:
  - IQ-5 — Inject a known per-frame state sequence into the session (`set_states` helper) for exact answers, plus one end-to-end test against ground truth with ±2 frames tolerance.
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Solution Architecture — US-3, US-4 lock zone analysis

- **Status**: Approved
- **Stage**: Solution Architecture
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/architecture/ARCHITECTURE.md (input: Requirement Analysis — US-3, US-4, approved 2026-11-21)
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - Lock logic as a pure Python module (app/lock.py) behind POST /analysis
  - Zone = pixel rectangle sent with every analysis request (stateless server)
  - Timeline drawn on one canvas from merged segments
  - Entities: Zone, LockPeriod, Segment
- **Open Questions Resolved This Session**:
  - AQ-8 — server-side pure Python
  - AQ-9 — original video pixels, top-left origin
  - AQ-10 — single canvas bar, min 1 px segments
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Requirement Analysis — US-3, US-4 lock zone analysis

- **Status**: Approved
- **Stage**: Requirement Analysis
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/design/DESIGN.md
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - US-3: lock zone + every continuous lock period
  - US-4: timeline of locked/unlocked periods + longest lock
  - NFR: lock-duration logic tested with generated box sequences with known answers
  - Out of scope this round: loss detection and re-selection
- **Open Questions Resolved This Session**:
  - OQ-9 — whole box inside the zone, borders inclusive
  - OQ-10 — rectangle, default 25–75% × 10–90%, user can redraw
  - OQ-11 — no minimum duration
  - OQ-12 — start = first/fps, end = (last+1)/fps, duration = frames/fps
  - OQ-13 — states: locked, tracked-not-locked, lost, not tracked
  - OQ-14 — tie → earliest period
  - OQ-15 — timeline and table rows seek the video
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

### Implementation — US-2 Track the target through the video

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-21
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md, docs/design/DESIGN.md, docs/architecture/ARCHITECTURE.md
- **Requested By**: Aras Yiğitalp Koşmaz
- **Decisions / Scope Covered**:
  - US-2 implemented on `feature/target-tracking`
  - Red: 30 passed, 1 warning, 3 errors in 2.63s
  - Green: 56 passed, 1 warning in 66.25s (0:01:06)
- **Open Questions Resolved This Session**:
  - IQ-3 — Only `opencv-contrib-python-headless==4.10.0.84` in a fresh virtual environment (README warns not to mix OpenCV packages).
  - IQ-4 — `requestVideoFrameCallback` mediaTime (fallback currentTime), `floor(t·fps + 1e-4)`; seeks go to the middle of the frame.
- **Approved By**: Aras Yiğitalp Koşmaz
- **Approval Date**: 2026-11-21

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

