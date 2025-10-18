import cv2
from typing import Any, Dict

class ConvertFilter:
    """
    Envelope in: payload = path (str)
    Envelope out: payload = ndarray (image)
    """
    def __init__(self):
        pass

    def process(self, envelope: Any) -> Dict:
        # support raw path for legacy calls
        if isinstance(envelope, str):
            env = {"id": envelope, "payload": envelope, "meta": {"attempts": 0, "stage": 0, "orig_path": envelope}}
        else:
            env = envelope

        path = env.get("payload")
        if not isinstance(path, str):
            raise ValueError("ConvertFilter expected envelope.payload to be a file path string")

        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"ConvertFilter: cannot read image from: {path}")

        env["payload"] = img
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env
