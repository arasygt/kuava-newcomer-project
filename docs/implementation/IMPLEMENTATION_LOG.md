# Implementation Log

Append one entry per implementation pass (one story per pass), **most recent first**. Never edit or delete a previous pass's entry — this file is a traceable history, not a living document.

---

## Pass: `2026-11-21` — US-`4` `See a lock timeline and the longest lock`

**Branch:** `feature/lock-timeline`
**Traces to:** `docs/design/DESIGN.md` (US-4), `docs/architecture/ARCHITECTURE.md` (entities/decisions: Segment; decision: canvas timeline)
**Approval basis:** Requirement Analysis entry approved `2026-11-21`; Solution Architecture entry approved `2026-11-21` (see `docs/APPROVAL_LOG.md`)

### Red / Green Evidence

- **Red** (tests committed before production code, `python -m pytest --continue-on-collection-errors -m "not perf"`): `3 failed, 105 passed, 1 deselected, 1 warning, 1 error in 13.14s` — exit code 1.
- Failing: `test_timeline_and_longest_lock`, `test_timeline_covers_whole_video_before_tracking`, `test_no_lock_means_no_longest`, `tests/test_timeline.py`
- **Green** (after the implementation commit, `python -m pytest`): `117 passed, 1 warning in 58.16s` — exit code 0. The tests were not modified between red and green.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Timeline covers the whole video | ✅ Pass | test_timeline.py::test_timeline_segments_cover_every_frame_in_order, test_api_timeline.py::test_timeline_and_longest_lock, ::test_timeline_covers_whole_video_before_tracking |
| Longest lock is highlighted | ✅ Pass | test_timeline.py::test_longest_period_is_selected; outline/star checked manually in the browser |
| Tie for the longest lock | ✅ Pass | test_timeline.py::test_longest_boundaries[4-2\|5-2\|6-8] |
| No lock at all | ✅ Pass | test_timeline.py::test_no_lock_means_no_longest, test_api_timeline.py::test_no_lock_means_no_longest |
| Jump from the timeline | ✅ Pass | Manual UI check (timeline click and table row click seek the video) |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `Segment coverage` | every frame exactly once, neighbours differ | test_timeline.py::test_timeline_segments_cover_every_frame_in_order |
| `Longest` | most frames; tie → earliest (L−1 / L / L+1 frames) | ::test_longest_boundaries |
| `Empty input` | empty timeline, longest null | ::test_empty_sequence_has_empty_timeline, ::test_no_lock_means_no_longest |

### Open Questions Raised This Pass

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-6 | Once `timeline()` exists, should `lock_periods()` keep its own loop? | Resolved | No. `lock_periods()` is now derived from the `locked` timeline segments, so both always agree (refactor step; US-3 tests unchanged and still green). |

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Version Control Actions

- Branch: `feature/lock-timeline`
- Commits: `test(timeline): add failing acceptance tests for US-4`; `feat(timeline): add lock timeline and longest lock`; `docs(implementation): log US-4 implementation pass`; `docs(approval): approve US-4 implementation`
- PR: `feature/lock-timeline` → `main` (merge commit, so the red and green commits stay visible in history)

---

## Pass: `2026-11-21` — US-`3` `Define a lock zone and report every lock period`

**Branch:** `feature/lock-zone-periods`
**Traces to:** `docs/design/DESIGN.md` (US-3), `docs/architecture/ARCHITECTURE.md` (entities/decisions: Zone, LockPeriod; decisions: lock logic on the server, pixel rectangle zone)
**Approval basis:** Requirement Analysis entry approved `2026-11-21`; Solution Architecture entry approved `2026-11-21` (see `docs/APPROVAL_LOG.md`)

### Red / Green Evidence

- **Red** (tests committed before production code, `python -m pytest --continue-on-collection-errors -m "not perf"`): `9 failed, 55 passed, 1 deselected, 1 warning, 1 error in 14.99s` — exit code 1.
- Failing: `test_analysis_reports_every_lock_period`, `test_analysis_changes_when_zone_changes`, `test_invalid_zone_gives_clear_error[zone0]`, `test_invalid_zone_gives_clear_error[zone1]`, `test_invalid_zone_gives_clear_error[zone2]`, `test_invalid_zone_gives_clear_error[zone3]`, `test_zone_equal_to_full_frame_is_accepted`, `test_analysis_unknown_video_is_404` (+2 more)
- **Green** (after the implementation commit, `python -m pytest`): `106 passed, 1 warning in 54.14s` — exit code 0. The tests were not modified between red and green.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Default lock zone | ✅ Pass | Manual UI check (dashed rectangle 25–75% × 10–90%); app.js defaultZone |
| User draws a new zone | ✅ Pass | test_api_lock.py::test_analysis_changes_when_zone_changes; drawing checked manually in the browser |
| Locked frame | ✅ Pass | test_lock_periods.py::test_box_inside_zone_boundaries (9 boundary cases), ::test_missing_box_is_never_inside |
| Every continuous lock period is reported | ✅ Pass | test_lock_periods.py::test_single_period_frames_and_times, ::test_multiple_periods_are_reported_separately, ::test_random_generated_sequences_match_known_answer[0-19], test_api_lock.py::test_analysis_reports_every_lock_period, ::test_end_to_end_lock_period_matches_ground_truth |
| Lost or untracked frames are never locked | ✅ Pass | test_lock_periods.py::test_lost_frame_breaks_a_lock_period, ::test_untracked_frames_are_never_locked |
| Invalid zone is rejected | ✅ Pass | test_api_lock.py::test_invalid_zone_gives_clear_error (4 cases), ::test_zone_equal_to_full_frame_is_accepted |
| Invalid fps is rejected by the lock logic | ✅ Pass | test_lock_periods.py::test_non_positive_fps_is_rejected[0\|-25] |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `Zone inside rule` | borders inclusive; 1 px and 0.001 px outside → not locked | test_lock_periods.py::test_box_inside_zone_boundaries |
| `LockPeriod.duration` | frames / fps; single frame = 1/fps | ::test_single_frame_lock_lasts_one_frame_period |
| `LockPeriod list` | matches run lengths of generated sequences (known answers) | ::test_random_generated_sequences_match_known_answer |
| `Box invariant` | w, h > 0 | ::test_box_rejects_zero_or_negative_size |

### Open Questions Raised This Pass

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-5 | How can API tests check exact lock periods when a real tracker's boxes jitter by a pixel or two? | Resolved | Inject a known per-frame state sequence into the session (`set_states` helper) for exact answers, plus one end-to-end test against ground truth with ±2 frames tolerance. |

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Version Control Actions

- Branch: `feature/lock-zone-periods`
- Commits: `test(lock): add failing acceptance tests for US-3`; `feat(lock): add lock zone and lock period analysis`; `docs(implementation): log US-3 implementation pass`; `docs(approval): approve US-3 implementation`
- PR: `feature/lock-zone-periods` → `main` (merge commit, so the red and green commits stay visible in history)

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
