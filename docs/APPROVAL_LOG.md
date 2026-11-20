# Approval Log

> Single file shared by the **entire pipeline** (`requirement-analysis`, `solution-architect`, and any future stage). Exactly **one active entry** exists at a time, regardless of which stage/skill created it, with status `Pending Approval`. Update it in place as decisions accumulate during a session — never create a second pending entry. Once a human operator explicitly sets it to `Approved` or `Rejected` and the associated commit/PR lands, move it to History below and leave the active slot empty for the next stage to use.

## Active Entry

- **Status**: Pending Approval
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
- **Approved By**: 
- **Approval Date**: 

---

## History

<!-- Closed (Approved/Rejected) entries, most recent first. -->

