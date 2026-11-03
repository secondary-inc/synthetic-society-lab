"""F v1 durable query journal, source-bound outputs and conservative charges."""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import time
from ..common import canonical_hash,atomic_json,sha256_file
from .national_budget import Blocked
from .full_adult_control_v1 import Policy,fixture_root
from .full_adult_types_v1 import strict_json,keys,hash_value
from .full_adult_analysis_v1 import catalog_bound,compile_plan,evaluate_query,validate_result


def line(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


class QueryLedger:
    def __init__(self,c,template,*,clock=time.time):
        self.c=c;self.root=fixture_root(c['fixture_root'],c);self.path=self.root/'analysis';self.path.mkdir(exist_ok=True);self.policy=Policy(c);self.clock=clock
        self.template=deepcopy(template);self.design=canonical_hash({'runtime':c,'template':template});self.catalog_cost=catalog_bound(template['selectors'],template['coefficients'])
        with self.lock():
            if not (self.path/'state.json').exists():
                if any(p.name!='.lock' for p in self.path.iterdir()):raise Blocked('query directory not new; no reset')
                now=clock();s={'design':self.design,'created':now,'last_clock':now,'generation':0,'ops':0,'bytes':0,'phases':{},'queries':{},'admitted':None,'binding':None,'halted':False,'outputs':{}}
                self.policy.json(self.path/'plan_input.json',self.template);self.policy.json(self.path/'runtime_config.json',c)
                self.policy.json(self.path/'genesis.json',s);self.policy.json(self.path/'state.json',s)
            self._verified()
    @contextmanager
    def lock(self):
        with (self.path/'.lock').open('a') as f:
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise Blocked('query ledger locked') from None
            try:yield
            finally:fcntl.flock(f,fcntl.LOCK_UN)
    def _rows(self,path):
        try:return [strict_json(x) for x in path.read_text().splitlines()] if path.exists() else []
        except OSError:raise Blocked('query history unavailable') from None
    def _state(self):return strict_json((self.path/'state.json').read_text())
    def _semantic(self,s):
        keys(s,['design','created','last_clock','generation','ops','bytes','phases','queries','admitted','binding','halted','outputs'])
        if s['design']!=self.design or type(s['halted']) is not bool:raise Blocked('query immutable design/schema')
        if any(type(s[k]) is not int or s[k]<0 for k in ('generation','ops','bytes')):raise Blocked('query counter type')
        if any(type(s[k]) not in (int,float) or not math.isfinite(s[k]) or s[k]<0 for k in ('created','last_clock')) or s['last_clock']<s['created']:raise Blocked('query clock schema')
        if self.clock()<s['last_clock'] or self.clock()-s['created']>self.c['limits']['batch_elapsed_seconds']:raise Blocked('query expiry/clock rollback')
        if type(s['phases']) is not dict or type(s['queries']) is not dict:raise Blocked('query state types')
        ops=0;byte_count=0;pending=0
        for key,p in s['phases'].items():
            keys(p,['cost','status','started','elapsed_seconds']);kind,sweep=key.split(':')
            if kind not in ('CATALOG','MANDATORY') or sweep not in ('PRIMARY','REPLAY') or p['cost']!=(self.catalog_cost if kind=='CATALOG' else 6000000) or p['status'] not in ('RESERVED','COMMITTED','FAILED','UNKNOWN'):raise Blocked('phase semantics')
            if type(p['started']) not in (int,float) or not math.isfinite(p['started']):raise Blocked('phase time')
            if p['status']=='COMMITTED' and (type(p['elapsed_seconds']) not in (int,float) or not 0<=p['elapsed_seconds']<=self.c['limits']['state_processing_seconds']):raise Blocked('phase elapsed')
            ops+=p['cost'];pending+=p['status']=='RESERVED'
        defs=s['admitted']
        if defs is not None:
            keys(defs,['queries','catalog_ops','total_ops','plan_hash'])
            if defs['catalog_ops']!=self.catalog_cost or defs['total_ops']!=2*(6000000+self.catalog_cost+sum(q['cost'] for q in defs['queries'])) or defs['total_ops']>64000000:raise Blocked('admitted operation reconciliation')
            if defs['plan_hash']!=canonical_hash(self.template):raise Blocked('plan template binding')
        for key,q in s['queries'].items():
            keys(q,['cost','charged_bytes','observed_bytes','status','result_sha256','pending_path','started','elapsed_seconds','result_status'])
            sweep,ident=key.split(':')
            if sweep not in ('PRIMARY','REPLAY') or defs is None:raise Blocked('query source key')
            d=next((x for x in defs['queries'] if x['query_id']==ident),None)
            if d is None or q['cost']!=(0 if q['status']=='REFUSED' else d['cost']) or type(q['charged_bytes']) is not int or not 0<=q['charged_bytes']<=2048:raise Blocked('query counter/identity')
            if q['status'] not in ('RESERVED','COMMITTED','FAILED','UNKNOWN','REFUSED'):raise Blocked('query status')
            if type(q['started']) not in (int,float) or not math.isfinite(q['started']):raise Blocked('query time')
            if q['status'] in ('COMMITTED','REFUSED'):
                pending_path=(self.root/q['pending_path']).resolve()
                if not pending_path.is_relative_to(self.root/'scratch') or not pending_path.is_file() or sha256_file(pending_path)!=q['result_sha256'] or pending_path.stat().st_size!=q['observed_bytes']:raise Blocked('committed result bytes changed')
                if type(q['elapsed_seconds']) not in (int,float) or not 0<=q['elapsed_seconds']<=self.c['limits']['state_processing_seconds']:raise Blocked('query elapsed')
                if type(q['observed_bytes']) is not int or q['charged_bytes']!=q['observed_bytes'] or q['result_sha256'] is None:raise Blocked('success bytes not proven')
            elif q['charged_bytes']!=2048:raise Blocked('failure reservation refunded')
            ops+=q['cost'];byte_count+=q['charged_bytes'];pending+=q['status']=='RESERVED'
        for sweep,output in s['outputs'].items():
            if sweep not in ('PRIMARY','REPLAY') or type(output) is not dict or set(output)!={'covariance_results_v1_1.jsonl','contrast_results_v1_1.jsonl','query_result_index.json'}:raise Blocked('output source key')
            for name,digest in output.items():
                if name not in ('covariance_results_v1_1.jsonl','contrast_results_v1_1.jsonl','query_result_index.json') or sha256_file(self.root/sweep/name)!=digest:raise Blocked('sealed query output changed')
        if pending>1 or s['ops']!=ops or s['bytes']!=byte_count or ops>64000000 or byte_count>2*4224*2048:raise Blocked('semantic query resource reconciliation')
    def _verified(self):
        try:
            s=self._state();self._semantic(s)
            if strict_json((self.path/'plan_input.json').read_text())!=self.template or strict_json((self.path/'runtime_config.json').read_text())!=self.c:raise Blocked('query frozen input/config changed')
            genesis=strict_json((self.path/'genesis.json').read_text());self._semantic(genesis)
            if genesis['generation']!=0:raise Blocked('query genesis')
            events=self._rows(self.path/'events.jsonl');receipts=self._rows(self.path/'query_receipts_v1_1.jsonl');previous=None;state_hash=canonical_hash(genesis);used=set();receipt_prev=None
            for i,e in enumerate(events,1):
                keys(e,['g','event','receipt','prev','before','after','h'])
                if e['g']!=i or e['prev']!=previous or e['before']!=state_hash or e['h']!=canonical_hash({k:v for k,v in e.items() if k!='h'}):raise Blocked('query core transition chain')
                if e['receipt'] is not None:
                    rec=next((r for r in receipts if r['h']==e['receipt']),None)
                    if rec is None or rec['h'] in used or rec['prev']!=receipt_prev or rec['state']!=e['after'] or rec['seq']!=i or rec['h']!=canonical_hash({k:v for k,v in rec.items() if k!='h'}):raise Blocked('query receipt binding/chain')
                    self._validate_receipt(rec,s);used.add(rec['h']);receipt_prev=rec['h']
                previous=e['h'];state_hash=e['after']
            if len(events)!=s['generation'] or len(used)!=len(receipts) or canonical_hash(s)!=state_hash:raise Blocked('torn query state/receipt/index; no reset')
            by_key={}
            for r in receipts:by_key.setdefault(r['w']+':'+r['q'],[]).append(r)
            if set(by_key)!=set(s['queries']):raise Blocked('receipt/state query set')
            for key,q in s['queries'].items():
                records=by_key[key];last=records[-1]
                if len(records)>2 or records[0]['phase'] not in ('RESERVED','REFUSED_BEFORE_RESERVATION') or (len(records)==2 and last['phase'] not in ('TERMINAL','RECOVERED_UNKNOWN')):raise Blocked('receipt transition cardinality')
                if last['o']!=q['cost'] or last['b']!=q['charged_bytes'] or last['rh']!=q['result_sha256'] or last['rb']!=q['observed_bytes'] or last['status']!=q['result_status']:raise Blocked('receipt/counter/result reconciliation')
            return s
        except (OSError,KeyError,TypeError,ValueError):raise Blocked('unprovable query ledger') from None
    def _validate_receipt(self,r,s):
        keys(r,['v','seq','q','w','phase','m','d','o','b','rh','rb','status','prev','state','h'])
        if r['status'] not in ('RESERVED','RECORDED_SDR_CONDITIONAL_ONLY','REVIEW_ZERO_ESTIMATE_OR_SE','BLOCKED_STORAGE','BLOCKED_QUERY_BUDGET','BLOCKED_INTEGRITY','BLOCKED_NONFINITE_OR_OVERFLOW','FAILED_WORKER_OR_CANCELLED','UNKNOWN_AFTER_CRASH'):raise Blocked('receipt status vocabulary')
        if len(line(r))>1024 or r['v']!='1.1' or r['w'] not in ('PRIMARY','REPLAY') or r['phase'] not in ('RESERVED','TERMINAL','RECOVERED_UNKNOWN','REFUSED_BEFORE_RESERVATION') or r['m']!=s['binding']:raise Blocked('receipt domain/binding')
        if s['admitted'] is None:raise Blocked('receipt without admission')
        d=next((q for q in s['admitted']['queries'] if q['query_id']==r['q']),None)
        if d is None or r['d']!=d['definition_sha256'] or r['o']!=(0 if r['phase']=='REFUSED_BEFORE_RESERVATION' else d['cost']) or type(r['b']) is not int or not 0<=r['b']<=2048:raise Blocked('receipt definition/charge')
        for name in ('m','d','state','h'):hash_value(r[name])
        if r['rh'] is not None:hash_value(r['rh'])
        if r['rb'] is not None and (type(r['rb']) is not int or not 0<=r['rb']<=2048):raise Blocked('receipt observed length')
    def _save(self,s,event,receipt=None,hook=lambda event:None):
        old=self._verified();s['generation']+=1;s['last_clock']=self.clock();self._semantic(s)
        events=self._rows(self.path/'events.jsonl');rs=self._rows(self.path/'query_receipts_v1_1.jsonl')
        if receipt is not None:
            receipt={**receipt,'v':'1.1','seq':s['generation'],'prev':rs[-1]['h'] if rs else None,'state':canonical_hash(s)};receipt['h']=canonical_hash(receipt);self._validate_receipt(receipt,s)
        e={'g':s['generation'],'event':event,'receipt':receipt['h'] if receipt else None,'prev':events[-1]['h'] if events else None,'before':canonical_hash(old),'after':canonical_hash(s)};e['h']=canonical_hash(e)
        self.policy.check('core',len(json.dumps(s,indent=2).encode())+len(line(e))+1024)
        if receipt:self.policy.check('receipts',len(line(receipt)))
        if receipt:
            with (self.path/'query_receipts_v1_1.jsonl').open('ab') as f:f.write(line(receipt));f.flush();os.fsync(f.fileno())
            hook('after_receipt_before_index')
        with (self.path/'events.jsonl').open('ab') as f:f.write(line(e));f.flush();os.fsync(f.fileno())
        hook('after_index_before_state');atomic_json(self.path/'state.json',s)
    def snapshot(self):
        with self.lock():return deepcopy(self._verified())
    def reserve_phase(self,kind,sweep):
        with self.lock():
            s=self._verified();key=kind+':'+sweep
            if kind not in ('CATALOG','MANDATORY') or sweep not in ('PRIMARY','REPLAY') or key in s['phases'] or s['halted'] or any(p['status']=='RESERVED' for p in [*s['phases'].values(),*s['queries'].values()]):raise Blocked('phase duplicate/concurrent/halted')
            cost=self.catalog_cost if kind=='CATALOG' else 6000000
            if s['ops']+cost>64000000:raise Blocked('analysis phase budget')
            s['ops']+=cost;s['phases'][key]={'cost':cost,'status':'RESERVED','started':self.clock(),'elapsed_seconds':None};self._save(s,'phase_reserved');return key
    def finish_phase(self,key,*,failed=False):
        with self.lock():
            s=self._verified()
            if s['phases'][key]['status']!='RESERVED':raise Blocked('phase not reserved')
            elapsed=self.clock()-s['phases'][key]['started']
            if not failed and elapsed>self.c['limits']['state_processing_seconds']:raise Blocked('phase elapsed cap')
            s['phases'][key].update(status='FAILED' if failed else 'COMMITTED',elapsed_seconds=elapsed if not failed else None);s['halted']|=failed;self._save(s,'phase_terminal')
    def admit(self,plan):
        with self.lock():
            s=self._verified()
            if s['admitted'] is not None:raise Blocked('plan already admitted')
            s['admitted']={'queries':[{'query_id':q['query_id'],'cost':q['cost'],'definition_sha256':q['query_definition_sha256'],'query_kind':q['query_kind']} for q in plan['queries']],'catalog_ops':plan['catalog_ops'],'total_ops':plan['total_ops'],'plan_hash':canonical_hash(self.template)};self._save(s,'plan_admitted')
    def bind(self,digest):
        hash_value(digest)
        with self.lock():
            s=self._verified()
            if s['binding'] is not None and s['binding']!=digest:raise Blocked('changed execution binding')
            if s['binding'] is None:s['binding']=digest;self._save(s,'execution_bound')
    def reserve_query(self,query,sweep,*,hook=lambda event:None):
        with self.lock():
            s=self._verified();key=sweep+':'+query['query_id']
            if sweep not in ('PRIMARY','REPLAY') or s['binding'] is None or s['admitted'] is None or key in s['queries'] or s['halted'] or any(v['status']=='RESERVED' for v in [*s['queries'].values(),*s['phases'].values()]):raise Blocked('query duplicate/unbound/concurrent/halted')
            d=next((q for q in s['admitted']['queries'] if q['query_id']==query['query_id']),None)
            if d is None or d['cost']!=query['cost'] or d['definition_sha256']!=query['query_definition_sha256'] or s['ops']+query['cost']>64000000:raise Blocked('query admission/budget')
            s['ops']+=query['cost'];s['bytes']+=2048;s['queries'][key]={'cost':query['cost'],'charged_bytes':2048,'observed_bytes':None,'status':'RESERVED','result_sha256':None,'pending_path':None,'started':self.clock(),'elapsed_seconds':None,'result_status':'RESERVED'}
            rec={'q':query['query_id'],'w':sweep,'phase':'RESERVED','m':s['binding'],'d':query['query_definition_sha256'],'o':query['cost'],'b':2048,'rh':None,'rb':None,'status':'RESERVED'};self._save(s,'query_index',rec,hook=hook);return key
    def finish_query(self,key,query,path,*,failure=None,hook=lambda event:None):
        with self.lock():
            s=self._verified();q=s['queries'][key]
            if q['status']!='RESERVED':raise Blocked('query not pending')
            if failure is None:
                path=Path(path).resolve()
                if not path.is_relative_to(self.root/'scratch') or path.stat().st_size>2048:raise Blocked('pending result path/bytes')
                blob=path.read_bytes();record=strict_json(blob)
                if record['query_id']!=query['query_id'] or record['execution_manifest_sha256']!=s['binding']:raise Blocked('pending result binding')
                elapsed=self.clock()-q['started']
                if elapsed>self.c['limits']['state_processing_seconds']:raise Blocked('query elapsed cap')
                q.update(status='COMMITTED',result_status=record['status'],elapsed_seconds=elapsed,observed_bytes=len(blob),charged_bytes=len(blob),result_sha256=hashlib.sha256(blob).hexdigest(),pending_path=str(path.relative_to(self.root)));s['bytes']-=2048-len(blob)
            else:q['status']='UNKNOWN' if failure=='UNKNOWN_AFTER_CRASH' else 'FAILED';q['result_status']=failure;s['halted']=True
            sweep,ident=key.split(':');rec={'q':ident,'w':sweep,'phase':'RECOVERED_UNKNOWN' if failure=='UNKNOWN_AFTER_CRASH' else 'TERMINAL','m':s['binding'],'d':query['query_definition_sha256'],'o':q['cost'],'b':q['charged_bytes'],'rh':q['result_sha256'],'rb':q['observed_bytes'],'status':failure or record['status']}
            self._save(s,'query_index',rec,hook=hook)
    def refuse_query(self,query,sweep,binding,spec,status='BLOCKED_INTEGRITY'):
        if status not in ('BLOCKED_INTEGRITY','BLOCKED_STORAGE','BLOCKED_QUERY_BUDGET'):raise Blocked('refusal status')
        with self.lock():
            s=self._verified();key=sweep+':'+query['query_id']
            if key in s['queries'] or s['binding']!=binding or s['admitted'] is None:raise Blocked('refusal key/binding')
            record=null_result(query,binding,spec,status);blob=line(record)
            if len(blob)>2048:raise Blocked('refusal bytes')
            path=self.root/'scratch'/sweep/(query['query_id']+'.refused.jsonl');digest=self.policy.write(path,blob)
            s['bytes']+=len(blob);s['halted']=True
            s['queries'][key]={'cost':0,'charged_bytes':len(blob),'observed_bytes':len(blob),'status':'REFUSED','result_sha256':digest,'pending_path':str(path.relative_to(self.root)),'started':self.clock(),'elapsed_seconds':0,'result_status':status}
            rec={'q':query['query_id'],'w':sweep,'phase':'REFUSED_BEFORE_RESERVATION','m':binding,'d':query['query_definition_sha256'],'o':0,'b':len(blob),'rh':digest,'rb':len(blob),'status':status}
            self._save(s,'query_index',rec)
    def seal_outputs(self,sweep,files):
        with self.lock():
            s=self._verified()
            if sweep in s['outputs']:raise Blocked('query outputs immutable')
            for name,digest in files.items():
                if sha256_file(self.root/sweep/name)!=digest:raise Blocked('output commit hash')
            s['outputs'][sweep]=files;self._save(s,'query_output_sealed')
    def recover_unknown(self,plan):
        # Only provably committed state is recoverable; torn chains refuse above.
        with self.lock():
            s=self._verified()
            for phase,p in s['phases'].items():
                if p['status']=='RESERVED':p['status']='UNKNOWN';s['halted']=True;self._save(s,'phase_unknown')
            pending=[k for k,v in s['queries'].items() if v['status']=='RESERVED']
        for key in pending:
            query=next(q for q in plan['queries'] if q['query_id']==key.split(':')[1]);self.finish_query(key,query,None,failure='UNKNOWN_AFTER_CRASH')
        return self.snapshot()


def prepare_plan(c,spec,selectors,coefficients,requests):
    template={'selectors':selectors,'coefficients':coefficients,'requests':requests};ledger=QueryLedger(c,template)
    key=ledger.reserve_phase('CATALOG','PRIMARY')
    try:plan=compile_plan(spec,selectors,coefficients,requests)
    except BaseException as error:
        ledger.finish_phase(key,failed=True)
        refusal={'schema_version':'E02_F_PLAN_REFUSAL_V1','plan_template_sha256':canonical_hash(template),'status':'BLOCKED_PLAN_OPERATION_QUOTA' if '64million' in str(error) else 'REJECTED_SCHEMA_OR_VERSION','error_type':type(error).__name__,'catalog_cost_charged':ledger.catalog_cost,'actual_authority':0}
        ledger.policy.json(ledger.root/'PRIMARY/plan_refusal.json',refusal)
        raise
    ledger.finish_phase(key);ledger.admit(plan)
    selectors_doc={'schema_version':'E02_U1_SELECTOR_CATALOG_V1_1','entries':selectors}
    coefficients_doc={'schema_version':'E02_U1_COEFFICIENT_CATALOG_V1_1','entries':coefficients}
    for sweep in ('PRIMARY','REPLAY'):
        ledger.policy.json(ledger.root/sweep/'selectors.json',selectors_doc);ledger.policy.json(ledger.root/sweep/'coefficients.json',coefficients_doc)
        document={'schema_version':'E02_U1_QUERY_PLAN_V1_1','query_plan_id':canonical_hash(template),'spec_config_sha256':c['specification_sha256'],'target_axes_sha256':canonical_hash(spec['universe']),'selectors_file_sha256':sha256_file(ledger.root/sweep/'selectors.json'),'coefficients_file_sha256':sha256_file(ledger.root/sweep/'coefficients.json'),'queries':requests,'frozen_before_person_parse':True}
        ledger.policy.json(ledger.root/sweep/'query_plan.json',document)
    return plan,ledger


def execute_query(ledger,matrix,query,binding,spec,sweep,*,hook=lambda event:None,context=None):
    if context:context.verify(matrix)
    key=ledger.reserve_query(query,sweep,hook=hook)
    try:
        hook('after_reservation')
        from .national_population import supervise_fixture
        record,_=supervise_fixture(lambda:evaluate_query(matrix,query,binding,spec),seconds=ledger.c['limits']['state_processing_seconds'],rss_bytes=ledger.c['limits']['rss_stop_bytes'],poll_seconds=ledger.c['limits']['watchdog_poll_seconds'])
        hook('after_evaluation')
        if context:context.verify(matrix)
        validate_result(record,matrix,query,binding,spec);blob=line(record)
        if len(blob)>2048:raise Blocked('query result line limit')
        path=ledger.root/'scratch'/sweep/(query['query_id']+'.jsonl');ledger.policy.write(path,blob);hook('after_pending_result')
        ledger.finish_query(key,query,path,hook=hook);return record
    except BaseException:
        if ledger.snapshot()['queries'][key]['status']=='RESERVED':ledger.finish_query(key,query,None,failure='FAILED_WORKER_OR_CANCELLED')
        raise


def null_result(query,binding,spec,status):
    kind=query['query_kind'];schema=spec['query_contract']['covariance_result_JSON_schema' if kind=='COUNT_COVARIANCE' else 'contrast_result_JSON_schema']
    result={k:None for k in schema['required']}
    for k,s in schema['properties'].items():
        if 'const' in s:result[k]=s['const']
    result.update(query_id=query['query_id'],execution_manifest_sha256=binding,query_definition_sha256=query['query_definition_sha256'],status=status)
    if kind=='COUNT_COVARIANCE':result.update(x_coefficient_sha256=query['x']['sha256'],y_coefficient_sha256=query['y']['sha256'])
    else:result['coefficient_sha256']=query['x']['sha256']
    return result


def assemble_results(ledger,plan,sweep,matrix,binding,spec):
    s=ledger.snapshot();buckets={'COUNT_COVARIANCE':[],'COUNT_LINEAR_SIGNED':[]}
    for query in plan['queries']:
        item=s['queries'].get(sweep+':'+query['query_id'])
        if item is None and s['halted']:
            ledger.refuse_query(query,sweep,binding,spec);s=ledger.snapshot();item=s['queries'][sweep+':'+query['query_id']]
        if item is None or item['status']=='RESERVED':raise Blocked('uncommitted query cannot appear as result')
        if item['status'] in ('FAILED','UNKNOWN'):
            record=null_result(query,binding,spec,item['result_status']);validate_result(record,matrix,query,binding,spec);buckets[query['query_kind']].append(line(record));continue
        path=(ledger.root/item['pending_path']).resolve()
        if not path.is_relative_to(ledger.root/'scratch') or sha256_file(path)!=item['result_sha256']:raise Blocked('committed pending result changed')
        record=strict_json(path.read_text());validate_result(record,matrix,query,binding,spec)
        buckets[query['query_kind']].append(line(record))
    out={}
    for kind,name in [('COUNT_COVARIANCE','covariance_results_v1_1.jsonl'),('COUNT_LINEAR_SIGNED','contrast_results_v1_1.jsonl')]:
        blob=b''.join(buckets[kind]);out[name]=ledger.policy.write(ledger.root/sweep/name,blob)
    index={'schema_version':'E02_F_QUERY_RESULT_INDEX_V1','execution_manifest_sha256':binding,'query_ids':[q['query_id'] for q in plan['queries']],'files':out,'scope':'MOCK_LOCAL_DEMOGRAPHICS_ONLY'}
    out['query_result_index.json']=ledger.policy.json(ledger.root/sweep/'query_result_index.json',index);ledger.seal_outputs(sweep,out)
    return out
