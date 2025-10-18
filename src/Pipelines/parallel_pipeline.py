import os
import time
import threading
import traceback
from queue import Queue
from typing import List, Any, Callable

from Filters.converter import ConvertFilter
from Filters.resize import ResizeFilter
from Filters.grayscale_blur import GrayscaleBlur
from Filters.edge_detector import EdgeDetector
from Filters.watermark import Watermark
from Filters.output_filter import OutputFilter
from Utils.image_loader import ImageLoader
from Utils.constants import SENTINEL


class ParallelPipeline:
    """
    Orchestrates stages (path-first):
      ImageLoader -> ConvertFilter -> Resize -> GrayscaleBlur -> EdgeDetector -> Watermark -> OutputFilter

    Features:
      - per-stage queues (bounded for backpressure)
      - n_workers per stage (elasticity)
      - per-stage metrics (count, errors, avg_latency)
      - graceful shutdown and sentinel propagation (SENTINEL)
      - fault tolerance: exceptions in filter processing are caught and counted
    """
    def __init__(self, input_dir: str, output_dir: str, n_workers: int = 2, resize_shape=(256,256), queue_size: int = 8):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.n_workers = max(1, int(n_workers))
        self.resize_shape = resize_shape
        self.queue_size = max(1, int(queue_size))

        # Stage factories/instances (use callables to make per-worker instances)
        self.stage_factories = [
            lambda: ImageLoader(self.input_dir),                      # source (will use process(input_q, output_q))
            lambda: ConvertFilter(),                                  # envelope (path) -> envelope (ndarray)
            lambda: ResizeFilter(width=resize_shape[0], height=resize_shape[1], keep_aspect_ratio=True),
            lambda: GrayscaleBlur(ksize=5, sigmaX=1.2, keep_3_channels=False),
            lambda: EdgeDetector(method="canny"),
            lambda: Watermark(text="DemoWM", alpha=0.35),
            lambda: OutputFilter(self.output_dir)
        ]

        self.num_stages = len(self.stage_factories)
        # create queues between stages (num_stages + 1 endpoints)
        self.queues = [Queue(maxsize=self.queue_size) for _ in range(self.num_stages + 1)]
        # metrics per stage (processing happens in workers consuming queues[i] and putting to queues[i+1])
        self.metrics = [{"count":0, "errors":0, "total_time":0.0} for _ in range(self.num_stages)]
        self.threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

    def _make_instance(self, factory):
        try:
            return factory()
        except Exception:
            return factory  # in case it's already an instance

    def _stage_worker(self, stage_idx: int, factory: Callable):
        """
        Worker: consumes from queues[stage_idx], applies filter.process, pushes to queues[stage_idx+1].
        Special-case: stage 0 is ImageLoader.process(input_q, output_q) which expects to be run as a producer.
        """
        if stage_idx == 0:
            # Source: run loader with input_queue ignored
            loader = self._make_instance(factory)
            try:
                loader.process(None, self.queues[1])
            except Exception as e:
                # record error and propagate sentinel so pipeline can finish
                self.metrics[stage_idx]["errors"] += 1
                print(f"[Stage 0] loader error: {e}")
                traceback.print_exc()
                self.queues[1].put(SENTINEL)
            return

        # Regular stage workers
        filter_obj = None
        while not self._stop_event.is_set():
            try:
                item = self.queues[stage_idx].get()
            except Exception:
                continue

            # check sentinel (object) propagation
            if item is SENTINEL:
                # forward sentinel to next queue once per worker termination
                self.queues[stage_idx+1].put(SENTINEL)
                self.queues[stage_idx].task_done()
                break

            # ensure each worker has own instance if factory callable
            if filter_obj is None:
                filter_obj = self._make_instance(factory)

            start = time.time()
            try:
                result_env = filter_obj.process(item)
                elapsed = time.time() - start
                self.metrics[stage_idx]["count"] += 1
                self.metrics[stage_idx]["total_time"] += elapsed
                self.queues[stage_idx+1].put(result_env)
            except Exception as e:
                self.metrics[stage_idx]["errors"] += 1
                # log with id if available
                item_id = item.get("id") if isinstance(item, dict) else None
                print(f"[Stage {stage_idx}] Error processing item id={item_id}: {e}")
                traceback.print_exc()
                # push sentinel for downstream to avoid blocking
                self.queues[stage_idx+1].put(SENTINEL)
            finally:
                try:
                    self.queues[stage_idx].task_done()
                except Exception:
                    pass

    def start(self):
        # spawn threads: stage 0 has one thread (producer), other stages have n_workers each
        # Stage 0 --> index 1 queue (loader puts to queues[1]); we keep queues[0] unused for symmetry
        # launch producer (stage 0)
        t = threading.Thread(target=self._stage_worker, args=(0, self.stage_factories[0]), daemon=True)
        t.start()
        self.threads.append(t)

        # launch workers for other stages
        for stage_idx in range(1, self.num_stages):
            for w in range(self.n_workers):
                t = threading.Thread(target=self._stage_worker, args=(stage_idx, self.stage_factories[stage_idx]), daemon=True)
                t.start()
                self.threads.append(t)

    def stop(self, timeout: float = 5.0):
        # signal stop to threads (won't stop if blocked on queue.get unless sentinel arrives)
        self._stop_event.set()
        # push sentinels to all queues to unblock
        for q in self.queues:
            try:
                q.put_nowait(SENTINEL)
            except Exception:
                pass
        # join threads
        for t in self.threads:
            t.join(timeout)

    def print_metrics(self):
        lines = []
        for idx, m in enumerate(self.metrics, start=1):
            count = m["count"]
            avg_latency = (m["total_time"] / count) if count else 0.0
            lines.append(f"Stage {idx}: processed={count}, errors={m['errors']}, avg_latency={avg_latency:.4f}s")
        print("\n".join(lines))


if __name__ == "__main__":
    # quick local run (ensure data/input has images)
    p = ParallelPipeline(input_dir="data/input", output_dir="data/output", n_workers=2, resize_shape=(300,300))
    p.start()
    try:
        # wait until threads finish (monitoring)
        while any(t.is_alive() for t in p.threads):
            time.sleep(1.0)
            p.print_metrics()
    except KeyboardInterrupt:
        p.stop()
    p.print_metrics()

