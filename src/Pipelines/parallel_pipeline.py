import os
import time
import threading
import traceback
from queue import Queue
from typing import List, Any, Callable

# Use the V2 filter implementations
from Filters.converter_v2 import ConvertFilterV2
from Filters.resize_v2 import ResizeFilterV2
from Filters.remove_background_v2 import RemoveBackgroundV2
from Filters.horizontal_flip_v2 import HorizontalFlipV2
from Filters.watermark_v2 import WatermarkV2
from Filters.output_filter_v2 import OutputFilterV2

from Utils.image_loader import ImageLoader
from Utils.constants import SENTINEL


class ParallelPipeline:
    """
    Pipeline using the V2 filters (envelope contract).
    Stages:
      ImageLoader -> ConvertFilterV2 -> ResizeFilterV2 -> RemoveBackgroundV2
      -> HorizontalFlipV2 -> WatermarkV2 -> OutputFilterV2
    """
    def __init__(self, input_dir: str, output_dir: str, n_workers: int = 2, resize_shape=(256,256), queue_size: int = 8):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.n_workers = max(1, int(n_workers))
        self.resize_shape = resize_shape
        self.queue_size = max(1, int(queue_size))

        # Use factories so each worker can get its own instance
        self.stage_factories = [
            lambda: ImageLoader(self.input_dir),
            lambda: ConvertFilterV2(),
            lambda: ResizeFilterV2(width=resize_shape[0], height=resize_shape[1], keep_aspect_ratio=True),
            lambda: RemoveBackgroundV2(),
            lambda: HorizontalFlipV2(),
            lambda: WatermarkV2(text="DemoWM"),
            lambda: OutputFilterV2(self.output_dir)
        ]

        self.num_stages = len(self.stage_factories)
        self.queues = [Queue(maxsize=self.queue_size) for _ in range(self.num_stages + 1)]
        self.metrics = [{"count":0, "errors":0, "total_time":0.0} for _ in range(self.num_stages)]
        self.threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

    def _make_instance(self, factory):
        try:
            return factory()
        except Exception:
            return factory

    def _stage_worker(self, stage_idx: int, factory: Callable):
        if stage_idx == 0:
            loader = self._make_instance(factory)
            try:
                loader.process(None, self.queues[1])
            except Exception as e:
                self.metrics[stage_idx]["errors"] += 1
                print(f"[Stage 0] loader error: {e}")
                traceback.print_exc()
                self.queues[1].put(SENTINEL)
            return

        filter_obj = None
        while not self._stop_event.is_set():
            try:
                item = self.queues[stage_idx].get()
            except Exception:
                continue

            if item is SENTINEL:
                # propagate sentinel once and exit
                self.queues[stage_idx+1].put(SENTINEL)
                try:
                    self.queues[stage_idx].task_done()
                except Exception:
                    pass
                break

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
                item_id = item.get("id") if isinstance(item, dict) else None
                print(f"[Stage {stage_idx}] Error processing item id={item_id}: {e}")
                traceback.print_exc()
                # push sentinel downstream for this worker to avoid blocking
                self.queues[stage_idx+1].put(SENTINEL)
            finally:
                try:
                    self.queues[stage_idx].task_done()
                except Exception:
                    pass

    def start(self):
        # producer thread (stage 0)
        t = threading.Thread(target=self._stage_worker, args=(0, self.stage_factories[0]), daemon=True)
        t.start()
        self.threads.append(t)

        # worker threads for other stages
        for stage_idx in range(1, self.num_stages):
            for w in range(self.n_workers):
                t = threading.Thread(target=self._stage_worker, args=(stage_idx, self.stage_factories[stage_idx]), daemon=True)
                t.start()
                self.threads.append(t)
            # print stage name for visibility
            try:
                name = self.stage_factories[stage_idx]().__class__.__name__
            except Exception:
                name = f"stage-{stage_idx}"
            print(f"[Pipeline] Started stage {stage_idx} ({name}) with {self.n_workers} worker(s)")

    def stop(self, timeout: float = 5.0):
        self._stop_event.set()
        for q in self.queues:
            try:
                q.put_nowait(SENTINEL)
            except Exception:
                pass
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

