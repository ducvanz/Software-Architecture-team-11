from queue import Queue
from threading import Thread
from Filters.converter import Converter
from Filters.grayscale_blur import GrayscaleBlur
from Filters.edge_detector import EdgeDetector
from Filters.watermark import Watermark

class ParallelPipeline:
    def __init__(self):
        self.queues = [Queue() for _ in range(5)]
        self.filters = [
            Converter(),
            GrayscaleBlur(),
            EdgeDetector(),
            Watermark()
        ]
        self.threads = []
        print("done")

    def start(self):
        return 0

    def put_image(self, image):
        return 0

    def get_result(self):
        return 0

    def stop(self):
        return 0