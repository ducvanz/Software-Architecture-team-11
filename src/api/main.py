from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from uuid import uuid4
import os, io, base64, json
import numpy as np
import cv2

from multiprocessing import Process, Queue, Manager, current_process

# ==== Cấu hình thư mục ====
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INPUT_DIR = os.path.join(ROOT_DIR, "data", "input")
OUTPUT_DIR = os.path.join(ROOT_DIR, "data", "output")
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==== Khởi tạo FastAPI + CORS (dev) ====
app = FastAPI(title="Pipes & Filters API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev: mở hết; khi deploy hãy hạn chế domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== Bộ lọc demo (thay thế bằng filter thật của nhóm nếu có) ====
class FilterBase:
    name = "Base"
    def apply(self, img, **kwargs):
        return img

class Grayscale(FilterBase):
    name = "Grayscale"
    def apply(self, img, **kwargs):
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

class Blur(FilterBase):
    name = "Blur"
    def apply(self, img, ksize: int = 5, **kwargs):
        k = int(ksize)
        if k % 2 == 0: k += 1
        return cv2.GaussianBlur(img, (k, k), 0)

# Đăng ký filter: tên → (class, schema tham số để FE tự vẽ control)
FILTERS = {
    "Grayscale": {"cls": Grayscale, "params": {}},
    "Blur": {"cls": Blur, "params": {"ksize": {"type":"int","min":1,"max":31,"default":5,"step":2}}},
}

# ==== Model pydantic ====
class StepConfig(BaseModel):
    name: str
    params: Optional[Dict] = {}

class ProcessRequest(BaseModel):
    images: List[str]              # danh sách tên file trong data/input
    steps: List[StepConfig]        # danh sách filter + params

# ==== Tiện ích IO ảnh ====
def read_image_from_disk(path: str):
    if not os.path.exists(path):
        return None
    data = np.fromfile(path, dtype=np.uint8)        # hỗ trợ unicode path trên Windows
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)      # BGR
    return img

def save_png_to_disk(img, path_out: str):
    if img.ndim == 3:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    else:
        ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("Encode PNG failed")
    with open(path_out, "wb") as f:
        f.write(buf.tobytes())

# ==== Job state (in-memory) ====
# jobs[job_id] = {
#   "status": "running|done|error",
#   "images": { filename: {"state":"queued|processing|done|error", "current_filter": str|None, "worker": str|None } },
#   "outputs": [output_filenames...],
#   "error": str|None
# }
manager = Manager()
JOBS = manager.dict()

# ==== Worker logic theo kiến trúc Pipes & Filters ====
def worker_filter(in_q: Queue, out_q: Queue, filt_cls, step_label, job_id: str, state_map, worker_name: str, params: Dict):
    filt = filt_cls()
    proc = current_process().name or worker_name
    while True:
        item = in_q.get()
        if item is None:   # sentinel kết thúc
            out_q.put(None)
            break
        filename, img = item
        # cập nhật trạng thái
        state_map[filename] = {"state": "processing", "current_filter": step_label, "worker": worker_name}
        try:
            out = filt.apply(img, **(params or {}))
            out_q.put((filename, out))
        except Exception as ex:
            state_map[filename] = {"state": "error", "current_filter": step_label, "worker": worker_name, "error": str(ex)}

def worker_sink(in_q: Queue, job_id: str, state_map, outputs_list):
    while True:
        item = in_q.get()
        if item is None:
            break
        filename, img = item
        # lưu file output: <tên gốc>__out.png
        name, _ = os.path.splitext(os.path.basename(filename))
        out_name = f"{name}__out.png"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        try:
            save_png_to_disk(img, out_path)
            outputs_list.append(out_name)
            state_map[filename] = {"state": "done", "current_filter": None, "worker": "sink"}
        except Exception as ex:
            state_map[filename] = {"state": "error", "current_filter": "sink", "worker": "sink", "error": str(ex)}

def run_pipeline_job(job_id: str, images: List[str], steps: List[Dict]):
    """
    Tạo hàng đợi theo số step: q0 (input) -> step1 -> step2 -> ... -> sink
    Cập nhật JOBS[job_id]["images"][filename] và JOBS[job_id]["outputs"]
    """
    try:
        job = JOBS[job_id]
        # tạo queues
        queues: List[Queue] = [Queue()]
        procs: List[Process] = []

        # state_map và outputs_list để worker cập nhật
        state_map = job["images"]   # manager.dict
        outputs_list = job["outputs"]

        # dựng chuỗi filter
        for i, s in enumerate(steps):
            meta = FILTERS.get(s["name"])
            if not meta:
                raise RuntimeError(f"Unknown filter: {s['name']}")
            in_q = queues[-1]
            out_q = Queue()
            queues.append(out_q)
            worker_name = f"worker-{s['name']}-{i+1}"
            p = Process(target=worker_filter, args=(in_q, out_q, meta["cls"], s["name"], job_id, state_map, worker_name, s.get("params") or {}))
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

        # gửi sentinel kết thúc vào q0
        q0.put(None)

        # đợi tất cả worker xong
        for p in procs:
            p.join()

        job["status"] = "done"
        JOBS[job_id] = job
    except Exception as ex:
        job = JOBS.get(job_id, None)
        if job is not None:
            job["status"] = "error"
            job["error"] = str(ex)
            JOBS[job_id] = job

# ==== Endpoints ====

@app.get("/api/filters")
def list_filters():
    return [
        {"name": name, "params": meta["params"]}
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
async def start_process(
    payload: ProcessRequest
):
    # validate step names
    for s in payload.steps:
        if s.name not in FILTERS:
            raise HTTPException(status_code=400, detail=f"Unknown filter: {s.name}")

    # khởi tạo job
    job_id = uuid4().hex[:8]
    JOBS[job_id] = {
        "status": "running",
        "images": manager.dict(),  # filename -> status dict
        "outputs": manager.list(),
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
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # chuyển manager.dict -> dict thường để trả JSON
    images_state = dict(job["images"])
    return {
        "job_id": job_id,
        "status": job["status"],
        "images": images_state,   # {filename: {state, current_filter, worker, ...}}
        "steps": job.get("steps", []),
        "error": job.get("error"),
    }

@app.get("/api/jobs/{job_id}/outputs")
def job_outputs(job_id: str):
    job = JOBS.get(job_id)
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
