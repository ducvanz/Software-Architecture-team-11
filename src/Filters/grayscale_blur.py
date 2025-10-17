# src/Filters/grayscale_blur.py
# Nhiệm vụ: lấy item từ input_queue -> chuyển GRAY -> Gaussian blur -> đẩy sang output_queue.
# Gặp None thì chuyển tiếp None và dừng.

import cv2

class GrayscaleBlur:
    def __init__(self, ksize: int = 5, sigmaX: float = 1.2, keep_3_channels: bool = False):
        """
        ksize           : kích thước kernel Gaussian (số lẻ: 3/5/7/...)
        sigmaX          : độ mờ theo trục X
        keep_3_channels : True nếu muốn trả lại ảnh 3 kênh (GRAY->BGR) cho đồng nhất với các filter 3 kênh phía sau
        """
        if ksize % 2 == 0:
            ksize += 1
        self.ksize = (ksize, ksize)
        self.sigmaX = sigmaX
        self.keep_3_channels = keep_3_channels

    def process(self, input_queue, output_queue):
        """
        Vòng lặp chuẩn của filter:
        - get() item
        - nếu item là None: chuyển tiếp None -> break
        - xử lý item["image"] -> put(item) sang output_queue
        """
        while True:
            item = input_queue.get()
            if item is None:
                output_queue.put(None)   # truyền sentinel cho stage sau
                break

            bgr = item["image"]                              # ảnh BGR
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)     # (H, W)
            blurred = cv2.GaussianBlur(gray, self.ksize, self.sigmaX)

            if self.keep_3_channels:
                blurred = cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)

            item["image"] = blurred
            output_queue.put(item)
