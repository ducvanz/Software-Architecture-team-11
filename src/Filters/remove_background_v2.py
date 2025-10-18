import cv2
import numpy as np
from typing import Any, Dict

try:
    from rembg import remove as rembg_remove
except Exception:
    rembg_remove = None

class RemoveBackgroundV2:
    """
    Use rembg if available. If not available or on error, return original image.
    Input/output: envelope.payload = ndarray (BGR)
    """
    def __init__(self, use_checkerboard_on_success: bool = False, checker_size:int=20):
        self.use_checkerboard_on_success = use_checkerboard_on_success
        self.checker_size = checker_size

    def _create_checkerboard(self, w: int, h: int, tile: int = 20) -> np.ndarray:
        img = np.zeros((h, w, 3), np.uint8)
        for y in range(0, h, tile):
            for x in range(0, w, tile):
                color = (255,255,255) if ((x//tile + y//tile) % 2)==0 else (200,200,200)
                cv2.rectangle(img, (x,y), (min(x+tile, w)-1, min(y+tile, h)-1), color, -1)
        return img

    def process(self, envelope: Any) -> Dict:
        env = dict(envelope) if isinstance(envelope, dict) else {"id": None, "payload": envelope, "meta": {}}
        img = env.get("payload")
        if img is None:
            raise ValueError("RemoveBackgroundV2: payload is None")
        arr = np.array(img)
        h, w = arr.shape[:2]

        if rembg_remove is None:
            env["payload"] = arr
        else:
            try:
                rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
                rgba = rembg_remove(rgb)
                if rgba is None:
                    env["payload"] = arr
                else:
                    if rgba.ndim == 3 and rgba.shape[2] == 4:
                        alpha = rgba[:,:,3].astype(np.float32) / 255.0
                        fg = rgba[:,:,:3].astype(np.float32)
                        if self.use_checkerboard_on_success:
                            bg_rgb = cv2.cvtColor(self._create_checkerboard(w,h,self.checker_size), cv2.COLOR_BGR2RGB).astype(np.float32)
                        else:
                            bg_rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB).astype(np.float32)
                        combined = (fg * alpha[:,:,None] + bg_rgb * (1 - alpha[:,:,None])).astype(np.uint8)
                        out = cv2.cvtColor(combined, cv2.COLOR_RGB2BGR)
                        env["payload"] = out
                    else:
                        env["payload"] = arr
            except Exception:
                env["payload"] = arr

        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env