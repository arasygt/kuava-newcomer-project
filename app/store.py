"""In-memory registry of uploaded videos and their tracking results."""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .lock import UNTRACKED, FrameState
from .tracking import TrackRun
from .video import VideoInfo


@dataclass
class VideoSession:
    id: str
    path: Path
    filename: str
    info: VideoInfo
    states: list[FrameState] = field(default_factory=list)
    last_run: Optional[TrackRun] = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if not self.states:
            self.states = [FrameState(i, UNTRACKED) for i in range(self.info.frame_count)]

    def apply_run(self, run: TrackRun) -> None:
        """Results from `run.start_frame` onwards replace anything tracked before."""
        for i in range(run.start_frame, len(self.states)):
            self.states[i] = FrameState(i, UNTRACKED)
        for s in run.states:
            if s.frame < len(self.states):
                self.states[s.frame] = s
        self.last_run = run


class VideoStore:
    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, VideoSession] = {}
        self._lock = threading.Lock()

    def new_path(self) -> tuple[str, Path]:
        vid = uuid.uuid4().hex
        return vid, self.upload_dir / f"{vid}.mp4"

    def add(self, session: VideoSession) -> None:
        with self._lock:
            self._sessions[session.id] = session

    def get(self, vid: str) -> Optional[VideoSession]:
        with self._lock:
            return self._sessions.get(vid)
