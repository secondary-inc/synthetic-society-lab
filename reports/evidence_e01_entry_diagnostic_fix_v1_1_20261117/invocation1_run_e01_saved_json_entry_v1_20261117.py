"""Offline one-call entry; default unarmed. Only root supplies armed packets."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import stat
import sys
import time
import types


class BootstrapRefused(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise BootstrapRefused(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def strict(raw):
    def pairs(items):
        result={}
        for key,value in items:need(key not in result,'BOOTSTRAP_DUPLICATE');result[key]=value
        return result
    def number(token):
        value=float(token);need(math.isfinite(value),'BOOTSTRAP_NONFINITE');return value
    def invalid(_):raise BootstrapRefused('BOOTSTRAP_NONFINITE')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid,parse_float=number)
def read_bootstrap(path,cap,packet=False):
    path=Path(path).absolute();need('..' not in path.parts and not any(p.is_symlink() for p in (path,*path.parents)),'BOOTSTRAP_ALIAS')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());need(stat.S_ISREG(before.st_mode) and before.st_size<=cap,'BOOTSTRAP_SIZE')
        if packet:need(before.st_uid==os.getuid() and stat.S_IMODE(before.st_mode)==0o600,'BOOTSTRAP_PACKET_MODE')
        raw=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
    ident=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    need(ident(before)==ident(after) and len(raw)==before.st_size,'BOOTSTRAP_DRIFT');return raw



_BASE_ERROR_DICT=BaseException.__dict__['__dict__']
_BASE_ERROR_ARGS=BaseException.__dict__['args']
_SAFE_BOOTSTRAP_CODES=frozenset(('BOOTSTRAP_ALIAS', 'BOOTSTRAP_DRIFT', 'BOOTSTRAP_DUPLICATE', 'BOOTSTRAP_HELPER_BINDING', 'BOOTSTRAP_LAUNCHER_BINDING', 'BOOTSTRAP_NONFINITE', 'BOOTSTRAP_PACKET_HASH', 'BOOTSTRAP_PACKET_MODE', 'BOOTSTRAP_PACKET_PATH', 'BOOTSTRAP_SIZE', 'BOOTSTRAP_UNARMED'))


def bootstrap_error(error):
    if type(error) is not BootstrapRefused:return 'BOOTSTRAP_FAILURE'
    if any(k in BootstrapRefused.__dict__ for k in ('code','args','__dict__','__getattribute__','__str__')):return 'BOOTSTRAP_FAILURE'
    fields=_BASE_ERROR_DICT.__get__(error,BootstrapRefused)
    args=_BASE_ERROR_ARGS.__get__(error,BootstrapRefused)
    if type(fields) is not dict or type(args) is not tuple or len(args)!=1:return 'BOOTSTRAP_FAILURE'
    code=dict.get(fields,'code')
    if type(code) is not str or type(args[0]) is not str or code not in _SAFE_BOOTSTRAP_CODES or args[0]!=code:return 'BOOTSTRAP_FAILURE'
    return code


def main():
    start=time.monotonic();module=None
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default=str(Path(__file__).absolute().parents[1]))
    parser.add_argument('--packet');parser.add_argument('--packet-sha256')
    parser.add_argument('--worker',action='store_true');parser.add_argument('--start',type=float);parser.add_argument('--initial')
    args=parser.parse_args()
    if args.packet is None or args.packet_sha256 is None:
        print(json.dumps({'status':'UNARMED_NO_ROOT_PACKET','actual_reader_calls':0,'model_calls':0,'cost_usd':0}));return 0
    if not (sys.flags.isolated and sys.flags.dont_write_bytecode and sys.flags.no_site):return 2
    resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(2097152,2097152))
    anchor=args.start if args.worker else start
    if anchor is None or not 0<anchor<=time.monotonic():return 2
    remaining=anchor+(57 if args.worker else 60)-time.monotonic()
    if remaining<=0:return 2
    signal.setitimer(signal.ITIMER_REAL,remaining)
    try:
        relative=Path(args.packet)
        need(not relative.is_absolute() and '..' not in relative.parts and str(relative)==args.packet and args.packet.startswith('data/processed/e01_saved_json_one_call_packets/'),'BOOTSTRAP_PACKET_PATH')
        packet_raw=read_bootstrap(Path(args.root)/relative,131072,True)
        need(sha(packet_raw)==args.packet_sha256,'BOOTSTRAP_PACKET_HASH');p=strict(packet_raw)
        need(type(p) is dict and p.get('kind')=='E01_SAVED_JSON_ROOT_ONE_CALL_V1' and p.get('armed') is True and p.get('issued_by')=='ROOT_REVIEWED_ONE_CALL','BOOTSTRAP_UNARMED')
        name='src/civiclab/e01/saved_json_entry_v1.py';helper=Path(args.root)/name;raw=read_bootstrap(helper,131072)
        r=p['code_refs'][name];need(r=={'path':name,'bytes':len(raw),'sha256':sha(raw)},'BOOTSTRAP_HELPER_BINDING')
        launcher=read_bootstrap(Path(__file__),8192);r=p['code_refs']['scripts/run_e01_saved_json_entry_v1_20261117.py']
        need(r=={'path':'scripts/run_e01_saved_json_entry_v1_20261117.py','bytes':len(launcher),'sha256':sha(launcher)},'BOOTSTRAP_LAUNCHER_BINDING')
        usage={'saved_JSON_bytes':len(packet_raw)+1,'project_source_bytes':len(raw)+len(launcher)+2}
        module=types.ModuleType('ssl_one_call_entry');module.__file__=str(helper)
        exec(compile(raw,str(helper),'exec'),module.__dict__)
        if args.worker:
            output=module.production_worker(args.root,args.packet,args.packet_sha256,args.start,module.strict(args.initial.encode()),bootstrap_usage=usage)
            sys.stdout.buffer.write(output);sys.stdout.buffer.flush()
        else:
            result=module.production_parent(args.root,args.packet,args.packet_sha256,start,bootstrap_usage=usage)
            print(json.dumps(result,sort_keys=True))
        return 0
    except BaseException as error:
        code=module.safe_error(error) if module is not None else bootstrap_error(error)
        print(json.dumps({'status':'FAILED_UNACCEPTED','error_code':code,'model_calls':0,'cost_usd':0}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
