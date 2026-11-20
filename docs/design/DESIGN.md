# Design & Requirements Atlas

Central index of requirement analysis output for this repository. Individual sessions may split their work into `DESIGN_<commit-id>.md` files (see [requirement-analysis SKILL.md](../../.claude/skills/requirement-analysis/SKILL.md)) when this file grows too large; every such file must be listed below.

Project: **B — Target-lock video tracker** (KUAVA newcomer task). Each round below covered exactly one feature; everything else was out of scope for that round.

## Linked Design Documents

| File | Scope / Topic | Started (commit) | Status |
|---|---|---|---|
| (this file) | Core | — | Active |

## User Stories

### US-1: Upload a video and select the target
As a UAV team analyst
I want to upload an MP4 (H.264) flight video and draw a box around the target on the first frame
So that the tool knows which object to track

Scope (round 1): upload, validation, showing the first frame, drawing/confirming the box. Tracking is out of scope.

### US-2: Track the target through the video
As a UAV team analyst
I want the selected target to be tracked through the whole video by an OpenCV tracker, with its box shown on every frame
So that I can see where the target is at any moment while the video plays

Scope (round 2): choosing a tracker, running it from the selected frame to the end, drawing the box over the normal video player. Lock zone, timeline and loss handling are out of scope.

Non-functional (from the task): a 30-second 720p video is processed in less than 60 seconds on a laptop CPU.

### US-3: Define a lock zone and report every lock period
As a UAV team analyst
I want to define a lock zone in the frame and get every continuous period in which the target box is inside it
So that I can measure how long our camera kept the target locked, as in the TEKNOFEST Fighter UAV lock-on task

Scope (round 3a): the zone, the locked/unlocked decision per frame and the list of lock periods.

### US-4: See a lock timeline and the longest lock
As a UAV team analyst
I want a timeline of locked and unlocked periods and the longest lock highlighted
So that I can judge the lock performance of a flight at a glance

Scope (round 3b): timeline segments, longest lock, summary numbers. Non-functional (from the task): the lock-duration logic is tested with generated box sequences that have known answers.

## Gherkin Acceptance Criteria

```gherkin
Feature: US-1 Upload a video and select the target

  Scenario: Valid H.264 MP4 is accepted
    Given the app is open on the upload screen
    When I upload "flight.mp4" encoded with H.264
    Then the video's width, height, fps, frame count and codec are shown
    And the first frame (frame 0) is displayed for box selection

  Scenario: Draw a box on the first frame
    Given a valid video is uploaded and frame 0 is displayed
    When I drag a rectangle of at least 4x4 pixels over the target
    Then the box is drawn on the frame
    And its size and position in video pixels are shown
    And the confirm/start button becomes enabled

  Scenario: Box that is too small is refused
    Given frame 0 is displayed
    When I drag a rectangle smaller than 4x4 pixels
    Then the message "Box too small" is shown
    And the confirm/start button stays disabled

  Scenario: The box cannot leave the frame
    Given frame 0 is displayed
    When I drag past the edge of the frame
    Then the box is clamped to the frame edge

  Scenario: Wrong file extension is rejected
    Given the app is open on the upload screen
    When I upload "notes.txt" or "clip.avi"
    Then the message "Only .mp4 files are supported" is shown
    And no video is stored

  Scenario: MP4 with a codec other than H.264 is rejected
    When I upload an MP4 file whose video stream is MPEG-4 Part 2
    Then the message "Only H.264 MP4 videos are supported" is shown
    And no video is stored

  Scenario: Corrupt, empty or truncated file is rejected
    When I upload a file named ".mp4" that is empty, not an MP4 container, or truncated
    Then a clear error message is shown ("empty", "not a valid MP4 container" or "could not be decoded")
    And the app keeps running

  Scenario: File larger than the upload limit is rejected
    When I upload a file larger than 500 MB
    Then the message "File is too large (limit 500 MB)" is shown

  Scenario: Unknown video
    When the UI requests a video id that does not exist
    Then a 404 with the message "Video not found. Please upload it again." is returned
```

```gherkin
Feature: US-2 Track the target through the video

  Scenario: Box on every frame
    Given a valid 75-frame video is uploaded and a box is drawn on frame 0
    When I press "Start tracking" with the default tracker
    Then the tracker returns a box for every frame 0..74
    And the box overlaps the true target position (IoU >= 0.5) on every frame of the synthetic test video
    And the video player shows the box over the video on the current frame, with frame number and time

  Scenario: Choose a tracker
    Given the tracker list contains CSRT, KCF and MIL
    When I choose one of them and start tracking
    Then the chosen tracker is used and reported with the run time

  Scenario: Invalid selection is refused
    When I start tracking with a box outside the frame, a box smaller than 4x4, a zero width,
      a negative or too large start frame, or an unknown tracker name
    Then a 400 error with a message naming the problem is shown
    And no tracking result is stored

  Scenario: Tracking twice at the same time is refused
    Given tracking is already running for a video
    When a second tracking request arrives for the same video
    Then it is refused with "Tracking is already running for this video."

  Scenario: Performance budget
    Given a 30-second 1280x720 30 fps H.264 video
    When it is tracked with the default tracker on a laptop CPU
    Then processing finishes in less than 60 seconds
```

