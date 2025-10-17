import cv2
from utils.dedup import DedupStore
from utils.retry import retry
from utils.dlq import write_dlq
from utils.thread_log import log_start, log_end

class ResizeFilter:
    def __init__(self, width=None, height=None, keep_aspect_ratio=True, dedup_db="dedup.db"):
        self.width = width
        self.height = height
        self.keep_aspect_ratio = keep_aspect_ratio
        self.dedup = DedupStore(dedup_db)
        self.stage_name = "resize"

    @retry(max_attempts=3, backoff=0.2)
    def process_single(self, envelope):
        log_start(self.stage_name, envelope)
        try:
            id_ = envelope["id"]
            if self.stage_name in self.dedup.get_stages(id_):
                log_end(self.stage_name, envelope, status="skip")
                return envelope

            img = envelope.get("image")
            if img is None:
                raise ValueError("No image in envelope")

            h, w = img.shape[:2]
            if self.keep_aspect_ratio:
                if self.width and not self.height:
                    ratio = self.width / w
                    new_size = (self.width, int(h * ratio))
                elif self.height and not self.width:
                    ratio = self.height / h
                    new_size = (int(w * ratio), self.height)
                elif self.width and self.height:
                    new_size = (self.width, self.height)
                else:
                    log_end(self.stage_name, envelope)
                    return envelope
            else:
                new_size = (self.width or w, self.height or h)

            envelope["image"] = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
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
            out_envelope = self.process_single(envelope)
            if out_q:
                out_q.put(out_envelope)
            in_q.task_done()
