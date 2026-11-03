"""Bounded fixed MOCK page-array backend. Actual PDF inspection always refuses."""
from pathlib import Path
import base64
import json
import math
import os
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from civiclab.e01.clerk2020_contracts_v1 import canonical,digest,require,ContractRejected,_safe_public

CONFIG='configs/e01_clerk2020_m1_v1_disabled.json'
CONFIG_SHA='173cb3243d3c2075519db25f0c3ec1588e75829998c02dd4215e83d8ab933d43'
ROOT=Path(__file__).resolve().parents[3]
WORKER='civiclab.e01.clerk2020_m1_worker_v1'
MAGIC=b'CLERK_M1_AUTHORED_ONLY\n'
DOC_KEYS={'schema_version','label','backend_id','backend_version','source_id','source_role','pages'}


def strict_json(raw,limits):
    def pairs(items):
        result={}
        for k,v in items:require(k not in result);result[k]=v
        return result
    def invalid(x):raise ContractRejected()
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    remaining=[limits['json_nodes']]
    def check(x,depth):
        remaining[0]-=1;require(remaining[0]>=0 and depth<=limits['json_depth'])
        if type(x) is dict:
            require(all(type(k) is str for k in x))
            for v in x.values():check(v,depth+1)
        elif type(x) is list:
            for v in x:check(v,depth+1)
        else:require(x is None or type(x) in {str,int,bool})
    check(value,0);return value


def policy_from_bytes(raw):
    require(type(raw) is bytes and len(raw)<=65536 and digest(raw)==CONFIG_SHA)
    cfg=json.loads(raw)
    require(cfg['actual_source_enabled'] is False and cfg['actual_backend'] is None and cfg['actual_source_release'] is None and cfg['actual_parser_or_baseline'] is False)
    require(cfg['backend']['id']=='AUTHORED_UTF8_PAGE_ARRAY_V1' and cfg['backend']['version']=='1.0.0' and cfg['backend']['pdf_parser'] is False)
    return cfg


def load_policy():
    raw=(ROOT/CONFIG).read_bytes();cfg=policy_from_bytes(raw)
    for key,path in [('methods_ref','configs/e01_clerk_2020_senate_input_methods_v1.json'),('methods_audit_ref','reports/INDEPENDENT_AUDIT_E01_CLERK2020_SENATE_INPUT_METHODS_V1.json')]:
        require(cfg[key]['path']==path and digest((ROOT/path).read_bytes())==cfg[key]['sha256'])
    return raw,cfg


def project_authored(documents,cfg):
    limits=cfg['limits'];require(type(documents) is list and 1<=len(documents)<=limits['documents'])
    require(all(type(x) is bytes and 0<len(x)<=limits['input_bytes_each'] and x.startswith(MAGIC) for x in documents))
    require(sum(map(len,documents))<=limits['input_bytes_total'])
    pages=0;characters=0;ids=set();output=[]
    for raw in documents:
        doc=strict_json(raw[len(MAGIC):],limits)
        require(type(doc) is dict and set(doc)==DOC_KEYS and type(doc['schema_version']) is int and doc['schema_version']==1 and doc['label']=='MOCK')
        require(doc['backend_id']==cfg['backend']['id'] and doc['backend_version']==cfg['backend']['version'])
        require(type(doc['source_id']) is str and re.fullmatch('DEMO_[A-Z0-9_]+',doc['source_id']) is not None and doc['source_id'] not in ids)
        ids.add(doc['source_id']);require(doc['source_role'] in cfg['roles'])
        require(type(doc['pages']) is list and 1<=len(doc['pages'])<=limits['pages_each'])
        page_rows=[]
        for i,text in enumerate(doc['pages'],1):
            require(type(text) is str and len(text)<=limits['text_characters_each_page'])
            pages+=1;characters+=len(text)
            require(pages<=limits['pages_total'] and characters<=limits['text_characters_total'])
            page_rows.append({'physical_pdf_page_1_based':i,'text_characters':len(text),'text_utf8_sha256':digest(text.encode('utf8')),'layout_status':'UNKNOWN_AUTHORED_TEXT_ONLY'})
        output.append({'source_id':doc['source_id'],'source_role':doc['source_role'],'input_sha256':digest(raw),'input_bytes':len(raw),'pages':page_rows})
    projection={'schema_version':1,'label':'MOCK','backend':cfg['backend'],'documents':output,'page_count':pages,'text_characters':characters,
                'candidate_or_vote_records_parsed':0,'actual_source_access':False,'source_adoption':False,'cost_usd':0,'model_calls':0}
    require(len(canonical(projection))<=limits['output_bytes']);return projection


def _kill_reap(process,wait):
    try:
        if process.poll() is None:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            except PermissionError:process.kill()
    finally:
        # A group permission race must not skip reaping our own child. This
        # direct-child path makes no promise about hostile/spawned descendants.
        process.wait(timeout=wait)


