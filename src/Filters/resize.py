import cv2
import numpy as np

class ResizeFilter:
    """
    Resize filter (process(image) -> image).
    If keep_aspect_ratio=True, scales to fit within provided width/height.
    """
    def __init__(self, width: int = None, height: int = None, keep_aspect_ratio: bool = True):
        self.width = width
        self.height = height
        self.keep_aspect_ratio = keep_aspect_ratio

    def process(self, image):
        if image is None:
            raise ValueError("Input image is None")

        h, w = image.shape[:2]

        # If no target provided, return original
        if self.width is None and self.height is None:
            return image

        if self.keep_aspect_ratio:
            if self.width is None:
                scale = self.height / float(h)
            elif self.height is None:
                scale = self.width / float(w)
            else:
                scale = min(self.width / float(w), self.height / float(h))
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
        else:
            new_w = self.width if self.width is not None else w
            new_h = self.height if self.height is not None else h

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized
