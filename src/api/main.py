from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from uuid import uuid4
import os
import numpy as np
import cv2

from multiprocessing import Process, Queue, Manager, current_process
import datetime
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

# =========================
# Windows multiprocessing (ổn định khi --reload)
# =========================
if os.name == "nt":
    import multiprocessing as mp
    mp.freeze_support()
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

# =========================
# Cấu hình thư mục
# =========================
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INPUT_DIR = os.path.join(ROOT_DIR, "data", "input")
OUTPUT_DIR = os.path.join(ROOT_DIR, "data", "output")
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# FastAPI + CORS (dev)
# =========================
app = FastAPI(title="Pipes & Filters API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Pydantic models
# =========================
class StepConfig(BaseModel):
    name: str
    params: Optional[Dict] = {}

class ProcessRequest(BaseModel):
    images: List[str]
    steps: List[StepConfig]

# =========================
# IO utils
# =========================
def read_image_from_disk(path: str):
    if not os.path.exists(path):
        return None
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)  # BGR
    return img

def save_png_to_disk(img, path_out: str):
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("Encode PNG failed")
    with open(path_out, "wb") as f:
        f.write(buf.tobytes())

# =========================
# Filters (theo repo)
# =========================
class FilterBase:
    name = "Base"
    def apply(self, img, **kwargs):
        return img

class Converter(FilterBase):
    name = "Converter"
    def apply(self, img, mode: str = "BGR2GRAY", **kwargs):
        m = (mode or "BGR2GRAY").upper()
        if m == "BGR2GRAY":
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if m == "BGR2RGB":
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        if m == "BGR2HSV":
            return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        return img

class HorizontalFlip(FilterBase):
    name = "HorizontalFlip"
    def apply(self, img, **kwargs):
        return cv2.flip(img, 1)

class Resize(FilterBase):
    name = "Resize"
    def apply(self, img, width: Optional[int] = None, height: Optional[int] = None, scale: Optional[float] = None, **kwargs):
        h, w = img.shape[:2]
        if scale is not None:
            s = float(scale)
            new_w = max(1, int(w * s))
            new_h = max(1, int(h * s))
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        if width is not None and height is not None:
            return cv2.resize(img, (int(width), int(height)), interpolation=cv2.INTER_AREA)
        if width is not None:
            new_w = int(width)
            new_h = max(1, int(h * (new_w / w)))
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        if height is not None:
            new_h = int(height)
            new_w = max(1, int(w * (new_h / h)))
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return img

class Watermark(FilterBase):
    name = "Watermark"
    def apply(self, img, text: str = "", image: str = "", pos: str = "bottom-right",
              opacity: float = 0.5, scale: float = 1.0, **kwargs):
        out = img.copy()
        h, w = out.shape[:2]

        # ưu tiên watermark ảnh
        if image:
            wm_path = os.path.join(ROOT_DIR, image) if not os.path.isabs(image) else image
            if os.path.exists(wm_path):
                wm = cv2.imread(wm_path, cv2.IMREAD_UNCHANGED)
                if wm is not None:
                    if scale and scale != 1.0:
                        wm = cv2.resize(
                            wm,
                            (max(1, int(wm.shape[1] * scale)), max(1, int(wm.shape[0] * scale))),
                            interpolation=cv2.INTER_AREA,
                        )
                    if wm.shape[2] == 4:
                        alpha = wm[:, :, 3] / 255.0 * float(opacity)
                        wm_rgb = wm[:, :, :3]
                    else:
                        alpha = np.full(wm.shape[:2], float(opacity), dtype=np.float32)
                        wm_rgb = wm
                    hh, ww = wm_rgb.shape[:2]
                    x, y = _place_xy(pos, w, h, ww, hh)
                    roi = out[y:y+hh, x:x+ww]
                    if roi.shape[0] == hh and roi.shape[1] == ww:
                        for c in range(3):
                            roi[:, :, c] = (alpha * wm_rgb[:, :, c] + (1 - alpha) * roi[:, :, c]).astype(np.uint8)
                        out[y:y+hh, x:x+ww] = roi
                    return out

        # watermark text
        if text:
            fs = 1.0 * float(scale)
            th = max(1, int(2 * scale))
            (tw, th_text), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
            x, y = _place_xy(pos, w, h, tw, th_text)
            y = max(th_text + 5, y + th_text)
            cv2.putText(out, text, (x+2, y+2), cv2.FONT_HERSHEY_SIMPLEX, fs, (0,0,0), th+1, cv2.LINE_AA)
            overlay = out.copy()
            cv2.putText(overlay, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, fs, (255,255,255), th, cv2.LINE_AA)
            cv2.addWeighted(overlay, float(opacity), out, 1.0 - float(opacity), 0, out)
        return out

