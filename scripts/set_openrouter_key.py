#!/usr/bin/env python3
"""Install a replacement key locally through a hidden terminal prompt.

No network, model execution, shell evaluation, secret printing or key argument.
Other .env settings are preserved. Temporary files match the ignored .env.* rule.
"""
import getpass
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


def save_key(root, key):
    root = Path(root).resolve()
    path = root/'.env'
    if (type(key) is not str or not 16 <= len(key) <= 4096
            or re.fullmatch(r'sk-or-v1-[A-Za-z0-9_-]+', key) is None):
        raise ValueError('Key has an invalid transport format; nothing saved.')
    if path.is_symlink():
        raise ValueError('Refusing a symlink credential file.')
    if path.exists():
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_size > 65536:
            raise ValueError('Credential file ownership or size is unexpected.')
        previous = path.read_text()
    else:
        previous = ''
    lines = previous.splitlines(keepends=True)
    expression = re.compile(r'^\s*(?:export\s+)?OPENROUTER_API_KEY\s*=')
    replacement = 'OPENROUTER_API_KEY='+key+'\n'
    output = []
    inserted = False
    for line in lines:
        if expression.match(line):
            if not inserted:
                output.append(replacement)
                inserted = True
        else:
            output.append(line)
    if not inserted:
        if output and not output[-1].endswith(('\n','\r')):
            output.append('\n')
        output.append(replacement)
    descriptor, temporary = tempfile.mkstemp(prefix='.env.key-', dir=root)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(''.join(output))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    root = Path(__file__).resolve().parents[1]
    if not sys.stdin.isatty():
        print('Run this command in an interactive terminal; hidden input is required.', file=sys.stderr)
        return 1
    ignored = subprocess.run(['git','check-ignore','--quiet','.env'], cwd=root, check=False)
    if ignored.returncode != 0:
        print('Refusing to save: .env is not Git-ignored.', file=sys.stderr)
        return 1
    try:
        key = getpass.getpass('Paste the NEW rotated OpenRouter key (hidden): ')
        save_key(root, key)
    except (ValueError, OSError, EOFError):
        print('Key was not saved. Check the key format and private file access.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nCancelled; key was not saved.', file=sys.stderr)
        return 1
    print('Saved privately to .env. No API request or experiment was run.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
