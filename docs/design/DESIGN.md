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

## Open Questions

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| OQ-1 | Which input formats must be accepted, and what happens with an MP4 whose codec is not H.264? | requirement-analysis | Open | — |
| OQ-2 | Is there a maximum upload size? | requirement-analysis | Open | — |
| OQ-3 | Must the target box be drawn on the first frame only, or may the user choose another starting frame? | requirement-analysis | Open | — |
| OQ-4 | What is the smallest box the user may draw? | requirement-analysis | Open | — |
| OQ-5 | May the box extend outside the frame? | requirement-analysis | Open | — |
