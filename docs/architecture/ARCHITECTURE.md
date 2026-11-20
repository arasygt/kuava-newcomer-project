# Architecture Atlas

Central index of solution-architect output for this repository. Only requirements `Approved` (Stage: Requirement Analysis) in [docs/APPROVAL_LOG.md](../APPROVAL_LOG.md) may be modeled here (see [solution-architect SKILL.md](../../.claude/skills/solution-architect/SKILL.md)). Individual sessions may split their work into `ARCHITECTURE_<commit-id>.md` files when this file grows too large; every such file must be listed below.

## Linked Architecture Documents

| File | Scope / Topic | Started (commit) | Status |
|---|---|---|---|
| (this file) | Core | — | Active |

## System Overview

```
Browser (vanilla JS SPA)                     Python server (FastAPI, uvicorn)
┌──────────────────────────┐   HTTP/JSON    ┌───────────────────────────────────────┐
│ upload / select / play   │ ─────────────▶ │ app/main.py     REST API + static     │
│ <video> + <canvas> overlay│ ◀───────────── │ app/video.py    validation, frames    │
│ timeline <canvas>, tables │   boxes/frame  │ app/tracking.py OpenCV trackers, loss │
└──────────────────────────┘                │ app/lock.py     lock zone logic (pure)│
                                            │ app/store.py    in-memory sessions    │
                                            └───────────────────────────────────────┘
```

The server decodes the video with OpenCV (FFmpeg backend), runs the tracker once, keeps one `FrameState` per frame in memory, and sends the boxes to the browser. The browser never re-encodes video: it plays the original MP4 and draws the boxes on a canvas over it.

## Data Models

### Entity: VideoInfo
Traces to: US-1 (docs/design/DESIGN.md)

| Field | Type | Unit | Constraints |
|---|---|---|---|
| width | int | px | > 0 |
| height | int | px | > 0 |
| fps | float | frames/s | > 0, rounded to 4 decimals |
| frame_count | int | frames | > 0 (from the MP4 container) |
| duration | float | s | = frame_count / fps |
| codec | str | — | FourCC reported by FFmpeg; must be one of `avc1`, `avc3`, `h264`, `x264` (case-insensitive) |

**Invariants** (must always hold true):
- A `VideoInfo` exists only for a file that passed all checks: non-empty, bytes 4..8 equal `ftyp`, opened by OpenCV, H.264 FourCC, first frame decodable.
- `duration == frame_count / fps` (to 4 decimals).

**Boundary Behavior:**
- Min/Max: file size 1 byte .. 500 MB (`MAX_UPLOAD_BYTES`); 500 MB + 1 byte is rejected with HTTP 413 while streaming, before probing.
- Empty/Null/Zero: empty file → "The uploaded file is empty."; fps, frame count, width or height of 0 → "The video has no readable frames."
- Overflow/Truncation: a truncated MP4 (header present, data missing) fails to open or to decode the first frame → rejected.

**Concurrency / Race-Scenario Analysis:**
- Two uploads at the same time → each gets its own `uuid4` id and file path; no shared state except the store dict, which is guarded by a lock.

### Entity: VideoSession
Traces to: US-1 (docs/design/DESIGN.md)

| Field | Type | Unit | Constraints |
|---|---|---|---|
| id | str | — | 32 hex chars (uuid4) |
| path | Path | — | `data/uploads/<id>.mp4`, git-ignored |
| filename | str | — | original name, display only |
| info | VideoInfo | — | required |

**Invariants** (must always hold true):
- A session is only added to the store after validation succeeded; a rejected upload leaves no file on disk.

**Boundary Behavior:**
- Min/Max: frame request index must be in `0 .. frame_count-1`; −1 and `frame_count` return HTTP 400.
- Empty/Null/Zero: unknown id → HTTP 404 "Video not found. Please upload it again."
- Overflow/Truncation: sessions live in memory only; restarting the server forgets them (the UI asks to upload again).

**Concurrency / Race-Scenario Analysis:**
- Reading frames concurrently → every request opens its own `cv2.VideoCapture`, so no capture object is shared between threads.

### Entity: Box
Traces to: US-2 (docs/design/DESIGN.md)

| Field | Type | Unit | Constraints |
|---|---|---|---|
| x | float | px (original video) | top-left corner |
| y | float | px (original video) | top-left corner |
| w | float | px | > 0 |
| h | float | px | > 0 |

**Invariants** (must always hold true):
- `w > 0 and h > 0` (constructor raises `ValueError` otherwise).
- All boxes stored or sent to the browser are in original video pixels, even when tracking ran on a downscaled frame.

