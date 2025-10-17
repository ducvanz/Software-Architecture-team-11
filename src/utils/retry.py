import time
import functools

def retry(max_attempts=3, backoff=0.2):
    """Decorator để thử lại một hàm nếu xảy ra lỗi."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    time.sleep(backoff * attempt)
        return wrapper
    return decorator