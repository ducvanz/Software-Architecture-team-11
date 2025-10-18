# ...existing code...
import time
import traceback
from typing import Callable, Any

def call_with_retry(func: Callable[[Any], Any], envelope: Any, max_attempts: int = 3, backoff: float = 0.2) -> Any:
    """
    Call func(envelope) with retry/backoff. Increment envelope['meta']['attempts'] on each try.

    - func: callable that accepts a single envelope and returns result (or raises)
    - envelope: dict-like envelope (we mutate envelope['meta']['attempts'])
    - Raises the last exception if attempts exhausted.
    """
    if not isinstance(envelope, dict):
        # normalize a minimal envelope so attempts/meta can be tracked
        envelope = {"payload": envelope, "meta": envelope.get("meta") if isinstance(envelope, dict) else {}}

    meta = envelope.setdefault("meta", {})
    attempts = int(meta.get("attempts", 0))

    last_exc = None
    for attempt in range(attempts, max_attempts):
        try:
            meta["attempts"] = attempt + 1
            result = func(envelope)
            return result
        except Exception as e:
            last_exc = e
            # exponential backoff (cap)
            sleep_t = backoff * (2 ** attempt)
            time.sleep(sleep_t)
            # continue to next attempt
    # exhausted
    # attach trace to exception and re-raise
    raise last_exc
# ...existing code...