**Boundary Behavior:**
- Min/Max: the initial box must satisfy `x >= 0, y >= 0, x+w <= width, y+h <= height` (touching the frame edge is allowed) and `w >= 4, h >= 4`; 3.9 px is rejected.
- Empty/Null/Zero: `w == 0` or `h == 0` → rejected (HTTP 400 from request validation).
- Overflow/Truncation: tracker boxes are rounded to 0.1 px.

**Concurrency / Race-Scenario Analysis:**
- Immutable (frozen dataclass), safe to share between threads.

### Entity: FrameState
Traces to: US-2 (docs/design/DESIGN.md)

| Field | Type | Unit | Constraints |
|---|---|---|---|
| frame | int | frame index | 0 .. frame_count-1 |
| status | str | — | `tracked` \| `lost` \| `untracked` |
| box | Box \| None | — | required when `tracked`, None otherwise |

**Invariants** (must always hold true):
- `status == "tracked"` ⇔ `box is not None`.
- A session always holds exactly `frame_count` states, index i has `frame == i`.

**Boundary Behavior:**
- Min/Max: frames beyond the container's frame count are ignored.
- Empty/Null/Zero: before any tracking, all states are `untracked`.
- Overflow/Truncation: if the decoder returns fewer frames than the container says, the remaining states stay `untracked`.

**Concurrency / Race-Scenario Analysis:**
- States are replaced only inside the tracking request that holds the session lock.

### Entity: TrackRun
Traces to: US-2 (docs/design/DESIGN.md)

| Field | Type | Unit | Constraints |
|---|---|---|---|
| tracker | str | — | one of `CSRT`, `KCF`, `MIL` |
| start_frame | int | frame index | 0 .. frame_count-1 |
| states | list[FrameState] | — | consecutive frames starting at `start_frame` |
| elapsed_s | float | s | ≥ 0, wall-clock time of the run |

**Invariants** (must always hold true):
- `states[0].frame == start_frame`, `states[0].box == init_box`, frames are consecutive.

**Boundary Behavior:**
- Min/Max: `start_frame == frame_count` or more → HTTP 400; `start_frame < 0` → HTTP 400.
- Empty/Null/Zero: a 1-frame video yields a run with exactly one state.
- Overflow/Truncation: frames wider than 640 px are downscaled for tracking only.

**Concurrency / Race-Scenario Analysis:**
- Two tracking requests for the same video → the second one gets HTTP 409 "Tracking is already running for this video." (non-blocking `threading.Lock.acquire`). Requests for different videos run in parallel in FastAPI's thread pool.

### Entity: Zone
Traces to: US-3 (docs/design/DESIGN.md)

Same fields as `Box` (x, y, w, h in original video pixels).

**Invariants** (must always hold true):
- The zone lies inside the frame: `x >= 0, y >= 0, x+w <= width, y+h <= height`.
- A box is inside the zone ⇔ `box.x >= z.x and box.y >= z.y and box.x+box.w <= z.x+z.w and box.y+box.h <= z.y+z.h`.

**Boundary Behavior:**
- Min/Max: zone equal to the full frame is accepted; one pixel outside (x = −1 or w = width+1) → HTTP 400. Box exactly on the zone border → inside; 1 px or 0.001 px beyond → outside.
- Empty/Null/Zero: zero width/height or a missing field → HTTP 400. The UI refuses zones smaller than 8×8 px.
- Overflow/Truncation: the UI rounds zone coordinates to whole pixels.

**Concurrency / Race-Scenario Analysis:**
- The zone is not stored on the server; every analysis request carries it, so two browser tabs with different zones cannot interfere.

### Entity: LockPeriod
Traces to: US-3 (docs/design/DESIGN.md)

| Field | Type | Unit | Constraints |
|---|---|---|---|
| start_frame | int | frame index | first locked frame |
| end_frame | int | frame index | last locked frame, ≥ start_frame |
| frames | int | frames | = end_frame − start_frame + 1 ≥ 1 |
| start_time | float | s | = start_frame / fps |
| end_time | float | s | = (end_frame + 1) / fps |
| duration | float | s | = frames / fps |

**Invariants** (must always hold true):
- Every frame in a period is `tracked` with its box inside the zone; the frames just before and after are not.
- Periods never overlap and are sorted by start frame.

**Boundary Behavior:**
- Min/Max: a 1-frame lock is a period of duration 1/fps; a fully locked video is one period from 0 to frame_count−1.
- Empty/Null/Zero: no locked frame → empty list; empty state list → empty list; fps ≤ 0 → `ValueError`.
- Overflow/Truncation: times are rounded to 4 decimals only in the JSON output.

