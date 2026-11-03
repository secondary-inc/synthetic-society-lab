"""Fixture-only implementation of the reviewed retrospective selection proposal.

No Cook ingestion or real frame selection is enabled. Integer MILP objectives
are optimized and locked sequentially; rank ties use exact 10-bit chunks.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time

from civiclab.common import canonical_hash

ALGORITHM = 'E01_2026_SELECTION_PROPOSAL_v1'
SEED = 20261103
CUTOFF = '2026-11-03T04:59:59Z'
BANDS = ('TOSS_UP', 'LEAN', 'LIKELY', 'SOLID')
PARTIES = ('D', 'R', 'OTHER')
REGIONS = {
    **dict.fromkeys('CT ME MA NH RI VT NJ NY PA'.split(), 'NORTHEAST'),
    **dict.fromkeys('IN IL MI OH WI IA KS MN MO NE ND SD'.split(), 'MIDWEST'),
    **dict.fromkeys('DE FL GA MD NC SC VA DC WV AL KY MS TN AR LA OK TX'.split(), 'SOUTH'),
    **dict.fromkeys('AZ CO ID MT NV NM UT WY AK CA HI OR WA'.split(), 'WEST'),
}
ROW_FIELDS = {'race_id', 'office', 'state', 'district', 'seat_class', 'band',
              'sampling_party', 'eligibility', 'exclusion_reason', 'evidence_refs'}
SOURCE_FIELDS = {'source_id', 'source_type', 'url', 'sha256', 'published_at_utc',
                 'first_observed_at_utc', 'retrieved_at_utc', 'revision',
                 'reuse_status', 'asof_status', 'amendment_status'}
FRAME_FIELDS = {'schema_version', 'dataset_kind', 'algorithm', 'seed', 'cutoff',
                'expected_race_ids', 'coverage_status', 'sources', 'rows'}


class SelectionBlocked(ValueError):
    """No accepted result may be emitted for a failed selection gate."""


def rank_key(row):
    value=f'{ALGORITHM}|{SEED}|{row["office"]}|{row["race_id"]}'
    return hashlib.sha256(value.encode('utf-8')).hexdigest(), row['race_id']


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value)!=fields:
        raise SelectionBlocked(label+' fields differ from strict schema')


def validate_fixture(frame):
    """No truthy permission flag, even in a perfect-looking REAL frame, enables it."""
    if not isinstance(frame, dict) or frame.get('dataset_kind')!='DEMO_SELECTION_FIXTURE':
        raise SelectionBlocked('REAL selection remains blocked: fixture implementation only; source acceptance not authorized')
    _exact(frame,FRAME_FIELDS,'frame')
    if (type(frame['schema_version']) is not int or frame['schema_version']!=1 or
        frame['algorithm']!=ALGORITHM or type(frame['seed']) is not int or frame['seed']!=SEED or frame['cutoff']!=CUTOFF):
        raise SelectionBlocked('unreviewed version, seed or cutoff')
    if frame['coverage_status']!='COMPLETE_FIXTURE':
        raise SelectionBlocked('incomplete or pending frame coverage')
    ids=frame['expected_race_ids']
    if not isinstance(ids,list) or any(not isinstance(x,str) for x in ids) or len(ids)!=len(set(ids)):
        raise SelectionBlocked('invalid expected universe')
    sources=frame['sources']
    if not isinstance(sources,list) or not sources:
        raise SelectionBlocked('missing source receipts')
    by_source={}
    from datetime import datetime, timezone
    cutoff=datetime.fromisoformat(CUTOFF.replace('Z','+00:00'))
    for source in sources:
        _exact(source,SOURCE_FIELDS,'source')
        if any(not isinstance(v,str) or not v for v in source.values()):
            raise SelectionBlocked('source fields must be nonempty text')
        if source['source_id'] in by_source or source['source_type'] not in {'RATINGS','BALLOT','SEAT_PARTY'}:
            raise SelectionBlocked('duplicate or unknown source type')
        if not source['url'].startswith('fixture://DEMO/') or source['reuse_status']!='FIXTURE_AUTHORED':
            raise SelectionBlocked('external source or unverified reuse cannot enter fixture path')
        if source['asof_status']!='VERIFIED_FIXTURE' or source['amendment_status']!='RESOLVED_FIXTURE':
            raise SelectionBlocked('pending source as-of or amendment review')
        if len(source['sha256'])!=64 or any(c not in '0123456789abcdef' for c in source['sha256']):
            raise SelectionBlocked('invalid source hash')
        dates=[]
        for field in ('published_at_utc','first_observed_at_utc','retrieved_at_utc'):
            try:
                d=datetime.fromisoformat(source[field].replace('Z','+00:00'))
            except ValueError:
                raise SelectionBlocked('invalid source timestamp') from None
            if d.tzinfo is None or d.utcoffset()!=timezone.utc.utcoffset(d):
                raise SelectionBlocked('source timestamp must be explicit UTC')
            dates.append(d)
        if dates[0]>cutoff or dates[1]>cutoff or not dates[0]<=dates[1]<=dates[2]:
            raise SelectionBlocked('post-cutoff publication/observation or inverted source dates')
        by_source[source['source_id']]=source
    rows=frame['rows']
    if not isinstance(rows,list):raise SelectionBlocked('rows must be list')
    seen=set()
    for row in rows:
        _exact(row,ROW_FIELDS,'row')
        if any(not isinstance(row[k],str) for k in ('race_id','office','state','district','band','sampling_party','eligibility')):
            raise SelectionBlocked('row identity and labels must be text')
        if row['exclusion_reason'] is not None and not isinstance(row['exclusion_reason'],str):
            raise SelectionBlocked('exclusion reason must be text or null')
        if not isinstance(row['race_id'],str) or row['race_id'] in seen:
            raise SelectionBlocked('duplicate or invalid race ID')
        seen.add(row['race_id'])
        if row['office'] not in {'HOUSE','SENATE'} or row['state'] not in REGIONS or row['state']=='DC':
            raise SelectionBlocked('unknown office or voting state')
        if row['office']=='HOUSE':
            if not isinstance(row['district'],str) or len(row['district'])!=2 or not row['district'].isdigit() or row['seat_class'] is not None:
                raise SelectionBlocked('invalid House identity')
            identity=f'DEMO-2026-{row["state"]}-HOUSE-{row["district"]}'
        else:
            if row['district']!='STATEWIDE' or type(row['seat_class']) is not int or row['seat_class'] not in {1,2,3}:
                raise SelectionBlocked('invalid Senate identity')
            identity=f'DEMO-2026-{row["state"]}-SENATE-C{row["seat_class"]}'
        if row['race_id']!=identity or row['band'] not in BANDS or row['sampling_party'] not in PARTIES:
            raise SelectionBlocked('unresolved race identity/rating/party label')
        if row['eligibility'] not in {'ELIGIBLE','EXCLUDED_STRUCTURAL'}:
            raise SelectionBlocked('pending eligibility is not an exclusion')
        if ((row['eligibility']=='ELIGIBLE' and row['exclusion_reason'] is not None) or
            (row['eligibility']=='EXCLUDED_STRUCTURAL' and row['exclusion_reason'] not in
             {'NONVOTING','SPECIAL','RUNOFF','NO_DEMOCRAT','NO_REPUBLICAN','MULTIPLE_MAJOR_CANDIDATES','UNCONTESTED'})):
            raise SelectionBlocked('invalid structural exclusion; input unavailability cannot select sample')
        refs=row['evidence_refs']
        if not isinstance(refs,list) or any(not isinstance(x,str) for x in refs) or len(refs)!=len(set(refs)) or any(x not in by_source for x in refs):
            raise SelectionBlocked('missing or duplicated source reference')
        if not {'RATINGS','BALLOT'} <= {by_source[x]['source_type'] for x in refs}:
            raise SelectionBlocked('ratings and ballot evidence both required')
        if row['band']=='TOSS_UP' and not any(by_source[x]['source_type']=='SEAT_PARTY' for x in refs):
            raise SelectionBlocked('toss-up requires seat-party source')
    if seen!=set(ids):raise SelectionBlocked('missing or additional contest in complete frame')
    return sorted(rows,key=lambda r:(r['office'],rank_key(r)))


class _MILP:
    def __init__(self, rows, n, deadline, stage_callback=None):
        try:
            import numpy as np
            import scipy
            from scipy.optimize import milp
        except ImportError:
            raise SelectionBlocked('optional selection extra scipy==1.16.3 required') from None
        if scipy.__version__!='1.16.3':raise SelectionBlocked('unverified SciPy version; expected 1.16.3')
        self.np=np;self.milp=milp;self.rows=rows;self.n=n;self.deadline=deadline
        self.stage_callback=stage_callback
        self.upper=[1]*len(rows);self.constraints=[];self.receipts=[]
        self.add(dict.fromkeys(range(len(rows)),1),n,n)

    def variable(self, upper):
        self.upper.append(upper);return len(self.upper)-1

    def add(self, coefficients, lo=-math.inf, hi=math.inf):
        self.constraints.append((coefficients,lo,hi))

    def absolute(self, coefficients, target=0):
        var=self.variable(max(64,len(self.rows)+abs(target)))
        self.add({**coefficients,var:-1},hi=target)
        self.add({i:-v for i,v in coefficients.items()} | {var:-1},hi=-target)
        return var

    def coverage(self, key):
        objective={}
        for value in sorted({key(r) for r in self.rows}):
            indices=[i for i,r in enumerate(self.rows) if key(r)==value]
            var=self.variable(1);objective[var]=-1
            self.add(dict.fromkeys(indices,1)|{var:-1},lo=0)
            self.add(dict.fromkeys(indices,1)|{var:-self.n},hi=0)
        return objective

    def optimize(self, objective, label, lock=True):
        from scipy.optimize import Bounds, LinearConstraint
        from scipy.sparse import csc_array
        np=self.np;remaining=self.deadline-time.monotonic()
        if self.stage_callback:self.stage_callback({'stage':label,'status':'STARTED'})
        if remaining<=0:raise SelectionBlocked('total selector time limit reached; no optimum accepted')
        c=np.zeros(len(self.upper))
        for i,value in objective.items():c[i]=value
        a=np.zeros((len(self.constraints),len(self.upper)));lo=[];hi=[]
        for j,(coefficients,l,h) in enumerate(self.constraints):
            for i,value in coefficients.items():a[j,i]=value
            lo.append(l);hi.append(h)
        result=self.milp(c,integrality=np.ones(len(c)),bounds=Bounds(np.zeros(len(c)),self.upper),
            constraints=LinearConstraint(csc_array(a),lo,hi),
            options={'time_limit':min(10.,remaining),'mip_rel_gap':0.,'presolve':True})
        if time.monotonic()>self.deadline:
            raise SelectionBlocked('total selector time limit reached; no late optimum accepted')
        x,value=_checked_solution(result,c,a,lo,hi,self.upper)
        self.receipts.append({'stage':label,'status':'OPTIMAL','objective':value,
                              'dual_bound':float(result.mip_dual_bound),'gap':float(result.mip_gap),
                              'nodes':int(result.mip_node_count)})
        if self.stage_callback:self.stage_callback(self.receipts[-1])
        if lock:self.add(dict(objective),value,value)
        return x,value

    def finish(self, objectives):
        for label,objective in objectives:self.optimize(objective,label)
        # Binary lex preference equals lex-smallest sorted rank list at fixed N.
        # Each exact chunk is optimized and fixed before the next; max weight 512.
        x=None
        for start in range(0,len(self.rows),10):
            indices=list(range(start,min(start+10,len(self.rows))))
            objective={i:-(2**(len(indices)-1-k)) for k,i in enumerate(indices)}
            x,_=self.optimize(objective,f'hash_lex_{start:03d}',lock=False)
            for i in indices:self.add({i:1},int(x[i]),int(x[i]))
        return [r for i,r in enumerate(self.rows) if x is not None and x[i]==1]


def _checked_solution(result,c,a,lo,hi,upper):
    """Numerical optimality receipt plus exact integer feasibility recheck."""
    import numpy as np
    if (result.status!=0 or not result.success or result.x is None or
        getattr(result,'mip_gap',None) is None or result.mip_gap!=0 or
        getattr(result,'mip_dual_bound',None) is None):
        raise SelectionBlocked('solver nonoptimal/timeout/unknown optimality; no selection accepted')
    raw=np.asarray(result.x)
    if len(raw)!=len(c) or not np.isfinite(raw).all() or np.max(np.abs(raw-np.rint(raw)),initial=0)>1e-6:
        raise SelectionBlocked('solver returned noninteger or nonfinite values')
    x=np.rint(raw).astype('int64');sums=a.astype('int64')@x
    if np.any(x<0) or np.any(x>upper) or np.any(sums<lo) or np.any(sums>hi):
        raise SelectionBlocked('solver integer constraints or bounds violated')
    value=int(c.astype('int64')@x)
    if (not math.isfinite(float(result.fun)) or not math.isfinite(float(result.mip_dual_bound))
            or abs(result.fun-value)>1e-6 or abs(result.mip_dual_bound-value)>1e-6):
        raise SelectionBlocked('solver objective/dual bound does not certify integer optimum')
    return x,value


def _quota(office):
    counts=(4,4,2,2) if office=='HOUSE' else (1,1,1,1)
    return {(b,p):(counts[i] if p!='OTHER' else 0) for i,b in enumerate(BANDS) for p in PARTIES}


def _broad(rows,office,deadline,callback=None):
    rows=sorted(rows,key=rank_key);n=min(24 if office=='HOUSE' else 8,len(rows))
    if not rows:return {'selected':[],'ranks':[],'stages':[],'counts':{},'objective_vector':[],
                            'status':'BLOCKED_EMPTY_OFFICE','absent_bands':list(BANDS),'shortfall':True}
    emit=(lambda receipt:callback('broad',office,receipt)) if callback else None
    model=_MILP(rows,n,deadline,emit);quota=_quota(office);deviations={}
    for band in BANDS:
        indices=[i for i,r in enumerate(rows) if r['band']==band]
        if indices:model.add(dict.fromkeys(indices,1),lo=1)
        for party in PARTIES:
            cell={i:1 for i,r in enumerate(rows) if (r['band'],r['sampling_party'])==(band,party)}
            deviations[model.absolute(cell,quota[band,party])]=1
    imbalance=model.absolute({i:1 if r['sampling_party']=='D' else -1 if r['sampling_party']=='R' else 0 for i,r in enumerate(rows)})
    regions=model.coverage(lambda r:REGIONS[r['state']]);states=model.coverage(lambda r:r['state'])
    selected=model.finish([('quota_L1',deviations),('party_imbalance',{imbalance:1}),('regions',regions),('states',states)])
    counts=Counter((r['band'],r['sampling_party']) for r in selected)
    objective=[sum(abs(counts[k]-v) for k,v in quota.items()),
               abs(sum(r['sampling_party']=='D' for r in selected)-sum(r['sampling_party']=='R' for r in selected)),
               -len({REGIONS[r['state']] for r in selected}),-len({r['state'] for r in selected})]
    if objective!=[r['objective'] for r in model.receipts[:4]]:raise SelectionBlocked('independent broad objective recomputation failed')
    absent=[b for b in BANDS if not any(r['band']==b for r in rows)]
    return {'selected':[r['race_id'] for r in selected],
            'ranks':[{'race_id':r['race_id'],'sha256':rank_key(r)[0],'rank':i} for i,r in enumerate(rows)],
            'counts':{b:{p:counts[b,p] for p in PARTIES} for b in BANDS},'objective_vector':objective,
            'stages':model.receipts,'status':'BLOCKED_HOUSE_TARGET' if office=='HOUSE' and n<24 else
            'BLOCKED_ABSENT_BAND' if absent else 'FIXTURE_SELECTED',
            'absent_bands':absent,'shortfall':objective[0]!=0}


def _deep(rows,office,deadline,callback=None):
    rows=sorted(rows,key=rank_key);bands={r['band'] for r in rows};fallback=None
    if office=='HOUSE' and bands!=set(BANDS):
        return {'status':'BLOCKED_DEEP_HOUSE_ABSENT_BAND','selected':[],'stages':[]}
    n=4 if office=='HOUSE' else 2
    if len(rows)<n:return {'status':'BLOCKED_DEEP_INSUFFICIENT_CONTESTS','selected':[],'stages':[]}
    emit=(lambda receipt:callback('deep',office,receipt)) if callback else None
    model=_MILP(rows,n,deadline,emit)
    if office=='HOUSE':
        for band in BANDS:model.add({i:1 for i,r in enumerate(rows) if r['band']==band},1,1)
    else:
        competitive=[i for i,r in enumerate(rows) if r['band'] in BANDS[:2]]
        less=[i for i,r in enumerate(rows) if r['band'] in BANDS[2:]]
        if competitive and less:model.add(dict.fromkeys(competitive,1),1,1)
        else:fallback='ABSENT_COMPETITIVE_GROUP' if not competitive else 'ABSENT_LESS_COMPETITIVE_GROUP'
    target=n//2;balance={model.absolute({i:1 for i,r in enumerate(rows) if r['sampling_party']==p},target):1 for p in ('D','R')}
    regions=model.coverage(lambda r:REGIONS[r['state']]);objectives=[('deep_party_target_L1',balance),('deep_regions',regions)]
    if office=='HOUSE':objectives.append(('deep_states',model.coverage(lambda r:r['state'])))
    selected=model.finish(objectives)
    objective=[sum(abs(sum(r['sampling_party']==p for r in selected)-target) for p in ('D','R')),
               -len({REGIONS[r['state']] for r in selected})]
    if office=='HOUSE':objective.append(-len({r['state'] for r in selected}))
    if objective!=[r['objective'] for r in model.receipts[:len(objective)]]:raise SelectionBlocked('independent deep objective recomputation failed')
    return {'status':'FIXTURE_SELECTED','selected':[r['race_id'] for r in selected],
            'fallback':fallback,'objective_vector':objective,'stages':model.receipts}


def select_fixture(frame,*,max_seconds=60.,_stage_callback=None):
    if not isinstance(max_seconds,(int,float)) or isinstance(max_seconds,bool) or not math.isfinite(max_seconds) or not 0<max_seconds<=120:
        raise SelectionBlocked('selector wall time must be bounded in (0,120] seconds')
    rows=validate_fixture(frame);deadline=time.monotonic()+max_seconds
    broad={office:_broad([r for r in rows if r['office']==office and r['eligibility']=='ELIGIBLE'],office,deadline,_stage_callback) for office in ('HOUSE','SENATE')}
    deep={office:_deep([r for r in rows if r['race_id'] in broad[office]['selected']],office,deadline,_stage_callback) for office in ('HOUSE','SENATE')}
    from scipy.optimize._highspy import _core
    solver='.'.join(str(getattr(_core,'HIGHS_VERSION_'+v)) for v in ('MAJOR','MINOR','PATCH'))
    payload={'dataset_kind':'DEMO_SELECTION_FIXTURE','algorithm':ALGORITHM,'seed':SEED,'cutoff':CUTOFF,
             'frame_sha256':canonical_hash({**frame,'rows':sorted(frame['rows'],key=lambda r:r['race_id']),
                                          'expected_race_ids':sorted(frame['expected_race_ids']),
                                          'sources':sorted(frame['sources'],key=lambda s:s['source_id'])}),
             'solver':{'scipy':'1.16.3','highs':solver,'relative_gap':0,'tie_chunk_bits':10},
             'broad':broad,'deep':deep,
             'exclusions':[r for r in rows if r['eligibility']!='ELIGIBLE'],
             'full_six_deep_fixture':all(len(deep[o]['selected'])==n for o,n in [('HOUSE',4),('SENATE',2)]),
             'scientific_gate':'BLOCKED_NO_ACCEPTED_REAL_FRAME','paid_calls':0,'cost_usd':0}
    # Node counts are diagnostics and can vary with solver platform; identities,
    # objective vectors and fixed input/rank hashes define deterministic selection.
    stable={'frame_sha256':payload['frame_sha256'],
            'broad':{o:v['selected'] for o,v in broad.items()},
            'deep':{o:v['selected'] for o,v in deep.items()}}
    return {**payload,'selection_sha256':canonical_hash(stable)}


def comparison_gate(selected_ids,predictions_by_method,*,cutoff=CUTOFF):
    """Fixture full-set admission, no favorable successful-pair intersection."""
    if cutoff!=CUTOFF:raise SelectionBlocked('unreviewed comparison cutoff')
    if not selected_ids or len(selected_ids)!=len(set(selected_ids)) or not all(isinstance(x,str) and x.startswith('DEMO-') for x in selected_ids):
        raise SelectionBlocked('invalid fixture selection IDs')
    if len(predictions_by_method)<2:raise SelectionBlocked('simpler matched comparator required')
    for method,records in predictions_by_method.items():
        if not isinstance(method,str) or not isinstance(records,list):raise SelectionBlocked('invalid method records')
        if len(records)!=len(selected_ids):raise SelectionBlocked('missing predictions block full-set comparison; no replacement')
        seen=set()
        for record in records:
            _exact(record,{'race_id','cutoff','status'},'comparison record')
            if record['cutoff']!=cutoff or record['status']!='COMPLETE':raise SelectionBlocked('failed or mismatched method condition')
            seen.add(record['race_id'])
        if seen!=set(selected_ids):raise SelectionBlocked('method race set differs from fixed selection')
    return {'status':'FIXTURE_FULL_SET_MATCHED','race_ids':sorted(selected_ids),'methods':sorted(predictions_by_method)}


def run_fixture(root,frame,*,max_seconds=60.):
    """Record valid fixture input and solver failures in shared immutable logging."""
    validate_fixture(frame)
    from civiclab.common import RunStore
    failure=None
    with RunStore(Path(root),'E01',{'role':'DEMO_SELECTION_FIXTURE','algorithm':ALGORITHM,
            'seed':SEED,'cutoff':CUTOFF,'frame_sha256':canonical_hash(frame),'max_seconds':max_seconds},kind='MOCK') as run:
        run.write('selection.fixture.json',frame)
        try:
            result=select_fixture(frame,max_seconds=max_seconds,
                _stage_callback=lambda group,office,receipt:run.event('selection_solver_stage',group=group,office=office,**receipt))
        except Exception as error:
            failure=error
            run.write('selection.failure.json',{'status':'FAILED','exception_type':type(error).__name__,'reason':str(error)})
            run.event('selection_failed',error_type=type(error).__name__)
            run.finish({'status':'DEMO_SELECTION_FIXTURE_FAILED','scientific_gate':'BLOCKED_NO_ACCEPTED_REAL_FRAME',
                        'paid_calls':0,'cost_usd':0})
        else:
            run.write('selection.result.json',result)
            run.finish({'status':'DEMO_SELECTION_FIXTURE_COMPLETE','selection_sha256':result['selection_sha256'],
                        'scientific_gate':result['scientific_gate'],'paid_calls':0,'cost_usd':0})
    if failure is not None:raise failure
    return run.path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture',type=Path);parser.add_argument('--max-seconds',type=float,default=60.)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args()
    print(run_fixture(args.root,json.loads(args.fixture.read_text()),max_seconds=args.max_seconds))


if __name__=='__main__':main()
