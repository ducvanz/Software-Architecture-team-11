import os
import cv2
import uuid
from typing import Any, Dict

class OutputFilterV2:
    """
    Saves envelope.payload (ndarray) to output_dir.
    envelope may include meta.filename or payload originally came from path -> filename will be preserved.
    Returns envelope with payload = saved_path.
    """
    def __init__(self, output_dir: str):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def process(self, envelope: Any) -> Dict:
        env = dict(envelope) if isinstance(envelope, dict) else {"id": None, "payload": envelope, "meta": {}}
        img = env.get("payload")
        if img is None:
            raise ValueError("OutputFilterV2: payload is None")
        # determine filename
        meta = env.get("meta", {})
        filename = meta.get("filename")
        if not filename:
            # try to derive from orig_path
            orig = meta.get("orig_path") or env.get("payload_path") or env.get("path")
            if isinstance(orig, str):
                filename = os.path.basename(orig)
            else:
                filename = f"output_{uuid.uuid4().hex[:8]}.jpg"
        out_path = os.path.join(self.output_dir, filename)
        success = cv2.imwrite(out_path, img)
        if not success:
            raise IOError(f"OutputFilterV2: failed to write {out_path}")
        env["payload"] = out_path
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        env["meta"]["filename"] = filename
        return env