"""Unarmed saved-JSON one-call admission/control draft; no actual worker.

Pure packet review and authored create-once/cleanup helpers only. This is not an
actual release, runtime sandbox or permission to read the sixteen saved inputs.
"""
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import time

LIMITS={'wall_seconds':60,'child_CPU_seconds':30,'saved_JSON_bytes':8388608,'project_source_bytes':1048576,
        'write_bytes':2097152,'public_output_bytes':131072,'console_bytes':16384,'reader_calls':1,'retries':0}
BINDING_KEYS=('reader','project_sources','config_file','config_contract_sha256','saved_inputs','references','adapter','adapter_entry','adapter_tests','launcher','historical_reader_review','runtime_selected_origins_sha256')
_ACTUAL_DISABLED='ACTUAL_DISABLED_COMPONENT_CORRECTION_ENTRY_REVIEW_AND_ROOT_RELEASE_REQUIRED'


class Refused(RuntimeError):pass

def need(ok,code):
    if not ok:raise Refused(code)
def packed(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def closed(value,keys):return type(value) is dict and set(value)==set(keys)
def hash_ok(value):return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def strict(raw):
    need(type(raw) is bytes and len(raw)<=131072,'PACKET_SIZE')
    def pairs(items):
        result={}
        for k,v in items:need(k not in result,'PACKET_DUPLICATE');result[k]=v
        return result
    def number(token):
        value=float(token);need(math.isfinite(value),'PACKET_NONFINITE');return value
    def bad(_):raise Refused('PACKET_NONFINITE')
    try:return json.loads(raw,object_pairs_hook=pairs,parse_float=number,parse_constant=bad)
    except (ValueError,UnicodeError,RecursionError):raise Refused('PACKET_JSON') from None


def relative(path):
    need(type(path) is str and path and ':' not in path and '\\' not in path and '\x00' not in path,'PATH')
    p=Path(path);need(not p.is_absolute() and '..' not in p.parts and str(p)==path,'PATH');return path

def ref(value):
    need(closed(value,('path','bytes','sha256')) and type(value['bytes']) is int and 0<=value['bytes']<=4194304 and hash_ok(value['sha256']),'REF')
    relative(value['path'])


def inspect_candidate(raw):
    """Closed unarmed metadata admission, zero filesystem or dispatch effects."""
    p=strict(raw)
    need(closed(p,('kind','state','actual_execution_enabled','scope_id','limits','invocation','bindings','reviews','one_shot_control','trusted_runtime_boundary','expected_metrics')),'PACKET_SCHEMA')
    need(p['kind']=='E01_SAVED_JSON_ONE_CALL_CANDIDATE_V1' and p['state']=='UNARMED_PREPARATION_ONLY' and p['actual_execution_enabled'] is False,'UNARMED_ONLY')
    need(p['scope_id']=='e01-saved-json-one-call-candidate-20261117','SCOPE')
    need(packed(p['limits'])==packed(LIMITS),'LIMITS')
    need(p['invocation']=={'module':'civiclab.e01.ballots_v1_9_1','function':'read_verified_public','calls':1,
        'arguments':'immutable_virtual_primary_dir,root=immutable_virtual_root,contract=detached_admitted_config'},'INVOCATION')
    b=p['bindings'];need(closed(b,BINDING_KEYS),'BINDINGS')
    for key in ('reader','config_file','adapter','adapter_entry','adapter_tests','launcher','historical_reader_review'):ref(b[key])
    need(hash_ok(b['config_contract_sha256']) and hash_ok(b['runtime_selected_origins_sha256']),'HASH')
    for key,count in (('project_sources',14),('saved_inputs',12),('references',4)):
        need(type(b[key]) is dict and len(b[key])==count,'REF_SET')
        for item in b[key].values():ref(item)
    need(b['reader']==b['project_sources'].get('src/civiclab/e01/ballots_v1_9_1.py'),'READER_JOIN')
    need(b['config_file']['sha256']!=b['config_contract_sha256'],'DISTINCT_HASH_MEANINGS')
    need(p['reviews']=={'corrected_component_review':None,'actual_entry_review':None,'root_one_call_release':None},'NO_RELEASE')
    need(p['one_shot_control']=={'directory':'data/processed/e01_saved_json_one_call_control_v1/20261117-candidate',
        'consume':'STARTED.json O_CREAT|O_EXCL|O_NOFOLLOW before any body read or child dispatch','retry':False,'actual_directory_created':False},'CONTROL')
    need(p['trusted_runtime_boundary']=='Pinned trusted CPython3.12.14 and selected prewarmed stdlib origins; startup/prewarm bytes excluded explicitly; no G03 qualification claim.','RUNTIME_BOUNDARY')
    need(p['expected_metrics']=={'regular_frame_slots':33,'document_state_coverage_count':13,'remaining_document_acquisition_jobs':20,'final_ballots_accepted':0},'METRICS')
    return {'status':_ACTUAL_DISABLED,'packet_sha256':sha(raw),'new_reader_calls':0,'actual_control_writes':0,'model_calls':0,'cost_usd':0}


class Deadline:
    """57s work +2s termination/reaping +1s bounded finalization =60s."""
    def __init__(self,clock=time.monotonic,cancel=lambda:False):
        self.clock=clock;self.cancel=cancel;self.start=self.last=clock();self.phase='WORK';self.primary=None
        need(type(self.start) in {int,float} and math.isfinite(self.start),'CLOCK')
    def fail(self,code):
        if self.primary is None:self.primary=Refused(code)
        raise self.primary
    def now(self):
        value=self.clock()
        if type(value) not in {int,float} or not math.isfinite(value) or value<self.last:self.fail('CLOCK')
        self.last=value;return value
    def check(self):
        if self.primary:raise self.primary
        if self.phase!='WORK':self.fail('AFTER_WORK')
        value=self.now();cancelled=self.cancel()
        if type(cancelled) is not bool or cancelled:self.fail('CANCELLED')
        if value>=self.start+57:self.fail('WORK_DEADLINE')
    def work_remaining(self):self.check();return self.start+57-self.last
    def cleanup(self):self.phase='CLEANUP';return max(0,self.start+59-self.now())
    def final_remaining(self):self.phase='FINALIZE';return max(0,self.start+60-self.now())


class AuthoredControl:
    """Exercise create-once protocol only under an owned authored temp tree."""
    def __init__(self,root,packet_sha256):
        need(hash_ok(packet_sha256),'PACKET_HASH')
        root=Path(root).absolute();need(root.name.startswith('ssl-saved-json-entry-fixture-'),'AUTHORED_ROOT')
        need('..' not in root.parts and not any(p.is_symlink() for p in (root,*root.parents)),'ROOT_ALIAS')
        need(root.is_dir(),'ROOT_DIRECTORY');self.root=root;self.packet_sha256=packet_sha256;self.bytes=0;self.spent=False
    def new(self,name,value):
        need(name in {'STARTED.json','COMPLETE.json','FAILURE.json','source_job_ledger.json'},'OUTPUT_NAME')
        raw=packed(value);need(len(raw)<=131072 and self.bytes+len(raw)<=2097152,'OUTPUT_CAP')
        fd=os.open(self.root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(raw);f.flush();os.fsync(f.fileno())
        finally:
            #fdopen owns/closesfd. No retry after partialfile/fsync failure.
            pass
        self.bytes+=len(raw)
    def consume(self):
        need(not self.spent,'SPENT_CONTROL');self.spent=True
        self.new('STARTED.json',{'kind':'AUTHORED_CONTROL_ONLY','packet_sha256':self.packet_sha256,'no_retry':True,'actual_reader_calls':0})


def terminate_and_reap(child,deadline):
    """Finite cleanup; caller preserves the original execution error."""
    remaining=deadline.cleanup()
    if child.poll() is None:
        child.terminate()
        try:child.wait(timeout=min(1,remaining))
        except subprocess.TimeoutExpired:
            child.kill();child.wait(timeout=max(0,deadline.start+59-deadline.now()))
    need(child.poll() is not None,'CHILD_NOT_REAPED')
    need(deadline.final_remaining()>0,'FINALIZATION_DEADLINE')


def collect_child(child,deadline):
    """Draft bounded transport: stdout publicartifact vs stderr console."""
    buffers={'artifact':bytearray(),'console':bytearray()};caps={'artifact':131072,'console':16384}
    primary=None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout,selectors.EVENT_READ,'artifact');selector.register(child.stderr,selectors.EVENT_READ,'console')
            while selector.get_map():
                wait=deadline.work_remaining()
                for key,_ in selector.select(min(wait,0.1)):
                    name=key.data;left=caps[name]-len(buffers[name]);chunk=os.read(key.fd,min(4096,left+1))
                    if not chunk:selector.unregister(key.fileobj);continue
                    if len(chunk)>left:deadline.fail('ARTIFACT_CAP' if name=='artifact' else 'CONSOLE_CAP')
                    buffers[name].extend(chunk)
            child.wait(timeout=deadline.work_remaining());deadline.check()
            need(child.returncode==0,'CHILD_EXIT')
    except BaseException as error:primary=deadline.primary or error
    finally:
        try:terminate_and_reap(child,deadline)
        except BaseException as error:
            if primary is None:primary=error
        child.stdout.close();child.stderr.close()
    if primary:raise primary
    return bytes(buffers['artifact']),bytes(buffers['console'])


def actual_entry(*args,**kwargs):
    # Deliberately before argument access, source/body opens, marker or Popen.
    # An actual worker and reviewed release API are not supplied by this draft.
    raise Refused(_ACTUAL_DISABLED)


def main():
    print(json.dumps({'status':_ACTUAL_DISABLED,'actual_reader_calls':0,'actual_control_writes':0,'model_calls':0,'cost_usd':0},sort_keys=True))
    return 0


if __name__=='__main__':raise SystemExit(main())
