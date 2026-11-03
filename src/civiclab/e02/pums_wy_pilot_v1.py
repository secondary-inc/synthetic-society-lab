"""Bounded public PUMS pilot controls and aggregate-only streaming arithmetic.

No person GET is enabled until a separate pinned predownload audit is supplied.
"""
from collections import Counter
import csv
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl
import hashlib
import io
from itertools import product
import json
import math
import os
from pathlib import Path
import stat
import time
from urllib.request import build_opener,HTTPRedirectHandler
import uuid
import zipfile
from ..common import canonical_hash,sha256_file,atomic_json

URL='https://www2.census.gov/programs-surveys/acs/data/pums/2024/5-Year/csv_pwy.zip'
AGES=('18-24','25-44','45-64','65+')
EDU=('HS_OR_LESS','SOME_COLLEGE','BA_PLUS')
CELLS=tuple(a+':'+e for a,e in product(AGES,EDU))


def validate_config(config):
    if config['url']!=URL or config['state']!='56' or config['limits']['automatic_retries']!=0:raise ValueError('frozen publicWYsource and zero retries required')
    for name,n in config['limits'].items():
        if name!='automatic_retries' and (not isinstance(n,int) or isinstance(n,bool) or n<=0):raise ValueError('positive finite integer resource ceilings required')
    if config['point_weight_range']!=[1,9999] or config['replicate_weight_range']!=[-9999,9999]:raise ValueError('dictionary weight domains changed')
    if config['education_recode']!={'HS_OR_LESS':[1,17],'SOME_COLLEGE':[18,20],'BA_PLUS':[21,24]}:raise ValueError('education crosswalk changed')
    if config['age_bins']!=list(AGES):raise ValueError('age bins changed')
    expected=['RT','STATE','AGEP','CIT','SCHL','RELSHIPP','PWGTP']+['PWGTP'+str(i) for i in range(1,81)]+['FAGEP','FCITP','FSCHLP','FRELSHIPP']
    if config['required_fields']!=expected:raise ValueError('required person projection changed')


def check_deadline(start,seconds,clock):
    if clock()-start>seconds:raise ValueError('resource deadline exceeded')


def integer(raw,low,high):
    if not isinstance(raw,str) or not raw.strip() or raw.strip().lstrip('-').isdigit() is False:raise ValueError('invalid required integer field')
    value=int(raw)
    if not low<=value<=high:raise ValueError('required integer field outside dictionary domain')
    return value


def _row(row,config):
    # Validate ALLrequiredrecorddomains before exclusions; same selection for all80weights.
    if row.get('RT')!='P' or row.get('STATE')!=config['state']:raise ValueError('wrong record type or state')
    point=integer(row.get('PWGTP'),1,9999)
    reps=[integer(row.get('PWGTP'+str(i)),-9999,9999) for i in range(1,81)]
    age=integer(row.get('AGEP'),0,99);cit=integer(row.get('CIT'),1,5);rel=integer(row.get('RELSHIPP'),20,38)
    raw_edu=row.get('SCHL')
    education=None if age<3 and isinstance(raw_edu,str) and not raw_edu.strip() else integer(raw_edu,1,24)
    flags={name:integer(row.get(name),0,1) for name in config['allocation_flags']}
    reason='noncitizen' if cit==5 else 'group_quarters' if rel in (37,38) else 'under18' if age<18 else None
    if reason:return reason,point,reps,None,flags
    agebin='18-24' if age<25 else '25-44' if age<45 else '45-64' if age<65 else '65+'
    edu='HS_OR_LESS' if education<=17 else 'SOME_COLLEGE' if education<=20 else 'BA_PLUS'
    return None,point,reps,agebin+':'+edu,flags


def _uncertainty(point,replicates):
    variance=sum((r-point)**2 for r in replicates)*4/80
    se=math.sqrt(variance)
    return {'variance_sdr':variance,'standard_error':se,'moe90':1.645*se,
            'status':'ZERO_ESTIMATE_OR_SE_REQUIRES_INDEPENDENT_REVIEW' if point==0 or se==0 else 'SDR_CONDITIONAL_SAMPLING_ERROR_ONLY'}


