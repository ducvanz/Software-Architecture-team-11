import cv2
import os
import hashlib
from utils.dlq import write_dlq
from utils.dedup import DedupStore
from utils.thread_log import log_start, log_end

def make_id_for_path(path: str) -> str:
    try:
        stat = os.stat(path)
        s = f"{path}|{stat.st_size}|{int(stat.st_mtime)}"
    except Exception:
        s = f"{path}|{os.path.basename(path)}"
    return hashlib.sha1(s.encode()).hexdigest()

class ConvertFilter:
    def __init__(self, dedup_db="dedup.db"):
        self.dedup = DedupStore(dedup_db)
        self.stage_name = "convert"

    def process_single(self, path):
        log_start(self.stage_name, {"filename": os.path.basename(path), "path": path})
        id_ = make_id_for_path(path)
        try:
            img = cv2.imread(path)
            if img is None:
                raise ValueError(f"Cannot read image: {path}")

            envelope = {
                "id": id_,
                "path": path,
                "image": img,
                "filename": os.path.basename(path),
            }

            self.dedup.add_stage(id_, self.stage_name)
            log_end(self.stage_name, envelope)
            return envelope
        except Exception as e:
            log_end(self.stage_name, {"filename": os.path.basename(path), "path": path}, status="error")
            write_dlq({"path": path, "error": str(e)})
            return None

    def process(self, in_q, out_q):
        while True:
            path = in_q.get()
            if path is None:
                # Truyền sentinel None cho stage tiếp theo
                if out_q:
                    out_q.put(None)
                in_q.task_done()
                break
            envelope = self.process_single(path)
            # Chỉ đẩy envelope nếu nó không phải là None (xử lý thành công) VÀ có Queue đầu ra
            if envelope and out_q:
                out_q.put(envelope)
            in_q.task_done()
