import os
import cv2
import hashlib
import numpy as np
from typing import Any, Dict

try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None

def _make_id_for_path(path: str) -> str:
    try:
        stat = os.stat(path)
        s = f"{path}|{stat.st_size}|{int(stat.st_mtime)}"
    except Exception:
        s = f"{path}|{os.path.basename(path)}"
    return hashlib.sha1(s.encode()).hexdigest()

class ConvertFilterV2:
    """
    Read path -> payload as BGR ndarray. Honor EXIF via Pillow if available.
    Input: envelope with payload = path (str)
    Output: envelope with payload = ndarray (BGR) and id/meta updated.
    """
    def process(self, envelope: Any) -> Dict:
        env = dict(envelope) if isinstance(envelope, dict) else {"id": None, "payload": envelope, "meta": {}}
        path = env.get("payload")
        if not isinstance(path, str):
            raise ValueError("ConvertFilterV2 expects envelope.payload to be a file path string")

        img_bgr = None
        if Image is not None:
            try:
                pil = Image.open(path)
                pil = ImageOps.exif_transpose(pil)
                rgb = pil.convert("RGB")
                arr = np.asarray(rgb, dtype=np.uint8)
                img_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            except Exception:
                img_bgr = None

        if img_bgr is None:
            img_bgr = cv2.imread(path)
            if img_bgr is None:
                raise ValueError(f"ConvertFilterV2: cannot read image: {path}")

        env["payload"] = img_bgr
        env.setdefault("id", _make_id_for_path(path))
        env.setdefault("meta", {})
        env["meta"]["orig_path"] = env["meta"].get("orig_path", path)
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env