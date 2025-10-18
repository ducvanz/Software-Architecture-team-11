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
from Utils.retry import call_with_retry
from Utils.dlq import write_dlq


class ParallelPipeline:
    def __init__(self, input_dir: str, output_dir: str, n_workers: int = 2, resize_shape=(256,256), queue_size: int = 8, max_attempts: int = 3, retry_backoff: float = 0.2, dlq_dir: str = None):
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
        self.max_attempts = int(max_attempts)
        self.retry_backoff = float(retry_backoff)
        self.dlq_dir = dlq_dir  # passed to write_dlq if provided

    def _make_instance(self, factory):
        try:
            return factory()
        except Exception:
            return None

    def _stage_worker(self, stage_idx: int, factory: Callable):
        """\
        stage_idx: 0 .. num_stages-1
        stage 0 is the ImageLoader (producer) which writes to queues[1]
        other stages consume from queues[stage_idx] and write to queues[stage_idx+1]
        """
        filter_obj = None
        in_q = self.queues[stage_idx]
        # determine out_q only if a downstream consumer exists
        out_q = self.queues[stage_idx + 1] if (stage_idx + 1) < len(self.queues) else None

        while not self._stop_event.is_set():
            try:
                item = in_q.get()
            except Exception:
                continue

            if item is SENTINEL:
                # forward sentinel only if there is a downstream queue / consumer
                if out_q is not None:
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
                # use retry wrapper which mutates envelope['meta']['attempts']
                result_env = call_with_retry(filter_obj.process, item, max_attempts=self.max_attempts, backoff=self.retry_backoff)
                elapsed = time.time() - start
                self.metrics.record_success(stage_idx, elapsed)
                if out_q is not None:
                    out_q.put(result_env)
            except Exception as e:
                # NO sentinel push on per-item processing error anymore
                self.metrics.record_error(stage_idx)
                item_id = item.get("id") if isinstance(item, dict) else None
                trace = traceback.format_exc()
                print(f"[Stage {stage_idx}] Error processing item id={item_id}: {e}\n{trace}")
                # write DLQ entry (best-effort)
                try:
                    write_dlq(item, str(e), exc_trace=trace, dlq_dir=self.dlq_dir)
                except Exception as dlq_e:
                    print(f"[Pipeline] Failed to write DLQ: {dlq_e}")
                # continue to next item (do not push sentinel)
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
        Block until all queued tasks are marked done for queues that have consumers.
        We only join queues[1:self.num_stages] because queues[num_stages] is the sink buffer with no consumer.
        """
        start = time.time()
        # join only queues that have consumers: queues[1] .. queues[num_stages-1]
        for q in self.queues[1:self.num_stages]:
            if timeout is None:
                q.join()
            else:
                end = start + timeout
                while getattr(q, "unfinished_tasks", 0) > 0 and time.time() < end:
                    time.sleep(0.05)
        # give threads a moment to exit after sentinels processed
        for t in self.threads:
            t.join(0.5)

    def print_metrics(self):
        snap = self.metrics.snapshot()
        lines = []
        # include queue sizes between stages; only for queues with consumers (queues[1..num_stages-1])
        for entry in snap:
            idx = entry["stage"]
            q_idx = idx + 1
            # only report queue_size when the queue has a downstream consumer
            if 1 <= q_idx < len(self.queues) - 1:
                qsize = self.queues[q_idx].qsize()
            else:
                qsize = 0
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

