# file: Filters/output_filter.py

import os
import cv2
from utils.dlq import write_dlq
from utils.dedup import DedupStore
from utils.retry import retry
from utils.thread_log import log_start, log_end

class OutputFilter:
    def __init__(self, output_dir, dedup_db="dedup.db"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.dedup = DedupStore(dedup_db)
        self.stage_name = "output"

    @retry(max_attempts=3, backoff=0.2)
    def process_single(self, envelope):
        log_start(self.stage_name, envelope)
        try:
            id_ = envelope["id"]
            if self.stage_name in self.dedup.get_stages(id_):
                log_end(self.stage_name, envelope, status="skip")
                return envelope
            img = envelope.get("image")
            fname = envelope.get("filename")
            if img is None or fname is None:
                raise ValueError("Missing image or filename")
            out_path = os.path.join(self.output_dir, fname)
            if not cv2.imwrite(out_path, img):
                raise IOError(f"Failed to write {out_path}")
            self.dedup.add_stage(id_, self.stage_name)
            log_end(self.stage_name, envelope)
            return envelope
        except Exception as e:
            # Ghi lỗi và DLQ sau khi retry đã thất bại
            log_end(self.stage_name, envelope, status="error")
            write_dlq(envelope)
            return envelope

    def process(self, in_q, out_q):
        """
        Lấy envelope từ in_q, xử lý (lưu file), và KHÔNG đẩy vào out_q.
        """
        while True:
            envelope = in_q.get()
            if envelope is None:
                # Nếu nhận được sentinel, kiểm tra và truyền đi (out_q là None nên sẽ bị bỏ qua)
                if out_q:
                    out_q.put(None)
                in_q.task_done()
                break
                
            # Xử lý: lưu file
            self.process_single(envelope)
            
            # ⚠️ KHÔNG CÓ out_q.put() 
            
            in_q.task_done()