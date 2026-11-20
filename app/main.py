"""FastAPI application: REST API + static single-page UI."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import cv2
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .store import VideoSession, VideoStore
from .video import MAX_UPLOAD_BYTES, VideoValidationError, check_extension, probe, read_frame

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"


def _readable(exc: RequestValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", []) if p != "body")
        parts.append(f"{loc}: {err.get('msg')}" if loc else err.get("msg", "invalid"))
    return "Invalid request — " + "; ".join(parts)


def create_app(upload_dir: Optional[Path] = None) -> FastAPI:
    app = FastAPI(title="Target-Lock Video Tracker")
    store = VideoStore(Path(upload_dir or os.environ.get("TLT_UPLOAD_DIR", DEFAULT_UPLOAD_DIR)))
    app.state.store = store

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content={"detail": _readable(exc)})

    @app.exception_handler(Exception)
    async def unexpected_handler(_: Request, exc: Exception):
        # Never crash or leak a stack trace to the UI
        return JSONResponse(status_code=500, content={"detail": f"Unexpected server error: {exc}"})

    def session_or_404(vid: str) -> VideoSession:
        session = store.get(vid)
        if session is None:
            raise HTTPException(404, "Video not found. Please upload it again.")
        return session

    def summary(session: VideoSession) -> dict:
        return {"id": session.id, "filename": session.filename, **session.info.to_dict()}

    @app.post("/api/videos")
    def upload(file: UploadFile = File(...)):
        try:
            check_extension(file.filename)
        except VideoValidationError as e:
            raise HTTPException(400, str(e))
        vid, path = store.new_path()
        written = 0
        with path.open("wb") as out:
            while chunk := file.file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    out.close()
                    path.unlink(missing_ok=True)
                    raise HTTPException(413, f"File is too large (limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).")
                out.write(chunk)
        try:
            info = probe(path)
        except VideoValidationError as e:
            path.unlink(missing_ok=True)
            raise HTTPException(400, str(e))
        session = VideoSession(vid, path, file.filename, info)
        store.add(session)
        return summary(session)

    @app.get("/api/videos/{vid}")
    def get_video(vid: str):
        session = session_or_404(vid)
        return summary(session)

    @app.get("/api/videos/{vid}/file")
    def video_file(vid: str):
        return FileResponse(session_or_404(vid).path, media_type="video/mp4")

    @app.get("/api/videos/{vid}/frames/{index}")
    def frame(vid: str, index: int):
        session = session_or_404(vid)
        if index < 0 or index >= session.info.frame_count:
            raise HTTPException(400, f"Frame index must be between 0 and {session.info.frame_count - 1}.")
        try:
            img = read_frame(session.path, index)
        except IndexError as e:
            raise HTTPException(400, str(e))
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return Response(buf.tobytes(), media_type="image/jpeg")

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
