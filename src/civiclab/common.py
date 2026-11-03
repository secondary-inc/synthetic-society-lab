"""Atomic artifacts and append-only run events. Not an OS security sandbox."""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import subprocess
import sys
import platform
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def canonical_hash(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".writing-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def redact(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if any(s in k.lower() for s in
                ("api_key", "access_token", "authorization", "secret", "password")) else redact(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"(?:sk-or-v1-[A-Za-z0-9]+|EAA[A-Za-z0-9]{30,}|Bearer\s+\S+)",
                      "[REDACTED]", value)
    return value


def code_identity(root):
    root = Path(root)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                           stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True))
    except (subprocess.SubprocessError, FileNotFoundError):
        revision, dirty = "UNVERSIONED", True
    # Captures uncommitted implementation used in a run; never scans .env/raw data.
    files = {str(p.relative_to(root)): sha256_file(p)
             for folder in ("src", "protocols", "configs")
             for p in sorted((root / folder).rglob("*"))
             if p.is_file() and p.suffix in (".py", ".json", ".md", ".csv", ".html")}
    if (root/'pyproject.toml').exists():
        files['pyproject.toml']=sha256_file(root/'pyproject.toml')
    return {"git_sha": revision, "dirty": dirty, "source_tree_sha256": canonical_hash(files)}


class RunStore:
    def __init__(self, root, module, config, kind="MOCK"):
        if module not in ("E01", "E02", "E03", "E04"):
            raise ValueError("unknown research module")
        if kind not in ("MOCK", "RETROSPECTIVE", "EXPLORATORY"):
            raise ValueError("unsupported run kind; prospective claims disabled")
        self.root = Path(root)
        config = redact(config)
        code = code_identity(self.root)
        self.experiment_id = canonical_hash({"module": module, "config": config, "code": code})
        self.run_id = f"{module.lower()}-{uuid.uuid4().hex}"
        self.path = self.root / "data/processed/runs" / self.run_id
        self.path.mkdir(parents=True, exist_ok=False)
        self._acquire_lock()
        self._sequence = 0
        self.finished = False
        self.write("manifest.json", {"schema_version": 1, "run_id": self.run_id,
                   "experiment_id": self.experiment_id, "module": module, "kind": kind,
                   "started_at_utc": utc_now(), "code": code, "config": config})
        self.write('environment.json',{'python':sys.version,'platform':platform.platform(),
                                      'runtime_dependencies':'Python standard library only'})
        self.event("started", kind_label=kind)

    def write(self, name, value):
        if self.finished:
            raise RuntimeError('run is finalized')
        target = self.path / name
        if not target.resolve().is_relative_to(self.path.resolve()):
            raise ValueError("artifact escapes run directory")
        if target.exists():
            raise FileExistsError("run artifacts are immutable")
        atomic_json(target, redact(value))

    def event(self, kind, **fields):
        if self.finished:
            raise RuntimeError('run is finalized')
        self._sequence += 1
        event = redact({"sequence": self._sequence, "at_utc": utc_now(), "event": kind, **fields})
        with (self.path / "events.jsonl").open("a") as stream:
            stream.write(canonical_bytes(event).decode() + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def finish(self, summary):
        if self.finished:
            raise RuntimeError("run already finished")
        self.event("completed")
        self.write("summary.json", summary)
        self.write("checksums.json", {str(p.relative_to(self.path)): sha256_file(p)
                                     for p in sorted(self.path.rglob("*")) if p.is_file() and p.name != '.lock'})
        self.finished = True
        self._release_lock()

    def _acquire_lock(self):
        self._lock = (self.path / '.lock').open('a')
        try:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._lock.close()
            raise RuntimeError('run already owned by another worker') from None

    def _release_lock(self):
        if getattr(self,'_lock',None) and not self._lock.closed:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_UN)
            self._lock.close()

    def __enter__(self):
        return self

    @classmethod
    def resume(cls, root, path, config):
        path, root = Path(path).resolve(), Path(root).resolve()
        if not path.is_relative_to(root / 'data/processed/runs'):
            raise ValueError('resume path outside run store')
        manifest = json.loads((path / 'manifest.json').read_text())
        if manifest['config'] != redact(config) or manifest['code'] != code_identity(root):
            raise ValueError('resume configuration or code changed')
        if (path / 'summary.json').exists():
            raise ValueError('run already finalized; create a new recorded run')
        obj = cls.__new__(cls)
        obj.root, obj.path = root, path
        obj.run_id, obj.experiment_id = manifest['run_id'], manifest['experiment_id']
        obj._acquire_lock()
        lines = (path / 'events.jsonl').read_text().splitlines()
        obj._sequence = max(json.loads(line)['sequence'] for line in lines)
        obj.finished = False
        obj.event('resumed')
        return obj

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.event("failed", error_type=exc_type.__name__)
        elif not self.finished:
            self.finish({"status": "DONE"})
        self._release_lock()
