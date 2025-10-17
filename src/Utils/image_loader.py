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
    Path-first ImageLoader: put envelope (dict) into output_queue.
    ConvertFilter (stage tiếp theo) sẽ đọc envelope['payload'] (path) -> ndarray.
    """
    def __init__(self, input_dir: str = "data/input",
                 patterns: Optional[Iterable[str]] = None):
        self.input_dir = input_dir
        self.patterns = list(patterns) if patterns else ["*.jpg", "*.jpeg", "*.png", "*.bmp"]

    def process(self, input_queue: Queue, output_queue: Queue):
        # Input queue is ignored for a source; push envelopes to output_queue
        for pat in self.patterns:
            for fp in glob.iglob(os.path.join(self.input_dir, pat)):
                env = {
                    "id": str(uuid.uuid4()),
                    "payload": fp,
                    "meta": {"attempts": 0, "stage": 0, "orig_path": fp}
                }
                output_queue.put(env)
        # Signal end of stream using SENTINEL
        output_queue.put(SENTINEL)
