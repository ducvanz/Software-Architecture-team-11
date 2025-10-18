import cv2
import numpy as np
from typing import Any, Dict

class EdgeDetector:
    def __init__(self, method="canny", threshold1=100, threshold2=200):
        self.method = method
        self.threshold1 = threshold1
        self.threshold2 = threshold2

    def process(self, envelope: Any) -> Dict:
        if isinstance(envelope, dict) and "payload" in envelope:
            env = envelope
            img = env["payload"]
        else:
            img = envelope
            env = {"id": None, "payload": img, "meta": {}}

        if img is None:
            raise ValueError("EdgeDetector: payload is None")

        arr = np.array(img)
        # Expect grayscale input; if 3-channel, convert
        if arr.ndim == 3 and arr.shape[2] >= 3:
            gray = cv2.cvtColor(arr[..., :3], cv2.COLOR_BGR2GRAY)
        elif arr.ndim == 2:
            gray = arr
        else:
            raise ValueError(f"Unsupported image shape for EdgeDetector: {arr.shape}")

        if self.method == "canny":
            edges = cv2.Canny(gray, self.threshold1, self.threshold2)
        else:
            # fallback: use simple Laplacian
            edges = cv2.Laplacian(gray, cv2.CV_8U)

        env["payload"] = edges
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env
