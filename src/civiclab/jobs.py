"""SQLite job checkpoints. Interrupted model calls are never automatically replayed."""
import json
import sqlite3
import time
from pathlib import Path
from .common import canonical_hash


class JobQueue:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT, status TEXT, result TEXT, updated REAL)")
            if 'priority' not in {r[1] for r in db.execute('PRAGMA table_info(jobs)')}:
                db.execute('ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 0')

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def add(self, payload):
        identity = canonical_hash(payload)
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO jobs (id,payload,status,result,updated,priority) VALUES (?,?,'PENDING',NULL,?,?)", (identity, json.dumps(payload, sort_keys=True), time.time(), payload.get('execution_order',0)))
        return identity

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT id,payload FROM jobs WHERE status='PENDING' ORDER BY priority,id LIMIT 1").fetchone()
            if not row:
                return None
            db.execute("UPDATE jobs SET status='RUNNING',updated=? WHERE id=?", (time.time(), row[0]))
            return row[0], json.loads(row[1])

    def finish(self, identity, result):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute("UPDATE jobs SET status='DONE',result=?,updated=? WHERE id=? AND status='RUNNING'", (json.dumps(result, sort_keys=True), time.time(), identity))
            if cursor.rowcount != 1:
                raise ValueError("job is not running")

    def snapshot(self):
        with self.connect() as db:
            return [{"id": r[0], "status": r[1], "result": json.loads(r[2]) if r[2] else None}
                    for r in db.execute("SELECT id,status,result FROM jobs ORDER BY id")]

    def recover_interrupted(self):
        with self.connect() as db:
            # Explicit operator action; quarantine rather than retry an uncertain call.
            db.execute("UPDATE jobs SET status='NEEDS_RECONCILIATION' WHERE status='RUNNING'")
