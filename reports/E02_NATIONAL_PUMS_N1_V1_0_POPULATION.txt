"""N1 authored source enrollment/streaming/union. Actual person access BLOCKED."""
from copy import deepcopy
import csv
import hashlib
import math
import multiprocessing
import os
from pathlib import Path
import stat
import subprocess
import time
import zipfile
from .national_budget import Blocked
from .pums_wy_pilot_v1 import _row,_uncertainty,CELLS
from .pums_wy_local_reuse_v1 import source_file_identity
from .population import FIPS_REGION
from ..common import canonical_hash,sha256_file,atomic_json


def fixture_gate(c):
    if c.get('authored_fixture') is not True:raise Blocked('N1 synthetic enrollment/parser only; actual source BLOCKED')


def inspect_fixture(path,c,manifest):
    fixture_gate(c);path=Path(path);limits=c['limits'];identity=source_file_identity(path)
    if manifest['period']!=c['period'] or manifest['metadata_hashes']!=c['metadata_hashes']:raise Blocked('mixed release/metadata')
    registry={s['state_fips']:s for s in c['registry']}
    state=manifest['state']
    if state not in registry or manifest['url']!=registry[state]['url']:raise Blocked('source URL/FIPS mismatch')
    known=registry[state].get('first_archive_sha256')
    if known is not None and known!=manifest['archive_sha256']:raise Blocked('known first source hash differs')
    if path.stat().st_size!=manifest['archive_bytes'] or path.stat().st_size>limits['archive_body_bytes'] or sha256_file(path)!=manifest['archive_sha256']:
        raise Blocked('source hash/size drift')
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();expected=manifest['members'];names=[x.filename for x in infos]
        if len(infos)>limits['members'] or len(set(n.casefold() for n in names))!=len(names) or set(names)!=set(expected):raise Blocked('literal member manifest mismatch')
        if sum(i.file_size for i in infos)>limits['state_uncompressed_bytes']:raise Blocked('expansion bound')
        if manifest['person_member']!='psam_p'+state+'.csv':raise Blocked('literal person name/FIPS mismatch')
        for item in infos:
            if Path(item.filename).name!=item.filename or '\\' in item.filename or stat.S_ISLNK(item.external_attr>>16) or item.flag_bits&1:raise Blocked('unsafe archive member')
            if item.file_size!=expected[item.filename]['bytes']:raise Blocked('member declared size differs')
            if item.filename!=manifest['person_member']:
                if item.file_size>limits['companion_bytes']:raise Blocked('companion bound')
                with z.open(item) as stream:
                    h=hashlib.sha256();n=0
                    while True:
                        chunk=stream.read(min(65536,limits['companion_bytes']-n+1))
                        if not chunk:break
                        n+=len(chunk);h.update(chunk)
                        if n>limits['companion_bytes']:raise Blocked('actual companion bound')
                if n!=item.file_size or h.hexdigest()!=expected[item.filename]['sha256']:raise Blocked('companion identity')
        with z.open(manifest['person_member']) as stream:header=stream.readline(limits['line_bytes']+1)
        if len(header)>limits['line_bytes'] or hashlib.sha256(header).hexdigest()!=manifest['header_sha256']:raise Blocked('source header identity')
        fields=next(csv.reader([header.decode('utf-8-sig')]))
        if len(fields)!=len(set(fields)) or not set(c['person_controls']['required_fields']).issubset(fields):raise Blocked('missing/duplicate schema')
    if source_file_identity(path)!=identity:raise Blocked('source changed during inspection')
    validation_bytes=len(header)+sum(i.file_size for i in infos if i.filename!=manifest['person_member'])
    return {'validation_expanded_bytes':validation_bytes,'processing_expanded_bytes':manifest['members'][manifest['person_member']]['bytes']+2*validation_bytes,'archive_sha256':manifest['archive_sha256'],'archive_bytes':manifest['archive_bytes'],'person_bytes':manifest['members'][manifest['person_member']]['bytes'],'identity':identity,'state':state,'manifest_sha256':canonical_hash(manifest)}


def enroll_fixture(path,c,manifest,audit,*,ledger=None):
    fixture_gate(c)
    if audit.get('auditor_role')!='independent_auditor' or audit.get('status')!='PASS_AUTHORED_SOURCE_MANIFEST' or audit.get('manifest_sha256')!=canonical_hash(manifest):
        raise Blocked('separate exact manifest review required')
    if ledger is None or ledger.c!=c:raise Blocked('metered enrollment ledger required')
    path=Path(path).resolve()
    if not path.is_relative_to(ledger.path.resolve()):
        source=next((r for r in c['registry'] if r['state_fips']==manifest['state']),{})
        if manifest['state']!='56' or source.get('first_archive_sha256')!=manifest['archive_sha256'] or source.get('exact_archive_bytes')!=manifest['archive_bytes']:raise Blocked('new source must remain in metered batch; only exact known WY cache may be external')
    key=ledger.reserve_enrollment(manifest)
    try:
        inspected,_=supervise_fixture(lambda:inspect_fixture(path,c,manifest),seconds=c['limits']['state_processing_seconds'],
            rss_bytes=c['limits']['rss_stop_bytes'],poll_seconds=c['limits']['watchdog_poll_seconds'])
        ledger.finish_enrollment(key,inspected)
        return inspected
    except BaseException:
        ledger.fail_processing(key);raise


