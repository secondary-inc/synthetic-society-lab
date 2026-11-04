"""Candidate finite read-only original-owner metadata collector; actual denied.

Does not open credentials, environment files, sockets, survey/source data or
create a control artifact. The eventual reviewed workflow must authorize actual
read-only access separately and keep its snapshot private.
"""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import stat

from .common import canonical_hash, sha256_file
from .model import ExecutionBlocked
from .production_owner_v4 import ProductionOwnerV4, production_owner_directory
from .additional_compatibility_owner_v1 import OLD_RECEIPT


def collect_actual(*args,**kwargs):
    raise ExecutionBlocked('read-only actual metadata collector unreleased')


def _collect_authored_snapshot():
    """Private candidate for fake OS homes; no path/owner/recovery override."""
    directory=production_owner_directory()
    paths={'registration':directory.parent/'openrouter-v4-bootstrap.local.json',
           'guard':directory/'owner-v4-guard.local.json',
           'anchor':directory/'owner-v4-head.local.json',
           'database':directory/'owner-v4.local.sqlite'}
    for parent in (directory,*directory.parents):
        if parent.is_symlink():raise ExecutionBlocked('symlink in fixed owner namespace refused')
    before={}
    for kind,path in paths.items():
        if path.is_symlink():raise ExecutionBlocked('symlink control file refused')
        info=path.stat()
        if not stat.S_ISREG(info.st_mode) or not 0<info.st_size<=(2097152 if kind=='database' else 65536):
            raise ExecutionBlocked('owner metadata exceeds finite regular-file bounds')
        before[kind]={'bytes':info.st_size,'sha256':sha256_file(path)}
    # Validate fixed original constructor paths/identity after finite size checks.
    owner=ProductionOwnerV4()
    with owner._lock():
        with closing(sqlite3.connect(owner.db_path.as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
            db.execute('PRAGMA query_only=ON')
            count=db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
            charge_count=db.execute('SELECT COUNT(*) FROM charges').fetchone()[0]
            max_event=db.execute('SELECT MAX(length(CAST(data AS BLOB))) FROM events').fetchone()[0]
            if not 1<=count<=9996 or charge_count!=1 or max_event is None or max_event>65536:
                raise ExecutionBlocked('original prefix does not fit one-shot snapshot envelope')
            state,head=owner._verify(db)
            old=state['rows'].get(OLD_RECEIPT)
            if (old is None or state['unfinished']!=1 or old['status']!='UNCERTAIN'
                or old['reserved']!=340 or old['charged']!=340
                or state['statistics_claims']
                or any(old[k] is not None for k in ('generation_id','observed_cost','output_hash','billing','checkpoint_hash'))
                or state['consumed']!={'total':340,'modules':{'E01':0,'E02':340},
                    'dispatches':1,'module_dispatches':{'E01':0,'E02':1}}):
                raise ExecutionBlocked('exact retained original uncertainty required')
            raw_events=db.execute('SELECT data FROM events ORDER BY sequence').fetchall()
            history=[json.loads(data) for data, in raw_events]
            result={'kind':'ORIGINAL_OWNER_READONLY_SNAPSHOT_V1','header':owner.header,'head':head,
                'active_approval_hash':state['active'],'history_hash':canonical_hash(history),
                'predecessor_receipt':OLD_RECEIPT,'predecessor_row':old,
                'predecessor_row_hash':canonical_hash(old),'predecessor_context_hash':canonical_hash(old['context']),
                'statistics_claims_hash':canonical_hash([]),'consumed':state['consumed'],
                'unfinished':1,'event_count':count,'files':before,
                'credential_access':False,'HTTP_requests':0,'owner_writes':False,
                'scope':'Readonly original history snapshot; no reconciliation or dispatch authority'}
        after={k:{'bytes':p.stat().st_size,'sha256':sha256_file(p)} for k,p in paths.items()}
        if after!=before:raise ExecutionBlocked('owner changed during snapshot; no replacement snapshot')
    return result
