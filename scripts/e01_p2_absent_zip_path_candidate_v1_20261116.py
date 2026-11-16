"""Unreleased pure path proposal; not wired into any installer."""
from pathlib import Path


def narrowed_paths(original, base_prefix):
    """Return exact directory roots only after verifying conventional ZIP absent."""
    if type(original) is not list or any(type(value) is not str for value in original):
        raise ValueError('PIP_PATH_SCHEMA')
    base = Path(base_prefix)
    if not base.is_absolute() or '..' in base.parts:
        raise ValueError('PIP_BASE_PATH')
    archive = base/'lib/python312.zip'
    stdlib = base/'lib/python3.12'
    dynamic = stdlib/'lib-dynload'
    if original != [str(archive), str(stdlib), str(dynamic)]:
        raise ValueError('PIP_UNEXPECTED_PATHS')
    for path in (archive, stdlib, dynamic):
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError('PIP_PATH_ALIAS')
    try:
        archive.lstat()
    except FileNotFoundError:
        pass
    else:
        raise ValueError('PIP_ZIP_PRESENT')
    if not stdlib.is_dir() or not dynamic.is_dir():
        raise ValueError('PIP_STDLIB_DIRECTORY')
    return [str(stdlib), str(dynamic)]
