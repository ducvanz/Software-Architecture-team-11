# SENTINEL object để báo end-of-stream; so sánh bằng "is"
SENTINEL = object()

# Envelope contract:
# envelope = {
#   "id": str,
#   "payload": <path | ndarray | other>,
#   "meta": {
#       "attempts": int,
#       "stage": int,
#       "orig_path": str,
#       ...
#   }
#}