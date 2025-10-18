import cv2
import numpy as np
from typing import Any, Dict, Tuple

class WatermarkV2:
    """
    Envelope in: payload = ndarray (gray or BGR)
    Envelope out: payload = BGR ndarray with text drawn.
    """
    def __init__(self, text: str = "Team 11", pos: Tuple[int,int]=(10,30), font_scale: float = 1.0, color: Tuple[int,int,int]=(0,255,0), thickness: int = 2, alpha: float = 0.0):
        self.text = text
        self.pos = pos
        self.font_scale = font_scale
        self.color = tuple(int(c) for c in color)
        self.thickness = int(thickness)
        # alpha kept for compatibility; we draw text directly (no blending) because original logic used putText
        self.alpha = float(alpha)

    def process(self, envelope: Any) -> Dict:
        env = dict(envelope) if isinstance(envelope, dict) else {"id": None, "payload": envelope, "meta": {}}
        img = env.get("payload")
        if img is None:
            raise ValueError("WatermarkV2: payload is None")

        arr = np.array(img)
        if arr.ndim == 2:
            bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        elif arr.ndim == 3 and arr.shape[2] == 4:
            bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        else:
            bgr = arr.copy()

        cv2.putText(bgr, self.text, self.pos, cv2.FONT_HERSHEY_SIMPLEX, self.font_scale, self.color, self.thickness, cv2.LINE_AA)

        env["payload"] = bgr
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env