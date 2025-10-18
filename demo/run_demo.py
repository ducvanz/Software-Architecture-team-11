import os
import sys
import time
import argparse

# Ensure src is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # d:\KTPM_demo
SRC_DIR = os.path.join(ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from Pipelines.parallel_pipeline import ParallelPipeline

def main():
    p = argparse.ArgumentParser(description="Run demo pipeline")
    p.add_argument("--n-workers", type=int, default=2, help="Number of workers per stage")
    p.add_argument("--queue-size", type=int, default=8, help="Bounded queue size between stages")
    p.add_argument("--resize", type=str, default="256x256", help="Resize WxH (e.g. 300x200)")
    p.add_argument("--input", type=str, default=os.path.join(ROOT, "data", "input"))
    p.add_argument("--output", type=str, default=os.path.join(ROOT, "data", "output"))
    args = p.parse_args()

    try:
        w,h = (int(x) for x in args.resize.split("x"))
    except Exception:
        w,h = 256,256

    os.makedirs(args.input, exist_ok=True)
    os.makedirs(args.output, exist_ok=True)

    pipeline = ParallelPipeline(input_dir=args.input, output_dir=args.output, n_workers=args.n_workers, resize_shape=(w,h), queue_size=args.queue_size)
    pipeline.start()

    try:
        # Wait until pipeline completes processing all input images
        pipeline.wait_for_completion(timeout=None)
    except KeyboardInterrupt:
        print("Interrupted — stopping pipeline")
        pipeline.stop()
    finally:
        pipeline.print_metrics()
        pipeline.stop()
        pipeline.wait_for_completion(timeout=2.0)

if __name__ == "__main__":
    main()