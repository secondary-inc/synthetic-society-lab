"""Fixed Clerk source-format campaign persistence; no source/backend entrypoint.

Only this campaign's finite slots, two issue/reservation ordinals and immutable
anchor chain exist. Trusted local owner/flock/fsync, not hostile-host protection.
No raw source paths, PDF imports, network, model or credential access occur here.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import stat

from civiclab.e01.clerk2020_m2_v1_1_contracts import (
    Axis, CEILINGS, Counters, Refused, canonical, decode, exact, hex64, require, sha,
)

CAMPAIGN = 'clerk2020_source_format_native_v2'
SOURCE_SET = 'clerk2020_counts_2026_nominees_FORMAT_v1'
ANCHOR = 'clerk2020_format_anchor_v2'
REGISTRY = 'data/processed/e01_clerk2020_m2_registry/' + CAMPAIGN
CONTROL = 'data/processed/e01_clerk2020_m2_control/' + CAMPAIGN
SOURCE_INDEX = 'data/processed/e01_clerk2020_m2_registry/source_sets/' + SOURCE_SET + '.successor-v2.local.json'

# Exact closed predecessor metadata, never raw inputs or arbitrary paths.
PREDECESSOR_CAMPAIGN = 'clerk2020_source_format_native_v1'
PREDECESSOR_REGISTRY = 'data/processed/e01_clerk2020_m2_registry/clerk2020_source_format_native_v1'
PREDECESSOR_RUN = 'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/runs/e01-12ab1efc0e59f97492e632663d650465'
PREDECESSOR_INDEX = 'data/processed/e01_clerk2020_m2_registry/source_sets/clerk2020_counts_2026_nominees_FORMAT_v1.local.json'
PREDECESSOR_FAILURE = 'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/failure-stderr.local.bin'
PREDECESSOR_STATE_SHA = 'b66e2ff9252b72269af956eb9b904191375e828ea831e00a30a41b35ea7680b6'
PREDECESSOR_REFS = {'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/failure-stderr.local.bin': {'bytes': 3738, 'path': 'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/failure-stderr.local.bin', 'sha256': '2f8fcd420e93e1f7ebbed23965fbcd79278d5589b8597a1c8c358a09d9ea0ff0'}, 'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/runs/e01-12ab1efc0e59f97492e632663d650465/child-0.local.json': {'bytes': 641, 'path': 'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/runs/e01-12ab1efc0e59f97492e632663d650465/child-0.local.json', 'sha256': 'f55332112475545b4c4cfa47def1716414ad121b7f069dc1f1fe32a8ed7c5571'}, 'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/runs/e01-12ab1efc0e59f97492e632663d650465/source-0-receipt.local.json': {'bytes': 214, 'path': 'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/runs/e01-12ab1efc0e59f97492e632663d650465/source-0-receipt.local.json', 'sha256': '01d727af466f2b0e388696b4e020e2c28c28d8ccc85a2ce06b78b4a99a0b6ca8'}, 'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/runs/e01-12ab1efc0e59f97492e632663d650465/terminal-failure.local.json': {'bytes': 210, 'path': 'data/processed/e01_clerk2020_m2_control/clerk2020_source_format_native_v1/runs/e01-12ab1efc0e59f97492e632663d650465/terminal-failure.local.json', 'sha256': '36272dead10ab5eb7186210ddf4bfe8e69291197ec1af7fc58f44c017a156a78'}, 'data/processed/e01_clerk2020_m2_registry/clerk2020_source_format_native_v1/EXEC-1.issued.local.json': {'bytes': 944, 'path': 'data/processed/e01_clerk2020_m2_registry/clerk2020_source_format_native_v1/EXEC-1.issued.local.json', 'sha256': '35c50f898f3d6eae1f9fa61b97f6d154ec997ae2694ff700f6f1c8388708ebeb'}, 'data/processed/e01_clerk2020_m2_registry/clerk2020_source_format_native_v1/EXEC-1.reservation.local.json': {'bytes': 1034, 'path': 'data/processed/e01_clerk2020_m2_registry/clerk2020_source_format_native_v1/EXEC-1.reservation.local.json', 'sha256': '26a614544f4bbf2eeca1446ca59312df4ed0cce8f93f7690deb275d89bbf0586'}, 'data/processed/e01_clerk2020_m2_registry/clerk2020_source_format_native_v1/anchor-2.local.json': {'bytes': 875, 'path': 'data/processed/e01_clerk2020_m2_registry/clerk2020_source_format_native_v1/anchor-2.local.json', 'sha256': '33d91c835ad96e4cbf73896f032bd38ee3558c81e3fefafe43da4a727ac6f876'}, 'data/processed/e01_clerk2020_m2_registry/source_sets/clerk2020_counts_2026_nominees_FORMAT_v1.local.json': {'bytes': 524, 'path': 'data/processed/e01_clerk2020_m2_registry/source_sets/clerk2020_counts_2026_nominees_FORMAT_v1.local.json', 'sha256': 'ee5c0dfe2ec03c36f0176bc5b50c8f3edebeb305a2014cb39574d2a711854ba8'}, 'reports/INDEPENDENT_AUDIT_E01_SOURCE_FORMAT_ACTUAL_EXEC_STOP_20261112.json': {'bytes': 19780, 'path': 'reports/INDEPENDENT_AUDIT_E01_SOURCE_FORMAT_ACTUAL_EXEC_STOP_20261112.json', 'sha256': 'f1e666f24a089f5238d4345701caa58a670622eb2fb8a6f08e7bb2d2b936a3b0'}}

# slot: relative-to-fixed-namespace, maximum, write category, phase partition
LAYOUT = {
 'source_index': (SOURCE_INDEX, 2048, 'control', 'BOOT'),
 'registration': (REGISTRY+'/registration.local.json',2048,'control','BOOT'),
 'boot_issued': (REGISTRY+'/BOOT-1.issued.local.json',2048,'control','BOOT'),
 'boot_reservation': (REGISTRY+'/BOOT-1.reservation.local.json',2048,'control','BOOT'),
 'genesis': (CONTROL+'/genesis.local.json',5120,'control','BOOT'),
 'anchor_initial': (REGISTRY+'/anchor-0.local.json',1536,'control','BOOT'),
 'boot_counters': (CONTROL+'/BOOT-counters.local.json',4096,'control','BOOT'),
 'boot_receipt': (CONTROL+'/BOOT-receipt.local.json',2048,'control','BOOT'),
 'anchor_boot': (REGISTRY+'/anchor-1.local.json',1536,'control','BOOT'),
 'prepared_metadata': (CONTROL+'/prepared-metadata.local.json',2048,'control','BOOT'),
 'runtime_stat_cache': (CONTROL+'/runtime-stat-cache.local.json',65536,'staging','staging'),
 'exec_reservation': (REGISTRY+'/EXEC-1.reservation.local.json',2048,'control','EXEC'),
 'exec_issued': (REGISTRY+'/EXEC-1.issued.local.json',2048,'control','EXEC'),
 'derived_context': (CONTROL+'/derived-context.local.json',2048,'control','EXEC'),
 'anchor_active': (REGISTRY+'/anchor-2.local.json',2048,'control','EXEC'),
 'source_receipt_0': (CONTROL+'/source-0-receipt.local.json',1024,'control','EXEC'),
 'source_receipt_1': (CONTROL+'/source-1-receipt.local.json',1024,'control','EXEC'),
 'child_ref_0': (CONTROL+'/child-0-ref.local.json',1024,'control','EXEC'),
 'child_ref_1': (CONTROL+'/child-1-ref.local.json',1024,'control','EXEC'),
 'manifest': (CONTROL+'/manifest.json',2048,'control','EXEC'),
 'environment': (CONTROL+'/environment.json',2048,'control','EXEC'),
 'summary': (CONTROL+'/summary.json',2048,'control','EXEC'),
 'payload_hashes': (CONTROL+'/inspection_payload_hashes.json',1024,'control','EXEC'),
 'inspection_commit': (CONTROL+'/inspection_commit.json',1024,'control','EXEC'),
 'counter_prefix': (CONTROL+'/counters.prefix.local.json',4096,'control','EXEC'),
 'normal_journal': (CONTROL+'/events.jsonl',48128,'control','journal'),
 'commit_event': (CONTROL+'/COMMIT-PREFIX.local.json',1024,'control','journal'),
 'private_projection': (CONTROL+'/inspection_projection.local.json',251904,'data','data'),
 'public_diagnostics': (CONTROL+'/inspection_diagnostics.json',8192,'data','data'),
 'private_provenance': (CONTROL+'/inspection_provenance.local.json',2048,'data','data'),
 'child_metadata_0': (CONTROL+'/child-0.local.json',8192,'staging','staging'),
 'child_metadata_1': (CONTROL+'/child-1.local.json',8192,'staging','staging'),
 'sealed_prefix': (CONTROL+'/normal-prefix.sealed.local.jsonl',49152,'staging','staging'),
 'prefix_anchor': (REGISTRY+'/anchor-3.local.json',2048,'control','terminal'),
 'seal': (CONTROL+'/seal.local.json',4096,'control','terminal'),
 'tail_verify': (CONTROL+'/tail-VERIFY.local.json',1024,'control','terminal'),
 'writer_ack': (CONTROL+'/writer-ACK.local.json',1024,'control','terminal'),
 'tail_ack': (CONTROL+'/tail-ACK.local.json',1024,'control','terminal'),
 'anchor_complete': (REGISTRY+'/anchor-4.local.json',2048,'control','terminal'),
 'tail_invalidate': (CONTROL+'/tail-INVALIDATE.local.json',1024,'control','terminal'),
 'anchor_invalid': (REGISTRY+'/anchor-5.local.json',2048,'control','terminal'),
 'terminal_failure': (CONTROL+'/terminal-failure.local.json',4096,'control','terminal'),
 'caller_observation': (CONTROL+'/caller-observation.local.json',1024,'control','terminal'),
 'private_stderr': (CONTROL+'/failure-stderr.local.bin',8192,'control','stderr'),
}
ANCHOR_SLOTS = ('anchor_initial','anchor_boot','anchor_active','prefix_anchor','anchor_complete','anchor_invalid')
ENGINEERING_CEILINGS = {'warmup_backend_attempts':8,'warmup_page_extractions':238,
    'total_backend_attempts':10,'total_page_extractions':357,'staging_write_bytes':131072}
PARTITIONS = {'code_integrity_read_bytes': {'BOOT':268435456,'EXEC':268435456},
              'metadata_read_bytes': {'BOOT':5242880,'EXEC':2883584,'DELIVERY':262144},
              'active_time_ms': {'BOOT':45000,'EXEC':75000},
              'cpu_ms': {'BOOT':10000,'EXEC':50000}}
PREFIX_BUDGETS = {
    'BOOT': {'metadata_read_bytes':5242880,'code_integrity_read_bytes':268435456,
             'source_read_attempts':0,'source_read_bytes':0,'source_jobs':0},
    'EXEC': {'metadata_read_bytes':2883584,'code_integrity_read_bytes':268435456,
             'source_read_attempts':2,'source_read_bytes':859913,'source_jobs':1},
}


def no_alias(path):
    require(type(path) is type(Path()) and path.is_absolute() and '..' not in path.parts)
    require(not any(p.is_symlink() for p in (path,*path.parents)))


def fsync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def file_identity(st):
    return (st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns)


class FixedStore:
    """One finite precharged layout. No slot names, namespaces or caps from disk."""
    def __init__(self, root, crash=None):
        self.root=Path(root).absolute();no_alias(self.root)
        self.crash=(lambda event: None) if crash is None else crash
        self.journal_frozen=False
        self.run_id=None
        self.read_meter=None
        # Maximum slot permissions intersect global/category ceilings once.
        totals={key:sum(v[1] for v in LAYOUT.values() if v[2]==key)
                for key in ['data','control','staging']}
        require(totals['data']<=262144 and totals['control']<=131072
                and totals['staging']<=131072 and sum(totals.values())<=524288)
        for partition,cap in [('BOOT',24576),('EXEC',24576),('journal',49152),
                              ('terminal',24576),('stderr',8192)]:
            require(sum(v[1] for v in LAYOUT.values() if v[3]==partition)<=cap)

    def path(self, slot):
        require(type(slot) is str and slot in LAYOUT)
        relative=LAYOUT[slot][0]
        if (relative.startswith(CONTROL+'/') and LAYOUT[slot][3]!='BOOT'
                and slot not in {'runtime_stat_cache','normal_journal','commit_event','private_stderr'}):
            require(type(self.run_id) is str)
            relative=CONTROL+'/runs/'+self.run_id+'/'+relative.rsplit('/',1)[1]
        path=self.root/relative;no_alias(path)
        return path

    def read_predecessor(self, ref):
        """Only pinned closed metadata; reservation before descriptor open."""
        require(type(ref) is dict and ref.get('path') in PREDECESSOR_REFS
                and ref==PREDECESSOR_REFS[ref['path']] and self.read_meter is not None)
        path=self.root/ref['path'];no_alias(path);before=path.stat()
        require(stat.S_ISREG(before.st_mode) and before.st_size==ref['bytes'])
        self.read_meter.reserve(ref['bytes']+1)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as stream:
            require(file_identity(os.fstat(stream.fileno()))==file_identity(before))
            raw=stream.read(ref['bytes']+1)
            require(file_identity(os.fstat(stream.fileno()))==file_identity(before))
        require(file_identity(path.stat())==file_identity(before)
                and len(raw)==ref['bytes'] and sha(raw)==ref['sha256'])
        self.read_meter.observe(len(raw));return raw

    @contextmanager
    def predecessor_lock(self):
        # Existing zero-byte predecessor lock; never create or rewrite it.
        path=self.root/PREDECESSOR_REGISTRY/'registrar.lock';no_alias(path)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            require(stat.S_ISREG(os.fstat(fd).st_mode) and os.fstat(fd).st_size==0)
            fcntl.flock(fd,fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)

    def bind_run(self, run_id):
        require(self.run_id is None and type(run_id) is str and run_id.startswith('e01-')
                and len(run_id)==36 and all(c in '0123456789abcdef' for c in run_id[4:]))
        self.run_id=run_id

    def exists(self, slot):
        return self.path(slot).exists()

    def create(self, slot, raw):
        require(type(slot) is str and slot in LAYOUT)
        require(type(raw) is bytes and len(raw)<=LAYOUT[slot][1])
        path=self.path(slot)
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);no_alias(path.parent)
        self.crash(slot+'.before')
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'wb') as stream:
                require(stream.write(raw)==len(raw));stream.flush();os.fsync(stream.fileno())
            fsync_dir(path.parent)
        finally:
            # O_EXCL file is never removed/reused, even if write/fsync failed.
            pass
        self.crash(slot+'.after')
        return {'path':str(path.relative_to(self.root)),'bytes':len(raw),'sha256':sha(raw)}

    def read(self, slot, allowance):
        path=self.path(slot);require(type(allowance) is int and allowance>0)
        before=path.stat();require(stat.S_ISREG(before.st_mode) and before.st_size+1<=allowance
                                  and before.st_size<=LAYOUT[slot][1])
        if self.read_meter is not None:self.read_meter.reserve(before.st_size+1)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as stream:
            require(file_identity(os.fstat(stream.fileno()))==file_identity(before))
            raw=stream.read(before.st_size+1)
            require(len(raw)==before.st_size and file_identity(os.fstat(stream.fileno()))==file_identity(before))
        require(file_identity(path.stat())==file_identity(before))
        if self.read_meter is not None:self.read_meter.observe(len(raw))
        return raw,len(raw)+1

    @contextmanager
    def lock(self):
        path=self.root/REGISTRY/'registrar.lock';no_alias(path)
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            require(os.fstat(fd).st_size==0)
            fcntl.flock(fd,fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)

    def append_event(self, raw):
        require(type(raw) is bytes and raw.endswith(b'\n') and len(raw)<=1024)
        require(not self.journal_frozen and not self.exists('commit_event') and (self.run_id is None or
                    (not self.exists('sealed_prefix') and not self.exists('seal'))))
        path=self.path('normal_journal')
        before=path.stat();require(before.st_size+len(raw)<=LAYOUT['normal_journal'][1])
        fd=os.open(path,os.O_APPEND|os.O_WRONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'ab') as stream:
            require(stream.write(raw)==len(raw));stream.flush();os.fsync(stream.fileno())
        fsync_dir(path.parent)
        self.crash('journal.after')


class FixedRegistrar:
    """Fixed BOOT1/EXEC1; source-set/root identity and immutable CAS anchors."""
    def __init__(self, store, source_set_sha256):
        require(type(store) is FixedStore and hex64(source_set_sha256))
        self.store=store;self.source_sha=source_set_sha256;self.boot_consumed_sha=None

    def binding(self):
        return {'campaign_id':CAMPAIGN,'source_set_id':SOURCE_SET,'source_set_sha256':self.source_sha,
                'anchor_id':ANCHOR,'repository_root_sha256':sha(str(self.store.root).encode()),
                'registry_namespace':REGISTRY,'control_namespace':CONTROL,
                'predecessor_campaign_id':PREDECESSOR_CAMPAIGN,
                'predecessor_source_index_sha256':PREDECESSOR_REFS[PREDECESSOR_INDEX]['sha256'],
                'predecessor_stop_sha256':PREDECESSOR_REFS[PREDECESSOR_FAILURE]['sha256'],
                'predecessor_terminal_state_sha256':PREDECESSOR_STATE_SHA,'recovery_ordinal':1}

    def consume(self, phase, issued_raw, expected):
        require(phase in {'BOOT','EXEC'} and type(issued_raw) is bytes and hex64(expected)
                and sha(issued_raw)==expected)
        issued=decode(issued_raw,8192)
        exact(issued,{'kind','phase','ordinal','binding','decision_sha256','expected_anchor_sha256','one_shot','prefix_budget'})
        require(issued['kind']=='CLERK_SOURCE_ISSUED_V2_1' and issued['phase']==phase
                and type(issued['ordinal']) is int and issued['ordinal']==1
                and issued['one_shot'] is True and canonical(issued['binding'])==canonical(self.binding())
                and canonical(issued['prefix_budget'])==canonical(PREFIX_BUDGETS[phase])
                and hex64(issued['decision_sha256'])
                and (issued['expected_anchor_sha256'] is None if phase=='BOOT'
                     else hex64(issued['expected_anchor_sha256'])))
        # Token memory validation precedes all byte reads. This create-once
        # external reservation consumes the ordinal before any existing state.
        # The issuer marker is durable first: even death before reservation
        # creation cannot make the same ordinal available to a new controller.
        self.store.create('boot_issued' if phase=='BOOT' else 'exec_issued',issued_raw)
        slot='boot_reservation' if phase=='BOOT' else 'exec_reservation'
        reservation={'kind':'CLERK_SOURCE_RESERVATION_V2_1','phase':phase,
                     'issued_sha256':expected,'binding':self.binding(),
                     'precharged_prefix':PREFIX_BUDGETS[phase],
                     'expected_anchor_sha256':issued['expected_anchor_sha256'],
                     'source_access_before_admission':False,'credit_restored':0,
                     'created_at_utc':datetime.now(timezone.utc).isoformat()}
        ref=self.store.create(slot,canonical(reservation))
        if phase=='BOOT':
            # Consumed is not adopted: no successor index/registration yet.
            self.boot_consumed_sha=expected
        else:
            with self.store.predecessor_lock(),self.store.lock():
                index,_=self.store.read('source_index',2049)
                require(canonical(decode(index))==canonical(self.binding()))
                current,_=self.current()
                require(current==issued['expected_anchor_sha256'])
        return issued,reservation,ref

    def adopt_successor(self, issued_sha256):
        """After durable BOOT metering, validate under lock before adoption."""
        require(hex64(issued_sha256) and self.boot_consumed_sha==issued_sha256
                and self.store.read_meter is not None)
        with self.store.predecessor_lock(),self.store.lock():
            require(not self.store.exists('source_index') and not self.store.exists('registration'))
            proof=self._verify_predecessor_locked()
            self.store.create('source_index',canonical(self.binding()))
            self.store.create('registration',canonical({'kind':'CLERK_SOURCE_REGISTRATION_V2_1',
                              **self.binding(),'boot_issued_sha256':issued_sha256}))
        self.boot_consumed_sha=None
        return proof

    def verify_predecessor(self):
        """Hash/read only the fixed stopped ancestor; never restarts its ledger."""
        with self.store.predecessor_lock():
            return self._verify_predecessor_locked()

    def _verify_predecessor_locked(self):
        bodies={p:self.store.read_predecessor(r) for p,r in PREDECESSOR_REFS.items()}
        index=decode(bodies[PREDECESSOR_INDEX],2048)
        require(index['campaign_id']==PREDECESSOR_CAMPAIGN
                and index['source_set_id']==SOURCE_SET and index['source_set_sha256']==self.source_sha
                and index['repository_root_sha256']==sha(str(self.store.root).encode()))
        failure=decode(bodies[PREDECESSOR_FAILURE],8192)
        require(failure['kind']=='CLERK_SOURCE_FAILED_OR_UNKNOWN_V1_2'
                and failure['phase']=='EXEC' and failure['no_retry'] is True
                and failure['source_format_accepted'] is False and failure['credit_restored']==0)
        state=failure['state'];require(sha(canonical(state))==PREDECESSOR_STATE_SHA)
        exact(state['legacy_axes'],CEILINGS);exact(state['engineering_axes'],ENGINEERING_CEILINGS)
        for axes,ceilings in [(state['legacy_axes'],CEILINGS),(state['engineering_axes'],ENGINEERING_CEILINGS)]:
            for key,axis in axes.items():
                require(axis['ceiling']==ceilings[key] and axis['charged']==axis['ceiling']
                        and axis['held']==axis['reserved']==0)
        # A terminal/second-source predecessor cannot become this stopped successor.
        absent=[PREDECESSOR_REGISTRY+'/anchor-'+str(i)+'.local.json' for i in (3,4,5)]
        absent += [PREDECESSOR_RUN+'/'+name for name in
            ('source-1-receipt.local.json','child-1.local.json','seal.local.json',
             'writer-ACK.local.json','caller-observation.local.json')]
        for relative in absent:
            path=self.store.root/relative;no_alias(path);require(not path.exists())
        return sha(canonical(PREDECESSOR_REFS))

    def current(self):
        previous=None;found=None;current=None;missing=False
        for slot in ANCHOR_SLOTS:
            if not self.store.exists(slot):
                missing=True
                continue
            require(not missing)
            raw,_=self.store.read(slot,2049);obj=decode(raw,2048)
            exact(obj,{'kind','binding','state','previous_anchor_sha256','payload'})
            require(obj['kind']=='CLERK_SOURCE_ANCHOR_V2_1'
                    and canonical(obj['binding'])==canonical(self.binding())
                    and obj['previous_anchor_sha256']==previous)
            require(type(obj['state']) is str and obj['state']==slot and type(obj['payload']) is dict)
            previous=sha(raw);current=previous;found=obj
        return current,found

    def cas(self, expected, slot, payload):
        require(slot in ANCHOR_SLOTS and type(payload) is dict)
        with self.store.lock():
            current,_=self.current();require(current==expected)
            occupied=[s for s in ANCHOR_SLOTS if self.store.exists(s)]
            require(len(occupied)<len(ANCHOR_SLOTS) and slot==ANCHOR_SLOTS[len(occupied)])
            obj={'kind':'CLERK_SOURCE_ANCHOR_V2_1','binding':self.binding(),'state':slot,
                 'previous_anchor_sha256':expected,'payload':payload}
            return self.store.create(slot,canonical(obj))


class PersistentCounters:
    """Original15 axes plus explicit warmup/total/staging engineering ceilings."""
    def __init__(self):
        self.legacy=Counters()
        self.legacy.transition('allocate',{k:v for k,v in CEILINGS.items()
            if k not in {'source_jobs','source_read_attempts','source_read_bytes','backend_attempts','page_extractions'}})
        self.engineering={k:(Axis(v).allocate(v) if k=='staging_write_bytes' else Axis(v))
                          for k,v in ENGINEERING_CEILINGS.items()}
        self.phase_reserved={phase:{axis:0 for axis in PARTITIONS} for phase in ['BOOT','EXEC','DELIVERY']}
        self.phase_observed={phase:{axis:0 for axis in PARTITIONS} for phase in ['BOOT','EXEC','DELIVERY']}

    def activate_source(self):
        names={'source_jobs','source_read_attempts','source_read_bytes','backend_attempts','page_extractions'}
        require(all(self.legacy._axes[k].held==self.legacy._axes[k].reserved==self.legacy._axes[k].charged==0
                    for k in names))
        engineering={k:v for k,v in ENGINEERING_CEILINGS.items() if k!='staging_write_bytes'}
        require(all(self.engineering[k].held==self.engineering[k].reserved==self.engineering[k].charged==0
                    for k in engineering))
        self.legacy.transition('allocate',{k:CEILINGS[k] for k in names})
        self.engineering.update({k:self.engineering[k].allocate(v) for k,v in engineering.items()})

    def reserve(self, amounts, phase):
        require(phase in self.phase_reserved and type(amounts) is dict)
        pending={k:v for k,v in amounts.items() if k in CEILINGS}
        engineering={k:v for k,v in amounts.items() if k in ENGINEERING_CEILINGS}
        require(len(pending)+len(engineering)==len(amounts))
        updates={}
        for axis,n in amounts.items():
            require(type(n) is int and n>=0)
            if axis in PARTITIONS:
                require(phase in PARTITIONS[axis] and self.phase_reserved[phase][axis]
                        +self.phase_observed[phase][axis]+n<=PARTITIONS[axis][phase])
            if axis in engineering:updates[axis]=self.engineering[axis].reserve(n)
        # All predicate checks complete before either set is published.
        self.legacy.transition('reserve',pending);self.engineering.update(updates)
        for axis,n in amounts.items():
            if axis in PARTITIONS:self.phase_reserved[phase][axis]+=n

    def settle(self, axis, reservation, actual, phase):
        require(phase in self.phase_reserved)
        if axis in PARTITIONS:require(reservation<=self.phase_reserved[phase][axis])
        if axis in CEILINGS:self.legacy.settle(axis,reservation,actual)
        else:
            require(axis in self.engineering)
            self.engineering[axis]=self.engineering[axis].settle(reservation,actual)
        if axis in PARTITIONS:
            self.phase_reserved[phase][axis]-=reservation
            self.phase_observed[phase][axis]+=reservation if actual is None else actual

    def precharge_writes(self):
        self.legacy.transition('precharge',{'owned_write_bytes':524288,
              'inspection_data_write_bytes':262144,'recorder_control_write_bytes':131072})
        self.engineering['staging_write_bytes']=self.engineering['staging_write_bytes'].precharge(131072)

    def stop_unknown(self):
        self.legacy.stop_unknown();self.engineering={k:v.stop_unknown() for k,v in self.engineering.items()}
        for phase,axes in self.phase_reserved.items():
            for axis,n in axes.items():
                self.phase_observed[phase][axis]+=n;axes[axis]=0

    def snapshot(self):
        return decode(canonical({'schema_version':1,'kind':'CLERK_SOURCE_COUNTERS_V2_1','legacy_axes':self.legacy.snapshot(),
                'engineering_axes':{k:v.record() for k,v in self.engineering.items()},
                'phase_reserved':self.phase_reserved,'phase_observed':self.phase_observed}))

    @classmethod
    def restore(cls, record):
        exact(record,{'schema_version','kind','legacy_axes','engineering_axes','phase_reserved','phase_observed'})
        require(record['schema_version']==1 and type(record['schema_version']) is int
                and record['kind']=='CLERK_SOURCE_COUNTERS_V2_1')
        out=cls();exact(record['legacy_axes'],CEILINGS);exact(record['engineering_axes'],ENGINEERING_CEILINGS)
        for group,ceilings in [('legacy_axes',CEILINGS),('engineering_axes',ENGINEERING_CEILINGS)]:
            restored={}
            for name,value in record[group].items():
                exact(value,{'ceiling','held','reserved','charged','observed','observed_known_sum','uncertain_charged'})
                require(value['ceiling']==ceilings[name])
                axis=Axis(**{k:v for k,v in value.items() if k!='observed'})
                require(axis.observed==value['observed']);restored[name]=axis
            if group=='legacy_axes':out.legacy._axes=restored
            else:out.engineering=restored
        for group in ['phase_reserved','phase_observed']:
            exact(record[group],{'BOOT','EXEC','DELIVERY'})
            for phase,values in record[group].items():
                exact(values,PARTITIONS)
                require(all(type(n) is int and n>=0 for n in values.values()))
            setattr(out,group,decode(canonical(record[group])))
        for axis,phases in PARTITIONS.items():
            for phase,cap in phases.items():
                require(out.phase_reserved[phase][axis]+out.phase_observed[phase][axis]<=cap)
            sums_reserved=sum(out.phase_reserved[p][axis] for p in out.phase_reserved)
            sums_observed=sum(out.phase_observed[p][axis] for p in out.phase_observed)
            legacy_axis=out.legacy._axes[axis]
            require(sums_reserved==legacy_axis.reserved
                    and legacy_axis.observed_known_sum<=sums_observed<=legacy_axis.charged)
        require(canonical(out.snapshot())==canonical(record))
        return out


EVENT_FIELDS={
 'BOOT_RESERVE':{'reservation_token_sha256'},
 'CODE_RUNTIME_RESERVE':{'effect_id'},
 'READ_SETTLE':{'effect_id','input_hash_verified'},
 'BOOT_COMMIT':{'verified_code_set_sha256','verified_runtime_manifest_sha256',
                'verified_metadata_set_sha256','counter_snapshot_sha256'},
 'EXEC_ADMISSION':{'context_sha256','reservation_token_sha256'},
 'SOURCE_RESERVE':{'source_id'},'SOURCE_SETTLE':{'source_id','source_sha256'},
 'BACKEND_RESERVE':{'source_id'},
 'BACKEND_SETTLE':{'source_id','outcome','observed_source_pages','observed_warmup_pages','runtime_manifest_sha256'},
 'DATA_WRITE_SLOT':{'slot_id'},'FAIL_STOP':{'safe_error_type'},
 'RESERVE_FINALIZATION':{'finalization_reservation_sha256'},
 'COMMIT_PREFIX':{'context_sha256','prefix_ledger_sha256','counter_snapshot_sha256',
                 'finalization_reservation_sha256'},
}
SOURCE_IDS=frozenset({'clerk2020_statistics','clerk2026_nominees'})


def counter_delta(counters, delta, phase):
    """Closed replayable transition; state is copied before any mutation."""
    require(type(counters) is PersistentCounters and phase in {'BOOT','EXEC','DELIVERY'})
    exact(delta,{'reserve','settle','stop_unknown','activate_source'})
    require(type(delta['reserve']) is dict and type(delta['settle']) is list
            and type(delta['stop_unknown']) is bool and type(delta['activate_source']) is bool
            and len(delta['settle'])<=20)
    if delta['stop_unknown']:
        require(not delta['reserve'] and not delta['settle'] and not delta['activate_source'])
    out=PersistentCounters.restore(counters.snapshot())
    if delta['activate_source']:
        require(phase=='EXEC');out.activate_source()
    if delta['reserve']:out.reserve(delta['reserve'],phase)
    seen=set()
    for row in delta['settle']:
        require(type(row) is list and len(row)==3 and type(row[0]) is str and row[0] not in seen)
        seen.add(row[0]);out.settle(row[0],row[1],row[2],phase)
    if delta['stop_unknown']:out.stop_unknown()
    return out


class NativeJournal:
    """At most48 closed events, durable reserve before effects, exact replay."""
    def __init__(self, store, genesis_sha256, counters, prefix=b''):
        require(type(store) is FixedStore and hex64(genesis_sha256)
                and type(counters) is PersistentCounters and type(prefix) is bytes and len(prefix)<=49152)
        self.store=store;self.genesis=genesis_sha256;self.head=genesis_sha256
        self.sequence=0;self.prefix=b'';self.frozen=False;self.last_phase='BOOT';self.counters=counters
        if prefix:
            for line in prefix.splitlines(keepends=True):
                require(line.endswith(b'\n') and len(line)<=1024)
                self._admit(line[:-1],persist=False)
            require(self.prefix==prefix)

    def _admit(self, raw, persist):
        require(not self.frozen and self.sequence<48 and type(raw) is bytes and len(raw)+1<=1024)
        obj=decode(raw,1024)
        exact(obj,{'schema_version','kind','campaign_id','phase','sequence','previous_event_sha256',
                   'event_type','payload','counter_delta','counter_before_sha256','counter_after_sha256'})
        require(type(obj['schema_version']) is int and obj['schema_version']==1
                and obj['kind']=='CLERK_SOURCE_EVENT_V2_1' and obj['campaign_id']==CAMPAIGN
                and obj['phase'] in {'BOOT','EXEC'} and (self.last_phase!='EXEC' or obj['phase']=='EXEC')
                and type(obj['sequence']) is int and obj['sequence']==self.sequence+1
                and obj['previous_event_sha256']==self.head and obj['event_type'] in EVENT_FIELDS)
        exact(obj['payload'],EVENT_FIELDS[obj['event_type']])
        require(not obj['counter_delta']['activate_source'] or obj['event_type']=='EXEC_ADMISSION')
        for key,value in obj['payload'].items():
            if key.endswith('_sha256'):require(hex64(value) or (value is None and key=='source_sha256'))
            elif key=='source_id':require(value in SOURCE_IDS and type(value) is str)
            elif key in {'observed_source_pages','observed_warmup_pages'}:
                require(value is None or (type(value) is int and 0<=value<=119))
            elif key=='input_hash_verified':require(value is None or type(value) is bool)
            elif key=='outcome':require(value in {'COMPLETE','FAILED','UNCERTAIN'})
            elif key=='slot_id':require(type(value) is str and value in LAYOUT)
            elif key=='effect_id':require(type(value) is str and value in {'boot_code','boot_metadata','hot_before','hot_after','exec_metadata'})
            elif key=='safe_error_type':require(value in {'INTEGRITY','IO_UNKNOWN','RESOURCE','WORKER_STOP','CONTRACT'})
            else:raise Refused()
        require(obj['counter_before_sha256']==sha(canonical(self.counters.snapshot())))
        after=counter_delta(self.counters,obj['counter_delta'],obj['phase'])
        require(obj['counter_after_sha256']==sha(canonical(after.snapshot())))
        require(len(self.prefix)+len(raw)+1<=49152)
        if persist:
            if obj['event_type']=='COMMIT_PREFIX':
                self.store.create('commit_event',raw+b'\n')
            else:self.store.append_event(raw+b'\n')
        self.prefix+=raw+b'\n';self.sequence+=1;self.head=sha(raw);self.counters=after
        self.last_phase=obj['phase'];self.frozen=obj['event_type']=='COMMIT_PREFIX'
        return obj

    def append(self, phase, event_type, payload, *, reserve=None, settle=None, stop_unknown=False, activate_source=False):
        delta={'reserve':{} if reserve is None else reserve,'settle':[] if settle is None else settle,
               'stop_unknown':stop_unknown,'activate_source':activate_source}
        before=sha(canonical(self.counters.snapshot()));after=counter_delta(self.counters,delta,phase)
        obj={'schema_version':1,'kind':'CLERK_SOURCE_EVENT_V2_1','campaign_id':CAMPAIGN,
             'phase':phase,'sequence':self.sequence+1,'previous_event_sha256':self.head,
             'event_type':event_type,'payload':payload,'counter_delta':delta,
             'counter_before_sha256':before,'counter_after_sha256':sha(canonical(after.snapshot()))}
        return self._admit(canonical(obj),persist=True)


LEDGER_MAP={'manifest.json':'manifest','environment.json':'environment','events.jsonl':'normal_journal',
 'summary.json':'summary','inspection_projection.local.json':'private_projection',
 'inspection_diagnostics.json':'public_diagnostics','inspection_provenance.local.json':'private_provenance',
 'inspection_payload_hashes.json':'payload_hashes','inspection_commit.json':'inspection_commit',
 'counters.prefix.local.json':'counter_prefix'}


class NativeTerminal:
    """Fixed seal/verification/ACK/anchor sequence, no source/backend callbacks."""
    def __init__(self, store, registrar, journal, context_sha256, resource_check=None):
        require(type(store) is FixedStore and type(registrar) is FixedRegistrar
                and type(journal) is NativeJournal and hex64(context_sha256) and store.run_id is not None)
        self.store=store;self.registrar=registrar;self.journal=journal;self.context=context_sha256
        self.used=False;self.verified_bytes=0
        self.check=(lambda:None) if resource_check is None else resource_check
        self.completed_result=None

    def finalize(self, payloads, bindings, prewritten=None):
        require(not self.used);self.used=True
        self.check()
        exact(payloads,set(LEDGER_MAP)-{'events.jsonl','counters.prefix.local.json'})
        exact(bindings,{'registration_sha256','static_spec_sha256','genesis_sha256',
                        'execution_decision_sha256','issued_envelope_sha256'})
        require(all(hex64(x) for x in bindings.values()) and all(type(b) is bytes for b in payloads.values()))
        prewritten={} if prewritten is None else prewritten
        require(type(prewritten) is dict and set(prewritten)<={'inspection_projection.local.json'})
        for name,raw in payloads.items():
            require(len(raw)<=LAYOUT[LEDGER_MAP[name]][1] and type(decode(raw).get('label')) is str
                    and decode(raw)['label'] in {'REAL_SOURCE_FORMAT_INSPECTION_ONLY','SOURCE_FORMAT_ONLY','MOCK'})
        # All future closing reads are charged unknown before any verification.
        reservation={'kind':'CLERK_SOURCE_FINALIZATION_RESERVATION_V2_1','context_sha256':self.context,
            'record_verification_read_bytes':2097152,'terminal_write_slots_bytes':24576,
            'no_source_backend_or_reseal':True}
        reservation_sha=sha(canonical(reservation))
        self.journal.append('EXEC','RESERVE_FINALIZATION',{'finalization_reservation_sha256':reservation_sha},
            reserve={'record_verification_read_bytes':2097152},
            settle=[['record_verification_read_bytes',2097152,None]])
        self.check()
        closing=ClosingReadMeter()
        self.store.read_meter=closing
        counter_snapshot={'label':'SOURCE_FORMAT_ONLY','context_sha256':self.context,
            'observed_through_sequence':self.journal.sequence,'journal_head_before_snapshot_sha256':self.journal.head,
            'state':self.journal.counters.snapshot()}
        owned=dict(payloads,**{'events.jsonl':self.journal.prefix,
                              'counters.prefix.local.json':canonical(counter_snapshot)})
        # Normal prefix is already durable. Ledger binds only the prefix through
        # RESERVE_FINALIZATION; final COMMIT is upstream of the separate seal.
        refs={}
        for name,raw in owned.items():
            self.check()
            slot=LEDGER_MAP[name]
            if slot=='normal_journal':
                refs[name]={'path':str(self.store.path(slot).relative_to(self.store.root)),
                            'bytes':len(raw),'sha256':sha(raw)}
            elif name in prewritten:
                ref=prewritten[name]
                require(ref=={'path':str(self.store.path(slot).relative_to(self.store.root)),
                              'bytes':len(raw),'sha256':sha(raw)})
                refs[name]=ref
            else:refs[name]=self.store.create(slot,raw)
            self.check()
        ledger={name:ref['sha256'] for name,ref in refs.items()}
        ledger_sha=sha(canonical(ledger));x_sha=refs['counters.prefix.local.json']['sha256']
        self.journal.append('EXEC','COMMIT_PREFIX',{'context_sha256':self.context,
            'prefix_ledger_sha256':ledger_sha,'counter_snapshot_sha256':x_sha,
            'finalization_reservation_sha256':reservation_sha})
        self.check()
        prefix_ref=self.store.create('sealed_prefix',self.journal.prefix)
        self.store.journal_frozen=True
        prior,_=self.registrar.current()
        prefix_anchor=self.registrar.cas(prior,'prefix_anchor',{'context_sha256':self.context,
            'sealed_prefix_sha256':prefix_ref['sha256'],'counter_snapshot_sha256':x_sha})
        self.check()
        seal={'schema_version':1,'kind':'CLERK_SOURCE_FINAL_SEAL_V2_1','context_sha256':self.context,
            **bindings,'prefix_ledger':ledger,'prefix_ledger_sha256':ledger_sha,
            'payload_sizes':{name:ref['bytes'] for name,ref in refs.items()},
            'sealed_prefix_ref':prefix_ref,'sealed_prefix_head_sha256':self.journal.head,
            'sealed_prefix_sequence':self.journal.sequence,'counter_snapshot_sha256':x_sha,
            'finalization_reservation_sha256':reservation_sha,'prefix_anchor_sha256':prefix_anchor['sha256'],
            'terminal_protocol':'VERIFY_ACK_CAS_NO_SOURCE_V2_1'}
        seal_ref=self.store.create('seal',canonical(seal))
        self.check()
        self.store.crash('verification.before')
        provenance=decode(owned['inspection_provenance.local.json'],2048)
        if provenance['label']!='MOCK':
            require(provenance['predecessor_refs_sha256']==self.registrar.verify_predecessor()
                    and provenance['predecessor_state_sha256']==PREDECESSOR_STATE_SHA)
            for ref in [provenance['stat_cache_ref'],provenance['boot_receipt_ref'],
                        provenance['prepared_ref'],*provenance['child_metadata_refs']]:
                exact(ref,{'slot','bytes','sha256'})
                require(ref['slot'] in {'runtime_stat_cache','boot_receipt','prepared_metadata',
                                        'child_metadata_0','child_metadata_1'}
                        and type(ref['bytes']) is int and ref['bytes']>=0 and hex64(ref['sha256']))
                self.check()
                body,charge=self.store.read(ref['slot'],2097152-closing.reserved)
                require(len(body)==ref['bytes'] and sha(body)==ref['sha256'])
        for name,ref in refs.items():
            self.check()
            slot=LEDGER_MAP[name]
            raw,charge=self.store.read(slot,2097152-self.verified_bytes)
            self.verified_bytes+=charge
            expected=owned[name]
            require(raw==expected)
            require(len(raw)==ref['bytes'] and sha(raw)==ref['sha256'])
        commit_bytes=self.journal.prefix[len(owned['events.jsonl']):]
        for slot,expected in [('commit_event',commit_bytes),
                             ('sealed_prefix',self.journal.prefix),('seal',canonical(seal))]:
            raw,charge=self.store.read(slot,2097152-self.verified_bytes);self.verified_bytes+=charge
            require(raw==expected)
            self.check()
        require(closing.reserved<=2097152)
        self.verified_bytes=closing.observed
        self.store.crash('verification.after')
        tail1={'kind':'CLERK_SOURCE_TAIL_V2_1','index':1,'event_type':'VERIFY_OK',
               'context_sha256':self.context,'seal_sha256':seal_ref['sha256'],
               'previous_sha256':seal_ref['sha256'],'observed_before_this_event':self.verified_bytes}
        t1=self.store.create('tail_verify',canonical(tail1))
        self.check()
        ack={'kind':'CLERK_SOURCE_WRITER_ACK_V2_1','context_sha256':self.context,
             'seal_sha256':seal_ref['sha256'],'verified_tail_event_sha256':t1['sha256'],
             'counter_snapshot_sha256':x_sha,'terminal_reservation_sha256':reservation_sha}
        ack_ref=self.store.create('writer_ack',canonical(ack))
        self.check()
        t2=self.store.create('tail_ack',canonical({'kind':'CLERK_SOURCE_TAIL_V2_1','index':2,
            'event_type':'ACK_COMMITTED','context_sha256':self.context,'seal_sha256':seal_ref['sha256'],
            'previous_sha256':t1['sha256'],'writer_ack_sha256':ack_ref['sha256'],
            'observed_before_this_event':self.verified_bytes}))
        self.check()
        completed=self.registrar.cas(prefix_anchor['sha256'],'anchor_complete',{'context_sha256':self.context,
            'seal_sha256':seal_ref['sha256'],'tail_head_sha256':t2['sha256'],'writer_ack_sha256':ack_ref['sha256']})
        require(closing.reserved<=2097152)
        self.completed_result={'label':'SOURCE_FORMAT_ONLY','status':'WRITER_COMMITTED_AWAITING_CALLER_OBSERVATION',
                'seal_ref':seal_ref,'writer_ack_ref':ack_ref,'completed_anchor_ref':completed,
                'source_counts_or_features_adopted':False,'model_calls':0,'cost_usd':0}
        self.check()
        return self.completed_result

    def invalidate_committed(self):
        """One prepaid third tail/anchor, never rewriting seal, prefix or ACK."""
        require(self.completed_result is not None)
        result=self.completed_result
        previous,_=self.store.read('tail_ack',1025)
        invalid=self.store.create('tail_invalidate',canonical({
            'kind':'CLERK_SOURCE_TAIL_V2_1','index':3,'event_type':'INVALIDATE',
            'context_sha256':self.context,'seal_sha256':result['seal_ref']['sha256'],
            'previous_sha256':sha(previous),'error_type':'RESOURCE_OR_CALLER_UNKNOWN'}))
        return self.registrar.cas(result['completed_anchor_ref']['sha256'],'anchor_invalid',{
            'context_sha256':self.context,'seal_sha256':result['seal_ref']['sha256'],
            'tail_head_sha256':invalid['sha256'],'writer_ack_sha256':result['writer_ack_ref']['sha256']})


class ClosingReadMeter:
    def __init__(self):self.reserved=0;self.observed=0
    def reserve(self,amount):
        require(type(amount) is int and amount>=0 and self.reserved+amount<=2097152)
        self.reserved+=amount
    def observe(self,amount):
        require(type(amount) is int and amount>=0 and self.observed+amount<=self.reserved)
        self.observed+=amount


class ProjectionStream:
    """One create-once private output, fsynced at each of two source boundaries.

    Only bounded already-projected JSON is accepted. No raw PDF bytes, path
    selection, replacement or reopen exists. Partial results remain unsealed.
    """
    def __init__(self,store):
        require(type(store) is FixedStore and store.run_id is not None and store.exists('anchor_active'))
        self.store=store;self.path=store.path('private_projection');self.count=0;self.closed=False
        self.used=0;self.hash=__import__('hashlib').sha256()
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        self.stream=os.fdopen(fd,'wb')
        self._write(b'{"candidate_or_vote_records_parsed":0,"documents":[')

    def _write(self,raw):
        require(not self.closed and type(raw) is bytes and self.used+len(raw)<=251904)
        require(self.stream.write(raw)==len(raw));self.used+=len(raw);self.hash.update(raw)
        self.stream.flush();os.fsync(self.stream.fileno());fsync_dir(self.path.parent)

    def add(self,raw,source_id):
        require(self.count<2 and source_id==('clerk2020_statistics','clerk2026_nominees')[self.count])
        require(type(raw) is bytes and len(raw)<=(167936 if self.count==0 else 79872))
        obj=decode(raw,167936)
        require(obj['source_id']==source_id and obj['candidate_or_vote_records_parsed']==0
                and obj['printed_dates_or_roles_adopted'] is False)
        self._write((b',' if self.count else b'')+raw);self.count+=1

    def finish(self):
        require(not self.closed)
        try:self._write(b'],"label":"REAL_SOURCE_FORMAT_INSPECTION_ONLY"}')
        finally:self.closed=True;self.stream.close()
        return {'path':str(self.path.relative_to(self.store.root)),'bytes':self.used,'sha256':self.hash.hexdigest()}
