# src/Filters/grayscale_blur.py
# Nhiệm vụ: lấy item từ input_queue -> chuyển GRAY -> Gaussian blur -> đẩy sang output_queue.
# Gặp None thì chuyển tiếp None và dừng.

import cv2
import numpy as np
from typing import Optional, Any, Dict


class GrayscaleBlur:
    """
    Envelope in: payload = ndarray (BGR or gray)
    Envelope out: payload = blurred ndarray (gray by default)
    """
    def __init__(self, ksize: int = 5, sigmaX: float = 1.2, keep_3_channels: bool = False):
        # ensure odd kernel size
        if ksize % 2 == 0:
            ksize += 1
        self.ksize = (ksize, ksize)
        self.sigmaX = float(sigmaX)
        self.keep_3_channels = bool(keep_3_channels)

    def process(self, envelope: Any) -> Dict:
        """
        Nhận 1 image (numpy.ndarray) ở định dạng BGR (H,W,3).
        Trả về blurred image:
          - nếu keep_3_channels=False: trả về (H,W) grayscale blurred
          - nếu keep_3_channels=True: trả về (H,W,3) BGR (gray->BGR)
        Nếu image is None -> trả về None.
        """
        if isinstance(envelope, dict) and "payload" in envelope:
            env = envelope
            img = env["payload"]
        else:
            img = envelope
            env = {"id": None, "payload": img, "meta": {}}

        if img is None:
            raise ValueError("GrayscaleBlur: payload is None")

        arr = np.array(img)  # đảm bảo ndarray (copy/view)
        orig_dtype = getattr(arr, "dtype", None)

        # Nếu input là 3 kênh BGR, convert sang grayscale
        if arr.ndim == 3 and arr.shape[2] >= 3:
            gray = cv2.cvtColor(arr[..., :3], cv2.COLOR_BGR2GRAY)
        elif arr.ndim == 2:
            gray = arr
        else:
            # Không biết định dạng -> raise để dễ phát hiện lỗi trong pipeline
            raise ValueError(f"Unsupported image shape for GrayscaleBlur: {arr.shape}")

        blurred = cv2.GaussianBlur(gray, self.ksize, self.sigmaX)

        if self.keep_3_channels:
            blurred = cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)

        env["payload"] = blurred
        env.setdefault("meta", {})
        env["meta"]["stage"] = env["meta"].get("stage", 0) + 1
        return env