**Concurrency / Race-Scenario Analysis:**
- Computed on demand from the current states (pure function); no cached result can become stale.

### Entity: Segment (timeline)
Traces to: US-4 (docs/design/DESIGN.md)

| Field | Type | Unit | Constraints |
|---|---|---|---|
| state | str | — | `locked` \| `unlocked` \| `lost` \| `untracked` |
| start_frame | int | frame index | ≥ 0 |
| end_frame | int | frame index | ≥ start_frame |
| start_time / end_time | float | s | start_frame/fps, (end_frame+1)/fps |

**Invariants** (must always hold true):
- Segments cover every frame exactly once, in order; two neighbouring segments never have the same state.
- The `locked` segments are exactly the lock periods of US-3.
- `longest` is the lock period with the most frames; on a tie, the earliest.

**Boundary Behavior:**
- Min/Max: a fully untracked video is a single `untracked` segment 0..frame_count−1.
- Empty/Null/Zero: empty state list → empty timeline; no lock → `longest = null`.
- Overflow/Truncation: segments narrower than one pixel are drawn 1 px wide in the UI so single lost frames stay visible.

**Concurrency / Race-Scenario Analysis:**
- Same as LockPeriod (pure function of states + zone).

### Entity: LossRule
Traces to: US-5 (docs/design/DESIGN.md)

| Field | Type | Unit | Constraints |
|---|---|---|---|
| AREA_CHANGE_LIMIT | float | ratio | 0.5 |
| lost_frame | int \| None | frame index | first frame where a rule fired |
| lost_reason | str \| None | — | `tracker_failure` \| `area_change` |

**Invariants** (must always hold true):
- Lost on frame t ⇔ tracker returned `ok == False`, or no box, or `w <= 0 or h <= 0`, or `|A_t − A_{t−1}| / A_{t−1} > 0.5`, where A_{t−1} is the area of the last tracked box.
- When a run is lost on frame t: `states[t].status == "lost"`, the run stops, and the session marks frames t+1.. as `untracked`.
- Re-selection at frame F replaces the session's states from F onwards and keeps states before F.

**Boundary Behavior:**
- Min/Max: with A_{t−1} = 100: 150 and 50 → tracked; 150.01 and 49.99 → lost.
- Empty/Null/Zero: a box of zero width/height counts as tracker failure (no division by zero is possible because A_{t−1} > 0 by the Box invariant).
- Overflow/Truncation: the ratio is computed in original pixels; it is scale-invariant, so downscaled tracking gives the same decision.

**Concurrency / Race-Scenario Analysis:**
- Re-selection while a run is active → HTTP 409 (same session lock as US-2).

## Technology / Design Decisions

### Decision: Language and framework

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Python + FastAPI backend, vanilla JS frontend | OpenCV's trackers are first-class in Python; FastAPI gives typed request validation and TestClient for tests; no frontend build step, so one command starts the app | Two languages; the UI is hand-written without a component framework | ✅ |
| Python + Streamlit | Very little UI code | Hard to draw boxes on a playing video and to sync a canvas with frames; reruns the whole script on every interaction | ❌ |
| Node.js + opencv.js in the browser | Single language, no server | opencv.js has no contrib trackers (CSRT/KCF) by default and is slow on 720p; browser decoding is not frame-exact | ❌ |
| React/Vite frontend + FastAPI | Better structure for a large UI | Extra build tooling and `npm install` break the "one command" requirement for a small UI | ❌ |

**Why Python + FastAPI + vanilla JS:** the hard part (tracking) lives in OpenCV-Python, and the UI is one page.
**Why not Streamlit:** it cannot overlay per-frame boxes on a normal video player.
**Why not opencv.js:** missing trackers and too slow for the 60 s budget.
**Why not React:** the build step adds setup cost without benefit for one page.

### Decision: How to check that a file is an H.264 MP4

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| `ftyp` magic bytes + OpenCV FourCC + decode first frame | No extra dependency; checks the container, the codec and that it really decodes | FourCC naming differs between builds (`avc1`/`h264`), so a set of names is accepted | ✅ |
| ffprobe (FFmpeg CLI) | Most detailed stream information | Requires FFmpeg installed on every laptop; harder setup | ❌ |
| Extension check only | Trivial | Accepts renamed or corrupt files, which would crash later | ❌ |

**Why magic + FourCC + decode:** it catches renamed, corrupt, truncated and wrong-codec files with what OpenCV already provides.
**Why not ffprobe:** an extra system dependency for the user.
**Why not extension only:** violates "invalid input never crashes the app".

