# Implementation Log

Append one entry per implementation pass (one story per pass), **most recent first**. Never edit or delete a previous pass's entry — this file is a traceable history, not a living document.

---

## Pass: `2026-11-21` — US-`2` `Track the target through the video`

**Branch:** `feature/target-tracking`
**Traces to:** `docs/design/DESIGN.md` (US-2), `docs/architecture/ARCHITECTURE.md` (entities/decisions: Box, FrameState, TrackRun; decisions: default tracker, tracking resolution, run model, time→frame mapping)
**Approval basis:** Requirement Analysis entry approved `2026-11-21`; Solution Architecture entry approved `2026-11-21` (see `docs/APPROVAL_LOG.md`)

### Red / Green Evidence

- **Red** (tests committed before production code, `python -m pytest --continue-on-collection-errors -m "not perf"`): `30 passed, 1 warning, 3 errors in 2.63s` — exit code 1.
- Failing: `tests/test_api_tracking.py`, `tests/test_performance.py`, `tests/test_tracking_core.py`
- **Green** (after the implementation commit, `python -m pytest`): `56 passed, 1 warning in 66.25s (0:01:06)` — exit code 0. The tests were not modified between red and green.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Box on every frame | ✅ Pass | test_tracking_core.py::test_tracker_follows_target_on_every_frame[KCF\|CSRT] (IoU ≥ 0.5 every frame), test_api_tracking.py::test_tracking_returns_a_box_for_every_frame, ::test_tracking_result_is_kept_on_the_video; overlay checked manually in the browser |
| Choose a tracker | ✅ Pass | test_api_tracking.py::test_tracker_list_endpoint, test_tracking_core.py (KCF and CSRT runs) |
| Invalid selection is refused | ✅ Pass | test_api_tracking.py::test_invalid_tracking_requests_give_clear_errors (7 cases), test_tracking_core.py::test_init_box_outside_frame_is_rejected, ::test_init_box_minimum_size, ::test_unknown_tracker_is_rejected, ::test_start_frame_past_end_is_rejected |
| Tracking twice at the same time is refused | ✅ Pass | test_api_tracking.py::test_tracking_while_already_running_is_refused |
| Performance budget | ✅ Pass | test_performance.py::test_30s_720p_video_tracks_within_budget (KCF: 900 frames of 1280×720 in ≈ 10 s) |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `Box.w / Box.h` | > 0 and initial box ≥ 4×4 px (4 accepted, 3.9 and 3 rejected) | test_tracking_core.py::test_init_box_minimum_size |
| `Initial box` | inside frame, touching edge allowed (−1 / 321 / 241 rejected) | ::test_init_box_outside_frame_is_rejected, ::test_init_box_touching_frame_edges_is_accepted |
| `Box units` | original pixels even when tracked at reduced width | ::test_downscaled_tracking_returns_boxes_in_original_pixels |
| `TrackRun.states` | start at start_frame, consecutive | ::test_tracking_can_start_mid_video |
| `Concurrency` | second run on same video → 409 | test_api_tracking.py::test_tracking_while_already_running_is_refused |

### Open Questions Raised This Pass

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-3 | The machine had both `opencv-python` and `opencv-python-headless` installed globally, and the plain packages may lack CSRT/KCF. Which package do we depend on? | Resolved | Only `opencv-contrib-python-headless==4.10.0.84` in a fresh virtual environment (README warns not to mix OpenCV packages). |
| IQ-4 | How does the browser know which frame it is showing, to draw the right box? | Resolved | `requestVideoFrameCallback` mediaTime (fallback currentTime), `floor(t·fps + 1e-4)`; seeks go to the middle of the frame. |

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Version Control Actions

- Branch: `feature/target-tracking`
- Commits: `test(tracking): add failing acceptance tests for US-2`; `feat(tracking): track target with OpenCV and overlay boxes`; `docs(implementation): log US-2 implementation pass`; `docs(approval): approve US-2 implementation`
- PR: `feature/target-tracking` → `main` (merge commit, so the red and green commits stay visible in history)

---

## Pass: `2026-11-21` — US-`1` `Upload a video and select the target`

