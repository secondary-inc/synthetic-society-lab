"""Ordinary CI wrapper for30 authored cases in a disposable interpreter.

Discovery performs no fixture/source reads, launches or process-control changes.
The child owns all fixture setup, audit hooks, alarm and resource limits. This
wrapper reports one ordinary case and30 explicitly validated nested cases.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).absolute().parents[1]
SCRIPT='scripts/run_e01_saved_job_ledger_suite_v1.py'
CONSOLE_CAP=262144
WALL_SECONDS=180
PINS={
 SCRIPT:(24290,'2d9913891b91d4ac155e5850f7e2ba98d5675a43320f16850cc8bb6b96b57f7a'),
 'src/civiclab/e01/source_job_ledger_v1.py':(25240,'fc0bf218eb486b4489bd109dcffc84d9538716cc80dd6034edb66bbb8b9415d7'),
 'scripts/compile_e01_saved_job_ledger_v1_20261117.py':(656,'f96156495896a196e3cf92418fc98a730fc1292b6a30a1889a91c1349e1d63a0')}


def verified_script():
    script=None
    for relative,(size,digest) in PINS.items():
        path=ROOT/relative
        if any(p.is_symlink() for p in (path,*path.parents)):raise AssertionError('CI_INPUT_ALIAS')
        if path.stat().st_size!=size:raise AssertionError('CI_INPUT_SIZE')
        raw=path.read_bytes()
        if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=digest:raise AssertionError('CI_INPUT_HASH')
        if relative==SCRIPT:script=raw
    return script


def bounded_child():
    """One child, finite output/deadline; terminate/reap on every failure."""
    start=time.monotonic();deadline=start+WALL_SECONDS-2
    child=subprocess.Popen([sys.executable,'-I','-B','-S',str(ROOT/SCRIPT)],
        cwd=ROOT,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    chunks=[];count=0
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout,selectors.EVENT_READ)
            while selector.get_map():
                left=deadline-time.monotonic()
                if left<=0:raise AssertionError('CI_CHILD_DEADLINE')
                for key,_ in selector.select(min(left,0.1)):
                    raw=os.read(key.fd,min(65536,CONSOLE_CAP-count+1))
                    if not raw:selector.unregister(key.fileobj);continue
                    count+=len(raw)
                    if count>CONSOLE_CAP:raise AssertionError('CI_CHILD_CONSOLE_CAP')
                    chunks.append(raw)
            left=deadline-time.monotonic()
            if left<=0:raise AssertionError('CI_CHILD_DEADLINE')
            child.wait(timeout=left)
        if time.monotonic()>deadline:raise AssertionError('CI_CHILD_DEADLINE')
        return child.returncode,b''.join(chunks),time.monotonic()-start
    finally:
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=1)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=1)
        child.stdout.close()


def validate_nested(raw,script):
    if type(raw) is not bytes or len(raw)>CONSOLE_CAP:raise AssertionError('CI_CHILD_CONSOLE_CAP')
    lines=raw.decode('utf-8',errors='strict').splitlines()
    tree=ast.parse(script)
    case=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LedgerTests')
    expected=sorted(n.name for n in case.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
    actual=sorted(line.split(' ',1)[0] for line in lines if line.startswith('test_') and line.endswith(' ... ok'))
    if len(expected)!=30 or actual!=expected:raise AssertionError('CI_NESTED_CASE_COVERAGE')
    records=[json.loads(line) for line in lines if line.startswith('{')]
    if len(records)!=1:raise AssertionError('CI_NESTED_RECEIPT_COUNT')
    receipt=records[0]
    keys={'kind','tests','failures','errors','guard','wall_seconds','real_saved_reader_calls','network_calls','model_calls','cost_usd','interpreter_startup_read_accounting'}
    if type(receipt) is not dict or set(receipt)!=keys:raise AssertionError('CI_NESTED_RECEIPT_SCHEMA')
    if receipt['kind']!='MOCK_SAVED_JOB_LEDGER_SUITE' or type(receipt['tests']) is not int or receipt['tests']!=30:raise AssertionError('CI_NESTED_CASE_COUNT')
    if any(type(receipt[k]) is not int or receipt[k]!=0 for k in ('failures','errors','real_saved_reader_calls','network_calls','model_calls','cost_usd')):raise AssertionError('CI_NESTED_FAILURE_OR_SIDE_EFFECT')
    guard=receipt['guard']
    if type(guard) is not dict or set(guard)!={'denied','logical_open_read_bytes','fixture_write_bytes'}:raise AssertionError('CI_NESTED_GUARD')
    if any(type(v) is not int or v<0 for v in guard.values()):raise AssertionError('CI_NESTED_GUARD')
    if guard['denied']!=0 or guard['logical_open_read_bytes']>67108864 or guard['fixture_write_bytes']>33554432:raise AssertionError('CI_NESTED_GUARD')
    if type(receipt['wall_seconds']) not in {int,float} or not 0<=receipt['wall_seconds']<120:raise AssertionError('CI_NESTED_TIME')
    if receipt['interpreter_startup_read_accounting']!='NOT_CLAIMED':raise AssertionError('CI_STARTUP_SCOPE')
    return receipt,expected


class SavedJobLedgerCIIntegration(unittest.TestCase):
    def test_saved_ledger_30_authored_cases_in_child(self):
        script=verified_script()
        returncode,raw,wall=bounded_child()
        # Failure output is retained by the calling CI log; do not report PASS.
        self.assertEqual(returncode,0,raw.decode('utf-8',errors='replace'))
        receipt,cases=validate_nested(raw,script)
        print('E01_SAVED_LEDGER_CI_NESTED_V1='+json.dumps({'status':'MOCK_NESTED_30_PASS',
            'ordinary_wrapper_cases':1,'nested_cases':cases,'nested_receipt':receipt,
            'child_wall_seconds':wall,'child_console_bytes':len(raw),
            'script_sha256':PINS[SCRIPT][1],'actual_saved_reader_calls':0,
            'startup_resource_qualification':'NOT_CLAIMED'},sort_keys=True))


if __name__=='__main__':unittest.main(verbosity=2)
