"use strict";
// Single-page UI: upload -> select target -> track -> review lock periods.
// Boxes come from the server per frame and are drawn over the normal <video>.

const $ = (id) => document.getElementById(id);
const COLORS = {
  locked: "#2ecc71", unlocked: "#e0b341", lost: "#e5534b",
  untracked: "#3a4653", longest: "#59a8ff", zone: "#35d0ba",
};

const state = {
  video: null,      // {id, fps, frame_count, width, height, ...}
  states: [],       // per frame: [status, x, y, w, h] | [status]
  zone: null,       // {x, y, w, h} in video pixels
  analysis: null,
  selectFrame: 0,
  selectBox: null,
  frameImage: null,
  drawingZone: false,
};

// ---------- helpers ----------
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  let body = null;
  try { body = await res.json(); } catch { /* non-JSON */ }
  if (!res.ok) throw new Error((body && body.detail) || `Request failed (${res.status})`);
  return body;
}
function showError(msg) {
  const el = $("error");
  el.textContent = msg;
  el.classList.toggle("hidden", !msg);
}
function fmt(t) { return `${t.toFixed(2)} s`; }
function show(view) {
  for (const v of ["uploadView", "selectView", "playView"]) $(v).classList.toggle("hidden", v !== view);
}
function normRect(a, b) {
  return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(a.x - b.x), h: Math.abs(a.y - b.y) };
}
function clampPoint(p) {
  const v = state.video;
  return { x: Math.max(0, Math.min(v.width, p.x)), y: Math.max(0, Math.min(v.height, p.y)) };
}
function canvasToVideo(canvas, ev) {
  const r = canvas.getBoundingClientRect();
  return clampPoint({
    x: ((ev.clientX - r.left) / r.width) * state.video.width,
    y: ((ev.clientY - r.top) / r.height) * state.video.height,
  });
}
// Lets the user drag a rectangle on `canvas`; reports it in video pixels.
function enableRectDraw(canvas, onChange, onDone) {
  let start = null;
  canvas.onpointerdown = (ev) => { start = canvasToVideo(canvas, ev); canvas.setPointerCapture(ev.pointerId); };
  canvas.onpointermove = (ev) => { if (start) onChange(normRect(start, canvasToVideo(canvas, ev))); };
  canvas.onpointerup = (ev) => {
    if (!start) return;
    const r = normRect(start, canvasToVideo(canvas, ev));
    start = null;
    onDone(r);
  };
}

// ---------- upload ----------
async function uploadFile(file) {
  showError("");
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".mp4")) {
    showError("Only .mp4 files are supported. Please upload an MP4 (H.264) video.");
    return;
  }
  $("uploadStatus").textContent = `Uploading ${file.name}…`;
  const form = new FormData();
  form.append("file", file);
  try {
    const v = await api("/api/videos", { method: "POST", body: form });
    state.video = v;
    state.states = Array.from({ length: v.frame_count }, () => ["untracked"]);
    $("videoMeta").textContent =
      `${v.filename} · ${v.width}×${v.height} · ${v.fps} fps · ${v.frame_count} frames · ${v.codec}`;
    $("video").src = `/api/videos/${v.id}/file`;
    $("uploadStatus").textContent = "";
    await openSelect(0, false);
  } catch (e) {
    $("uploadStatus").textContent = "";
    showError(e.message);
  }
}

// ---------- target selection ----------
async function openSelect(frame, cancellable) {
  state.selectFrame = frame;
  state.selectBox = null;
  $("startTrackBtn").disabled = true;
  $("selectTitle").textContent = frame === 0
    ? "2. Draw a box around the target (first frame)"
    : `Re-select the target at frame ${frame} (${fmt(frame / state.video.fps)})`;
  $("selectStatus").textContent = "Loading frame…";
  show("selectView");
  const img = new Image();
  try {
    await new Promise((resolve, reject) => {
      img.onload = resolve;
      img.onerror = reject;
      img.src = `/api/videos/${state.video.id}/frames/${frame}`;
    });
  } catch { showError("Could not load the video frame."); return; }
  if (state.selectFrame !== frame) return;  // a newer frame request superseded this one
  state.frameImage = img;
  const c = $("selectCanvas");
  c.width = state.video.width;
  c.height = state.video.height;
  drawSelect();
  $("selectStatus").textContent = "Click and drag on the frame to draw the target box.";
  enableRectDraw(c, (r) => { state.selectBox = r; drawSelect(); }, (r) => {
    if (r.w < 4 || r.h < 4) {
      state.selectBox = null;
      $("startTrackBtn").disabled = true;
      $("selectStatus").textContent = "Box too small — drag a larger box (at least 4×4 px).";
    } else {
      state.selectBox = { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.w), h: Math.round(r.h) };
      $("startTrackBtn").disabled = false;
      $("selectStatus").textContent = `Box ${state.selectBox.w}×${state.selectBox.h} at (${state.selectBox.x}, ${state.selectBox.y}).`;
    }
    drawSelect();
  });
}
function drawSelect() {
  const c = $("selectCanvas"), ctx = c.getContext("2d");
  ctx.drawImage(state.frameImage, 0, 0, c.width, c.height);
  const lw = Math.max(2, c.width / 400);
  if (state.selectBox) {
    const b = state.selectBox;
    ctx.strokeStyle = COLORS.longest; ctx.lineWidth = lw;
    ctx.strokeRect(b.x, b.y, b.w, b.h);
  }
}
function confirmSelection() {
  const b = state.selectBox;
  $("selectStatus").textContent = `Target selected: ${b.w}×${b.h} box at (${b.x}, ${b.y}) on frame ${state.selectFrame}.`;
}

// ---------- rendering ----------
function frameStatus(i) {
  const s = state.states[i];
  return s ? s[0] : "untracked";
}

// ---------- wiring ----------
async function init() {
  $("fileInput").onchange = (e) => uploadFile(e.target.files[0]);
  const dz = $("dropZone");
  dz.ondragover = (e) => { e.preventDefault(); dz.classList.add("over"); };
  dz.ondragleave = () => dz.classList.remove("over");
  dz.ondrop = (e) => { e.preventDefault(); dz.classList.remove("over"); uploadFile(e.dataTransfer.files[0]); };

  $("startTrackBtn").onclick = confirmSelection;
}
init();