def _place_xy(pos: str, W: int, H: int, w: int, h: int):
    pos = (pos or "bottom-right").lower()
    margin = 10
    if pos == "top-left":
        return margin, margin
    if pos == "top-right":
        return max(margin, W - w - margin), margin
    if pos == "bottom-left":
        return margin, max(margin, H - h - margin)
    if pos == "center":
        return max(0, (W - w)//2), max(0, (H - h)//2)
    return max(margin, W - w - margin), max(margin, H - h - margin)  # bottom-right

class OutputFilter(FilterBase):
    name = "OutputFilter"

# RemoveBackground (nếu có rembg)
try:
    from rembg import remove as _rembg_remove  # type: ignore
    class RemoveBackground(FilterBase):
        name = "RemoveBackground"
        def apply(self, img, **kwargs):
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            out = _rembg_remove(rgb)
            bgr = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
            return bgr
    _HAVE_REMBG = True
except Exception:
    _HAVE_REMBG = False

# Registry
FILTERS: Dict[str, Dict] = {
    "Converter": {"cls": Converter, "params": {
        "mode": {"type": "enum", "options": ["BGR2GRAY", "BGR2RGB", "BGR2HSV"], "default": "BGR2GRAY"}
    }},
    "HorizontalFlip": {"cls": HorizontalFlip, "params": {}},
    "Resize": {"cls": Resize, "params": {
        "width":  {"type": "int", "min": 1, "max": 8192, "default": None, "step": 1},
        "height": {"type": "int", "min": 1, "max": 8192, "default": None, "step": 1},
        "scale":  {"type": "float",  "min": 0.1, "max": 4.0, "default": None, "step": 0.1}
    }},
    "Watermark": {"cls": Watermark, "params": {
        "text":    {"type": "string", "default": ""},
        "image":   {"type": "string", "default": ""},
        "pos":     {"type": "enum", "options": ["top-left","top-right","bottom-left","bottom-right","center"], "default": "bottom-right"},
        "opacity": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5, "step": 0.05},
        "scale":   {"type": "float", "min": 0.1, "max": 3.0, "default": 1.0, "step": 0.1}
    }},
    "OutputFilter": {"cls": OutputFilter, "params": {}},
}
if _HAVE_REMBG:
    FILTERS["RemoveBackground"] = {"cls": RemoveBackground, "params": {}}

# =========================
# Store dùng Manager — LAZY (không tạo lúc import)
# =========================
_manager = None
_JOBS = None

def get_store():
    """Khởi tạo Manager + JOBS đúng lúc (chỉ trong process cha)."""
    global _manager, _JOBS
    if _manager is None:
        _manager = Manager()
    if _JOBS is None:
        _JOBS = _manager.dict()
    return _manager, _JOBS

LOG_MAX = 2000  # max log entries to keep in job["logs"]

def _now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"

def _append_log(logs_list, level, stage_idx, stage_label, worker_name, filename, message):
    try:
        logs_list.append({
            "ts": _now_iso(),
            "level": level,
            "stage_idx": stage_idx,
            "stage": stage_label,
            "worker": worker_name,
            "file": filename,
            "msg": message,
        })
        # trim oldest entries when exceed limit (best-effort)
        try:
            while len(logs_list) > LOG_MAX:
                # Manager().list supports pop(0)
                logs_list.pop(0)
        except Exception:
            # ignore trim errors (race)
            pass
    except Exception:
        # best-effort logging; avoid breaking worker on logging failure
        pass

