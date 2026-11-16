"""PREPARED ONLY. Requires exact separate PASS review AND explicit lead release.

There is no automatic dispatch on an auditor result or preparation completion.
One STARTED marker consumes this packet; no retry, refresh or evidence overwrite.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
RUNNER_SHA='61bdc69cdcf592af213c0e8c357a0a8976a3140bcd8a60a4731a1972f2d6a3ae'
TEST_SHA='f3ba0b75b883545194696955d067a11d44a96fe90f9736edbf5fca968d27d631'
SCOPE='ONE_HISTORICAL_312_COLLECTION_ONLY_V1_2'
LIMITS={'child_wall_seconds':120,'child_cpu_seconds':120,'source_technical_read_bytes':268435456,'owned_temp_write_bytes':33554432,'console_bytes':524288}


def require(ok,code):
    if not ok:raise RuntimeError(code)


def packed(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def new_json(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(packed(value));stream.flush();os.fsync(stream.fileno())


def verify(row):
    path=Path(row['path'])
    require(path.is_absolute(),'UNBOUND_INPUT_PATH')
    require(str(path.resolve())==row['resolved_path'],'INPUT_ALIAS_CHANGED')
    body=path.read_bytes()
    require(len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256'],'FROZEN_INPUT_CHANGED')
    return body


def code_paths():
    return sorted(str(p) for name in ('tests','scripts','src') for p in (ROOT/name).rglob('*.py') if '__pycache__' not in p.parts)


def sanitized_environment(scratch):
    return {'PATH':os.defpath,'HOME':str(scratch),'TMPDIR':str(scratch),'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC','CI':'true','PYTHONHASHSEED':'0','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','PAID_API_ENABLED':'false','MAX_SPEND_USD':'0','MPLCONFIGDIR':str(scratch/'matplotlib')}


def mentions(value,needle):
    if isinstance(value,str):return value==needle
    if isinstance(value,dict):return any(mentions(v,needle) for v in value.values())
    if isinstance(value,list):return any(mentions(v,needle) for v in value)
    return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lead-release',required=True,type=Path)
    args=parser.parse_args()
    started=False
    try:
        require(args.lead_release.absolute()==E/'LEAD_RELEASE.json','WRONG_RELEASE_LOCATION')
        require(not any((E/name).exists() for name in ('STARTED.json','PREFLIGHT_STOP.json','SUPERVISOR.json','FINAL.json','owned-temp-python312')),'SCOPE_ALREADY_STARTED_OR_STOPPED')
        release_raw=args.lead_release.read_bytes();release=json.loads(release_raw)
        require(release.get('kind')=='LEAD_HISTORICAL_COLLECTION_V1_2_RELEASE' and release.get('status')=='RELEASED_ONE_CHILD' and release.get('approved_scope')==SCOPE and release.get('maximum_children')==1,'EXPLICIT_LEAD_RELEASE_REQUIRED')
        packet_raw=(E/'PACKET.json').read_bytes();packet=json.loads(packet_raw)
        require(hashlib.sha256(packet_raw).hexdigest()==release.get('packet_sha256'),'LEAD_PACKET_HASH_BINDING')
        require(packet['scope']==SCOPE and packet['state']=='PREPARED_NOT_RELEASED' and packet['maximum_children']==1 and packet['limits']==LIMITS,'PACKET_SCOPE_OR_BOUNDS')
        review=release['component_review']
        require(review.get('runner_sha256')==RUNNER_SHA and review.get('test_sha256')==TEST_SHA,'COMPONENT_REVIEW_INPUT_BINDING')
        review_path=Path(review['report_ref']['path'])
        require(review_path.is_relative_to(ROOT/'reports') and review_path.suffix=='.json','REVIEW_REPORT_OUTSIDE_PUBLIC_TECHNICAL_SCOPE')
        reviewed=json.loads(verify(review['report_ref']))
        field=review.get('decision_field')
        require(field in {'decision','status'},'REVIEW_DECISION_FIELD')
        decision=reviewed.get(field)
        require(isinstance(decision,str) and decision.startswith('PASS') and decision==review.get('decision'),'COMPONENT_PASS_REQUIRED')
        require(mentions(reviewed,RUNNER_SHA) and mentions(reviewed,TEST_SHA),'REVIEW_DOES_NOT_BIND_CANDIDATE')
        require(code_paths()==sorted(row['path'] for row in packet['code_inputs']),'CODE_INPUT_SET_CHANGED')
        for row in packet['code_inputs']+packet['metadata_inputs']+packet['runtime_inputs']+packet['harness_sources']:
            verify(row)
        require(hashlib.sha256((ROOT/'scripts/run_offline_ci_v1.py').read_bytes()).hexdigest()==RUNNER_SHA,'CI_RUNNER_CHANGED')
        require(hashlib.sha256((ROOT/'tests/test_ci_collection_isolation_v1.py').read_bytes()).hexdigest()==TEST_SHA,'CI_TEST_CHANGED')
        scratch=E/'owned-temp-python312'
        command=[str(ROOT/'.venv/bin/python'),'-I','-B',str(E/'collection_child.py'),str(scratch)]
        require(packet['command']==command and packet['environment']==sanitized_environment(scratch),'DISPATCH_CONTEXT_CHANGED')
        new_json(E/'STARTED.json',{'kind':'HISTORICAL_COLLECTION_V1_2_STARTED','scope':SCOPE,'attempt':1,'maximum_children':1,'timestamp_utc':datetime.now(timezone.utc).isoformat(),'packet_sha256':hashlib.sha256(packet_raw).hexdigest(),'lead_release_sha256':hashlib.sha256(release_raw).hexdigest(),'component_review':review,'state':'CONSUMED_BEFORE_DISPATCH_NO_RETRY'})
        started=True
        scratch.mkdir(mode=0o700,exist_ok=False)
        path=ROOT/'scripts/run_offline_ci_v1.py';raw=path.read_bytes()
        spec=importlib.util.spec_from_file_location('reviewed_historical_collection_v1_2_supervisor',path)
        c=importlib.util.module_from_spec(spec);exec(compile(raw,str(path),'exec'),c.__dict__)
        job={'id':'historical-python312-collection-v1_2','wall_seconds':120,'output_bytes':524288}
        execution=c.supervise(command,packet['environment'],job,E)
        new_json(E/'SUPERVISOR.json',execution)
        status='CAPTURED_HISTORICAL_COLLECTION_ONLY' if execution['reason'] is None and execution['reaped'] and execution['returncode']==0 else 'CAPTURED_CHILD_STOP_OR_ERROR'
        new_json(E/'FINAL.json',{'kind':'HISTORICAL_COLLECTION_V1_2_DRIVER_FINAL','scope':SCOPE,'status':status,'actual_dispatch_attempts':1,'execution':execution,'research_or_current_ci_acceptance':False,'retry_allowed':False})
        print(json.dumps({'status':status,'actual_dispatch_attempts':1,'reaped':execution['reaped'],'returncode':execution['returncode']},sort_keys=True))
        return 0 if status=='CAPTURED_HISTORICAL_COLLECTION_ONLY' else 1
    except BaseException as error:
        record={'kind':'HISTORICAL_COLLECTION_V1_2_DRIVER_STOP','status':'STOPPED_NO_RETRY','started':started,'error_type':type(error).__name__,'scope':SCOPE,'note':'Closed error type only. Preserve all original evidence; no automatic replay.'}
        target=E/('FINAL.json' if started else 'PREFLIGHT_STOP.json')
        if not target.exists():new_json(target,record)
        print(json.dumps(record,sort_keys=True))
        return 1


if __name__=='__main__':raise SystemExit(main())
