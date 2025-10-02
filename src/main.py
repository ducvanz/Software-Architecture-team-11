
from Pipelines.parallel_pipeline import ParallelPipeline
import cv2
import glob

def main():
    # Khởi tạo pipeline
    pipeline = ParallelPipeline()
    pipeline.start()

if __name__ == "__main__":
    main()
