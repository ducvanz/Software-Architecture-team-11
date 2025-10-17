import cv2
from utils.dedup import DedupStore
from utils.retry import retry
from utils.dlq import write_dlq
from utils.thread_log import log_start, log_end

class HorizontalFlip:
    def __init__(self, dedup_db="dedup.db"):
        self.dedup = DedupStore(dedup_db)
        self.stage_name = "hflip"

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
            envelope["image"] = cv2.flip(img, 1)
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
