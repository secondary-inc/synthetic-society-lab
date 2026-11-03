"""Two fixed official PDFs; reviewed external plan required; no retries/parser.

Application-body/cooperative limits are not absolute TLS/wire or OS guarantees.
No environment credentials, proxies, cookies, redirects or alternate sources.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import signal
import time
from urllib.parse import urlsplit

SCOPE = 'data/raw/e01_clerk_documents_capture_v1'
SOURCES = [
    {'id':'clerk2020_statistics','url':'https://clerk.house.gov/member_info/electionInfo/2020/statistics2020.pdf',
     'role':'HISTORICAL_2020_OFFICIAL_COUNTS_NOT_2026_OUTCOMES'},
    {'id':'clerk2026_nominees','url':'https://clerk.house.gov/member_info/electionInfo/2026/120-nominations.pdf',
     'role':'DATED_2026_OFFICIAL_NOMINEE_COMPILATION_NOT_FINAL_BALLOT_OR_LATEST_CERTIFICATE'}]
LIMITS = {'requests':2,'body_bytes_each':8388608,'body_bytes_total':16777216,
          'request_seconds':45,'socket_seconds':15,'unit_seconds':120,
          'metadata_bytes':1048576,'retained_bytes':17825792,'minimum_free_bytes':67108864}

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def digest(raw):return hashlib.sha256(raw).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def code_sha():return digest(Path(__file__).read_bytes())

def strict_json(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('duplicate JSON key')
            value[key]=item
        return value
    def constant(_):raise ValueError('nonfinite JSON')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)

def metadata_bytes(path,limit):
    def identity(st):
        return (st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('metadata alias')
    before=path.stat()
    if not path.is_file() or before.st_size>limit:raise ValueError('metadata bound')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        opened=os.fstat(f.fileno())
        if identity(opened)!=identity(before):
            raise ValueError('metadata identity changed')
        raw=f.read(limit)
        after=os.fstat(f.fileno())
    if (len(raw)!=before.st_size or identity(after)!=identity(opened) or identity(path.stat())!=identity(before)):
        raise ValueError('metadata changed during read')
    return raw

def load_plan(root,name):
    rel=Path(name)
    if rel.is_absolute() or '..' in rel.parts or rel.parts[:3]!=('data','processed','e01_clerk_capture_plans') or rel.suffix!='.json':
        raise ValueError('plan must be in dedicated metadata area')
    return strict_json(metadata_bytes(Path(root)/rel,65536))

def write_once(path,value):
    raw=canonical(value)
    if len(raw)>65536:raise ValueError('metadata record bound')
    with path.open('xb') as f:
        os.fchmod(f.fileno(),0o600)
        f.write(raw);f.flush()
        os.fsync(f.fileno())

@contextmanager
def deadline(seconds):
    if seconds<=0:raise TimeoutError('unit deadline')
    def expired(*_):raise TimeoutError('cooperative request deadline')
    old=signal.signal(signal.SIGALRM,expired)
    prior,interval=signal.getitimer(signal.ITIMER_REAL)
    began=time.monotonic()
    signal.setitimer(signal.ITIMER_REAL,min(seconds,prior) if prior>0 else seconds)
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old)
        if prior>0:
            signal.setitimer(signal.ITIMER_REAL,max(0.000001,prior-(time.monotonic()-began)),interval)

def validate(root,plan,expected):
    root=Path(root).absolute()
    if '..' in root.parts or any(p.is_symlink() for p in (root,*root.parents)):
        raise ValueError('lexical root refused')
    required={'schema_version','kind','root_sha256','code_sha256','sources','limits','code_review'}
    if (type(plan) is not dict or set(plan)!=required or type(plan['schema_version']) is not int
        or plan['schema_version']!=1 or plan['kind']!='CLERK_DOCUMENT_CAPTURE_RELEASE_V1'
        or digest(canonical(plan))!=expected or plan['root_sha256']!=digest(str(root).encode())
        or plan['code_sha256']!=code_sha() or canonical(plan['sources'])!=canonical(SOURCES)
        or canonical(plan['limits'])!=canonical(LIMITS)):
        raise ValueError('exact reviewed external plan required')
    ref=plan['code_review']
    if type(ref) is not dict or set(ref)!={'path','sha256'}:raise ValueError('code review reference')
    rel=Path(ref['path'])
    if rel.is_absolute() or '..' in rel.parts or rel.parts[:1]!=('reports',) or rel.suffix!='.json':
        raise ValueError('code review path')
    p=root/rel
    raw=metadata_bytes(p,131072)
    if digest(raw)!=ref['sha256']:raise ValueError('code review changed')
    review=strict_json(raw)
    if (review.get('status')!='PASS_BOUNDED_CLERK_DOCUMENT_CAPTURE_V1_CODE'
        or review.get('auditor_role')!='independent_auditor'
        or review.get('code_sha256')!=code_sha()
        or review.get('source_policy_sha256')!=digest(canonical({'sources':SOURCES,'limits':LIMITS}))):
        raise ValueError('code/source-policy review mismatch')
    return root

def _capture(root,plan,expected):
    root=validate(root,plan,expected)
    scope=root/SCOPE
    for p in (scope,*scope.parents):
        if p.is_symlink():raise ValueError('scope alias refused')
    if scope.exists():raise FileExistsError('prior scope retained; no retry/reset')
    if shutil.disk_usage(root).free<LIMITS['minimum_free_bytes']:raise ValueError('free disk bound')
    scope.mkdir(parents=True,mode=0o700,exist_ok=False)
    started=time.monotonic();total=0;rows=[]
    write_once(scope/'STARTED.local.json',{'plan_sha256':expected,'started_utc':now(),
        'limits':LIMITS,'no_resume':True,'reserved_body_bytes':LIMITS['body_bytes_total']})
    for source in SOURCES:
        prefix=scope/source['id'];part=prefix.with_suffix('.part');final=prefix.with_suffix('.pdf')
        record={'source_id':source['id'],'url':source['url'],'role':source['role'],
            'started_utc':now(),'status':None,'body_bytes':0,'body_sha256':None,
            'body_complete':False,'pdf_admitted':False,'headers':{},'error_type':None,'automatic_retry':False}
        write_once(prefix.with_suffix('.intent.local.json'),{'source':source,'at_utc':now(),
            'reserved_body_bytes':LIMITS['body_bytes_each'],'reserved_seconds':LIMITS['request_seconds']})
        response=None;connection=None;body_hash=hashlib.sha256();error=None
        try:
            remaining=LIMITS['unit_seconds']-(time.monotonic()-started)
            with deadline(min(LIMITS['request_seconds'],remaining)):
                url=urlsplit(source['url'])
                connection=http.client.HTTPSConnection(url.hostname,timeout=LIMITS['socket_seconds'])
                connection.request('GET',url.path,headers={'Accept':'application/pdf','Accept-Encoding':'identity',
                    'User-Agent':'SyntheticSocietyLab-source-research/1.0'})
                response=connection.getresponse();record['status']=response.status
                for key in ('Content-Type','Content-Length','Content-Encoding','Last-Modified','Date'):
                    value=response.getheader(key)
                    if value is not None:
                        if type(value) is not str or len(value)>4096:raise ValueError('header bound')
                        record['headers'][key]=value
                length=record['headers'].get('Content-Length')
                if length is not None and (not length.isascii() or not length.isdigit() or len(length)>12):
                    raise ValueError('length format')
                length=int(length) if length is not None else None
                if length is not None and length>LIMITS['body_bytes_each']:raise ValueError('length cap')
                if record['headers'].get('Content-Encoding','identity').lower()!='identity':raise ValueError('encoded body')
                prefix_bytes=b'';eof=False
                with part.open('xb') as f:
                    os.fchmod(f.fileno(),0o600)
                    while record['body_bytes']<LIMITS['body_bytes_each']:
                        if length is not None and record['body_bytes']==length:break
                        amount=min(65536,LIMITS['body_bytes_each']-record['body_bytes'])
                        if length is not None:amount=min(amount,length-record['body_bytes'])
                        chunk=response.read(amount)
                        if not chunk:eof=True;break
                        if len(chunk)>amount:raise ValueError('response read exceeded requested bound')
                        f.write(chunk);body_hash.update(chunk);prefix_bytes=(prefix_bytes+chunk)[:5]
                        record['body_bytes']+=len(chunk);total+=len(chunk)
                        if total>LIMITS['body_bytes_total']:raise ValueError('cumulative body cap')
                    f.flush()
                    os.fsync(f.fileno())
                complete=(record['body_bytes']==length if length is not None else eof)
                if not complete:raise ValueError('incomplete or cap without verified EOF')
                record['body_complete']=True
                if response.status!=200:raise ValueError('HTTP status refused; no redirect or retry')
                if record['headers'].get('Content-Type','').split(';')[0].lower()!='application/pdf' or prefix_bytes!=b'%PDF-':
                    raise ValueError('not declared PDF bytes')
                response.close();response=None;connection.close();connection=None
                if final.exists() or final.is_symlink():raise FileExistsError('output already exists')
                part.rename(final);record['pdf_admitted']=True
                record['body_path']=str(final.relative_to(root))
        except BaseException as exc:
            error=exc;record['error_type']=type(exc).__name__
        finally:
            for resource in (response,connection):
                if resource is not None:
                    try:resource.close()
                    except BaseException as exc:
                        error=error or exc;record['error_type']=record['error_type'] or type(exc).__name__
            record['body_sha256']=body_hash.hexdigest();record['finished_utc']=now()
            record['elapsed_unit_seconds']=time.monotonic()-started
            write_once(prefix.with_suffix('.receipt.local.json'),record);rows.append(record)
        if error is not None:
            write_once(scope/'STOP.local.json',{'source_id':source['id'],'error_type':type(error).__name__,
                'attempted_sources':len(rows),'body_bytes_observed':total,'reserved_body_bytes':LIMITS['body_bytes_total'],
                'no_retry_or_remaining_source_fallback':True})
            return {'status':'STOPPED_NO_RETRY','records':rows,'model_calls':0}
    retained=sum(p.stat().st_size for p in scope.iterdir() if p.is_file())
    if retained>LIMITS['retained_bytes']:raise ValueError('retained scope cap')
    write_once(scope/'COMPLETED.local.json',{'status':'CAPTURED_PDF_BYTES_ONLY_NOT_PARSED_OR_ADOPTED',
        'sources':len(rows),'body_bytes':total,'reserved_body_bytes':LIMITS['body_bytes_total'],
        'model_calls':0,'publication_or_roster_adoption':False})
    return {'status':'CAPTURED_PDF_BYTES_ONLY_NOT_PARSED_OR_ADOPTED','records':rows,'model_calls':0}

def capture(root,plan,expected):
    # The outer timer remains active across closing resources and receipts.
    with deadline(LIMITS['unit_seconds']):
        return _capture(root,plan,expected)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True);parser.add_argument('--expected-plan-canonical-sha256',required=True)
    args=parser.parse_args()
    try:
        plan=load_plan(Path.cwd(),args.plan)
        result=capture(Path.cwd(),plan,args.expected_plan_canonical_sha256)
        print(json.dumps(result,sort_keys=True))
        if result['status']=='STOPPED_NO_RETRY':raise SystemExit(2)
    except KeyboardInterrupt:
        print(json.dumps({'status':'INTERRUPTED_PRESERVE_SCOPE_NO_RETRY','error_type':'KeyboardInterrupt'}))
        raise SystemExit(130) from None
    except Exception as error:
        print(json.dumps({'status':'REFUSED_OR_INCOMPLETE_PRESERVE_SCOPE_NO_RETRY','error_type':type(error).__name__}))
        raise SystemExit(2) from None
