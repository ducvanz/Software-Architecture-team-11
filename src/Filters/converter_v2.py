import os
import cv2
import hashlib
from typing import Any, Dict

def make_id_for_path(path: str) -> str:
    try:
        stat = os.stat(path)
        s = f"{path}|{stat.st_size}|{int(stat.st_mtime)}"
    except Exception:
        s = f"{path}|{os.path.basename(path)}"
    return hashlib.sha1(s.encode()).hexdigest()

class ConvertFilterV2:
    """
    Accepts envelope with payload = path (str)
    Returns envelope with payload = ndarray and adds 'id' if missing.
    """
    def __init__(self):
        pass

    def process(self, envelope: Any) -> Dict:
        # support raw path string for backward compatibility
        if isinstance(envelope, str):
            env = {"id": None, "payload": envelope, "meta": {}}
        else:
            env = dict(envelope)  # shallow copy
        path = env.get("payload")
        if not isinstance(path, str):
            raise ValueError("ConvertFilterV2 expected envelope.payload to be a file path string")

        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"ConvertFilterV2: cannot read image: {path}")

        env["payload"] = img
        env.setdefault("id", make_id_for_path(path))
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env