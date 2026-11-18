#!/usr/bin/env python3
"""Admit the exact one-slot launcher, then inject the existing private saved key.

This entry does not grant authority or retry. The unchanged launcher rechecks its
packet/release and enforces the original owner, request and spending limits.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'scripts/continue_e02_wrapper_crossmodel_canary_v1_20261117.py'
KEY_READER = ROOT / 'scripts/collect_connectivity_billing_once.py'
LAUNCHER_SHA = '0ff0db64c9c89abc699b367b743945bf464e676f13278cacf5f76ece53be545d'
KEY_READER_SHA = '0b5ea3cca5d6d71550985d1da12f9264f223662af7d6429ecab4d88b4cb8f4a7'


def _load_exact(path, expected):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RuntimeError('aliased entry dependency')
    with path.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError('entry dependency changed')
    namespace = {'__name__': '_reviewed_canary_entry_dependency', '__file__': str(path)}
    exec(compile(raw, str(path), 'exec'), namespace)
    return SimpleNamespace(**namespace)


def run(packet_sha, release_sha):
    # Source execution uses verified bytes rather than an unchecked pyc cache.
    launcher = _load_exact(LAUNCHER, LAUNCHER_SHA)
    from civiclab.e02.wrapper_crossmodel_canary_v1_client import validate_release
    packet = launcher.read_exact(launcher.SCOPE / 'packet.json', packet_sha)
    release = launcher.read_exact(launcher.SCOPE / 'lead-release.json', release_sha)
    validate_release(release, packet, packet_sha, release_sha)
    reader = _load_exact(KEY_READER, KEY_READER_SHA)
    credential = reader._credential(ROOT)
    previous = os.environ.get('OPENROUTER_API_KEY')
    previous_argv = sys.argv
    try:
        os.environ['OPENROUTER_API_KEY'] = credential._value
        sys.argv = [str(LAUNCHER), '--packet-sha256', packet_sha,
                    '--release-sha256', release_sha]
        return launcher.main()
    finally:
        sys.argv = previous_argv
        if previous is None:
            os.environ.pop('OPENROUTER_API_KEY', None)
        else:
            os.environ['OPENROUTER_API_KEY'] = previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet-sha256', required=True)
    parser.add_argument('--release-sha256', required=True)
    args = parser.parse_args()
    run(args.packet_sha256, args.release_sha256)


def safe_failure(error):
    result = {'status': 'STOPPED_NO_RETRY',
              'original_full80_analysis': 'NOT_RUN_INCOMPLETE'}
    # Preserve only the existing transport's closed, revalidated diagnostic.
    # Never inspect or print arbitrary exception text, response bodies or keys.
    try:
        from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
        if type(error) is _SafeTransportFailure:
            result['diagnostic'] = _SafeTransportFailure.diagnostic(error)
    except BaseException:
        pass
    return result


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'src'))
    try:
        main()
    except BaseException as error:
        print(json.dumps(safe_failure(error), sort_keys=True))
        raise SystemExit(1)