def _sample_rss(process,limits,remaining):
    if process.poll() is not None:return None
    probe=subprocess.run(['/bin/ps','-o','rss=','-p',str(process.pid)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         timeout=min(remaining,limits['rss_probe_seconds']),env={'PATH':os.defpath,'LC_ALL':'C'})
    if process.poll() is not None:return None
    require(probe.returncode==0 and not probe.stderr and len(probe.stdout)<=128)
    value=probe.stdout.strip();require(re.fullmatch(b'[0-9]+',value) is not None)
    rss=int(value)*1024;require(0<rss<=limits['rss_peak_bytes']);return rss


def _exchange(process,packet,limits):
    last=[None]
    def clock():
        value=time.monotonic();require(type(value) in {float,int} and math.isfinite(value) and value>=0 and (last[0] is None or value>=last[0]));last[0]=value;return value
    deadline=clock()+limits['wall_seconds'];offset=0;output=bytearray();error=bytearray();samples=[]
    with selectors.DefaultSelector() as selection:
        for stream,event in [(process.stdin,selectors.EVENT_WRITE),(process.stdout,selectors.EVENT_READ),(process.stderr,selectors.EVENT_READ)]:
            os.set_blocking(stream.fileno(),False);selection.register(stream,event)
        while selection.get_map():
            remaining=deadline-clock();require(remaining>0)
            peak=_sample_rss(process,limits,remaining)
            if peak is not None:samples.append(peak)
            remaining=deadline-clock();require(remaining>0)
            for key,events in selection.select(min(remaining,limits['poll_seconds'])):
                stream=key.fileobj
                if stream is process.stdin:
                    try:n=os.write(stream.fileno(),packet[offset:offset+65536])
                    except BlockingIOError:continue
                    require(n>0);offset+=n
                    if offset==len(packet):selection.unregister(stream);stream.close()
                else:
                    try:chunk=os.read(stream.fileno(),65536)
                    except BlockingIOError:continue
                    if not chunk:selection.unregister(stream);stream.close();continue
                    destination=output if stream is process.stdout else error;destination.extend(chunk)
                    require(len(destination)<=limits['output_bytes'] if stream is process.stdout else len(destination)<=limits['stderr_bytes'])
        remaining=deadline-clock();require(remaining>0)
        process.wait(timeout=remaining)
    require(process.returncode==0 and not error and offset==len(packet))
    return bytes(output),{'rss_sample_count':len(samples),'sampled_rss_peak_bytes':max(samples) if samples else None,'semantics':'SAMPLED_THRESHOLD_NOT_HARD_MEMORY_CONTAINMENT'}


def validate_response(raw,expected,cfg):
    require(type(raw) is bytes and len(raw)<=cfg['limits']['output_bytes'])
    response=strict_json(raw,cfg['limits'])
    require(type(response) is dict and set(response)=={'projection','resources'})
    require(canonical(response['projection'])==canonical(expected))
    metrics=response['resources'];require(type(metrics) is dict and set(metrics)=={'rss_peak_bytes','cpu_limit_applied','rss_checks_applied','cpu_soft_seconds','cpu_hard_seconds','rss_semantics','rss_backend'})
    require(type(metrics['rss_peak_bytes']) is int and 0<metrics['rss_peak_bytes']<=cfg['limits']['rss_peak_bytes'])
    require(metrics['cpu_limit_applied'] is True and metrics['rss_checks_applied'] is True)
    for k in ['cpu_soft_seconds','cpu_hard_seconds']:require(type(metrics[k]) is int and metrics[k]==cfg['limits'][k])
    require(metrics['rss_semantics']=='TRUSTED_CHILD_GETRUSAGE_PEAK_NOT_CONTINUOUS_HARD_RSS')
    require(metrics['rss_backend']==cfg['rss_backend'])
    return response


@_safe_public
def inspect_authored(documents):
    # Immutable serialization before dispatch prevents caller alias drift.
    require(type(documents) is list and all(type(x) is bytes for x in documents));documents=list(documents)
    raw,cfg=load_policy();require(sys.platform in cfg['rss_probe']['platforms']);expected=project_authored(documents,cfg)
    packet=canonical({'policy_b64':base64.b64encode(raw).decode('ascii'),'documents_b64':[base64.b64encode(x).decode('ascii') for x in documents]})
    require(len(packet)<=cfg['limits']['request_bytes'])
    environment={'PATH':os.defpath,'PYTHONPATH':str(ROOT/'src'),'PYTHONNOUSERSITE':'1','PYTHONHASHSEED':'0'}
    process=None
    with tempfile.TemporaryDirectory(prefix='clerk-m1-authored-') as cwd:
        try:
            process=subprocess.Popen([sys.executable,'-m',WORKER],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                     start_new_session=True,cwd=cwd,env=environment)
            response,supervision=_exchange(process,packet,cfg['limits'])
            return {**validate_response(response,expected,cfg),'supervision':supervision}
        finally:
            if process is not None:
                try:_kill_reap(process,cfg['limits']['termination_wait_seconds'])
                finally:
                    for stream in [process.stdin,process.stdout,process.stderr]:
                        if stream is not None and not stream.closed:stream.close()


def inspect_actual(*args,**kwargs):
    # No argument/path/config/source-object inspection before unconditional refusal.
    raise ContractRejected()
