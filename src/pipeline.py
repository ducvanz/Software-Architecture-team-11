# file: Pipeline/ParallelPipeline.py

import os
import threading
from queue import Queue
import time # <-- Đã thêm import time

from Filters.converter import ConvertFilter
from Filters.resize import ResizeFilter
from Filters.remove_background import RemoveBackground
from Filters.horizontal_flip import HorizontalFlip
from Filters.watermark import Watermark
from Filters.output_filter import OutputFilter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

class ParallelPipeline:
    def __init__(self, n_workers=2, resize_shape=(500, 500)):
        self.input_dir = os.path.join(DATA_DIR, "input")
        self.output_dir = os.path.join(DATA_DIR, "output")
        self.n_workers = max(1, n_workers)
        os.makedirs(self.output_dir, exist_ok=True)

        # Cần 6 Queue cho 5 filter + OutputFilter. Kích thước Queue (maxsize=8)
        self.queues = [Queue(maxsize=8) for _ in range(6)]

        self.stages = [
            (ConvertFilter(), self.queues[0], self.queues[1]),
            (ResizeFilter(resize_shape[0], resize_shape[1]), self.queues[1], self.queues[2]),
            (RemoveBackground(), self.queues[2], self.queues[3]),
            (HorizontalFlip(), self.queues[3], self.queues[4]),
            (Watermark("Team 11"), self.queues[4], self.queues[5]),
            (OutputFilter(self.output_dir), self.queues[5], None),
        ]
        self.threads = []

    def start(self):
        if not os.path.exists(self.input_dir):
            raise FileNotFoundError(f"Input directory not found: {self.input_dir}")
        
        # Bắt đầu tính thời gian
        start_time = time.time() # <-- Bắt đầu tính
        
        # Khởi động worker threads trước
        for i, (filter_obj, in_q, out_q) in enumerate(self.stages):
            for j in range(self.n_workers):
                # Đặt tên thread rõ ràng hơn để dễ debug
                thread_name = f"Thread-{i}-{filter_obj.stage_name}-{j}"
                t = threading.Thread(target=filter_obj.process, args=(in_q, out_q), name=thread_name, daemon=True)
                t.start()
                self.threads.append(t)
            print(f"[Pipeline] Started stage {i} ({filter_obj.__class__.__name__}) with {self.n_workers} worker(s)")

        # Đưa files vào Queue đầu tiên
        count = 0
        file_names = os.listdir(self.input_dir)
        for fn in file_names:
            if fn.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                # Blocking put là an toàn ở đây
                self.queues[0].put(os.path.join(self.input_dir, fn)) 
                count += 1
        print(f"[Pipeline] Enqueued {count} files from {self.input_dir}")

        # Gửi sentinel None cho mỗi worker của stage 0
        for _ in range(self.n_workers):
            self.queues[0].put(None)

        # Chờ tất cả các tác vụ trong Queue hoàn thành
        for in_q in self.queues:
            in_q.join() 
            
        print("[Pipeline] All tasks done in all queues. Shutting down threads.")
        
        # Chờ tất cả threads thoát
        for t in self.threads:
             if t.is_alive():
                 t.join(timeout=1) # Chờ một chút để thread thoát an toàn

        end_time = time.time() # <-- Kết thúc tính
        duration = end_time - start_time
        
        # In kết quả thời gian
        print("-" * 50)
        print("[Pipeline] Completed all stages.")
        print(f"TỔNG KẾT HIỆU SUẤT PIPELINE SONG SONG:")
        print(f"Tổng số file xử lý: {count}")
        print(f"Thời gian thực thi: {duration:.4f} giây")
        print("-" * 50)


if __name__ == "__main__":
    pipeline = ParallelPipeline(n_workers=4, resize_shape=(500, 500))
    pipeline.start()