import os
import cv2
import time

class OutputFilter:
    """
    Filter xuất ảnh ra thư mục đầu ra. Ghi tất cả ảnh ra cùng một thư mục output_dir.
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.counter = 0

    def process(self, image):
        """Lưu ảnh ra file, tự sinh tên ảnh"""
        if image is None:
            raise ValueError("OutputFilter: image is None, cannot save.")

        self.counter += 1
        filename = f"output_{self.counter:03d}.jpg"
        output_path = os.path.join(self.output_dir, filename)

        # Ghi file
        success = cv2.imwrite(output_path, image)
        if not success:
            raise IOError(f"Failed to write image to {output_path}")

        print(f"💾 Saved: {output_path}")
        return output_path
