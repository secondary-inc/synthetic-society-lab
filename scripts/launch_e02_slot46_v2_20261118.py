#!/usr/bin/env python3
"""Exact separate slot46 entry. No preparation, self-release or retry mode."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys

ROOT=Path(__file__).resolve().parents[1]
SCOPE=ROOT/'data/processed/e02_wrapper_slot46_v2_20261118_actual_01'
KEY_READER_SHA='0b5ea3cca5d6d71550985d1da12f9264f223662af7d6429ecab4d88b4cb8f4a7'


def read_exact(path,digest,maximum=65536):
    if not path.is_relative_to(SCOPE) or '..' in path.parts or any(p.is_symlink() for p in (path,*path.parents)):
        raise RuntimeError('exact separate release scope required')
    with path.open('rb') as stream:raw=stream.read(maximum+1)
    if len(raw)>maximum or hashlib.sha256(raw).hexdigest()!=digest:
        raise RuntimeError('bounded exact release required')
    return json.loads(raw)


def _credential():
    # Verified source bytes, no unchecked project bytecode; admitted before read.
    path=ROOT/'scripts/collect_connectivity_billing_once.py'
    if any(p.is_symlink() for p in (path,*path.parents)):raise RuntimeError('aliased key reader')
    with path.open('rb') as stream:raw=stream.read(65537)
    if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=KEY_READER_SHA:
        raise RuntimeError('changed key reader')
    namespace={'__name__':'_reviewed_slot46_key_reader','__file__':str(path)}
    exec(compile(raw,str(path),'exec'),namespace)
    return namespace['_credential'](ROOT)


def _make_owner():
    from civiclab.e02.wrapper_crossmodel_slot46_v2_owner import Slot46OwnerV2
    return Slot46OwnerV2()


def _make_transport(credential):
    from civiclab.e02.exploratory_live_client_v1 import _transport
    return _transport(credential)


def _catalog(model):
    from civiclab.e02.exploratory_live_client_v1 import _fetch_public_catalog
    return _fetch_public_catalog(model)


def main():
    # CPU includes process startup; wall timer covers admission, owner, key and
    # all success/error finalization. This is intentionally a one-process entry.
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_CPU,(120,125))
    # A Python TimeoutError can be swallowed by best-effort error cleanup.
    # Native termination makes this a hard wall bound even inside that cleanup.
    # Outstanding reservations remain held; a late diagnostic is not guaranteed.
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,240)
    try:
        parser=argparse.ArgumentParser(description=__doc__)
        for name in ('packet','release'):parser.add_argument('--'+name+'-sha256',required=True)
        args=parser.parse_args()
        from civiclab.e02.wrapper_crossmodel_slot46_v2_client import validate_release,execute
        packet=read_exact(SCOPE/'packet.json',args.packet_sha256)
        release=read_exact(SCOPE/'lead-release.json',args.release_sha256)
        validate_release(release,packet,args.packet_sha256,args.release_sha256)
        # No key or normal owner access before both exact releases are verified.
        owner=_make_owner();credential=_credential()
        result=execute(packet,expected_packet_hash=args.packet_sha256,release=release,
                       expected_release_hash=args.release_sha256,owner=owner,
                       credential=credential,transport=_make_transport(credential),
                       catalog_fetch=_catalog,provenance='EXPLORATORY_REAL_MODEL')
        print(json.dumps({'kind':result['kind'],'status':result['status'],
                          'records':len(result['records']),
                          'original_full80_analysis':'NOT_RUN_INCOMPLETE'},sort_keys=True))
        return result
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'src'))
    try:main()
    except BaseException:
        print(json.dumps({'status':'STOPPED_NO_RETRY','original_full80_analysis':'NOT_RUN_INCOMPLETE'}))
        raise SystemExit(1)
