import cv2
import numpy as np
from typing import Any, Dict

class HorizontalFlipV2:
    """
    Flip payload horizontally.
    Input/output: envelope with payload = ndarray
    """
    def process(self, envelope: Any) -> Dict:
        env = dict(envelope) if isinstance(envelope, dict) else {"id": None, "payload": envelope, "meta": {}}
        img = env.get("payload")
        if img is None:
            raise ValueError("HorizontalFlipV2: payload is None")
        arr = np.array(img)
        flipped = cv2.flip(arr, 1)
        env["payload"] = flipped
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env