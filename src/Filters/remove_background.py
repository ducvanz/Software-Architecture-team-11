import cv2
import numpy as np
from rembg import remove
from utils.dedup import DedupStore
from utils.retry import retry
from utils.dlq import write_dlq
from utils.thread_log import log_start, log_end

class RemoveBackground:
    def __init__(self, dedup_db="dedup.db", checker_size=20):
        self.dedup = DedupStore(dedup_db)
        self.stage_name = "rembg"
        self.checker_size = checker_size

    def _create_checkerboard(self, w, h):
        img = np.zeros((h, w, 3), np.uint8)
        for y in range(0, h, self.checker_size):
            for x in range(0, w, self.checker_size):
                color = (255,255,255) if (x//self.checker_size+y//self.checker_size)%2==0 else (200,200,200)
                cv2.rectangle(img, (x,y), (x+self.checker_size, y+self.checker_size), color, -1)
        return img

    @retry(max_attempts=2, backoff=0.1)
    def process_single(self, envelope):
        log_start(self.stage_name, envelope)
        try:
            id_ = envelope["id"]
            if self.stage_name in self.dedup.get_stages(id_):
                log_end(self.stage_name, envelope, status="skip")
                return envelope

            img = envelope.get("image")
            if img is None:
                raise ValueError("No image")
            h, w = img.shape[:2]
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            rgba = remove(img_rgb)
            alpha = rgba[:,:,3]/255.0
            fg = rgba[:,:,:3]
            bg = cv2.cvtColor(self._create_checkerboard(w,h), cv2.COLOR_BGR2RGB)
            combined = (fg*alpha[:,:,None]+bg*(1-alpha[:,:,None])).astype(np.uint8)
            envelope["image"] = cv2.cvtColor(combined, cv2.COLOR_RGB2BGR)
            self.dedup.add_stage(id_, self.stage_name)
            log_end(self.stage_name, envelope)
            return envelope
        except Exception as e:
            log_end(self.stage_name, envelope, status="error")
            write_dlq(envelope)
            return envelope

    def process(self, in_q, out_q):
        while True:
            envelope = in_q.get()
            if envelope is None:
                if out_q:
                    out_q.put(None)
                in_q.task_done()
                break
            out_q.put(self.process_single(envelope))
            in_q.task_done()
