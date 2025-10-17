# src/Utils/image_loader.py
# Nhiệm vụ: duyệt thư mục input, đọc ảnh bằng OpenCV (BGR), bơm từng item vào output_queue.
# Khi hết dữ liệu: gửi None để báo stage tiếp theo dừng.

import os
import glob
from typing import Iterable, Optional
from queue import Queue

class ImageLoader:
    """
    Path-first ImageLoader: put file path strings vào output_queue.
    ConvertFilter (stage tiếp theo) sẽ đọc file thành ndarray.
    """
    def __init__(self, input_dir: str = "data/input",
                 patterns: Optional[Iterable[str]] = None):
        self.input_dir = input_dir
        self.patterns = list(patterns) if patterns else ["*.jpg", "*.jpeg", "*.png", "*.bmp"]

    def process(self, input_queue: Queue, output_queue: Queue):
        # Input queue is ignored for a source; push file paths to output_queue
        for pat in self.patterns:
            for fp in glob.iglob(os.path.join(self.input_dir, pat)):
                output_queue.put(fp)
        # Signal end of stream
        output_queue.put(None)
