"""One read-only normal-verifier capture after consumed slot46; no inference."""
from pathlib import Path
import os,json,sqlite3,signal,resource,hashlib,time,sys
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from civiclab.common import canonical_bytes,canonical_hash
from civiclab.e02.wrapper_crossmodel_slot46_v2_owner import Slot46OwnerV2,STATE,ANCHOR,_jsonable
resource.setrlimit(resource.RLIMIT_CPU,(119,120));signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(120)
started=time.monotonic();cap=ROOT/'data/processed/e02_wrapper_slot46_v2_20261118_actual_01/closed-capture-03';cap.mkdir(mode=0o700)
def save(name,raw):
 p=cap/name;p.parent.mkdir(mode=0o700,exist_ok=True)
 fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw)
def obj(name,v):
 def serial(x):
  if isinstance(x,datetime):return x.isoformat()
  raise TypeError(type(x).__name__)
 save(name,json.dumps(_jsonable(v),sort_keys=True,separators=(",",":"),default=serial).encode())
summary={'kind':'E02_SLOT46_ACTUAL_CLOSED_OUTCOME_V1','capture_scope':'closed-capture-03','previous_capture':'capture02 normal replay completed; datetime serialization failed before copying; preserved separately','model_inference':False,'owner_mutations':False,'retry_allowed':False}
try:
 owner=Slot46OwnerV2()
 with owner._lock(),sqlite3.connect(owner.db_path.as_uri()+'?mode=ro',uri=True) as db:
  state,head=owner._verify(db)
  obj('verified-state.local.json',state);obj('verified-head.local.json',head)
  dest=cap/'owner-v4.local.sqlite';dest.touch(mode=0o600,exist_ok=False)
  with sqlite3.connect(dest) as target:db.backup(target)
  for path in (owner.guard,owner.anchor,owner.registration):save(path.name,path.read_bytes())
  journal=owner._journal('e02-wrapper-slot46-v2-20261118-01')
  names=[]
  for path in sorted(journal.iterdir()):
   if not path.is_file() or path.is_symlink() or path.stat().st_size>2_000_000:raise RuntimeError('journal_file_bound')
   save('journal/'+path.name,path.read_bytes());names.append(path.name)
  b=state[STATE]
  summary.update(status='VERIFIED_NORMAL_REPLAY',event_count=head['sequence']+1,rows=len(state['rows']),unfinished_holds=state['unfinished'],total_exposure_microusd=state['consumed']['total'],prior_rows_unchanged=canonical_hash(state['rows'])==ANCHOR['rows'],branch_counts=b['counts'],branch_closed=b['closed'],new_receipt=b['receipt'],new_witness=b['witness'],journal_names=names,post_intent_recorded=b['counts']['POST'],new_reservation=b['receipt'] is not None)
  events=db.execute('SELECT data FROM events WHERE sequence>=1189 ORDER BY sequence').fetchall()
  summary['new_event_kinds']=[json.loads(x[0])['body']['kind'] for x in events]
except Exception as e:
 summary.update(status='CAPTURE_FAILED',error_type=type(e).__name__)
 # Fixed source validation diagnostics only; never keys or data values.
 msg=str(e)
 summary['safe_error_code']=msg if len(msg)<=160 and all(c.isalnum() or c in ' _-/+.,:;()' for c in msg) else 'OMITTED'
summary['elapsed_seconds']=time.monotonic()-started
obj('summary.local.json',summary)
refs=[{'name':str(p.relative_to(cap)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(cap.rglob('*')) if p.is_file()]
obj('manifest.local.json',{'files':refs})
public=ROOT/'reports/E02_SLOT46_ACTUAL_CLOSED_OUTCOME_V1_1_20261118.json'
with public.open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary));signal.alarm(0)