### Decision: Storage of uploads and results

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Files in `data/uploads/` (git-ignored) + results in memory | Simple; nothing to install; videos never land in the repo | Results are lost when the server restarts | ✅ |
| SQLite database | Results survive restarts | Schema and migrations for a single-user local tool | ❌ |

**Why files + memory:** a local single-user tool; re-tracking a 30 s clip takes seconds.
**Why not SQLite:** persistence is not a requirement and adds code.

### Decision: Frame-exact access

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Decode sequentially and `grab()` up to the frame | Always the exact frame, same decoder as tracking | Slower for frames late in long videos (decodes everything before) | ✅ |
| `CAP_PROP_POS_FRAMES` seek | Fast | Not guaranteed frame-exact for H.264 (seeks to key frames); the selection frame could differ from the tracked frame | ❌ |

**Why sequential grab:** the box the user draws must be on exactly the frame the tracker starts on.
**Why not POS_FRAMES:** off-by-some-frames errors are silent and break the box position.

### Decision: Default tracker

Measured on the development laptop (2 CPU cores), 320×240 synthetic clip: CSRT ≈ 40–50 ms/frame, MIL ≈ 120 ms/frame, KCF ≈ 4 ms/frame. A 30 s 720p clip has 900 frames.

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| KCF default, CSRT and MIL selectable | 900 frames of 720p in ≈ 10 s, well within 60 s; reports failure reliably when the target disappears | Fixed box size (no scale change); can drift on fast motion | ✅ |
| CSRT default | Most accurate, follows scale changes | ≈ 40–50 s for 900 frames on a 2-core laptop, too close to the 60 s budget; rarely reports failure | ❌ |
| MIL default | Robust to partial occlusion | Slowest (> 100 s for 900 frames) | ❌ |

**Why KCF:** it is the only one that meets the performance budget with a margin; the user can still choose CSRT when accuracy matters more than speed.
**Why not CSRT:** it does not reliably meet the 60 s budget on a normal laptop.
**Why not MIL:** far over the budget.

### Decision: Tracking resolution

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Downscale frames wider than 640 px for tracking, scale boxes back | 720p → 640×360 is ~4× fewer pixels; faster resize-friendly trackers | Small targets (< 8 px after scaling) lose detail | ✅ |
| Track at full resolution | Best detail | Slower; risks the budget with CSRT | ❌ |

**Why downscale to 640:** speed with no visible accuracy loss on targets of normal size.
**Why not full resolution:** no benefit for typical target sizes and costs time.

### Decision: Run model and transport of results

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Synchronous `POST /track` (thread pool), boxes returned as JSON, drawn on a canvas over `<video>` | Simple; no job queue; follows the task tip (no re-encoding) | The HTTP request is open during tracking (≤ 60 s by the budget) | ✅ |
| Background job + polling/WebSocket progress | Progress bar for long videos | Job state, cancellation and more tests | ❌ |
| Render an annotated video on the server | Works in any player | Slow encoding, large files, codec issues | ❌ |

**Why synchronous + overlay:** the budget keeps requests short and the overlay avoids encoding entirely.
**Why not background jobs:** complexity without a requirement for it.
**Why not annotated video:** the task explicitly suggests the overlay instead.

### Decision: Mapping video time to frame index in the browser

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| `requestVideoFrameCallback` mediaTime (fallback `currentTime`), `frame = floor(t·fps + 1e-4)`; seeks go to the middle of the frame | Updates exactly once per displayed frame; mid-frame seeking avoids rounding to the previous frame | Assumes constant frame rate | ✅ |
| `timeupdate` event | Supported everywhere | Fires only ~4 times per second, box lags behind | ❌ |

**Why rVFC:** box stays in sync with every displayed frame.
**Why not timeupdate:** too coarse.

### Decision: Where the lock logic runs

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Pure Python module `app/lock.py` on the server, called by `POST /analysis` | Testable with generated sequences (task NFR); single source of truth | A request per zone change (cheap: ~1 ms for 900 frames) | ✅ |
| Compute in browser JavaScript | Instant feedback | Would need a JS test setup; logic duplicated if the server also needs it | ❌ |

**Why server-side pure Python:** the lock-duration logic must be unit-tested with known answers; pure functions make that easy.
**Why not browser JS:** duplicate logic and a second test stack. (The browser only colours the current box locked/unlocked for display.)

