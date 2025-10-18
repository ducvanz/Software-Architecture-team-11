# src/Utils/image_loader.py
# Nhiệm vụ: duyệt thư mục input, đọc ảnh bằng OpenCV (BGR), bơm từng item vào output_queue.
# Khi hết dữ liệu: gửi None để báo stage tiếp theo dừng.

import os
import glob
import uuid
from typing import Iterable, Optional
from queue import Queue

from Utils.constants import SENTINEL

class ImageLoader:
    """
    Source: pushes envelope with payload=path into output_queue, then emits
    SENTINEL equal to downstream_workers so all downstream workers exit cleanly.
    """
    def __init__(self, input_dir: str = "data/input",
                 patterns: Optional[Iterable[str]] = None,
                 downstream_workers: int = 1):
        self.input_dir = input_dir
        self.patterns = list(patterns) if patterns else ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
        self.downstream_workers = max(1, int(downstream_workers))

    def process(self, input_queue: Queue, output_queue: Queue):
        # Push envelopes (path-first)
        for pat in self.patterns:
            for fp in glob.iglob(os.path.join(self.input_dir, pat)):
                env = {
                    "id": str(uuid.uuid4()),
                    "payload": fp,
                    "meta": {"attempts": 0, "stage": 0, "orig_path": fp}
                }
                output_queue.put(env)
        # emit one SENTINEL per downstream worker so all workers can exit
        for _ in range(self.downstream_workers):
            output_queue.put(SENTINEL)
