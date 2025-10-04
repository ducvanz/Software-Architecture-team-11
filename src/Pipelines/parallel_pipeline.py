import os
import threading
from queue import Queue
from ..Filters.converter import ConvertFilter
from ..Filters.resize import ResizeFilter
from ..Filters.output_filter import OutputFilter
from ..Filters.grayscale_blur import GrayscaleBlur
from ..Filters.edge_detector import EdgeDetector
from ..Filters.watermark import Watermark


class ParallelPipeline:
    """
    Pipeline xử lý ảnh song song gồm nhiều Filter.
    Dữ liệu đi qua: path → img → img → ... → output. img là mảng numpy (BGR).
    """
    def __init__(self, input_dir, output_dir, n_threads=2, resize_shape=(256, 256)):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.n_threads = n_threads
        os.makedirs(output_dir, exist_ok=True)

        # 6 queue cho tối đa 6 filter
        self.queues = [Queue() for _ in range(6)]

        # Định nghĩa pipeline — chỉ bật các filter cần thiết
        self.filters = [
            (ConvertFilter(), self.queues[0], self.queues[1]),       # path → image (BGR)
            (ResizeFilter(resize_shape[0], resize_shape[1]), self.queues[1], self.queues[2]),  # image → image
            # (GrayscaleBlur(), self.queues[2], self.queues[3]),      # image → image
            # (EdgeDetector(), self.queues[3], self.queues[4]),       # image → image
            # (Watermark("Team 11"), self.queues[4], self.queues[5]), # image → image
            (OutputFilter(output_dir), self.queues[2], None)         # image → ghi file
        ]

        self.threads = []
        print("Pipeline initialized: Convert → Resize → (optional filters) → Output")

    def start(self):
        """Khởi động pipeline song song"""
        input_paths = [
            os.path.join(self.input_dir, f)
            for f in os.listdir(self.input_dir)
            if f.lower().endswith((".jpg", ".png", ".jpeg"))
        ]

        print(f"Found {len(input_paths)} image(s) in {self.input_dir}")
        for path in input_paths:
            self.queues[0].put(path)

        # Tạo thread cho từng filter
        for filter_obj, input_q, output_q in self.filters:
            for _ in range(self.n_threads):
                t = threading.Thread(
                    target=self._worker,
                    args=(filter_obj, input_q, output_q),
                    daemon=True
                )
                self.threads.append(t)
                t.start()

        # Gửi tín hiệu kết thúc cho ConvertFilter
        for _ in range(self.n_threads):
            self.queues[0].put(None)

        # Chờ toàn bộ thread kết thúc
        for t in self.threads:
            t.join()

        print("Pipeline completed successfully!")

    def _worker(self, filter_obj, input_q, output_q):
        """Luồng xử lý riêng cho mỗi filter"""
        while True:
            item = input_q.get()
            if item is None:
                if output_q:
                    output_q.put(None)
                input_q.task_done()
                break

            try:
                # ConvertFilter: nhận path
                if isinstance(filter_obj, ConvertFilter):
                    result = filter_obj.process(item)

                # OutputFilter: nhận ảnh, ghi ra file
                elif isinstance(filter_obj, OutputFilter):
                    filter_obj.process(item)
                    result = None

                # Các filter còn lại: nhận ảnh, trả ảnh
                else:
                    result = filter_obj.process(item)

                # Truyền qua filter kế tiếp nếu có output queue
                if output_q and result is not None:
                    output_q.put(result)

            except Exception as e:
                print(f"Error in {filter_obj.__class__.__name__}: {e}")
            finally:
                input_q.task_done()

    def stop(self):
        """Dừng pipeline thủ công (nếu cần)"""
        for q in self.queues:
            while not q.empty():
                q.get_nowait()
        print("Pipeline stopped.")


if __name__ == "__main__":
    pipeline = ParallelPipeline(
        input_dir="data/input",
        output_dir="data/output",
        n_threads=2,
        resize_shape=(500, 500)
    )
    pipeline.start()

