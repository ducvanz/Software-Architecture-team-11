# SENTINEL object để báo end-of-stream; dùng "is" để so sánh
SENTINEL = object()

# Envelope keys / contract (hints)
# envelope = {
#   "id": str,
#   "payload": <path or ndarray>,
#   "meta": {"attempts":0, "stage":0, "orig_path": "..."}
# }