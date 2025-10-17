import cv2
import numpy as np
from typing import Optional, Any, Tuple


class Watermark:
    """
    Add text watermark. process(image) -> image (3-channel BGR).
    If input is grayscale (H,W) it will be converted to BGR before drawing.
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

    def process(self, image: Optional[Any]) -> Optional[np.ndarray]:
        if image is None:
            return None

        img = np.array(image)
        orig_dtype = getattr(img, "dtype", None)

        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        overlay = img.copy()
        (text_w, text_h), baseline = cv2.getTextSize(self.text, self.font, self.font_scale, self.thickness)
        x = max(self.margin, img.shape[1] - text_w - self.margin)
        y = max(text_h + self.margin, img.shape[0] - self.margin)

        cv2.putText(overlay, self.text, (x, y), self.font, self.font_scale, self.color, self.thickness, cv2.LINE_AA)
        blended = cv2.addWeighted(overlay, self.alpha, img, 1.0 - self.alpha, 0)

        if orig_dtype is not None:
            try:
                blended = blended.astype(orig_dtype)
            except Exception:
                pass

        return blended
