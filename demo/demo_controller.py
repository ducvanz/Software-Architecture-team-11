"""
Demo Controller - Bridge between UI and Pipeline
Chức năng:
- Khởi tạo ParallelPipeline
- Quản lý trạng thái demo (running, paused, completed)
- Thu thập metrics hiệu năng
- Cập nhật real-time data cho visualization
- Xử lý events từ UI
"""

import time
from src.Pipelines.parallel_pipeline import ParallelPipeline

class DemoController:
    """
    Simple controller to start pipeline and periodically print metrics.
    Use to demonstrate throughput, fault-tolerance, modularity, elasticity.
    """
    def __init__(self, input_dir="data/input", output_dir="data/output", workers=2):
        self.pipeline = ParallelPipeline(input_dir=input_dir, output_dir=output_dir, n_workers=workers)

    def run_blocking(self):
        self.pipeline.start()
        try:
            while any(t.is_alive() for t in self.pipeline.threads):
                time.sleep(1.0)
                self.pipeline.print_metrics()
        except KeyboardInterrupt:
            self.pipeline.stop()
        finally:
            self.pipeline.print_metrics()