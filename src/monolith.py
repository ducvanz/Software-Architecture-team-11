# file: monolith.py

import os
import time
import cv2
import hashlib
import numpy as np
from rembg import remove # Giả định thư viện này đã được cài đặt

# --- HÀM HỖ TRỢ TỪ CÁC FILE UTILS ---

def make_id_for_path(path: str) -> str:
    # Logic tạo ID tương tự ConvertFilter
    try:
        stat = os.stat(path)
        s = f"{path}|{stat.st_size}|{int(stat.st_mtime)}"
    except Exception:
        s = f"{path}|{os.path.basename(path)}"
    return hashlib.sha1(s.encode()).hexdigest()

def _create_checkerboard(w, h, checker_size=20):
    # Logic tạo background từ RemoveBackground
    img = np.zeros((h, w, 3), np.uint8)
    for y in range(0, h, checker_size):
        for x in range(0, w, checker_size):
            color = (255,255,255) if (x//checker_size+y//checker_size)%2==0 else (200,200,200)
            cv2.rectangle(img, (x,y), (x+checker_size, y+checker_size), color, -1)
    return img

# --- HÀM XỬ LÝ MONOLITH CHÍNH ---

def process_file_monolith(input_path, output_dir, resize_w=500, resize_h=500):
    """Xử lý một file tuần tự qua tất cả các bước (Monolith)."""
    
    fname = os.path.basename(input_path)
    
    # 1. CONVERT (Đọc ảnh)
    img = cv2.imread(input_path)
    if img is None:
        print(f"  [LỖI] Bỏ qua {fname}: Không thể đọc ảnh.")
        return False

    # ID và Envelope giả lập (không dùng DedupStore)
    id_ = make_id_for_path(input_path)
    
    # 2. RESIZE
    h, w = img.shape[:2]
    new_size = (resize_w, resize_h) # Giả định không giữ aspect ratio cho đơn giản
    img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

    # 3. REMOVE BACKGROUND
    h, w = img.shape[:2]
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    try:
        rgba = remove(img_rgb)
    except Exception:
        # Xử lý trường hợp rembg thất bại (rất thường xảy ra)
        print(f"  [LỖI] Bỏ qua rembg cho {fname}.")
        return False
        
    alpha = rgba[:,:,3]/255.0
    fg = rgba[:,:,:3]
    bg = cv2.cvtColor(_create_checkerboard(w, h), cv2.COLOR_BGR2RGB)
    combined = (fg*alpha[:,:,None]+bg*(1-alpha[:,:,None])).astype(np.uint8)
    img = cv2.cvtColor(combined, cv2.COLOR_RGB2BGR)
    
    # 4. HORIZONTAL FLIP
    img = cv2.flip(img, 1)
    
    # 5. WATERMARK
    text = "Team 11"
    pos = (10, 30)
    font_scale = 1.0
    color = (0, 255, 0)
    thickness = 2
    
    out = img.copy()
    cv2.putText(out, text, pos, cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, color, thickness, cv2.LINE_AA)
    img = out
    
    # 6. OUTPUT (Ghi ảnh)
    out_path = os.path.join(output_dir, fname)
    if not cv2.imwrite(out_path, img):
        print(f"  [LỖI] Ghi file thất bại: {out_path}")
        return False
        
    print(f"  [MONOLITH] Xử lý thành công {fname}")
    return True

# --- HÀM CHẠY CHÍNH ---

def run_monolith_test():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INPUT_DIR = os.path.join(BASE_DIR, "data", "input")
    OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output_monolith")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    file_list = []
    for fn in os.listdir(INPUT_DIR):
        if fn.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            file_list.append(os.path.join(INPUT_DIR, fn))

    print("-" * 50)
    print(f"BẮT ĐẦU KIỂM TRA MONOLITH (TUẦN TỰ) - {len(file_list)} files")
    print("-" * 50)
    
    start_time = time.time()
    
    processed_count = 0
    for file_path in file_list:
        if process_file_monolith(file_path, OUTPUT_DIR):
            processed_count += 1
            
    end_time = time.time()
    duration = end_time - start_time
    
    print("-" * 50)
    print(f"TỔNG KẾT HIỆU SUẤT MONOLITH:")
    print(f"Tổng số file xử lý: {processed_count}/{len(file_list)}")
    print(f"Thời gian thực thi: {duration:.4f} giây")
    print("-" * 50)
    return duration

if __name__ == "__main__":
    run_monolith_test()