def aggregate_rows(rows,config,*,clock=time.monotonic,start=None):
    """Streaming projection: no raw values/keys/rowpositions returned or persisted."""
    validate_config(config);start=clock() if start is None else start
    data={key:{'count':0,'weight_sum':0,'weight_squared_sum':0,'replicate_sums':[0]*80,
               'allocated_counts':{f:0 for f in config['allocation_flags']},
               'allocated_point_weight_sums':{f:0 for f in config['allocation_flags']}} for key in CELLS}
    exclusions=Counter();excluded_weights=Counter();total_rows=0
    for row in rows:
        if None in row or any(row.get(f) is None for f in config['required_fields']):raise ValueError('malformed person row')
        total_rows+=1
        if total_rows>config['limits']['maximum_rows']:raise ValueError('row ceiling exceeded')
        check_deadline(start,config['limits']['processing_total_seconds'],clock)
        reason,point,reps,key,flags=_row(row,config)
        if reason:exclusions[reason]+=1;excluded_weights[reason]+=point;continue
        cell=data[key];cell['count']+=1;cell['weight_sum']+=point;cell['weight_squared_sum']+=point*point
        for i,w in enumerate(reps):cell['replicate_sums'][i]+=w
        for f,n in flags.items():
            cell['allocated_counts'][f]+=n;cell['allocated_point_weight_sums'][f]+=point*n
    if not total_rows:raise ValueError('empty person file')
    total=sum(c['weight_sum'] for c in data.values())
    if total<=0:raise ValueError('no retained citizen18+household person weight')
    denominators=[sum(c['replicate_sums'][i] for c in data.values()) for i in range(80)]
    for key,c in data.items():
        c['point_share']=c['weight_sum']/total;c['count_uncertainty']=_uncertainty(c['weight_sum'],c['replicate_sums'])
        c['low_support']=c['count']<config['disclosure']['minimum_unweighted_cell_count_for_sharing']
        if any(n<=0 for n in denominators):
            c['share_uncertainty']={'status':'BLOCKED_NONPOSITIVE_REPLICATE_DENOMINATOR','invalid_replicates':sum(n<=0 for n in denominators)}
        else:c['share_uncertainty']=_uncertainty(c['point_share'],[n/d for n,d in zip(c['replicate_sums'],denominators)])
    covariance={a:{b:4/80*sum((x-data[a]['weight_sum'])*(y-data[b]['weight_sum']) for x,y in zip(data[a]['replicate_sums'],data[b]['replicate_sums'])) for b in CELLS} for a in CELLS}
    return {'kind':'LOCAL_ONLY_PUMS_WY_AGGREGATE_NOT_NATIONAL_OR_FIT','state':'56','period':'2020-2024five-year',
            'total_person_rows':total_rows,'retained_unweighted_count':sum(c['count'] for c in data.values()),
            'point_person_weight_sum':total,'replicate_person_weight_sums':denominators,'cells':data,
            'count_covariance_sdr':covariance,'exclusion_counts':dict(exclusions),'excluded_point_weight_sums':dict(excluded_weights),
            'sharing':'LOCAL_ONLY_PENDING_INDEPENDENT_DISCLOSURE_REVIEW','uncertainty':'SDRsamplingapproximationonly;nozeroSEcertainty,fullerror,ANEStransportorhumanvalidityclaim',
            'person_weight_rescaled':False,'population_fit':'NOT_RUN','paid_calls':0,'api_spend_usd':0}


