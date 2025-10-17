# src/Filters/grayscale_blur.py
# Nhiệm vụ: lấy item từ input_queue -> chuyển GRAY -> Gaussian blur -> đẩy sang output_queue.
# Gặp None thì chuyển tiếp None và dừng.

import cv2
import numpy as np
from typing import Optional, Any


class GrayscaleBlur:
    """
    Filter chuyển BGR -> grayscale -> Gaussian blur.
    API đơn giản: process(image) -> image
    Nếu keep_3_channels=True sẽ trả về ảnh 3 kênh (BGR) để đồng nhất với các filter phía sau.
    """
    def __init__(self, ksize: int = 5, sigmaX: float = 1.2, keep_3_channels: bool = False):
        # ensure odd kernel size
        if ksize % 2 == 0:
            ksize += 1
        self.ksize = (ksize, ksize)
        self.sigmaX = float(sigmaX)
        self.keep_3_channels = bool(keep_3_channels)

    def process(self, image: Optional[Any]) -> Optional[np.ndarray]:
        """
        Nhận 1 image (numpy.ndarray) ở định dạng BGR (H,W,3).
        Trả về blurred image:
          - nếu keep_3_channels=False: trả về (H,W) grayscale blurred
          - nếu keep_3_channels=True: trả về (H,W,3) BGR (gray->BGR)
        Nếu image is None -> trả về None.
        """
        if image is None:
            return None

        img = np.array(image)  # đảm bảo ndarray (copy/view)
        orig_dtype = getattr(img, "dtype", None)

        # Nếu input là 3 kênh BGR, convert sang grayscale
        if img.ndim == 3 and img.shape[2] >= 3:
            gray = cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2GRAY)
        elif img.ndim == 2:
            gray = img
        else:
            # Không biết định dạng -> raise để dễ phát hiện lỗi trong pipeline
            raise ValueError(f"Unsupported image shape for GrayscaleBlur: {img.shape}")

        blurred = cv2.GaussianBlur(gray, self.ksize, self.sigmaX)

        if self.keep_3_channels:
            blurred = cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)

        # restore dtype if possible
        if orig_dtype is not None:
            try:
                blurred = blurred.astype(orig_dtype)
            except Exception:
                pass

        return blurred