```gherkin
Feature: US-3 Lock zone and lock periods

  Scenario: Default lock zone
    Given a video of width W and height H is uploaded
    Then the lock zone is the rectangle x from 0.25W to 0.75W and y from 0.10H to 0.90H
    And it is drawn as a dashed rectangle over the video

  Scenario: User draws a new zone
    Given tracking results exist
    When I press "Draw lock zone" and drag a rectangle of at least 8x8 pixels on the video
    Then the zone is replaced and all lock periods are recalculated

  Scenario: Locked frame
    Given a frame with a tracked box
    When the whole box lies inside the zone (touching the border counts as inside)
    Then the frame is locked
    And a box that is 1 pixel (or 0.001 pixel) outside any edge is not locked

  Scenario: Every continuous lock period is reported
    Given per-frame states "O*10, I*20, O*5, I*30, L, U*9" at 25 fps (I inside, O outside, L lost, U untracked)
    When the analysis runs
    Then the periods are frames 10-29 (0.80 s) and 35-64 (1.20 s)
    And each period shows start time, end time and duration
    And the total locked time is 2.00 s

  Scenario: Lost or untracked frames are never locked
    Given a lost or untracked frame between two locked frames
    Then it splits the lock into two periods

  Scenario: Invalid zone is rejected
    When the zone is partly outside the frame, has zero width/height or is missing a field
    Then a 400 error with a clear message is returned and nothing changes

  Scenario: Invalid fps is rejected by the lock logic
    When the lock logic is called with fps <= 0
    Then it raises an error instead of producing durations
```

```gherkin
Feature: US-4 Timeline and longest lock

  Scenario: Timeline covers the whole video
    Given per-frame states "U*2, O*3, I*4, L, U*2"
    Then the timeline segments are untracked 0-1, unlocked 2-4, locked 5-8, lost 9, untracked 10-11
    And they are drawn in different colours on a bar that spans the whole video

  Scenario: Longest lock is highlighted
    Given lock periods of 3, 9 and 4 frames
    Then the 9-frame period is the longest and is outlined on the timeline and starred in the table
    And the "Longest lock" value shows its duration

  Scenario: Tie for the longest lock
    Given two lock periods of 5 frames
    Then the earlier one is the longest

  Scenario: No lock at all
    Given the target is never inside the zone (or nothing is tracked yet)
    Then the longest lock is empty ("0.00 s" / null) and the timeline still covers the whole video

  Scenario: Jump from the timeline
    When I click a point on the timeline or a row of the period table
    Then the video seeks to that frame and the overlay shows it
```

## Open Questions

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| OQ-1 | Which input formats must be accepted, and what happens with an MP4 whose codec is not H.264? | requirement-analysis | Resolved | Only `.mp4` with an H.264 video stream. Everything else (other extensions, other codecs inside MP4, corrupt files) is rejected with a clear message; nothing is stored. |
| OQ-2 | Is there a maximum upload size? | requirement-analysis | Resolved | 500 MB. Larger uploads are rejected with "File is too large (limit 500 MB)". A 30 s 720p clip is ~5–20 MB, so this is generous. |
| OQ-3 | Must the target box be drawn on the first frame only, or may the user choose another starting frame? | requirement-analysis | Resolved | Round 1: first frame (frame 0), as the task says. Choosing another frame is only needed for re-selection and is handled in US-5. |
| OQ-4 | What is the smallest box the user may draw? | requirement-analysis | Resolved | 4×4 video pixels. Smaller boxes are refused with "Box too small"; the trackers need some texture to work. |
| OQ-5 | May the box extend outside the frame? | requirement-analysis | Resolved | No. The drag is clamped to the frame in the UI and the server rejects boxes outside the frame. |
| OQ-6 | Which OpenCV tracker must be used? | requirement-analysis | Resolved | The user can choose CSRT, KCF or MIL. The default is decided in the architecture stage (performance vs. accuracy, see AQ-6). |
| OQ-7 | Should tracking run live while the video plays, or once before playback? | requirement-analysis | Resolved | Once, on the server, before playback. The browser then draws the stored boxes over the normal video player (as suggested in the task tip). |
| OQ-8 | What exactly does "show its box on every frame" require in the UI? | requirement-analysis | Resolved | A canvas over the HTML5 video draws the box of the current frame, plus a frame counter and time; it updates during playback, pause and seeking. |
| OQ-9 | What does "the box is inside the zone" mean: fully inside, centre inside, or some overlap? | requirement-analysis | Resolved | Fully inside, borders inclusive (box edge exactly on the zone edge still counts). |
| OQ-10 | What shape and default size does the lock zone have, and can the user change it? | requirement-analysis | Resolved | Axis-aligned rectangle. Default: 25%–75% of the width and 10%–90% of the height (similar to the TEKNOFEST target-hit area). The user can redraw it at any time. |
| OQ-11 | Is there a minimum duration for a lock to count (TEKNOFEST counts a lock after 4 s)? | requirement-analysis | Resolved | No minimum: every continuous period of at least 1 frame is reported. The longest lock is highlighted (US-4). A minimum-duration filter is out of scope. |
| OQ-12 | How are start, end and duration of a period calculated? | requirement-analysis | Resolved | From frame indices: start = first/fps, end = (last+1)/fps, duration = frames/fps. A 1-frame lock lasts 1/fps seconds. |
| OQ-13 | Which states must the timeline distinguish? | requirement-analysis | Resolved | Locked, tracked but not locked, lost, and not tracked. The longest lock is outlined. |
| OQ-14 | If two periods have the same (longest) length, which one is the longest? | requirement-analysis | Resolved | The earliest one. |
| OQ-15 | Should the timeline be interactive? | requirement-analysis | Resolved | Yes: clicking the timeline or a row of the period table seeks the video to that frame. |