def parse_fixture(path,c,manifest,enrolled,*,clock=time.monotonic,hook=lambda:None):
    fixture_gate(c);start=clock();path=Path(path);state=manifest['state'];limits=c['limits']
    if inspect_fixture(path,c,manifest)!=enrolled:raise Blocked('enrollment/source drift')
    cells={key:{'count':0,'weight_sum':0,'weight_squared_sum':0,'replicate_sums':[0]*80,
          'allocated_counts':{f:0 for f in c['person_controls']['allocation_flags']},
          'allocated_point_weight_sums':{f:0 for f in c['person_controls']['allocation_flags']}} for key in CELLS}
    controls=deepcopy(c['person_controls']);controls['state']=state
    exclusions={};excluded_weights={};count=0;nbytes=0;digest=hashlib.sha256()
    with zipfile.ZipFile(path) as z:
        with z.open(manifest['person_member']) as stream:
            def lines():
                nonlocal nbytes
                while True:
                    if clock()-start>limits['state_processing_seconds']:raise Blocked('processing deadline')
                    b=stream.readline(limits['line_bytes']+1)
                    if not b:break
                    nbytes+=len(b)
                    if len(b)>limits['line_bytes'] or nbytes>limits['state_uncompressed_bytes']:raise Blocked('actual CSV byte/line ceiling')
                    digest.update(b);yield b.decode('utf-8-sig' if nbytes==len(b) else 'utf-8')
            for row in csv.DictReader(lines()):
                count+=1
                if count>limits['state_rows'] or None in row or any(row.get(f) is None for f in controls['required_fields']):raise Blocked('row/schema bound')
                reason,point,reps,key,flags=_row(row,controls)
                if reason:
                    exclusions[reason]=exclusions.get(reason,0)+1;excluded_weights[reason]=excluded_weights.get(reason,0)+point;continue
                cell=cells[key];cell['count']+=1;cell['weight_sum']+=point;cell['weight_squared_sum']+=point*point
                for i,w in enumerate(reps):cell['replicate_sums'][i]+=w
                for f,value in flags.items():cell['allocated_counts'][f]+=value;cell['allocated_point_weight_sums'][f]+=point*value
    expected=next(s['published_person_rows'] for s in c['registry'] if s['state_fips']==state)
    member=manifest['members'][manifest['person_member']]
    if count!=expected or nbytes!=member['bytes'] or digest.hexdigest()!=member['sha256']:raise Blocked('exact count/member bytes/hash mismatch')
    hook()
    if inspect_fixture(path,c,manifest)!=enrolled:raise Blocked('postparse source drift')
    return {'state':state,'period':c['period'],'metadata_hashes':c['metadata_hashes'],'source':enrolled,
            'rows':count,'csv_bytes':nbytes,'expanded_bytes':nbytes+2*enrolled['validation_expanded_bytes'],'cells':cells,'exclusions':exclusions,'excluded_weights':excluded_weights,
            'kind':'MOCK_AUTHORED_PUMS_LOCAL_ONLY','actual_source_processed':False}


def summarize(cells):
    total=sum(x['weight_sum'] for x in cells.values());reps=[sum(x['replicate_sums'][i] for x in cells.values()) for i in range(80)]
    if total<=0:raise Blocked('no eligible point weight')
    result={'point':total,'replicates':reps,'count_uncertainty':_uncertainty(total,reps)}
    if any(r<=0 for r in reps):result['ratio_status']='BLOCKED_NONPOSITIVE_REPLICATE_DENOMINATOR'
    else:result['ratio_status']='MATCHED_REPLICATE_DENOMINATORS'
    return result