**Branch:** `feature/video-upload-target-selection`
**Traces to:** `docs/design/DESIGN.md` (US-1), `docs/architecture/ARCHITECTURE.md` (entities/decisions: VideoInfo, VideoSession; decisions: framework, H.264 check, storage, frame-exact access)
**Approval basis:** Requirement Analysis entry approved `2026-11-21`; Solution Architecture entry approved `2026-11-21` (see `docs/APPROVAL_LOG.md`)

### Red / Green Evidence

- **Red** (tests committed before production code, `python -m pytest --continue-on-collection-errors -m "not perf"`): `collection aborted — ImportError while loading conftest (ModuleNotFoundError: No module named 'app')` — exit code 4.
- **Green** (after the implementation commit, `python -m pytest`): `30 passed, 1 warning in 6.73s` — exit code 0. The tests were not modified between red and green.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Valid H.264 MP4 is accepted | ✅ Pass | test_video.py::test_valid_h264_mp4_reports_metadata, test_api_upload.py::test_upload_valid_video_returns_metadata, ::test_first_frame_is_served_as_jpeg |
| Draw a box on the first frame | ✅ Pass | Manual UI check (canvas drag → box, size shown, button enabled); frame served by ::test_first_frame_is_served_as_jpeg |
| Box that is too small is refused | ✅ Pass | Manual UI check ("Box too small" message, button disabled); server-side rule tested in US-2 |
| The box cannot leave the frame | ✅ Pass | Manual UI check (drag clamped by clampPoint) |
| Wrong file extension is rejected | ✅ Pass | test_video.py::test_non_mp4_extensions_are_rejected, test_api_upload.py::test_upload_wrong_extension_gives_clear_error |
| MP4 with a codec other than H.264 is rejected | ✅ Pass | test_video.py::test_mpeg4_codec_in_mp4_container_is_rejected, test_api_upload.py::test_upload_non_h264_gives_clear_error |
| Corrupt, empty or truncated file is rejected | ✅ Pass | test_video.py::test_non_video_file_named_mp4_is_rejected, ::test_empty_file_is_rejected, ::test_truncated_mp4_is_rejected, test_api_upload.py::test_upload_garbage_mp4_gives_clear_error, ::test_rejected_upload_is_not_kept_on_disk |
| File larger than the upload limit is rejected | ✅ Pass | Inspection of main.upload (streams in 1 MB chunks, 413 above MAX_UPLOAD_BYTES); not automated to avoid writing 500 MB in tests |
| Unknown video | ✅ Pass | test_api_upload.py::test_unknown_video_id_is_404_with_message |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `VideoInfo` | exists only after ftyp + FourCC + first-frame checks | test_video.py (5 rejection tests) |
| `VideoSession.frame index` | 0..frame_count-1; −1 and frame_count → 400 | test_api_upload.py::test_frame_index_boundaries (74 / 75 / −1) |
| `read_frame` | returns exactly frame i (same pixels as sequential decode) | test_video.py::test_read_frame_returns_the_exact_requested_frame |
| `Rejected upload` | leaves no file on disk | test_api_upload.py::test_rejected_upload_is_not_kept_on_disk |

### Open Questions Raised This Pass

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-1 | How do we get H.264 test videos without committing video files (task: test videos < 5 MB, never commit large videos)? | Resolved | Generate them at test time with imageio-ffmpeg (bundled FFmpeg with libx264) into pytest's temp folder (`tests/videogen.py`). |
| IQ-2 | FastAPI returns HTTP 422 with a nested JSON error for invalid requests. Is that a "clear error message"? | Resolved | No. A custom handler returns HTTP 400 with one readable sentence, e.g. `Invalid request — file: Field required`. |

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Version Control Actions

- Branch: `feature/video-upload-target-selection`
- Commits: `test(upload): add failing acceptance tests for US-1`; `feat(upload): validate MP4/H.264 uploads and select target`; `docs(implementation): log US-1 implementation pass`; `docs(approval): approve US-1 implementation`
- PR: `feature/video-upload-target-selection` → `main` (merge commit, so the red and green commits stay visible in history)
