import cv2

class EdgeDetector:
    def __init__(self, method="canny", threshold1=100, threshold2=200):
        self.method = method
        self.threshold1 = threshold1
        self.threshold2 = threshold2

    def process(self, image):
        """
        image: numpy.ndarray (grayscale)
        return: numpy.ndarray (binary edge map)
        """
        if self.method == "canny":
            edges = cv2.Canny(image, self.threshold1, self.threshold2)
        elif self.method == "sobel":
            grad_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
            edges = cv2.convertScaleAbs(cv2.magnitude(grad_x, grad_y))
        else:
            raise ValueError(f"Unknown method: {self.method}")

        return edges
