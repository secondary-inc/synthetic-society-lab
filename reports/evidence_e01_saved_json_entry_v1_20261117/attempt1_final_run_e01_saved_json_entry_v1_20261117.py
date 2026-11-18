"""Offline one-call entry; default unarmed. Only root supplies armed packets."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time
import types


def main():
    start=time.monotonic()
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default=str(Path(__file__).absolute().parents[1]))
    parser.add_argument('--packet');parser.add_argument('--packet-sha256')
    parser.add_argument('--worker',action='store_true');parser.add_argument('--start',type=float);parser.add_argument('--initial')
    args=parser.parse_args()
    if args.packet is None or args.packet_sha256 is None:
        print(json.dumps({'status':'UNARMED_NO_ROOT_PACKET','actual_reader_calls':0,'model_calls':0,'cost_usd':0}));return 0
    if not (sys.flags.isolated and sys.flags.dont_write_bytecode and sys.flags.no_site):return 2
    # Explicit entry only; never runs in a generic test collector.
    resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(2097152,2097152))
    anchor=args.start if args.worker else start
    if anchor is None or not 0<anchor<=time.monotonic():return 2
    remaining=anchor+(57 if args.worker else 60)-time.monotonic()
    if remaining<=0:return 2
    signal.setitimer(signal.ITIMER_REAL,remaining)
    helper=Path(args.root)/'src/civiclab/e01/saved_json_entry_v1.py'
    if helper.is_symlink() or helper.stat().st_size>131072:return 2
    raw=helper.read_bytes();module=types.ModuleType('ssl_one_call_entry');module.__file__=str(helper)
    exec(compile(raw,str(helper),'exec'),module.__dict__)
    try:
        if args.worker:
            output=module.production_worker(args.root,args.packet,args.packet_sha256,args.start,module.strict(args.initial.encode()))
            sys.stdout.buffer.write(output);sys.stdout.buffer.flush()
        else:
            result=module.production_parent(args.root,args.packet,args.packet_sha256,start)
            print(json.dumps(result,sort_keys=True))
        return 0
    except BaseException as error:
        print(json.dumps({'status':'FAILED_UNACCEPTED','error_code':module.safe_error(error),'model_calls':0,'cost_usd':0}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
