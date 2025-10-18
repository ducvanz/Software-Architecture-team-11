import os
import json
import uuid
import time
import traceback
from typing import Any, Dict, Optional

def _default_dlq_dir() -> str:
    # project root = two levels up from src/Utils
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(root, "data", "dlq")

def write_dlq(envelope: Any, error: str, exc_trace: Optional[str] = None, dlq_dir: Optional[str] = None) -> str:
    """
    Write a DLQ entry as a JSON file. Returns path to written file.

    Stored fields:
      - id (if present)
      - meta (if present)
      - error (string)
      - trace (full traceback string, optional)
      - timestamp, uuid
      - minimal payload info (do NOT dump raw image bytes)
    """
    dlq_dir = dlq_dir or _default_dlq_dir()
    os.makedirs(dlq_dir, exist_ok=True)
    entry = {
        "id": None,
        "meta": None,
        "error": error,
        "trace": exc_trace,
        "ts": time.time(),
        "uuid": uuid.uuid4().hex,
        "payload_info": None
    }

    try:
        if isinstance(envelope, dict):
            entry["id"] = envelope.get("id")
            entry["meta"] = envelope.get("meta")
            # try to record orig_path / filename / payload type without serializing image
            pi = {}
            if "payload" in envelope:
                p = envelope["payload"]
                if isinstance(p, str):
                    pi["type"] = "path"
                    pi["payload"] = p
                else:
                    pi["type"] = type(p).__name__
                    # record shape if ndarray-like
                    try:
                        import numpy as _np
                        if hasattr(p, "shape"):
                            pi["shape"] = getattr(p, "shape")
                    except Exception:
                        pass
            if "path" in envelope:
                pi["path"] = envelope.get("path")
            if "filename" in envelope:
                pi["filename"] = envelope.get("filename")
            entry["payload_info"] = pi
        else:
            entry["payload_info"] = {"type": type(envelope).__name__}
    except Exception:
        # defensive: ensure DLQ write doesn't fail
        entry["payload_info"] = {"type": "unknown", "repr": repr(envelope)[:200]}

    fname = f"dlq_{int(entry['ts'])}_{entry['uuid']}.json"
    out_path = os.path.join(dlq_dir, fname)
    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(entry, fh, indent=2, default=str)
    except Exception:
        # best-effort fallback: try minimal write
        try:
            with open(out_path + ".err", "w", encoding="utf-8") as fh:
                fh.write(str(entry))
        except Exception:
            pass
    return out_path