import cv2
from typing import Any, Dict

class ConvertFilter:
    """
    Accepts envelope with payload = path (str).
    Reads image via cv2.imread and returns envelope with payload = ndarray.
    """
    def __init__(self):
        pass

    def process(self, envelope: Any) -> Dict:
        # support legacy (if passed a raw path string)
        if isinstance(envelope, str):
            path = envelope
            env = {"id": path, "payload": path, "meta": {"attempts": 0, "stage": 0, "orig_path": path}}
        else:
            env = envelope

        path = env.get("payload")
        if not isinstance(path, str):
            raise ValueError("ConvertFilter expected envelope.payload to be a file path string")

        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"Cannot read image from: {path}")

        env["payload"] = img
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env