### Decision: Representation of the lock zone

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Axis-aligned rectangle in video pixels, sent with each analysis request | Matches the competition's rectangular target area; stateless server | Cannot express non-rectangular zones | ✅ |
| Polygon zone | Any shape | Point-in-polygon for boxes, more UI | ❌ |
| Normalised coordinates (0..1) | Resolution-independent | Needs conversion everywhere; boxes are in pixels | ❌ |

**Why pixel rectangle:** simplest rule that matches the requirement.
**Why not polygon:** no requirement for it.
**Why not normalised:** every other quantity is in pixels.

### Decision: Timeline rendering

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Single `<canvas>` bar drawn from server segments | Handles thousands of frames fast; easy to outline the longest lock | Needs manual click → frame mapping | ✅ |
| One DOM element per segment | Easy styling and hover | Thousands of elements for flickering states; slower | ❌ |
| Chart library (Chart.js) | Axes and tooltips for free | Extra dependency for one bar | ❌ |

**Why canvas:** fast, dependency-free, consistent with the video overlay.
**Why not DOM segments:** poor performance on long, noisy timelines.
**Why not a chart library:** unnecessary dependency.

### Decision: Behaviour after a loss

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Stop at the loss frame; user re-selects on any frame; keep earlier results | Never shows boxes known to be unreliable; matches "let the user select the target again" | User must act after every loss | ✅ |
| Keep tracking and only flag the loss | No user action | Following frames are probably wrong and would count as locks | ❌ |
| Automatic re-detection | No user action | Needs a detector (bonus feature, out of scope) | ❌ |

**Why stop:** correctness of lock times matters more than convenience.
**Why not continue:** produces false locks.
**Why not auto re-detection:** out of scope for the core requirements.

## Non-Functional Requirements Mapping

| NFR | How it is met | Verified by |
|---|---|---|
| 30 s 720p processed in < 60 s on a laptop CPU | KCF default + 640 px tracking width (≈ 10 s measured) | `tests/test_performance.py` |
| Lock logic tested with generated sequences with known answers | `app/lock.py` is pure; tests build sequences from run lengths | `tests/test_lock_periods.py`, `tests/test_timeline.py` |
| Large videos never committed; test videos < 5 MB | Test videos are generated into a temp folder at test time; `data/` and `*.mp4` are git-ignored | `.gitignore`, `tests/videogen.py` |
| One command to run, one command to test | `python run.py`, `python -m pytest` | README |
| Invalid input never crashes the app | Validation in `video.py`, request models, 400/404/409/413 handlers and a catch-all 500 handler with a message | `tests/test_api_*.py` |

## Open Questions

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| AQ-1 | Which language/framework should the app use, given "one command to run" and OpenCV trackers? | solution-architect | Resolved | Python 3.12 + FastAPI + vanilla JS (see decision matrix). |
| AQ-2 | Should uploads and results be persisted across server restarts? | solution-architect | Resolved | No. Uploads go to git-ignored `data/uploads/`; results are kept in memory. |
| AQ-3 | How do we guarantee that the frame shown for selection is exactly the frame the tracker starts on? | solution-architect | Resolved | Sequential decode with `grab()` instead of `CAP_PROP_POS_FRAMES` seeking. |
| AQ-4 | How do we detect H.264 without requiring FFmpeg on the user's machine? | solution-architect | Resolved | `ftyp` magic + OpenCV FourCC (`avc1/avc3/h264/x264`) + decode of the first frame. |
| AQ-5 | Should tracking run in a background job with progress, or in the request? | solution-architect | Resolved | In the request (thread pool). The 60 s budget keeps it short; concurrent runs on the same video get HTTP 409. |
| AQ-6 | Which tracker is the default, given the performance budget? | solution-architect | Resolved | KCF (≈ 10 s for 30 s 720p on the dev laptop). CSRT/MIL stay selectable. |
| AQ-7 | Should frames be downscaled for tracking, and to what size? | solution-architect | Resolved | Yes, to a maximum width of 640 px; boxes are scaled back to original pixels. |
| AQ-8 | Should the lock logic run in the browser or on the server? | solution-architect | Resolved | Server, as a pure Python module, so it can be tested with generated sequences. |
| AQ-9 | Which coordinate system do boxes and zones use? | solution-architect | Resolved | Original video pixels, origin top-left, floats. |
| AQ-10 | How should a timeline with thousands of frames be drawn efficiently? | solution-architect | Resolved | One canvas bar from merged segments; segments < 1 px are drawn 1 px wide. |
| AQ-11 | Is the area-change ratio affected by tracking on downscaled frames? | solution-architect | Resolved | No: the ratio is scale-invariant. It is computed on boxes converted back to original pixels against the previous tracked box. |
