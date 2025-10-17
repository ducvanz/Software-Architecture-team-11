import os
import cv2
import threading
import uuid

class OutputFilter:
    """
    Thread-safe output filter: saves images with unique filenames.
    process(image) -> path
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._counter = 0
        self._lock = threading.Lock()

    def process(self, image):
        if image is None:
            raise ValueError("OutputFilter: image is None, cannot save.")

        with self._lock:
            self._counter += 1
            idx = self._counter

        filename = f"output_{idx:03d}_{uuid.uuid4().hex[:8]}.jpg"
        output_path = os.path.join(self.output_dir, filename)

        success = cv2.imwrite(output_path, image)
        if not success:
            raise IOError(f"Failed to write image to {output_path}")

        return output_path
