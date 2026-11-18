#!/usr/bin/env python3
"""Future exact lead-release entry only. No preparation or self-release mode."""
from pathlib import Path
import argparse
import hashlib
import json
import resource
import signal
import sys

ROOT=Path(__file__).resolve().parents[1]
SCOPE=ROOT/'data/processed/e02_wrapper_crossmodel_canary_v1_20261117_actual_01'


def read_exact(path,digest,maximum=65536):
    if not path.is_relative_to(SCOPE) or any(p.is_symlink() for p in (path,*path.parents)):
        raise RuntimeError('exact future release scope required')
    if not path.is_file() or path.stat().st_size>maximum:raise RuntimeError('bounded release file required')
    raw=path.read_bytes()
    if len(raw)>maximum or hashlib.sha256(raw).hexdigest()!=digest:raise RuntimeError('release hash mismatch')
    return json.loads(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('packet','release'):parser.add_argument('--'+name+'-sha256',required=True)
    args=parser.parse_args()
    # No key, owner or scope creation until exact packet/review/lead gate passes.
    from civiclab.common import canonical_hash
    from civiclab.e02.wrapper_crossmodel_canary_v1_client import validate_release
    packet=read_exact(SCOPE/'packet.json',args.packet_sha256)
    release=read_exact(SCOPE/'lead-release.json',args.release_sha256)
    validate_release(release,packet,args.packet_sha256,args.release_sha256)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(59,60))
    def timeout(*_):raise TimeoutError('canary240seconddeadline')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,240)
    from civiclab.e02.wrapper_crossmodel_canary_v1_owner import CanaryOwnerV1
    from civiclab.e02.wrapper_crossmodel_canary_v1_client import execute
    from civiclab.e02.exploratory_live_client_v1 import _read_environment_key,_transport,_fetch_public_catalog
    # These established credential/transport functions are not called in author work.
    owner=CanaryOwnerV1();credential=_read_environment_key()
    result=execute(packet,expected_packet_hash=args.packet_sha256,release=release,
                   expected_release_hash=args.release_sha256,owner=owner,credential=credential,
                   transport=_transport(credential),catalog_fetch=_fetch_public_catalog,
                   provenance='EXPLORATORY_REAL_MODEL')
    print(json.dumps({'kind':result['kind'],'status':result['status'],'records':len(result['records']),
                      'original_full80_analysis':'NOT_RUN_INCOMPLETE'},sort_keys=True))


if __name__=='__main__':
    try:main()
    except BaseException:
        print(json.dumps({'status':'STOPPED_NO_RETRY','original_full80_analysis':'NOT_RUN_INCOMPLETE'}))
        raise SystemExit(1)