# =========================
# Workers
# =========================
def worker_filter(in_q: Queue, out_q: Queue, filt_cls, step_label, stage_idx: int, job_id: str, state_map, worker_name: str, params: Dict, logs_list, next_step_label: Optional[str] = None):
    filt = filt_cls()
    proc_name = current_process().name
    worker_label = worker_name or proc_name
    while True:
        item = in_q.get()
        if item is None:
            # propagate sentinel and log
            _append_log(logs_list, "info", stage_idx, step_label, worker_label, None, "sentinel received, exiting")
            if out_q:
                out_q.put(None)
            break
        filename, img = item
        state_map[filename] = {"state": "processing", "current_filter": step_label, "worker": worker_label, "ts": _now_iso()}
        _append_log(logs_list, "info", stage_idx, step_label, worker_label, filename, "received")
        try:
            out = filt.apply(img, **(params or {}))
            if out is not None and getattr(out, "ndim", None) == 2:
                out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
            # mark queued for next stage (so UI can show it moved to next column)
            next_label = next_step_label or None
            state_map[filename] = {"state": "queued", "current_filter": next_label, "worker": None, "ts": _now_iso()}
            _append_log(logs_list, "info", stage_idx, step_label, worker_label, filename, f"processed -> queued for {next_label or 'sink'}")
            if out_q is not None:
                out_q.put((filename, out))
        except Exception as ex:
            state_map[filename] = {"state": "error", "current_filter": step_label, "worker": worker_label, "error": str(ex), "ts": _now_iso()}
            _append_log(logs_list, "error", stage_idx, step_label, worker_label, filename, f"error: {ex}")

def worker_sink(in_q: Queue, job_id: str, state_map, outputs_list, logs_list, sink_name="sink"):
    while True:
        item = in_q.get()
        if item is None:
            _append_log(logs_list, "info", None, "sink", sink_name, None, "sentinel received, exiting")
            break
        filename, img = item
        name, _ = os.path.splitext(os.path.basename(filename))
        out_name = f"{name}__out.png"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        _append_log(logs_list, "info", None, "sink", sink_name, filename, "received")
        try:
            save_png_to_disk(img, out_path)
            outputs_list.append(out_name)
            state_map[filename] = {"state": "done", "current_filter": None, "worker": "sink", "ts": _now_iso()}
            _append_log(logs_list, "info", None, "sink", sink_name, filename, f"saved -> {out_name}")
        except Exception as ex:
            state_map[filename] = {"state": "error", "current_filter": "sink", "worker": "sink", "error": str(ex), "ts": _now_iso()}
            _append_log(logs_list, "error", None, "sink", sink_name, filename, f"error: {ex}")

def run_pipeline_job(job_id: str, images: List[str], steps: List[Dict], JOBS):
    """Hàm chạy trong process con – dùng proxy JOBS truyền từ cha (không đụng vào globals)."""
    try:
        job = JOBS[job_id]
        queues: List[Queue] = [Queue()]
        procs: List[Process] = []

        state_map = job["images"]     # proxy manager.dict
        outputs_list = job["outputs"] # proxy manager.list
        logs_list = job.get("logs")   # proxy manager.list

        # Dựng chuỗi filter
        for i, s in enumerate(steps):
            meta = FILTERS.get(s["name"])
            if not meta:
                raise RuntimeError(f"Unknown filter: {s['name']}")
            in_q = queues[-1]
            out_q = Queue()
            queues.append(out_q)
            worker_name = f"worker-{s['name']}-{i+1}"
            # determine next stage label (or None -> sink)
            next_label = steps[i+1]["name"] if (i+1) < len(steps) else "sink"
            p = Process(
                target=worker_filter,
                args=(in_q, out_q, meta["cls"], s["name"], i, job_id, state_map, worker_name, s.get("params") or {}, logs_list, next_label)
            )
            p.start()
            procs.append(p)

        # sink
        sink_in = queues[-1]
        sink_p = Process(target=worker_sink, args=(sink_in, job_id, state_map, outputs_list, logs_list))
        sink_p.start()
        procs.append(sink_p)

        # nạp input
        q0 = queues[0]
        for fn in images:
            path = os.path.join(INPUT_DIR, fn)
            img = read_image_from_disk(path)
            if img is None:
                state_map[fn] = {"state": "error", "current_filter": "load", "worker": "loader", "error": "cannot read", "ts": _now_iso()}
                _append_log(logs_list, "error", None, "loader", "loader", fn, "cannot read")
                continue
            # queued for first stage (loader)
            state_map[fn] = {"state": "queued", "current_filter": None, "worker": None, "ts": _now_iso()}
            _append_log(logs_list, "info", None, "loader", "loader", fn, "queued")
            q0.put((fn, img))

        # kết thúc input
        q0.put(None)
        _append_log(logs_list, "info", None, "loader", "loader", None, "input sentinel sent")

        # đợi tất cả worker xong
        for p in procs:
            p.join()

        job["status"] = "done"
        JOBS[job_id] = job
        _append_log(logs_list, "info", None, "job", "master", None, "job done")
    except Exception as ex:
        job = JOBS.get(job_id, None)
        if job is not None:
            job["status"] = "error"
            job["error"] = str(ex)
            JOBS[job_id] = job
            logs_list = job.get("logs")
            if logs_list is not None:
                _append_log(logs_list, "error", None, "job", "master", None, f"job error: {ex}")

