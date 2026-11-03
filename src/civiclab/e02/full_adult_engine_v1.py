"""New full-adult F authored-stream engine. No real source path is enabled."""
from copy import deepcopy
import csv
import hashlib
from pathlib import Path
import time
import zipfile
from ..common import canonical_hash,sha256_file
from .national_budget import Blocked
from .national_population import inspect_fixture,supervise_fixture
from .full_adult_control_v1 import fixture_root
from .full_adult_types_v1 import AdultMatrix,parse_person,axes,i64,FILES,FLAGS,keys,hash_value


def source_guard(path,c,manifest):
    root=fixture_root(c['fixture_root'],c)
    keys(manifest,['input_kind','state','url','period','metadata_hashes','archive_bytes','archive_sha256','person_member','header_sha256','members'])
    if type(manifest['state']) is not str or manifest['state'] not in [r['state_fips'] for r in c['registry']] or type(manifest['archive_bytes']) is not int or not 0<manifest['archive_bytes']<=c['limits']['archive_body_bytes']:raise Blocked('F source key/size')
    hash_value(manifest['archive_sha256']);hash_value(manifest['header_sha256'])
    if type(manifest['members']) is not dict:raise Blocked('F member manifest type')
    for member in manifest['members'].values():
        keys(member,['bytes','sha256'])
        if type(member['bytes']) is not int or member['bytes']<0:raise Blocked('F member byte domain')
        hash_value(member['sha256'])
    path=Path(path).resolve()
    if not path.is_relative_to(root/'sources') or manifest.get('input_kind')!='AUTHORED_F_V1' or manifest.get('url')!='fixture://F/'+manifest.get('state',''):
        raise Blocked('only authored F sources; actual/WY input refused before open')
    return path


def inspect_F(path,c,manifest):
    path=source_guard(path,c,manifest);result=inspect_fixture(path,c,manifest)
    with zipfile.ZipFile(path) as z:
        with z.open(manifest['person_member']) as stream:header=stream.readline(c['limits']['line_bytes']+1)
    if len(next(csv.reader([header.decode('utf-8-sig')])))>512:raise Blocked('F header columns')
    return result


def enroll_F(ledger,path,manifest,review):
    c=ledger.c;path=source_guard(path,c,manifest)
    if set(review)!={'kind','manifest_sha256'} or review['kind']!='AUTHORED_REVIEW_F_ONLY' or review['manifest_sha256']!=canonical_hash(manifest):raise Blocked('F authored manifest review binding')
    key=ledger.reserve_enrollment(manifest)
    try:
        source,_=supervise_fixture(lambda:inspect_F(path,c,manifest),seconds=c['limits']['state_processing_seconds'],rss_bytes=c['limits']['rss_stop_bytes'],poll_seconds=c['limits']['watchdog_poll_seconds'])
        ledger.finish_enrollment(key,source);return source
    except BaseException:
        ledger.fail_processing(key);raise


def parse_F(path,c,manifest,source,*,clock=time.monotonic):
    path=source_guard(path,c,manifest);start=clock()
    if inspect_F(path,c,manifest)!=source:raise Blocked('F preparse source drift')
    state=manifest['state'];sidx=[r['state_fips'] for r in c['registry']].index(state);matrix=AdultMatrix();n=0;nb=0;digest=hashlib.sha256()
    account={name:{'count':0,'point':0,'replicates':[0]*80} for name in ('all','adult','under18')}
    with zipfile.ZipFile(path) as z:
        with z.open(manifest['person_member']) as stream:
            def lines():
                nonlocal nb
                while True:
                    if clock()-start>c['limits']['state_processing_seconds']:raise Blocked('F parse time')
                    raw=stream.readline(c['limits']['line_bytes']+1)
                    if not raw:break
                    nb+=len(raw)
                    if len(raw)>c['limits']['line_bytes'] or nb>c['limits']['state_uncompressed_bytes']:raise Blocked('F delivered line/expansion')
                    digest.update(raw);yield raw.decode('utf-8-sig' if nb==len(raw) else 'utf-8')
            reader=csv.DictReader(lines())
            for row in reader:
                n+=1
                if n>c['limits']['state_rows']:raise Blocked('F row cap')
                local,w,reps,flags=parse_person(row,state,c['person_controls']['required_fields'])
                for which in ('all','under18' if local is None else 'adult'):
                    a=account[which];a['count']+=1;a['point']=i64(a['point']+w)
                    for r,value in enumerate(reps):a['replicates'][r]=i64(a['replicates'][r]+value)
                if local is not None:matrix.add(sidx*72+local,w,reps,flags)
    declared=manifest['members'][manifest['person_member']]
    if n!=next(s['published_person_rows'] for s in c['registry'] if s['state_fips']==state) or nb!=declared['bytes'] or digest.hexdigest()!=declared['sha256']:raise Blocked('F actual count/member hash/size')
    if inspect_F(path,c,manifest)!=source:raise Blocked('F postparse source drift')
    matrix.mark_state(sidx)
    # Return one bounded72-cell checkpoint, never a row or source identifier.
    cells={str(i):{'count':matrix.data['count.i64le'][sidx*72+i],'point':matrix.data['point.i64le'][sidx*72+i],
       'squared':matrix.data['sum_squared.i64le'][sidx*72+i],'replicates':list(matrix.data['replicates.i64le'][(sidx*72+i)*80:(sidx*72+i+1)*80]),
       'alloc_counts':list(matrix.data['allocation_counts.i64le'][(sidx*72+i)*4:(sidx*72+i+1)*4]),'alloc_weights':list(matrix.data['allocation_weights.i64le'][(sidx*72+i)*4:(sidx*72+i+1)*4])} for i in range(72)}
    result={'kind':'MOCK_F_ADULT_STATE_V1','state':state,'period':c['period'],'metadata_hashes':c['metadata_hashes'],'source':source,'rows':n,'csv_bytes':nb,'expanded_bytes':nb+2*source['validation_expanded_bytes'],'cells':cells,'accounting':account,'actual_person_rows_processed':0}
    validate_part(result,c);return result


