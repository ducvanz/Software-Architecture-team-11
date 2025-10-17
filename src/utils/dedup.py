import sqlite3
import threading
from typing import Set

class DedupStore:
    """
    Simple persistent dedup store using SQLite.
    Stores id -> comma-separated stages.
    Thread-safe.
    """
    def __init__(self, db_path="dedup.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_table()
        
    def _init_table(self):
        with self.conn:
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dedup (
                id TEXT PRIMARY KEY,
                stages TEXT,
                last_ts INTEGER
            )
            """)

    def get_stages(self, id_: str) -> Set[str]:
        cur = self.conn.execute("SELECT stages FROM dedup WHERE id=?", (id_,))
        row = cur.fetchone()
        if not row or not row[0]:
            return set()
        return set([s for s in row[0].split(",") if s])

    def add_stage(self, id_: str, stage: str):
        with self.lock:
            stages = self.get_stages(id_)
            stages.add(stage)
            stages_str = ",".join(sorted(stages))
            # Sử dụng UPSERT (ON CONFLICT) để cập nhật stages nếu id đã tồn tại
            self.conn.execute(
                "INSERT INTO dedup(id, stages, last_ts) VALUES(?,?,strftime('%s','now')) "
                "ON CONFLICT(id) DO UPDATE SET stages=?, last_ts=strftime('%s','now')",
                (id_, stages_str, stages_str)
            )
            self.conn.commit()