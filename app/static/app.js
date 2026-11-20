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
function defaultZone(v) {
  // TEKNOFEST-style lock zone: middle 50% horizontally, middle 80% vertically
  return { x: Math.round(v.width * 0.25), y: Math.round(v.height * 0.1),
           w: Math.round(v.width * 0.5), h: Math.round(v.height * 0.8) };
}
function frameAt(t) {
  const v = state.video;
  return Math.max(0, Math.min(v.frame_count - 1, Math.floor(t * v.fps + 1e-4)));
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
    state.zone = defaultZone(v);
    state.analysis = null;
    $("videoMeta").textContent =
      `${v.filename} · ${v.width}×${v.height} · ${v.fps} fps · ${v.frame_count} frames · ${v.codec}`;
    $("video").src = `/api/videos/${v.id}/file`;
    $("uploadStatus").textContent = "";
    renderSummary();
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
  drawZone(ctx, lw);
  if (state.selectBox) {
    const b = state.selectBox;
    ctx.strokeStyle = COLORS.longest; ctx.lineWidth = lw;
    ctx.strokeRect(b.x, b.y, b.w, b.h);
  }
}
async function startTracking() {
  showError("");
  $("startTrackBtn").disabled = true;
  $("selectStatus").textContent = "Tracking… this may take a moment for long videos.";
  try {
    const res = await api(`/api/videos/${state.video.id}/track`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start_frame: state.selectFrame, box: state.selectBox, tracker: $("trackerSelect").value }),
    });
    state.states = res.states;
    const r = res.run;
    $("statRun").textContent = `${r.tracker}: ${r.frames_processed} frames in ${r.elapsed_s.toFixed(1)} s`;
    show("playView");
    await refreshAnalysis();
    seekToFrame(state.selectFrame);
  } catch (e) {
    showError(e.message);
    $("startTrackBtn").disabled = false;
    $("selectStatus").textContent = "Tracking failed — adjust the box and try again.";
  }
}

