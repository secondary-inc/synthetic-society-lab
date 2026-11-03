"""Public N1-F runtime: authored fixtures only, shared ownership and time budget."""
from contextlib import contextmanager
import fcntl
from pathlib import Path
from .national_budget import Blocked,FixtureResponse,acquire_fixture
from .full_adult_control_v1_2 import fixture_root,FResourceLedger
from .full_adult_engine_v1_2 import enroll_F,process_F
from .full_adult_queries_v1_2 import prepare_plan,execute_query,assemble_results
from .full_adult_analysis_v1_2 import compile_plan
from .full_adult_codec_v1_2 import write_benchmark,ExecutionBinding


class FullAdultFixtureEngine:
    def __init__(self,c,spec,selectors,coefficients,queries):
        self.c=c;self.spec=spec;self.root=fixture_root(c['fixture_root'],c);self.sources=FResourceLedger(c)
        with self.phase():
            self.plan,self.queries=prepare_plan(c,spec,selectors,coefficients,queries)
        self.parts={'PRIMARY':[],'REPLAY':[]};self.manifests={};self.matrices={};self.binding=None
    @contextmanager
    def phase(self):
        with (self.root/'.F_phase_lock').open('a') as f:
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise Blocked('F shared phase already active') from None
            try:yield
            finally:fcntl.flock(f,fcntl.LOCK_UN)
    def time_guard(self,extra=300):
        s=self.sources.snapshot();q=self.queries.snapshot();seconds=s['processing_seconds_charged']
        # MANDATORY is inside the source UNION reservation; do not double bill it.
        for name,p in q['phases'].items():
            if name.startswith('CATALOG:'):seconds+=p['elapsed_seconds'] if p['status']=='COMMITTED' else self.c['limits']['state_processing_seconds']
        for p in q['queries'].values():seconds+=p['elapsed_seconds'] if p['status'] in ('COMMITTED','REFUSED') else self.c['limits']['state_processing_seconds']
        if seconds+extra>self.c['limits']['processing_seconds']:raise Blocked('F combined source/query elapsed budget')
        if s['active'] is not None or s['processing_active'] is not None or q['halted'] or any(p['status']=='RESERVED' for p in [*q['phases'].values(),*q['queries'].values()]):raise Blocked('F pending/halted state needs explicit recovery')
        return seconds
    def source(self,path,manifest,review,*,fake_delivery=False):
        with self.phase():
            self.time_guard(self.c['limits']['state_processing_seconds'])
            if fake_delivery:
                path=Path(path)
                if path.stat().st_size>self.c['limits']['archive_body_bytes']:raise Blocked('fixture BODY bound')
                if manifest['state']=='56':raise Blocked('WY reused once, no delivery')
                import mmap
                with path.open('rb') as stream:
                    with mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as body:
                        _,path=acquire_fixture(self.sources,manifest['state'],FixtureResponse(body,url=manifest['url'],content_length=len(body)))
            enrolled=enroll_F(self.sources,path,manifest,review);self.manifests[manifest['state']]=manifest
            for sweep in ('PRIMARY','REPLAY'):
                self.time_guard(self.c['limits']['state_processing_seconds']);part,res=process_F(self.sources,path,manifest,enrolled,sweep=sweep);self.parts[sweep].append(part)
            return path
    def benchmark(self):
        with self.phase():
            for sweep in ('PRIMARY','REPLAY'):
                self.time_guard(self.c['limits']['state_processing_seconds']);m,meta,res=write_benchmark(self.sources,self.parts[sweep],self.spec,self.manifests,sweep=sweep,query_ledger=self.queries);self.matrices[sweep]=m
            self.binding=ExecutionBinding(self.c,self.spec,self.plan,self.queries)
            return self.matrices
    def analyze(self):
        if self.binding is None:raise Blocked('benchmark/source binding incomplete')
        with self.phase():
            self.time_guard(self.c['limits']['state_processing_seconds'])
            key=self.queries.reserve_phase('CATALOG','REPLAY')
            try:
                replay=compile_plan(self.spec,self.plan['selectors'],self.plan['coefficients'],self.plan['requests'])
                if replay['catalog_ops']!=self.plan['catalog_ops'] or replay['queries']!=self.plan['queries']:raise Blocked('catalog replay changed')
            except BaseException:
                self.queries.finish_phase(key,failed=True);raise
            self.queries.finish_phase(key);self.time_guard(0)
            results={}
            for sweep in ('PRIMARY','REPLAY'):
                results[sweep]=[]
                for query in self.plan['queries']:
                    self.time_guard(self.c['limits']['state_processing_seconds'])
                    results[sweep].append(execute_query(self.queries,self.matrices[sweep],query,self.binding.digest,self.spec,sweep,context=self.binding))
                assemble_results(self.queries,self.plan,sweep,self.matrices[sweep],self.binding.digest,self.spec)
            return results