# =========================
# Endpoints
# =========================
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/api/filters")
def list_filters():
    return [{"name": name, "params": meta.get("params", {})} for name, meta in FILTERS.items()]

@app.get("/api/images")
def list_input_images():
    files = []
    for f in sorted(os.listdir(INPUT_DIR)):
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp")):
            files.append({"name": f, "url": f"/api/file/input/{f}"})
    return {"images": files}

@app.get("/api/outputs")
def list_outputs():
    files = []
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp")):
            files.append({"name": f, "url": f"/api/file/output/{f}"})
    return {"outputs": files}

@app.post("/api/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    saved = []
    for uf in files:
        name = uf.filename
        if not name:
            continue
        data = await uf.read()
        path = os.path.join(INPUT_DIR, name)
        with open(path, "wb") as f:
            f.write(data)
        saved.append(name)
    return {"saved": saved}

@app.post("/api/process")
async def start_process(payload: ProcessRequest):
    # validate
    for s in payload.steps:
        if s.name not in FILTERS:
            raise HTTPException(status_code=400, detail=f"Unknown filter: {s.name}")

    # tạo store lazily
    mgr, JOBS = get_store()

    # khởi tạo job (proxy)
    job_id = uuid4().hex[:8]
    JOBS[job_id] = {
        "status": "running",
        "images": mgr.dict(),
        "outputs": mgr.list(),
        "logs": mgr.list(),               # <-- thêm logs list
        "error": None,
        "steps": [s.dict() for s in payload.steps],
        "inputs": payload.images,
    }

    # chạy pipeline (truyền JOBS proxy vào)
    p = Process(target=run_pipeline_job, args=(job_id, payload.images, [s.dict() for s in payload.steps], JOBS))
    p.start()

    return {"job_id": job_id, "status": "running"}

@app.get("/api/jobs/{job_id}/status")
def job_status(job_id: str):
    _, JOBS = get_store()
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    images_state = dict(job["images"])
    return {
        "job_id": job_id,
        "status": job["status"],
        "images": images_state,
        "steps": job.get("steps", []),
        "error": job.get("error"),
        "logs": list(job.get("logs", [])),   # <-- trả về logs
    }

@app.get("/api/jobs/{job_id}/outputs")
def job_outputs(job_id: str):
    _, JOBS = get_store()
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    outputs = list(job["outputs"])
    return {"job_id": job_id, "outputs": [{"name": n, "url": f"/api/file/output/{n}"} for n in outputs]}

@app.get("/api/file/{kind}/{filename}")
def get_file(kind: str, filename: str):
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if kind == "input":
        path = os.path.join(INPUT_DIR, filename)
    elif kind == "output":
        path = os.path.join(OUTPUT_DIR, filename)
    else:
        raise HTTPException(status_code=400, detail="Invalid kind")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, headers={"Cache-Control": "no-store, max-age=0"})

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.websocket("/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint: gửi snapshot job (images state + logs + status) định kỳ.
    Frontend có thể kết nối ws://host:8000/ws/jobs/{job_id}
    """
    await websocket.accept()
    try:
        while True:
            _, JOBS = get_store()
            job = JOBS.get(job_id)
            if not job:
                # nếu job chưa tồn tại, gửi 404-like message rồi chờ
                try:
                    await websocket.send_json({"job_id": job_id, "status": "not_found"})
                except Exception:
                    break
                await asyncio.sleep(0.5)
                continue
            
            # convert proxy objects -> plain JSON-serializable
            try:
                images = dict(job.get("images", {}))
            except Exception:
                images = {}
            try:
                logs = list(job.get("logs", []))
            except Exception:
                logs = []
            try:
                outputs = list(job.get("outputs", []))
            except Exception:
                outputs = []

            payload = {
                "job_id": job_id,
                "status": job.get("status"),
                "images": images,
                "steps": job.get("steps", []),
                "logs": logs,
                "error": job.get("error"),
                "outputs": outputs,
            }

            try:
                await websocket.send_json(payload)
            except Exception:
                # socket broken
                break

            # throttle send frequency
            await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        pass
    except Exception:
        # swallow to avoid crashing server loop
        pass

# chạy trực tiếp (tuỳ chọn)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
