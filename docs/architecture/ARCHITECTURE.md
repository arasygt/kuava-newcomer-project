# Architecture Atlas

Central index of solution-architect output for this repository. Only requirements `Approved` (Stage: Requirement Analysis) in [docs/APPROVAL_LOG.md](../APPROVAL_LOG.md) may be modeled here (see [solution-architect SKILL.md](../../.claude/skills/solution-architect/SKILL.md)). Individual sessions may split their work into `ARCHITECTURE_<commit-id>.md` files when this file grows too large; every such file must be listed below.

## Linked Architecture Documents

| File | Scope / Topic | Started (commit) | Status |
|---|---|---|---|
| (this file) | Core | — | Active |

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

## Open Questions

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| AQ-1 | Which language/framework should the app use, given "one command to run" and OpenCV trackers? | solution-architect | Resolved | Python 3.12 + FastAPI + vanilla JS (see decision matrix). |
| AQ-2 | Should uploads and results be persisted across server restarts? | solution-architect | Resolved | No. Uploads go to git-ignored `data/uploads/`; results are kept in memory. |
| AQ-3 | How do we guarantee that the frame shown for selection is exactly the frame the tracker starts on? | solution-architect | Resolved | Sequential decode with `grab()` instead of `CAP_PROP_POS_FRAMES` seeking. |
| AQ-4 | How do we detect H.264 without requiring FFmpeg on the user's machine? | solution-architect | Resolved | `ftyp` magic + OpenCV FourCC (`avc1/avc3/h264/x264`) + decode of the first frame. |