def aggregate_archive(path,config,*,clock=time.monotonic):
    validate_config(config);start=clock();limits=config['limits'];path=Path(path)
    if path.stat().st_size>limits['compressed_bytes']:raise ValueError('compressed byte ceiling exceeded')
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        if len(infos)>limits['maximum_members'] or len(set(n.lower() for n in names))!=len(names):raise ValueError('duplicate or excessive archive members')
        if sum(x.file_size for x in infos)>limits['uncompressed_bytes']:raise ValueError('uncompressed byte ceiling exceeded')
        chosen=[]
        for info in infos:
            if Path(info.filename).name!=info.filename or '\\' in info.filename or stat.S_ISLNK(info.external_attr>>16) or info.flag_bits&1:raise ValueError('unsafe archive path/type/encryption')
            if info.filename.lower()==config['person_member_casefold']:chosen.append(info)
            elif info.filename.lower() not in config['optional_members_casefold'] or info.file_size>config['optional_member_bytes']:raise ValueError('unapproved archive member')
        if len(chosen)!=1:raise ValueError('exactlyoneWYperson member required')
        digest=hashlib.sha256();bytes_read=0
        with z.open(chosen[0]) as stream:
            def lines():
                nonlocal bytes_read
                while True:
                    check_deadline(start,limits['processing_total_seconds'],clock)
                    raw=stream.readline(limits['csv_line_bytes']+1)
                    if not raw:break
                    if len(raw)>limits['csv_line_bytes']:raise ValueError('CSVline byte ceiling exceeded')
                    bytes_read+=len(raw)
                    if bytes_read>limits['uncompressed_bytes']:raise ValueError('actual uncompressed byte ceiling exceeded')
                    digest.update(raw)
                    yield raw.decode('utf-8-sig' if bytes_read==len(raw) else 'utf-8')
            reader=csv.DictReader(lines())
            if reader.fieldnames is None or len(reader.fieldnames)!=len(set(reader.fieldnames)) or not set(config['required_fields']).issubset(reader.fieldnames):raise ValueError('required person header missing/duplicate')
            result=aggregate_rows(reader,config,clock=clock,start=start)
        if result['total_person_rows']!=limits['expected_person_rows']:raise ValueError('published unfiltered record count mismatch')
    result['source']={'archive_sha256':sha256_file(path),'member_name':chosen[0].filename,'member_sha256':digest.hexdigest(),'actual_uncompressed_bytes':bytes_read,
                      'unused_columns_discarded':True,'required_projection':config['required_fields']}
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('public source redirect refused')


def require_predownload_approval(root,config):
    validate_config(config);root=Path(root).resolve()
    for name,expected in config['required_files'].items():
        p=(root/name).resolve()
        if not p.is_relative_to(root) or sha256_file(p)!=expected:raise ValueError('pinned pilot source/code changed')
    approval=config.get('predownload_approval')
    if not isinstance(approval,dict) or not approval.get('path') or not approval.get('sha256'):raise ValueError('personGET BLOCKED: separate predownload controls/code/fixture audit required')
    p=(root/approval['path']).resolve()
    if not p.is_relative_to(root) or sha256_file(p)!=approval['sha256']:raise ValueError('predownload audit bytes changed')
    audit=json.loads(p.read_text());design={k:v for k,v in config.items() if k!='predownload_approval'}
    if audit.get('auditor_role')!='independent_auditor' or audit.get('status')!='PASS_WYOMING_PREDOWNLOAD_CONTROLS_AND_FIXTURES' or audit.get('reviewed_design_sha256')!=canonical_hash(design):raise ValueError('predownload audit scope/design mismatch')


def stream_download(response,destination,limits,*,clock=time.monotonic):
    start=clock();size=0;digest=hashlib.sha256()
    header=response.headers.get('Content-Length')
    if header is not None and (not header.isdigit() or int(header)>limits['compressed_bytes']):raise ValueError('sourceContentLength outside compressed ceiling')
    with Path(destination).open('xb') as out:
        while True:
            check_deadline(start,limits['network_total_seconds'],clock)
            chunk=response.read(min(65536,limits['compressed_bytes']-size+1))
            if not chunk:break
            size+=len(chunk)
            if size>limits['compressed_bytes']:raise ValueError('actual download byte ceiling exceeded')
            out.write(chunk);digest.update(chunk)
    check_deadline(start,limits['network_total_seconds'],clock)
    if size==0 or header is not None and size!=int(header):raise ValueError('empty or truncated download')
    return {'bytes':size,'sha256':digest.hexdigest()}


