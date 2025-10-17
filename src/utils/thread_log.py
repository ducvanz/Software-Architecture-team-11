import threading

def log_start(filter_name, envelope):
    thread_name = threading.current_thread().name
    fname = envelope.get("filename") or envelope.get("path") or envelope.get("id")
    print(f"[{thread_name}][{filter_name}] START {fname}")

def log_end(filter_name, envelope, status="done"):
    thread_name = threading.current_thread().name
    fname = envelope.get("filename") or envelope.get("path") or envelope.get("id")
    print(f"[{thread_name}][{filter_name}] {status.upper()} {fname}")
