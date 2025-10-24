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
# Cấu hình thư mục (file ở repo/src/api/main.py → .., .. về gốc repo)
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
    allow_origins=["*"],   # dev: mở hết; deploy nên giới hạn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Mô hình Pydantic
# =========================
class StepConfig(BaseModel):
    name: str
    params: Optional[Dict] = {}

class ProcessRequest(BaseModel):
    images: List[str]
    steps: List[StepConfig]

# =========================
# Tiện ích IO ảnh
# =========================
def read_image_from_disk(path: str):
    if not os.path.exists(path):
        return None
    data = np.fromfile(path, dtype=np.uint8)    # hỗ trợ unicode path trên Windows
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)  # BGR
    return img

def save_png_to_disk(img, path_out: str):
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("Encode PNG failed")
    with open(path_out, "wb") as f:
        f.write(buf.tobytes())

# =========================
# Các FILTER đúng theo repo của bạn
# (tự cài đặt tối thiểu để DEMO chạy chắc chắn)
# =========================
class FilterBase:
    name = "Base"
    def apply(self, img, **kwargs):
        return img

class Converter(FilterBase):
    """Đổi không gian màu."""
    name = "Converter"
    def apply(self, img, mode: str = "BGR2GRAY", **kwargs):
        m = (mode or "BGR2GRAY").upper()
        if m == "BGR2GRAY":
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if m == "BGR2RGB":
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        if m == "BGR2HSV":
            return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # không hỗ trợ thì trả nguyên
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
    """Watermark text đơn giản; nếu có ảnh PNG (alpha) thì dán ảnh."""
    name = "Watermark"
    def apply(self, img, text: str = "", image: str = "", pos: str = "bottom-right",
              opacity: float = 0.5, scale: float = 1.0, **kwargs):
        out = img.copy()
        h, w = out.shape[:2]

        # Ưu tiên watermark ảnh PNG nếu cung cấp đường dẫn hợp lệ
        if image:
            wm_path = os.path.join(ROOT_DIR, image) if not os.path.isabs(image) else image
            if os.path.exists(wm_path):
                wm = cv2.imread(wm_path, cv2.IMREAD_UNCHANGED)  # có thể RGBA
                if wm is not None:
                    if scale and scale != 1.0:
                        wm = cv2.resize(wm, (max(1, int(wm.shape[1]*scale)), max(1, int(wm.shape[0]*scale))), interpolation=cv2.INTER_AREA)
                    # tách alpha
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
                        # blend
                        for c in range(3):
                            roi[:, :, c] = (alpha * wm_rgb[:, :, c] + (1 - alpha) * roi[:, :, c]).astype(np.uint8)
                        out[y:y+hh, x:x+ww] = roi
                    return out  # nếu dùng ảnh thì kết thúc ở đây

        # nếu không có ảnh → viết chữ
        if text:
            fs = 1.0 * float(scale)
            th = max(1, int(2 * scale))
            (tw, th_text), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
            x, y = _place_xy(pos, w, h, tw, th_text)
            y = max(th_text + 5, y + th_text)  # baseline
            # shadow
            cv2.putText(out, text, (x+2, y+2), cv2.FONT_HERSHEY_SIMPLEX, fs, (0,0,0), th+1, cv2.LINE_AA)
            # text
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
    # bottom-right (default)
    return max(margin, W - w - margin), max(margin, H - h - margin)

class OutputFilter(FilterBase):
    """Không làm gì; để giữ chỗ cuối pipeline (nếu FE muốn)."""
    name = "OutputFilter"

# RemoveBackground: chỉ đăng ký nếu có rembg
try:
    from rembg import remove as _rembg_remove  # type: ignore
    class RemoveBackground(FilterBase):
        name = "RemoveBackground"
        def apply(self, img, **kwargs):
            # rembg dùng RGB; chuyển đổi và quay lại BGR
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            out = _rembg_remove(rgb)
            bgr = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
            return bgr
    _HAVE_REMBG = True
except Exception:
    _HAVE_REMBG = False

# =========================
# Registry FILTERS (đúng tên theo repo)
# =========================
FILTERS: Dict[str, Dict] = {
    "Converter": {"cls": Converter, "params": {
        "mode": {"type": "enum", "options": ["BGR2GRAY", "BGR2RGB", "BGR2HSV"], "default": "BGR2GRAY"}
    }},
    "HorizontalFlip": {"cls": HorizontalFlip, "params": {}},
    "Resize": {"cls": Resize, "params": {
        "width":  {"type": "int", "min": 1, "max": 8192, "default": None, "step": 1},
        "height": {"type": "int", "min": 1, "max": 8192, "default": None, "step": 1},
        "scale":  {"type": "float", "min": 0.1, "max": 4.0, "default": None, "step": 0.1}
    }},
    "Watermark": {"cls": Watermark, "params": {
        "text":    {"type": "string", "default": ""},
        "image":   {"type": "string", "default": ""},  # đường dẫn tương đối từ ROOT_DIR (vd: "dir/wm.png")
        "pos":     {"type": "enum",   "options": ["top-left","top-right","bottom-left","bottom-right","center"], "default": "bottom-right"},
        "opacity": {"type": "float",  "min": 0.0, "max": 1.0, "default": 0.5, "step": 0.05},
        "scale":   {"type": "float",  "min": 0.1, "max": 3.0, "default": 1.0, "step": 0.1}
    }},
    "OutputFilter": {"cls": OutputFilter, "params": {}},
}

