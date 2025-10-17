import json
import os
from datetime import datetime

def write_dlq(envelope: dict, dlq_dir: str = "../data/dlq"):
    """
    Ghi envelope bị lỗi vào Dead Letter Queue.
    Sử dụng 'filename' hoặc 'id' làm tên file.
    """
    dlq_dir = os.path.abspath(dlq_dir)
    os.makedirs(dlq_dir, exist_ok=True)

    # Lấy tên file gốc, nếu không có thì fallback về ID (hash)
    file_name_base = envelope.get("filename", envelope.get("id"))
    
    # Nếu vẫn không có, dùng timestamp làm fallback cuối cùng
    if not file_name_base:
        file_name_base = f"unknown_{int(datetime.now().timestamp())}"

    # Đảm bảo tên file kết thúc bằng .json
    fname = f"{file_name_base}.json"
    
    out_path = os.path.join(dlq_dir, fname)
    
    try:
        # Sử dụng default=str để xử lý numpy array (image) an toàn khi serialize
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False, indent=2, default=str)
        print(f"[DLQ] Wrote envelope id={envelope.get('id', 'N/A')} to {out_path}")
    except Exception as e:
        print(f"[DLQ] Failed to write DLQ for id={envelope.get('id', 'N/A')}: {e}")