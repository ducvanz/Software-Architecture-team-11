import cv2
import numpy as np
from typing import Any, Dict

class ResizeFilter:
    """
    Envelope in: payload = ndarray
    Envelope out: payload = resized ndarray
    """
    def __init__(self, width: int = None, height: int = None, keep_aspect_ratio: bool = True):
        self.width = width
        self.height = height
        self.keep_aspect_ratio = keep_aspect_ratio

    def process(self, envelope: Any) -> Dict:
        if isinstance(envelope, dict) and "payload" in envelope:
            env = envelope
            img = env["payload"]
        else:
            # legacy raw ndarray
            img = envelope
            env = {"id": None, "payload": img, "meta": {}}

        if img is None:
            raise ValueError("ResizeFilter: payload is None")

        h, w = img.shape[:2]
        if self.width is None and self.height is None:
            resized = img
        else:
            if self.keep_aspect_ratio:
                if self.width is None:
                    scale = self.height / float(h)
                elif self.height is None:
                    scale = self.width / float(w)
                else:
                    scale = min(self.width / float(w), self.height / float(h))
                new_w = max(1, int(round(w * scale)))
                new_h = max(1, int(round(h * scale)))
            else:
                new_w = self.width if self.width is not None else w
                new_h = self.height if self.height is not None else h
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        env["payload"] = resized
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env
