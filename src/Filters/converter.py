import cv2

class ConvertFilter:
    """
    Filter này chỉ nhận 1 path ảnh, 
    đọc ảnh và convert sang BGR (numpy array).
    """
    def __init__(self):
        pass

    def process(self, image_path: str):
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Không đọc được ảnh từ: {image_path}")

        return img
