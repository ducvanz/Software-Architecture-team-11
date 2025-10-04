import cv2

class ConvertFilter:
    """
    Filter này chỉ nhận 1 path ảnh, 
    đọc ảnh và convert sang BGR (numpy array).
    """
    def __init__(self):
        pass

    def process(self, image: str):
        img = cv2.imread(image)
        if img is None:
            raise ValueError(f"Không đọc được ảnh từ: {image}")

        return img
