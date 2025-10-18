import cv2
import numpy as np
from typing import Any, Dict

try:
    from rembg import remove as rembg_remove
except Exception:
    rembg_remove = None

class RemoveBackgroundV2:
    """
    Envelope in: payload = BGR ndarray
    Envelope out: payload = BGR ndarray with background removed + checkerboard fill if rembg unavailable.
    """
    def __init__(self, checker_size: int = 20):
        self.checker_size = checker_size

    def _create_checkerboard(self, w: int, h: int) -> np.ndarray:
        img = np.zeros((h, w, 3), np.uint8)
        for y in range(0, h, self.checker_size):
            for x in range(0, w, self.checker_size):
                color = (255,255,255) if ((x//self.checker_size + y//self.checker_size) % 2)==0 else (200,200,200)
                cv2.rectangle(img, (x,y), (min(x+self.checker_size, w)-1, min(y+self.checker_size, h)-1), color, -1)
        return img

    def process(self, envelope: Any) -> Dict:
        env = dict(envelope) if isinstance(envelope, dict) else {"id": None, "payload": envelope, "meta": {}}
        img = env.get("payload")
        if img is None:
            raise ValueError("RemoveBackgroundV2: payload is None")

        arr = np.array(img)
        h, w = arr.shape[:2]

        if rembg_remove is not None:
            try:
                rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
                rgba = rembg_remove(rgb)  # may return ndarray with alpha
                if rgba is None:
                    raise RuntimeError("rembg returned None")
                alpha = rgba[:,:,3].astype(np.float32) / 255.0
                fg = rgba[:,:,:3].astype(np.float32)
                bg = cv2.cvtColor(self._create_checkerboard(w,h), cv2.COLOR_BGR2RGB).astype(np.float32)
                combined = (fg * alpha[:,:,None] + bg * (1 - alpha[:,:,None])).astype(np.uint8)
                out = cv2.cvtColor(combined, cv2.COLOR_RGB2BGR)
            except Exception:
                # fallback to checkerboard if rembg fails
                out = self._create_checkerboard(w, h)
        else:
            out = self._create_checkerboard(w, h)

        env["payload"] = out
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env