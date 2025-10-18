import cv2
import numpy as np
from typing import Optional, Any, Tuple, Dict


class Watermark:
    """
    Envelope in: payload = ndarray (gray or BGR)
    Envelope out: payload = BGR ndarray with watermark blended
    """
    def __init__(
        self,
        text: str = "Watermark",
        font_scale: float = 1.0,
        color: Tuple[int, int, int] = (255, 255, 255),
        thickness: int = 2,
        alpha: float = 0.35,
        margin: int = 10,
    ):
        self.text = str(text)
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = float(font_scale)
        self.color = tuple(int(c) for c in color)
        self.thickness = int(thickness)
        self.alpha = float(alpha)
        self.margin = int(margin)

    def process(self, envelope: Any) -> Dict:
        if isinstance(envelope, dict) and "payload" in envelope:
            env = envelope
            img = env["payload"]
        else:
            img = envelope
            env = {"id": None, "payload": img, "meta": {}}

        if img is None:
            raise ValueError("Watermark: payload is None")

        arr = np.array(img)

        if arr.ndim == 2:
            img_bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        elif arr.ndim == 3 and arr.shape[2] == 4:
            img_bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        else:
            img_bgr = arr

        overlay = img_bgr.copy()
        (text_w, text_h), baseline = cv2.getTextSize(self.text, self.font, self.font_scale, self.thickness)
        x = max(self.margin, img_bgr.shape[1] - text_w - self.margin)
        y = max(text_h + self.margin, img_bgr.shape[0] - self.margin)
        cv2.putText(overlay, self.text, (x, y), self.font, self.font_scale, self.color, self.thickness, cv2.LINE_AA)
        blended = cv2.addWeighted(overlay, self.alpha, img_bgr, 1.0 - self.alpha, 0)

        env["payload"] = blended
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env
