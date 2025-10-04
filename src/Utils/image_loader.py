# src/Utils/image_loader.py
# Nhiệm vụ: duyệt thư mục input, đọc ảnh bằng OpenCV (BGR), bơm từng item vào output_queue.
# Khi hết dữ liệu: gửi None để báo stage tiếp theo dừng.

import os
import glob
import cv2
from typing import Iterable, Optional

class ImageLoader:
    def __init__(self, input_dir: str = "data/input",
                 patterns: Optional[Iterable[str]] = None):
        """
        input_dir: thư mục chứa ảnh đầu vào
        patterns : các pattern file muốn đọc (mặc định: jpg/jpeg/png/bmp)
        """
        self.input_dir = input_dir
        self.patterns = list(patterns) if patterns else ["*.jpg", "*.jpeg", "*.png", "*.bmp"] 

    def process(self, input_queue, output_queue):
        """
        Source của pipeline -> không dùng input_queue.
        - Duyệt file -> cv2.imread(...) => ndarray BGR
        - Tạo item {id, path, image} -> put sang output_queue
        - Kết thúc: put(None)
        """
        idx = 0
        for pat in self.patterns:
            for fp in glob.iglob(os.path.join(self.input_dir, pat)): # fp là đường dẫn đầy đủ tới từng file
                img = cv2.imread(fp)          # đọc BGR (H, W, 3), dtype=uint8, đọc file thành mảng numpy kênh bgr
                if img is None:               # bỏ qua file lỗi/không phải ảnh
                    continue
                output_queue.put({
                    "id": idx,                # số thứ tự (giúp đặt tên khi lưu)
                    "path": fp,               # đường dẫn gốc (tham khảo/debug)
                    "image": img              # dữ liệu ảnh trong RAM
                })
                idx += 1

        # báo hết dữ liệu cho stage tiếp theo
        output_queue.put(None)