if _HAVE_REMBG:
    FILTERS["RemoveBackground"] = {"cls": RemoveBackground, "params": {}}
# Nếu chưa cài rembg, filter này sẽ không có trong /api/filters (đúng ý “đừng làm lỗi”).

# =========================
# Job state (in-memory) — dùng Manager lazy cho an toàn spawn
# =========================
_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = Manager()
    return _manager

_JOBS: Dict[str, Dict] = {}  # chỉ dùng trong process API

# =========================
# Workers theo kiến trúc Pipes & Filters
# =========================
def worker_filter(in_q: Queue, out_q: Queue, filt_cls, step_label, job_id: str, state_map, worker_name: str, params: Dict):
    filt = filt_cls()
    _ = current_process().name
    while True:
        item = in_q.get()
        if item is None:
            out_q.put(None)
            break
        filename, img = item
        state_map[filename] = {"state": "processing", "current_filter": step_label, "worker": worker_name}
        try:
            out = filt.apply(img, **(params or {}))
            # một số filter có thể trả ảnh xám → chuẩn hoá về 3 kênh trước khi ghi nếu cần
            if out is not None and out.ndim == 2:
                out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
            out_q.put((filename, out))
        except Exception as ex:
            state_map[filename] = {
                "state": "error", "current_filter": step_label, "worker": worker_name, "error": str(ex)
            }

def worker_sink(in_q: Queue, job_id: str, state_map, outputs_list):
    while True:
        item = in_q.get()
        if item is None:
            break
        filename, img = item
        name, _ = os.path.splitext(os.path.basename(filename))
        out_name = f"{name}__out.png"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        try:
            save_png_to_disk(img, out_path)
            outputs_list.append(out_name)
            state_map[filename] = {"state": "done", "current_filter": None, "worker": "sink"}
        except Exception as ex:
            state_map[filename] = {
                "state": "error", "current_filter": "sink", "worker": "sink", "error": str(ex)
            }

def run_pipeline_job(job_id: str, images: List[str], steps: List[Dict]):
    try:
        job = _JOBS[job_id]
        queues: List[Queue] = [Queue()]
        procs: List[Process] = []

        state_map = job["images"]     # proxy manager.dict
        outputs_list = job["outputs"] # proxy manager.list

        # Dựng chuỗi filter
        for i, s in enumerate(steps):
            meta = FILTERS.get(s["name"])
            if not meta:
                raise RuntimeError(f"Unknown filter: {s['name']}")
            in_q = queues[-1]
            out_q = Queue()
            queues.append(out_q)
            worker_name = f"worker-{s['name']}-{i+1}"
            p = Process(
                target=worker_filter,
                args=(in_q, out_q, meta["cls"], s["name"], job_id, state_map, worker_name, s.get("params") or {})
            )
            p.start()
            procs.append(p)

        # sink (lưu file)
        sink_in = queues[-1]
        sink_p = Process(target=worker_sink, args=(sink_in, job_id, state_map, outputs_list))
        sink_p.start()
        procs.append(sink_p)

        # nạp input
        q0 = queues[0]
        for fn in images:
            path = os.path.join(INPUT_DIR, fn)
            img = read_image_from_disk(path)
            if img is None:
                state_map[fn] = {"state": "error", "current_filter": "load", "worker": "loader", "error": "cannot read"}
                continue
            state_map[fn] = {"state": "queued", "current_filter": None, "worker": None}
            q0.put((fn, img))

        # kết thúc input
        q0.put(None)

        # đợi tất cả worker xong
        for p in procs:
            p.join()

        job["status"] = "done"
        _JOBS[job_id] = job
    except Exception as ex:
        job = _JOBS.get(job_id)
        if job is not None:
            job["status"] = "error"
            job["error"] = str(ex)
            _JOBS[job_id] = job

# =========================
# Endpoints
# =========================
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/api/filters")
def list_filters():
    return [
        {"name": name, "params": meta.get("params", {})}
        for name, meta in FILTERS.items()
    ]

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
    # validate step names
    for s in payload.steps:
        if s.name not in FILTERS:
            raise HTTPException(status_code=400, detail=f"Unknown filter: {s.name}")

    # khởi tạo job
    job_id = uuid4().hex[:8]
    mgr = get_manager()
    _JOBS[job_id] = {
        "status": "running",
        "images": mgr.dict(),   # filename -> status dict (proxy)
        "outputs": mgr.list(),  # danh sách tên file output (proxy)
        "error": None,
        "steps": [s.dict() for s in payload.steps],
        "inputs": payload.images,
    }

    # chạy pipeline trong process riêng (để API trả về ngay job_id)
    p = Process(target=run_pipeline_job, args=(job_id, payload.images, [s.dict() for s in payload.steps]))
    p.start()

    return {"job_id": job_id, "status": "running"}

@app.get("/api/jobs/{job_id}/status")
def job_status(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    images_state = dict(job["images"])
    return {
        "job_id": job_id,
        "status": job["status"],
        "images": images_state,
        "steps": job.get("steps", []),
        "error": job.get("error"),
    }

@app.get("/api/jobs/{job_id}/outputs")
def job_outputs(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    outputs = list(job["outputs"])
    return {
        "job_id": job_id,
        "outputs": [{"name": n, "url": f"/api/file/output/{n}"} for n in outputs]
    }

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
    return FileResponse(path)

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

# (tuỳ chọn) cho phép chạy trực tiếp: python src/api/main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