@contextmanager
def _pilot_lock(path):
    with path.with_suffix('.lock').open('a') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('pilot alreadyowned; no concurrent duplicate request') from None
        try:yield
        finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def acquire_pilot(root,config,*,clock=time.monotonic,opener=None):
    """No invocation on actual person data during preparation. No retries/fallbacks."""
    root=Path(root).resolve();require_predownload_approval(root,config)
    start=clock();path=(root/config['local_archive']).resolve()
    if not path.is_relative_to(root/'data/raw/e02_pums_wy'):raise ValueError('pilot archive outside ignoredsource directory')
    path.parent.mkdir(parents=True,exist_ok=True)
    with _pilot_lock(path):return _recorded_acquisition_attempt(root,config,path,start,clock,opener)


def _recorded_acquisition_attempt(root,config,path,start,clock,opener):
    """Durable bounded metadata before network; never persist rows/error bodies."""
    attempt_id='wy-'+uuid.uuid4().hex
    directory=path.parent/'attempts'/attempt_id;directory.mkdir(parents=True,exist_ok=False)
    manifest={'schema_version':1,'attempt_id':attempt_id,'status':'STARTED',
              'source_url':URL,'state':'56','period':config['period'],
              'started_at_utc':datetime.now(timezone.utc).isoformat(),
              'config_sha256':canonical_hash(config),'code_sha256':sha256_file(Path(__file__)),
              'limits':config['limits'],'predownload_approval':config['predownload_approval'],
              'privacy':'Attemptmetadataonly;noIDs,rawrows,exceptiontext,responsebodies',
              'deadline_semantics':'Cooperative elapsed checks plus per-operation socket timeout; not an absolute OS wall-clock termination guarantee'}
    atomic_json(directory/'attempt.json',manifest)
    atomic_json(directory/'control-config.json',config)
    sequence=0;stage='attempt_created';quarantined=[];http_status=None;validation=None
    def observe(event,**fields):
        nonlocal sequence,stage,http_status,validation
        sequence+=1;stage=event
        if event=='network_response_received':http_status=fields['http_status']
        if event=='quarantined':
            source=Path(fields.pop('path')).resolve()
            if not source.is_relative_to(path.parent):raise ValueError('quarantine path outside pilot directory')
            size=source.stat().st_size
            record={'path':str(source.relative_to(root)),'bytes':size,
                    'sha256':sha256_file(source) if size<=config['limits']['compressed_bytes'] else None}
            if record['sha256'] is None:record['hash_status']='NOT_HASHED_EXCEEDS_DECLARED_COMPRESSED_CEILING'
            quarantined.append(record);fields.update(record)
        if event=='validation_completed':validation=fields.copy()
        entry={'sequence':sequence,'at_utc':datetime.now(timezone.utc).isoformat(),'event':event,**fields}
        with (directory/'events.jsonl').open('a') as out:
            out.write(json.dumps(entry,sort_keys=True)+'\n');out.flush();os.fsync(out.fileno())
    observe('attempt_created')
    try:
        result=_acquire_after_guard(root,config,path,start,clock,opener,observe)
        summary={'status':'COMPLETED','attempt_id':attempt_id,'terminal_stage':'completed',
                 'completed_at_utc':datetime.now(timezone.utc).isoformat(),'source_url':URL,
                 'archive_path':str(result.relative_to(root)),'archive_sha256':sha256_file(result),
                 'archive_bytes':result.stat().st_size,'http_status':http_status,
                 'cache_hit':http_status is None,'validation':validation,
                 'paid_calls':0,'api_spend_usd':0}
        observe('attempt_completed');atomic_json(directory/'summary.json',summary)
        return result
    except BaseException as error:
        code=getattr(error,'code',None)
        if isinstance(code,int) and 100<=code<=599:http_status=code
        summary={'status':'FAILED','attempt_id':attempt_id,'last_stage':stage,
                 'failed_at_utc':datetime.now(timezone.utc).isoformat(),'error_type':type(error).__name__,
                 'http_status':http_status,'cancelled':isinstance(error,(KeyboardInterrupt,SystemExit)),
                 'quarantined_artifacts':quarantined,'paid_calls':0,'api_spend_usd':0}
        # Intentional type/status-only record; no exception str, repr or HTTP body.
        atomic_json(directory/'failure.json',summary)
        observe('attempt_failed',error_type=summary['error_type'],http_status=http_status)
        atomic_json(directory/'summary.json',summary)
        raise


