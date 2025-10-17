import os
import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # d:\KTPM_demo
INPUT_DIR = os.path.join(ROOT, "data", "input")
os.makedirs(INPUT_DIR, exist_ok=True)

def create_images(n=6):
    for i in range(n):
        h, w = 200 + (i * 10) % 120, 300 + (i * 15) % 160
        img = np.full((h, w, 3), 50 + i * 30, dtype=np.uint8)
        # draw some text/shape to make images differ
        cv2.putText(img, f"img_{i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
        fn = os.path.join(INPUT_DIR, f"sample_{i:02d}.jpg")
        cv2.imwrite(fn, img)
    print(f"Created {n} sample images in: {INPUT_DIR}")

if __name__ == "__main__":
    create_images(8)