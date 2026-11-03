"""Exact original prior subpartitions plus whole old/new accounting; read-only."""
from pathlib import Path
import stat
from .national_budget import Blocked
from .n2b_metrics_v1_1_1 import stat_size

ROOTS={
 'data/processed/e02_F_wy_private/conditional-actual-v1-20261103-01':'WY_RUNTIME',
 'data/processed/e02_F_wy_private_bootstrap/conditional-actual-v1-20261103-01':'WY_BOOTSTRAP',
 'data/processed/e02_n2a_registry_v1':'N2A_CORE',
 'data/processed/e02_n2a_core_v1':'N2A_CORE',
 'data/raw/e02_n2a_sources_v1':'N2A_RAW',
 'data/raw/e02_pums_wy':'RAW',
 'data/raw/e02_pums_metadata':'RAW',
}
CATALOG={'selectors.json','coefficients.json','query_plan.json','execution_manifest.json','plan_refusal.json','query_result_index.json'}

def policy(native_storage,n2a_limits):
 return {'roots':ROOTS,'required_history_directories':list(ROOTS)+[next(r for r,v in ROOTS.items() if v=='WY_RUNTIME')+'/'+q for q in ('PRIMARY','REPLAY','ledger')]+['data/raw/e02_n2a_sources_v1/11'],'native_storage':native_storage,'n2a_limits':n2a_limits,'rules':'ORIGINAL_SUBCAPS_REQUIRED_DIRECTORY_PRESENCE_V1_1_1','test_only_presence_waiver':False,'optional_new_partitions':'Only fixed new stage directories/scratch may be absent before use; new output/registry may be absent only before ownership.'}

def directory(p,root,*,required):
 """No-follow directory type for every existing ancestor and target."""
 cursor=root
 for part in p.relative_to(root).parts:
  cursor=cursor/part
  try:mode=cursor.lstat().st_mode
  except FileNotFoundError:
   if required:raise Blocked('required directory/history missing') from None
   return False
  except OSError:raise Blocked('owned directory ancestry unavailable') from None
  if not stat.S_ISDIR(mode):raise Blocked('owned root/ancestor must be directory, no file/link/special entry')
 return True


def _ancestors(p,root):return directory(p,root,required=True)

def _name(name):
 while any(name.endswith(s) for s in ('.atomic','.tmp','.part','.partial')):name=name.rsplit('.',1)[0]
 return name

def validate_subcaps(u,p):
 n=p['n2a_limits'];w=p['native_storage'];caps=w['caps'];over=[]
 for k,cap in [('N2A:raw',n['raw_retained_bytes']),('N2A:core',n['core_metadata_bytes']),('N2A:scratch',n['scratch_bytes']),('N2A:total',n['all_stage_retained_bytes']),('WY:core',caps['core']),('WY:receipts',caps['receipts']),('WY:scratch',caps['scratch']),('WY:raw',caps['raw']),('WY:logs',w['logs']),('WY:data_both',w['data_both']),('WY:all_artifacts',w['all_artifacts'])]:
  if u.get(k,0)>cap:over.append(k)
 for phase in ('PRIMARY','REPLAY'):
  # Original actual outer puts every phase file in :base, even query/catalog.
  for suffix in ('base','catalog','query'):
   if u.get('WY:'+phase+':'+suffix,0)>caps[phase+':'+suffix]:over.append('WY:'+phase+':'+suffix)
 if over:raise Blocked('prior original subcaps: '+','.join(sorted(over)))
 return True

def scan(c):
 p=c.config['prior_storage_policy'];u={};tot={'old_data':0,'old_core':0,'old_raw':0,'old_scratch':0};seen=set()
 def add(k,n):u[k]=u.get(k,0)+n
 # Mandatory in both realms. Fixtures create declared authored directory roots;
 # TEST_ONLY does not make a missing equivalent-production path look empty.
 for relative in p['required_history_directories']:directory(c.root/relative,c.root,required=True)
 for relative,role in p['roots'].items():
  root=c.root/relative;seen.add(relative);directory(root,c.root,required=True)
  for f in root.rglob('*'):
   if f.is_symlink():raise Blocked('prior owned symlink')
   if not f.is_file():
    if not f.is_dir():raise Blocked('unexpected prior special entry')
    continue
   n=stat_size(f);rel=f.relative_to(root);first=rel.parts[0];name=_name(f.name)
   if role.startswith('N2A'):
    kind='scratch' if first=='scratch' else 'raw' if role=='N2A_RAW' else 'core';add('N2A:'+kind,n)
    tot['old_'+kind]+=n
   elif role=='RAW':tot['old_raw']+=n
   elif role in ('WY_RUNTIME','WY_BOOTSTRAP'):
    if first=='scratch':add('WY:scratch',n);tot['old_scratch']+=n
    elif role=='WY_RUNTIME' and first in ('PRIMARY','REPLAY'):
     phase=first;add('WY:'+phase+':base',n);tot['old_data']+=n
     if name.endswith('_results_v1_1.jsonl') or any(q in ('query','queries') for q in rel.parts[1:-1]):add('WY:'+phase+':query',n)
     elif name in CATALOG or any(q in ('catalog','catalogs') for q in rel.parts[1:-1]):add('WY:'+phase+':catalog',n)
    else:
     add('WY:core',n);tot['old_core']+=n
     if name=='query_receipts_v1_1.jsonl' or first=='receipts':add('WY:receipts',n)
     if first=='inputs':add('WY:raw',n)
   else:raise Blocked('closed prior role')
 # Legacy TEST_ONLY generic inventory remains an additional whole-cap view.
 for relative,kind in c.config['prior_directories'].items():
  if relative in seen:continue
  if c.realm.kind=='PRODUCTION':raise Blocked('unexpected prior inventory root')
  root=c.root/relative;directory(root,c.root,required=True)
  for f in root.rglob('*'):
   if f.is_symlink():raise Blocked('extra prior symlink')
   if not f.is_file() and not f.is_dir():raise Blocked('unexpected fallback special entry')
   if f.is_file():
    if kind not in ('raw','core','data'):raise Blocked('extra prior kind')
    tot['old_'+kind]+=stat_size(f)
 u['N2A:total']=sum(u.get('N2A:'+k,0) for k in ('raw','core','scratch'))
 u['WY:data_both']=sum(u.get('WY:'+q+':base',0) for q in ('PRIMARY','REPLAY'))
 u['WY:logs']=u.get('WY:core',0)
 u['WY:all_artifacts']=u['WY:data_both']+u['WY:logs']+u.get('WY:scratch',0)
 validate_subcaps(u,p)
 return {**tot,'prior_subpartitions':u}
