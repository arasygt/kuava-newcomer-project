# Approval Log

> Single file shared by the **entire pipeline** (`requirement-analysis`, `solution-architect`, and any future stage). Exactly **one active entry** exists at a time, regardless of which stage/skill created it, with status `Pending Approval`. Update it in place as decisions accumulate during a session — never create a second pending entry. Once a human operator explicitly sets it to `Approved` or `Rejected` and the associated commit/PR lands, move it to History below and leave the active slot empty for the next stage to use.

## Active Entry

_No active entry — the next stage will open one._

---

## History

<!-- Closed (Approved/Rejected) entries, most recent first. -->