def union_fixture(parts,c):
    fixture_gate(c);states=[p['state'] for p in parts];wanted={s['state_fips'] for s in c['registry']}
    if len(parts)!=51 or len(set(states))!=51 or set(states)!=wanted or wanted!=set(FIPS_REGION):raise Blocked('complete51unique states required')
    if len({p['source']['archive_sha256'] for p in parts})!=51:raise Blocked('duplicate source partition')
    if any(p['period']!=c['period'] or p['metadata_hashes']!=c['metadata_hashes'] for p in parts):raise Blocked('mixed release')
    allcells={p['state']+':'+key:cell for p in sorted(parts,key=lambda x:x['state']) for key,cell in deepcopy(p['cells']).items()}
    if len(allcells)!=612 or sum(p['rows'] for p in parts)!=sum(s['published_person_rows'] for s in c['registry']):raise Blocked('full coverage/count mismatch')
    national=summarize(allcells);point=national['point'];den=national['replicates']
    for cell in allcells.values():
        cell['count_uncertainty']=_uncertainty(cell['weight_sum'],cell['replicate_sums'])
        cell['share']=cell['weight_sum']/point
        cell['share_uncertainty']=_uncertainty(cell['share'],[r/d for r,d in zip(cell['replicate_sums'],den)]) if all(d>0 for d in den) else {'status':'BLOCKED_NONPOSITIVE_REPLICATE_DENOMINATOR'}
        cell['low_support']=cell['count']<c['minimum_sharing_count']
    regions={region:summarize({key:cell for key,cell in allcells.items() if FIPS_REGION[key[:2]]==region}) for region in ('1','2','3','4')}
    return {'kind':'MOCK_AUTHORED_PUMS_UNION_NOT_ACTUAL_POPULATION','cells':allcells,'national':national,'regions':regions,
            'sharing':'LOCAL_ONLY_NOT_DISCLOSURE_APPROVED','fit':'NOT_RUN','scientific_gate':'BLOCKED'}


def covariance(a,b):
    return 4/80*sum((x-a['weight_sum'])*(y-b['weight_sum']) for x,y in zip(a['replicate_sums'],b['replicate_sums']))


def _worker(send,work):
    try:send.send(('OK',work()))
    except BaseException as error:send.send(('FAILED',type(error).__name__))
    finally:send.close()


def supervise_fixture(work,*,seconds,rss_bytes,poll_seconds=0.1,cancelled=lambda:False):
    """Parent process-group cancellation; ps RSS sampling, explicitly not hard caps."""
    context=multiprocessing.get_context('fork');receive,send=context.Pipe(False)
    def child():os.setsid();_worker(send,work)
    process=context.Process(target=child);process.start();send.close();start=time.monotonic();peak=0
    try:
        while True:
            if cancelled():raise Blocked('parent cancellation')
            if time.monotonic()-start>seconds:raise Blocked('parent processing deadline')
            if process.is_alive():
                reading=subprocess.run(['ps','-o','rss=','-p',str(process.pid)],capture_output=True,text=True,timeout=1)
                if reading.returncode==0 and reading.stdout.strip():
                    peak=max(peak,int(reading.stdout.strip())*1024)
                    if peak>rss_bytes:raise Blocked('parent sampled RSS stop threshold')
                elif process.is_alive():raise Blocked('RSS unknown; no silent continuation')
            if receive.poll(poll_seconds):
                status,value=receive.recv();process.join(timeout=1)
                if status!='OK' or process.is_alive() or process.exitcode!=0:raise Blocked('child failed or unsealed exit')
                return value,{'elapsed_seconds':time.monotonic()-start,'sampled_peak_rss_bytes':peak,'limits':'SAMPLED_NOT_ABSOLUTE_OS_CAP'}
            if not process.is_alive():raise Blocked('abrupt child exit/no result')
    finally:
        if process.is_alive():
            try:os.killpg(process.pid,15)
            except ProcessLookupError:process.terminate()
            process.join(timeout=0.5)
            if process.is_alive():
                try:os.killpg(process.pid,9)
                except ProcessLookupError:process.kill()
                process.join(timeout=1)
        receive.close()


def process_fixture(ledger,path,manifest,enrolled,*,sweep='PRIMARY',cancelled=lambda:False,work=None):
    fixture_gate(ledger.c);ledger.register_fixture_source(enrolled);key=ledger.reserve_processing(manifest['state'],sweep)
    try:
        result,resources=supervise_fixture(work or (lambda:parse_fixture(path,ledger.c,manifest,enrolled)),
            seconds=ledger.c['limits']['state_processing_seconds'],rss_bytes=ledger.c['limits']['rss_stop_bytes'],
            poll_seconds=ledger.c['limits']['watchdog_poll_seconds'],cancelled=cancelled)
        ledger.finish_processing(key,result)
        return result,resources
    except BaseException:
        ledger.fail_processing(key);raise


def finalize_fixture_union(ledger,parts,*,sweep='PRIMARY'):
    from .national_budget import storage_guard
    fixture_gate(ledger.c);key=ledger.reserve_union(parts,sweep)
    try:
        result,resources=supervise_fixture(lambda:union_fixture(parts,ledger.c),seconds=ledger.c['limits']['state_processing_seconds'],
            rss_bytes=ledger.c['limits']['rss_stop_bytes'],poll_seconds=ledger.c['limits']['watchdog_poll_seconds'])
        path=ledger.path/('MOCK-'+sweep+'-local-only.json')
        if path.exists():raise Blocked('immutable union artifact exists')
        import json
        storage_guard(ledger,len(json.dumps(result,indent=2,sort_keys=True).encode())+1)
        atomic_json(path,result);ledger.finish_union(key,path,sha256_file(path))
        return result,resources,path
    except BaseException:
        ledger.fail_processing(key);raise
