import os
import cv2
import uuid
from typing import Any, Dict

class OutputFilterV2:
    """
    Save envelope.payload to disk. Returns envelope with payload = saved_path.
    """
    def __init__(self, output_dir: str):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def process(self, envelope: Any) -> Dict:
        env = dict(envelope) if isinstance(envelope, dict) else {"id": None, "payload": envelope, "meta": {}}
        img = env.get("payload")
        if img is None:
            raise ValueError("OutputFilterV2: payload is None")
        meta = env.get("meta", {})
        filename = meta.get("filename")
        if not filename:
            orig = meta.get("orig_path") or meta.get("path") or env.get("path")
            if isinstance(orig, str):
                filename = os.path.basename(orig)
            else:
                filename = f"output_{uuid.uuid4().hex[:8]}.jpg"
        out_path = os.path.join(self.output_dir, filename)
        ok = cv2.imwrite(out_path, img)
        if not ok:
            raise IOError(f"OutputFilterV2: failed to write {out_path}")
        env["payload"] = out_path
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        env["meta"]["filename"] = filename
        return env