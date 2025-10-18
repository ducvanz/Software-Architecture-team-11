import cv2
import numpy as np
from typing import Any, Dict, Tuple

class ResizeFilterV2:
    """
    Envelope in: payload = ndarray
    Envelope out: payload = resized ndarray
    """
    def __init__(self, width: int = None, height: int = None, keep_aspect_ratio: bool = True):
        self.width = width
        self.height = height
        self.keep_aspect_ratio = keep_aspect_ratio

    def process(self, envelope: Any) -> Dict:
        env = dict(envelope) if isinstance(envelope, dict) else {"id": None, "payload": envelope, "meta": {}}
        img = env.get("payload")
        if img is None:
            raise ValueError("ResizeFilterV2: payload is None")

        arr = np.array(img)
        h, w = arr.shape[:2]

        if self.width is None and self.height is None:
            resized = arr
        else:
            if self.keep_aspect_ratio and self.width and self.height:
                scale = min(self.width / float(w), self.height / float(h))
                new_w = max(1, int(round(w * scale)))
                new_h = max(1, int(round(h * scale)))
            elif self.keep_aspect_ratio and self.width and not self.height:
                scale = self.width / float(w)
                new_w = self.width
                new_h = max(1, int(round(h * scale)))
            elif self.keep_aspect_ratio and self.height and not self.width:
                scale = self.height / float(h)
                new_h = self.height
                new_w = max(1, int(round(w * scale)))
            else:
                new_w = self.width or w
                new_h = self.height or h
            resized = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_AREA)

        env["payload"] = resized
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env