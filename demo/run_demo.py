import os
import sys
import time

# Ensure imports like "from Filters..." resolve by adding src/ to sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # d:\KTPM_demo
SRC_DIR = os.path.join(ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Import the pipeline (which expects to import Filters, Utils from src/)
from Pipelines.parallel_pipeline import ParallelPipeline

def main():
    input_dir = os.path.join(ROOT, "data", "input")
    output_dir = os.path.join(ROOT, "data", "output")
    # ensure directories exist
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    p = ParallelPipeline(input_dir=input_dir, output_dir=output_dir, n_workers=2, resize_shape=(300,300), queue_size=8)
    p.start()
    try:
        while any(t.is_alive() for t in p.threads):
            time.sleep(1.0)
            p.print_metrics()
    except KeyboardInterrupt:
        p.stop()
    finally:
        p.print_metrics()

if __name__ == "__main__":
    main()