import cv2

class ResizeFilter:
    """
    Filter resize ảnh về kích thước mong muốn.
    Kích thước target được cấu hình khi khởi tạo filter.
    """
    def __init__(self, width: int = None, height: int = None, keep_aspect_ratio: bool = True):
        self.width = width
        self.height = height
        self.keep_aspect_ratio = keep_aspect_ratio

    def process(self, image):
        if image is None:
            raise ValueError("Input image is None")

        h, w = image.shape[:2]

        # Nếu có giữ tỷ lệ
        if self.keep_aspect_ratio:
            if self.width is not None and self.height is None:
                ratio = self.width / w
                new_w, new_h = self.width, int(h * ratio)
            elif self.height is not None and self.width is None:
                ratio = self.height / h
                new_w, new_h = int(w * ratio), self.height
            elif self.width is not None and self.height is not None:
                # ép cứng về width, height => có thể méo hình
                new_w, new_h = self.width, self.height
            else:
                # không cấu hình thì giữ nguyên
                return image
        else:
            # Nếu không giữ tỷ lệ thì dùng width, height trực tiếp
            new_w = self.width if self.width else w
            new_h = self.height if self.height else h

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized
