"""Read-only installer fingerprint preparation; does not install or import pip."""
from pathlib import Path
import hashlib
import json
import os
import resource
import signal
import stat
import sys
import time
from email.parser import BytesParser

ROOT = Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
BASE = Path('/Users/joshua/.cache/codex-runtimes/codex-primary-runtime/dependencies/python')
OUT = ROOT / 'data/processed/e01_pypdf701_installer_binding_v1_20261115'
CAPS = dict(files=4096, directories=4096, total_bytes=134217728,
            file_bytes=67108864, output_bytes=2097152, wall_seconds=60)


def main():
    if Path.cwd() != ROOT or sys.version.split()[0] != '3.12.14':
        raise RuntimeError('unexpected runtime')
    executable = Path(sys.executable).resolve(strict=True)
    if executable != BASE / 'bin/python3.12' or Path(sys.base_prefix) != BASE:
        raise RuntimeError('unexpected base interpreter')
    if any(p.is_symlink() for p in (OUT, *OUT.parents)):
        raise RuntimeError('output alias')
    OUT.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    counts = dict(files=0, directories=0, total_bytes=0)
    metadata_body = bytearray()
    written = 0

    def save(name, obj):
        nonlocal written
        body = json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        if written + len(body) > CAPS['output_bytes']:
            raise RuntimeError('output cap')
        written += len(body)
        fd = os.open(OUT / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        return dict(path=str((OUT / name).relative_to(ROOT)), bytes=len(body),
                    sha256=hashlib.sha256(body).hexdigest())

    def fingerprint(path):
        if time.monotonic() - started > CAPS['wall_seconds']:
            raise RuntimeError('deadline')
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise RuntimeError('input alias')
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size > CAPS['file_bytes']:
            raise RuntimeError('input type or size')
        counts['files'] += 1
        counts['total_bytes'] += before.st_size
        if counts['files'] > CAPS['files'] or counts['total_bytes'] > CAPS['total_bytes']:
            raise RuntimeError('read cap')
        digest = hashlib.sha256()
        size = 0
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise RuntimeError('input changed')
            while size < before.st_size:
                body = stream.read(min(65536, before.st_size - size))
                if not body:
                    raise RuntimeError('short input')
                size += len(body)
                digest.update(body)
                if path == metadata:
                    metadata_body.extend(body)
            after = os.fstat(stream.fileno())
            if (after.st_size, after.st_mtime_ns) != (opened.st_size, opened.st_mtime_ns):
                raise RuntimeError('input changed')
        return dict(bytes=size, sha256=digest.hexdigest())

    def deadline(*_):
        raise RuntimeError('deadline')

    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, CAPS['wall_seconds'])
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    save('STARTED.json', dict(kind='INSTALLER_BINDING_STARTED', caps=CAPS,
                             network=0, installation=False, package_imports=False))
    try:
        site = ROOT / '.venv/lib/python3.12/site-packages'
        pip_root = site / 'pip'
        metadata = site / 'pip-25.0.1.dist-info/METADATA'
        manifest = {}
        for parent, dirs, names in os.walk(pip_root, followlinks=False):
            counts['directories'] += 1
            if counts['directories'] > CAPS['directories']:
                raise RuntimeError('directory cap')
            for name in dirs:
                if (Path(parent) / name).is_symlink():
                    raise RuntimeError('package alias')
            for name in sorted(names):
                path = Path(parent) / name
                manifest[str(path.relative_to(ROOT))] = fingerprint(path)
        if not manifest or not (pip_root / '__pip-runner__.py').is_file():
            raise RuntimeError('missing pip')
        metadata_ref = dict(path=str(metadata.relative_to(ROOT)), **fingerprint(metadata))
        parsed = BytesParser().parsebytes(bytes(metadata_body))
        if parsed.get('Name') != 'pip' or parsed.get('Version') != '25.0.1':
            raise RuntimeError('pip identity')
        binding = dict(kind='E01_INSTALLER_BINDING_V1',
                       target=dict(python='3.12.14', OS='macOS', architecture='arm64'),
                       executable_ref=dict(path=str(executable), **fingerprint(executable)),
                       base_prefix=str(BASE), pip_version='25.0.1',
                       pip_root=str(pip_root.relative_to(ROOT)),
                       pip_metadata_ref=metadata_ref,
                       pip_files=manifest, counts=counts, caps=CAPS,
                       installation=False, package_imports=False, network=0)
        ref = save('binding.json', binding)
        save('TERMINAL.json', dict(status='COMPLETE_BINDING_ONLY', binding_ref=ref,
                                  counts=counts, elapsed_seconds=time.monotonic()-started))
        print(json.dumps(dict(status='COMPLETE_BINDING_ONLY', binding_ref=ref, counts=counts)))
    except BaseException as error:
        save('TERMINAL.json', dict(status='FAILED_NO_RETRY', error_type=type(error).__name__,
                                  counts=counts, elapsed_seconds=time.monotonic()-started))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    main()