// ---------- lock zone + analysis ----------
async function refreshAnalysis() {
  try {
    state.analysis = await api(`/api/videos/${state.video.id}/analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ zone: state.zone }),
    });
  } catch (e) {
    showError(e.message);
  }
  renderSummary();
  drawOverlay();
}
function toggleZoneDraw() {
  state.drawingZone = !state.drawingZone;
  const ov = $("overlay");
  $("zoneBtn").classList.toggle("active", state.drawingZone);
  $("zoneBtn").textContent = state.drawingZone ? "Drag on video…" : "Draw lock zone";
  ov.classList.toggle("drawing", state.drawingZone);
  if (!state.drawingZone) { ov.onpointerdown = ov.onpointermove = ov.onpointerup = null; return; }
  $("video").pause();
  enableRectDraw(ov, (r) => { state.pendingZone = r; drawOverlay(); }, (r) => {
    state.pendingZone = null;
    if (r.w < 8 || r.h < 8) {
      showError("Lock zone too small — drag a larger rectangle.");
    } else {
      showError("");
      state.zone = { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.w), h: Math.round(r.h) };
      refreshAnalysis();
    }
    toggleZoneDraw();
  });
}

// ---------- rendering ----------
function drawZone(ctx, lw) {
  const z = state.pendingZone || state.zone;
  if (!z) return;
  ctx.save();
  ctx.setLineDash([lw * 4, lw * 3]);
  ctx.strokeStyle = COLORS.zone; ctx.lineWidth = lw;
  ctx.strokeRect(z.x, z.y, z.w, z.h);
  ctx.restore();
}
function frameStatus(i) {
  const s = state.states[i];
  if (!s) return "untracked";
  if (s[0] !== "tracked") return s[0];
  const z = state.zone, [, x, y, w, h] = s;
  return x >= z.x && y >= z.y && x + w <= z.x + z.w && y + h <= z.y + z.h ? "locked" : "unlocked";
}
let lastFrame = -1;
function drawOverlay(frame) {
  if (!state.video) return;
  const vid = $("video"), ov = $("overlay");
  if (frame === undefined) frame = frameAt(vid.currentTime);
  lastFrame = frame;
  ov.style.width = vid.clientWidth + "px";
  ov.style.height = vid.clientHeight + "px";
  if (ov.width !== state.video.width) { ov.width = state.video.width; ov.height = state.video.height; }
  const ctx = ov.getContext("2d");
  ctx.clearRect(0, 0, ov.width, ov.height);
  const lw = Math.max(2, ov.width / 400);
  drawZone(ctx, lw);
  const s = state.states[frame], st = frameStatus(frame), color = COLORS[st];
  if (s && s[0] === "tracked") {
    const [, x, y, w, h] = s;
    ctx.strokeStyle = color; ctx.lineWidth = lw * 1.5;
    ctx.strokeRect(x, y, w, h);
    ctx.fillStyle = color;
    ctx.font = `${Math.round(lw * 7)}px Consolas, monospace`;
    ctx.fillText(st === "locked" ? "LOCKED" : "TRACKING", x, Math.max(lw * 8, y - lw * 2));
  }
  ctx.fillStyle = "rgba(0,0,0,.55)";
  ctx.fillRect(0, 0, lw * 75, lw * 11);
  ctx.fillStyle = "#fff";
  ctx.font = `${Math.round(lw * 7)}px Consolas, monospace`;
  ctx.fillText(`F ${frame}  ${(frame / state.video.fps).toFixed(2)}s`, lw * 3, lw * 8);
  $("hudFrame").textContent = frame;
  $("hudTime").textContent = fmt(vid.currentTime);
  $("hudState").textContent = st.toUpperCase();
  $("hudState").style.color = COLORS[st] || COLORS.untracked;
}
function renderSummary() {
  const a = state.analysis, body = $("periodsBody");
  if (!a) {
    $("statTotal").textContent = $("statCount").textContent = "—";
    body.innerHTML = '<tr><td colspan="4" class="hint">No data yet</td></tr>';
    return;
  }
  $("statTotal").textContent = fmt(a.total_locked_time);
  $("statCount").textContent = a.periods.length;
  if (!a.periods.length) {
    body.innerHTML = '<tr><td colspan="4" class="hint">No lock periods</td></tr>';
    return;
  }
  body.innerHTML = "";
  a.periods.forEach((p, i) => {
    const tr = document.createElement("tr");
    const isLongest = false;
    if (isLongest) tr.className = "longest";
    tr.innerHTML = `<td>${i + 1}${isLongest ? " ★" : ""}</td><td>${fmt(p.start_time)}</td>` +
      `<td>${fmt(p.end_time)}</td><td>${fmt(p.duration)}</td>`;
    tr.title = `Frames ${p.start_frame}–${p.end_frame}`;
    tr.onclick = () => seekToFrame(p.start_frame);
    body.appendChild(tr);
  });
}
function seekToFrame(f) {
  const vid = $("video");
  vid.currentTime = (f + 0.5) / state.video.fps;  // middle of the frame avoids rounding to f-1
  drawOverlay(f);
}

// Redraw on every presented video frame when supported, else on animation frames.
function startRenderLoop() {
  const vid = $("video");
  if ("requestVideoFrameCallback" in HTMLVideoElement.prototype) {
    const cb = (_, meta) => { if (state.video) drawOverlay(frameAt(meta.mediaTime)); vid.requestVideoFrameCallback(cb); };
    vid.requestVideoFrameCallback(cb);
  }
  const tick = () => {
    if (state.video && !$("playView").classList.contains("hidden") && vid.paused) {
      const f = frameAt(vid.currentTime);
      if (f !== lastFrame) drawOverlay(f);
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  vid.addEventListener("seeked", () => drawOverlay());
  window.addEventListener("resize", () => drawOverlay(lastFrame >= 0 ? lastFrame : undefined));
}

// ---------- wiring ----------
async function init() {
  try {
    const t = await api("/api/trackers");
    $("trackerSelect").innerHTML = t.trackers.map((n) => `<option ${n === t.default ? "selected" : ""}>${n}</option>`).join("");
  } catch (e) { showError(e.message); }

  $("fileInput").onchange = (e) => uploadFile(e.target.files[0]);
  const dz = $("dropZone");
  dz.ondragover = (e) => { e.preventDefault(); dz.classList.add("over"); };
  dz.ondragleave = () => dz.classList.remove("over");
  dz.ondrop = (e) => { e.preventDefault(); dz.classList.remove("over"); uploadFile(e.dataTransfer.files[0]); };

  $("startTrackBtn").onclick = startTracking;
  $("zoneBtn").onclick = toggleZoneDraw;
  $("zoneResetBtn").onclick = () => { state.zone = defaultZone(state.video); refreshAnalysis(); };
  $("newVideoBtn").onclick = () => {
    state.video = null; state.analysis = null; showError("");
    $("video").removeAttribute("src"); $("fileInput").value = ""; $("videoMeta").textContent = "";
    $("statRun").textContent = "—"; show("uploadView");
    renderSummary();
  };
  $("video").onerror = () => { if (state.video) showError("The browser could not play this video."); };
  startRenderLoop();
}
init();