def validate_part(part,c):
    keys(part,['kind','state','period','metadata_hashes','source','rows','csv_bytes','expanded_bytes','cells','accounting','actual_person_rows_processed'])
    if type(part['cells']) is not dict:raise Blocked('F cells vocabulary')
    if part['kind']!='MOCK_F_ADULT_STATE_V1' or part['period']!=c['period'] or part['metadata_hashes']!=c['metadata_hashes'] or set(part['cells'])!={str(i) for i in range(72)}:raise Blocked('F state checkpoint schema/release')
    if part['state'] not in [r['state_fips'] for r in c['registry']] or type(part['rows']) is not int or part['rows']!=next(r['published_person_rows'] for r in c['registry'] if r['state_fips']==part['state']) or type(part['actual_person_rows_processed']) is not int or part['actual_person_rows_processed']!=0:raise Blocked('F checkpoint source/row identity')
    for cell in part['cells'].values():
        keys(cell,['count','point','squared','replicates','alloc_counts','alloc_weights'])
        if any(type(cell[k]) is not int or cell[k]<0 for k in ('count','point','squared')) or cell['point']<cell['count'] or cell['point']>9999*cell['count'] or cell['squared']<cell['point'] or cell['squared']>9999*cell['point']:raise Blocked('F cell scalar algebra')
        if len(cell['replicates'])!=80 or len(cell['alloc_counts'])!=4 or len(cell['alloc_weights'])!=4:raise Blocked('F checkpoint shape')
        for v in cell['replicates']:i64(v)
        if any(type(v) is not int or not 0<=v<=cell['count'] for v in cell['alloc_counts']) or any(type(v) is not int or not 0<=v<=cell['point'] for v in cell['alloc_weights']):raise Blocked('F allocation domain')
        if cell['count']==0 and any([cell['point'],cell['squared'],*cell['replicates'],*cell['alloc_counts'],*cell['alloc_weights']]):raise Blocked('F source sample-zero algebra')
    a=part['accounting'];keys(a,['all','adult','under18'])
    for account in a.values():
        keys(account,['count','point','replicates'])
        if type(account['count']) is not int or account['count']<0 or type(account['point']) is not int or account['point']<0 or len(account['replicates'])!=80:raise Blocked('F accounting schema')
        for v in account['replicates']:i64(v)
    for name in ('count','point'):
        if a['all'][name]!=a['adult'][name]+a['under18'][name]:raise Blocked('F all-age selection identity')
    if a['all']['count']!=part['rows'] or a['adult']['count']!=sum(v['count'] for v in part['cells'].values()) or a['adult']['point']!=sum(v['point'] for v in part['cells'].values()):raise Blocked('F adult cell totals')
    for r in range(80):
        if a['all']['replicates'][r]!=a['adult']['replicates'][r]+a['under18']['replicates'][r] or a['adult']['replicates'][r]!=sum(v['replicates'][r] for v in part['cells'].values()):raise Blocked('F same-index accounting')


def process_F(ledger,path,manifest,source,*,sweep='PRIMARY',work=None,cancelled=lambda:False):
    source_guard(path,ledger.c,manifest);ledger.register_fixture_source(source);key=ledger.reserve_processing(manifest['state'],sweep)
    try:
        result,resources=supervise_fixture(work or (lambda:parse_F(path,ledger.c,manifest,source)),seconds=ledger.c['limits']['state_processing_seconds'],rss_bytes=ledger.c['limits']['rss_stop_bytes'],poll_seconds=ledger.c['limits']['watchdog_poll_seconds'],cancelled=cancelled)
        validate_part(result,ledger.c);ledger.finish_processing(key,result);return result,resources
    except BaseException:
        ledger.fail_processing(key);raise


def merge_F(parts,c,spec):
    states=[p['state'] for p in parts];expected=[r['state_fips'] for r in c['registry']]
    if len(states)!=51 or len(set(states))!=51 or set(states)!=set(expected) or len({p['source']['archive_sha256'] for p in parts})!=51:raise Blocked('F complete unique source partition')
    matrix=AdultMatrix()
    for p in parts:
        validate_part(p,c);s=expected.index(p['state'])
        for local,cell in p['cells'].items():
            i=s*72+int(local)
            for name,key in [('count.i64le','count'),('point.i64le','point'),('sum_squared.i64le','squared')]:matrix.data[name][i]=i64(cell[key])
            for j,v in enumerate(cell['replicates']):matrix.data['replicates.i64le'][i*80+j]=i64(v)
            for j in range(4):matrix.data['allocation_counts.i64le'][i*4+j]=i64(cell['alloc_counts'][j]);matrix.data['allocation_weights.i64le'][i*4+j]=i64(cell['alloc_weights'][j])
        matrix.mark_state(s)
    matrix.validate(spec);return matrix
