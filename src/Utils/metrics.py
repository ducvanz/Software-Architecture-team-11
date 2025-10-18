import threading
import time
from typing import List, Dict, Any

class MetricsCollector:
    """
    Thread-safe per-stage metrics: count, errors, total_time.
    Use record_success / record_error from workers.
    """
    def __init__(self, num_stages: int):
        self._lock = threading.Lock()
        self._num_stages = max(0, int(num_stages))
        self._counts = [0] * self._num_stages
        self._errors = [0] * self._num_stages
        self._total_time = [0.0] * self._num_stages
        self._last_report_ts = time.time()

    def record_success(self, stage_idx: int, elapsed: float):
        if stage_idx < 0 or stage_idx >= self._num_stages:
            return
        with self._lock:
            self._counts[stage_idx] += 1
            self._total_time[stage_idx] += float(elapsed)

    def record_error(self, stage_idx: int):
        if stage_idx < 0 or stage_idx >= self._num_stages:
            return
        with self._lock:
            self._errors[stage_idx] += 1

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            out = []
            for i in range(self._num_stages):
                count = self._counts[i]
                total = self._total_time[i]
                errors = self._errors[i]
                avg = (total / count) if count else 0.0
                out.append({"stage": i, "processed": count, "errors": errors, "avg_latency": avg, "total_time": total})
            return out

    def reset(self):
        with self._lock:
            self._counts = [0] * self._num_stages
            self._errors = [0] * self._num_stages
            self._total_time = [0.0] * self._num_stages