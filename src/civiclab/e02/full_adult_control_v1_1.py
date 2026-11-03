"""Separate F fixture controls. Read-only N1 primitives are NOT F approval."""
from pathlib import Path
import json
import os
import shutil
from ..common import atomic_json,canonical_hash,sha256_file
from .national_budget import Ledger,Blocked


def fixture_root(root,c,*,create=False):
    if c.get('authored_fixture') is not True or c.get('engine_scope')!='F_AUTHORED_V1_1':raise Blocked('F actual authority absent')
    root=Path(root).resolve()
    if str(root)!=c.get('fixture_root'):raise Blocked('fixture root binding')
    marker=root/'.AUTHORED_F_ONLY'
    if create:
        root.mkdir(parents=True,exist_ok=True)
        if marker.exists():raise Blocked('fixture root already exists; no reset')
        marker.write_text('MOCK_F_AUTHORED_V1_1\n')
    if not marker.is_file() or marker.read_text()!='MOCK_F_AUTHORED_V1_1\n':raise Blocked('authored root marker required')
    return root


class Policy:
    def __init__(self,c):self.c=c;self.root=fixture_root(c['fixture_root'],c)
    def category(self,p):
        relative=p.relative_to(self.root);parts=relative.parts;name=p.name
        if parts[0]=='scratch':return 'scratch'
        if parts[0] in ('PRIMARY','REPLAY'):
            if name.endswith('_results_v1_1.jsonl'):return parts[0]+':query'
            if name in ('selectors.json','coefficients.json','query_plan.json','execution_manifest.json','plan_refusal.json','query_result_index.json'):return parts[0]+':catalog'
            return parts[0]+':base'
        if name=='query_receipts_v1_1.jsonl':return 'receipts'
        if name.endswith(('.zip','.quarantine','.partial')):return 'raw'
        return 'core'
    def check(self,category=None,extra=0,*,initial=False):
        q=self.c['F_storage'];usage={};paths=[]
        for p in self.root.rglob('*'):
            if p.is_symlink():raise Blocked('symlink in metered F workspace')
            if p.is_file():paths.append(p);key=self.category(p);usage[key]=usage.get(key,0)+p.stat().st_size
        if extra<0:raise Blocked('negative projected storage')
        if category:usage[category]=usage.get(category,0)+extra
        free=shutil.disk_usage(self.root).free
        if free<max(q['free'],q['initial_free'] if initial else 0)+extra:raise Blocked('F free reserve/atomic headroom')
        for name,cap in q['caps'].items():
            if usage.get(name,0)>cap:raise Blocked('F artifact partition '+name)
        data=sum(v for k,v in usage.items() if k.startswith(('PRIMARY:','REPLAY:')))
        if data>q['data_both'] or usage.get('receipts',0)+usage.get('core',0)>q['logs'] or data+usage.get('receipts',0)+usage.get('core',0)>q['all_artifacts']:raise Blocked('F cumulative artifacts/logs')
        return usage
    def write(self,path,blob,*,category=None):
        path=Path(path).resolve()
        if not path.is_relative_to(self.root) or path.exists():raise Blocked('immutable F artifact/path')
        self.check(category or self.category(path),len(blob));path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as out:out.write(blob);out.flush();os.fsync(out.fileno())
        return sha256_file(path)
    def json(self,path,value):return self.write(path,(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())


class FResourceLedger(Ledger):
    """New F design/hash namespace; inherited C acceptance never enables this scope."""
    def __init__(self,c):
        self.policy=Policy(c);self.policy.check(initial=not (self.policy.root/'sources/ledger.json').exists())
        super().__init__(self.policy.root/'sources',c)
    def _save(self,s,event,**fields):
        self.policy.check('core',len(json.dumps(s,indent=2).encode())+4096)
        return super()._save(s,event,**fields)
