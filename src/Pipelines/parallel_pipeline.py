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
from Utils.metrics import MetricsCollector


class ParallelPipeline:
    def __init__(self, input_dir: str, output_dir: str, n_workers: int = 2, resize_shape=(256,256), queue_size: int = 8):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.n_workers = max(1, int(n_workers))
        self.resize_shape = resize_shape
        self.queue_size = max(1, int(queue_size))

        # ImageLoader receives downstream_workers so it emits correct number of sentinels
        self.stage_factories = [
            lambda: ImageLoader(self.input_dir, downstream_workers=self.n_workers),
            lambda: ConvertFilterV2(),
            lambda: ResizeFilterV2(width=resize_shape[0], height=resize_shape[1], keep_aspect_ratio=True),
            lambda: RemoveBackgroundV2(),
            lambda: HorizontalFlipV2(),
            lambda: WatermarkV2(text="DemoWM"),
            lambda: OutputFilterV2(self.output_dir)
        ]

        self.num_stages = len(self.stage_factories)
        self.queues = [Queue(maxsize=self.queue_size) for _ in range(self.num_stages + 1)]
        self.metrics = MetricsCollector(self.num_stages)
        self.threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

    def _make_instance(self, factory):
        try:
            return factory()
        except Exception:
            return factory

    def _stage_worker(self, stage_idx: int, factory: Callable):
        """
        stage_idx: 0 .. num_stages-1
        stage 0 is the ImageLoader (producer) which writes to queues[1]
        other stages consume from queues[stage_idx] and write to queues[stage_idx+1]
        """
        if stage_idx == 0:
            loader = self._make_instance(factory)
            try:
                loader.process(None, self.queues[1])
            except Exception as e:
                self.metrics.record_error(stage_idx)
                print(f"[Stage 0] loader error: {e}")
                traceback.print_exc()
                # ensure downstream not blocked
                self.queues[1].put(SENTINEL)
            return

        filter_obj = None
        in_q = self.queues[stage_idx]
        out_q = self.queues[stage_idx + 1]
        while not self._stop_event.is_set():
            try:
                item = in_q.get()
            except Exception:
                continue

            if item is SENTINEL:
                # forward sentinel once and mark task done
                out_q.put(SENTINEL)
                try:
                    in_q.task_done()
                except Exception:
                    pass
                break

            if filter_obj is None:
                filter_obj = self._make_instance(factory)

            start = time.time()
            try:
                result_env = filter_obj.process(item)
                elapsed = time.time() - start
                self.metrics.record_success(stage_idx, elapsed)
                # push downstream
                out_q.put(result_env)
            except Exception as e:
                self.metrics.record_error(stage_idx)
                item_id = item.get("id") if isinstance(item, dict) else None
                print(f"[Stage {stage_idx}] Error processing item id={item_id}: {e}")
                traceback.print_exc()
                # push sentinel downstream for this worker to avoid blocking (keeps pipeline progressing)
                out_q.put(SENTINEL)
            finally:
                try:
                    in_q.task_done()
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
            # print stage class name for visibility
            try:
                name = self.stage_factories[stage_idx]().__class__.__name__
            except Exception:
                name = f"stage-{stage_idx}"
            print(f"[Pipeline] Started stage {stage_idx} ({name}) with {self.n_workers} worker(s)")

    def stop(self, timeout: float = 5.0):
        # request stop and push sentinels to unblock queues
        self._stop_event.set()
        for q in self.queues:
            try:
                q.put_nowait(SENTINEL)
            except Exception:
                pass

        # attempt graceful join of threads
        deadline = time.time() + timeout
        for t in self.threads:
            remaining = max(0.0, deadline - time.time())
            t.join(remaining)

    def wait_for_completion(self, timeout: float = None):
        """
        Block until all queued tasks are marked done (queue.join) for all inter-stage queues.
        After that, join worker threads (short timeout) and return.
        """
        start = time.time()
        for q in self.queues[1:]:
            if timeout is None:
                q.join()
            else:
                # approximate timed join by polling unfinished_tasks
                end = start + timeout
                while getattr(q, "unfinished_tasks", 0) > 0 and time.time() < end:
                    time.sleep(0.05)
        # give threads a moment to exit after sentinels processed
        for t in self.threads:
            t.join(0.5)

    def print_metrics(self):
        snap = self.metrics.snapshot()
        lines = []
        # include queue sizes between stages; queues indices 1..num_stages correspond to after stage 0..num_stages-1
        for entry in snap:
            idx = entry["stage"]
            q_idx = idx + 1
            qsize = self.queues[q_idx].qsize() if q_idx < len(self.queues) else 0
            lines.append(f"Stage {idx+1}: processed={entry['processed']}, errors={entry['errors']}, avg_latency={entry['avg_latency']:.4f}s, queue_size={qsize}")
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