def _acquire_after_guard(root,config,path,start,clock,opener,observe):
    receipt_path=path.with_suffix('.receipt.json')
    if path.exists():
        observe('cache_check_started')
        if not receipt_path.exists():raise ValueError('existingarchive lacksimmutable receipt')
        receipt=json.loads(receipt_path.read_text())
        if sha256_file(path)!=receipt['sha256']:
            quarantine=path.with_name('QUARANTINED-CACHE-'+uuid.uuid4().hex+'.zip')
            path.rename(quarantine);observe('quarantined',path=quarantine)
            raise ValueError('cachedarchive changed;quarantinedforreview')
        if receipt.get('url')!=URL or receipt.get('state')!='56' or receipt.get('period')!=config['period']:raise ValueError('cachedreceipt product mismatch')
        if config.get('archive_sha256') is not None and receipt['sha256']!=config['archive_sha256']:raise ValueError('cachedhash differsfrompinnedsource')
        observe('cache_verified')
        return path
    if receipt_path.exists():raise ValueError('receiptwithoutarchive requires explicit reconciliation before newrequest')
    temporary=path.with_name('.download-'+uuid.uuid4().hex)
    opener=opener or build_opener(NoRedirect())
    try:
        observe('network_request_started',source_url=URL)
        with opener.open(config['url'],timeout=config['limits']['network_timeout_seconds']) as response:
            observe('network_response_received',http_status=response.status)
            if response.geturl()!=URL or response.status!=200:raise ValueError('wrongsource URL/status')
            receipt=stream_download(response,temporary,config['limits'],clock=clock)
            receipt['http_last_modified']=response.headers.get('Last-Modified')
            receipt['retrieved_at_utc']=datetime.now(timezone.utc).isoformat()
            observe('download_completed',bytes=receipt['bytes'],sha256=receipt['sha256'])
        check_deadline(start,config['limits']['overall_seconds'],clock)
        # Validate actual product/member/rowcount and limits BEFORE promoting bytes.
        observe('validation_started')
        aggregate=aggregate_archive(temporary,config,clock=clock)
        observe('validation_completed',total_person_rows=aggregate['total_person_rows'],
                retained_unweighted_count=aggregate['retained_unweighted_count'],aggregate_sha256=canonical_hash(aggregate))
        check_deadline(start,config['limits']['overall_seconds'],clock)
        expected=config.get('archive_sha256')
        if expected is not None and receipt['sha256']!=expected:raise ValueError('pinnedsource bytes drifted')
        if path.exists() or receipt_path.exists():raise ValueError('concurrent/existingpilot artifact mustnotoverwrite')
        os.link(temporary,path)  # Atomic create; cannot overwrite an existing archive.
        temporary.unlink()
        receipt.update(url=URL,state='56',period=config['period'],config_sha256=canonical_hash(config))
        with receipt_path.open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True)
        observe('archive_promoted',bytes=receipt['bytes'],sha256=receipt['sha256'])
        return path
    except BaseException:
        if temporary.exists():
            quarantine=path.with_name('QUARANTINED-'+uuid.uuid4().hex+'.zip')
            temporary.rename(quarantine);observe('quarantined',path=quarantine)
        raise
