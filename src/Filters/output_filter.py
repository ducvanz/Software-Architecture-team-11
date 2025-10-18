import os
import cv2
import threading
import uuid
from typing import Any, Dict

class OutputFilter:
    """
    Thread-safe output filter: saves images with unique filenames.
    process(envelope) -> envelope with payload = saved_path
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._counter = 0
        self._lock = threading.Lock()

    def process(self, envelope: Any) -> Dict:
        # accept envelope or raw ndarray
        if isinstance(envelope, dict) and "payload" in envelope:
            env = envelope
            img = env["payload"]
        else:
            img = envelope
            env = {"id": None, "payload": img, "meta": {}}

        if img is None:
            raise ValueError("OutputFilter: payload is None, cannot save.")

        with self._lock:
            self._counter += 1
            idx = self._counter

        filename = f"output_{idx:03d}_{uuid.uuid4().hex[:8]}.jpg"
        output_path = os.path.join(self.output_dir, filename)

        success = cv2.imwrite(output_path, img)
        if not success:
            raise IOError(f"OutputFilter: failed to write image to {output_path}")

        env["payload"] = output_path
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env
