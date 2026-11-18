"""One additional unauthenticated catalog-A diagnostic, never a model request."""
from pathlib import Path
import os,sys,json,hashlib,signal,resource,time
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from civiclab.production_admission_v4 import _fetch_public_catalog
from civiclab.e02.crossmodel_price_v1 import semantic
from civiclab.common import canonical_hash
SCOPE=ROOT/'data/processed/e02_catalog_diagnostic_20261118_01';SCOPE.mkdir(mode=0o700)
resource.setrlimit(resource.RLIMIT_CPU,(59,60));signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(60)
plan={'kind':'E02_ONE_CATALOG_A_DIAGNOSTIC','reason':'Consumed slot46 stopped at CATALOG_A, no retained raw metadata; diagnose without inference or altering owner','catalog_GET_max':1,'model_POST_max':0,'statistics_GET_max':0,'wall_seconds':60,'CPU_seconds':60,'raw_bytes_max':2000000,'retries':0,'credential_reads':0,'owner_mutations':0,'conservative_parent_catalog_before':13,'conservative_parent_catalog_after_max':14,'parent_catalog_ceiling':16,'monetary_caps_unchanged':True}
with (SCOPE/'claim.local.json').open('x') as f:json.dump(plan,f)
with (ROOT/'reports/E02_CATALOG_DIAGNOSTIC_PLAN_20261118.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
q=json.loads((ROOT/'data/processed/e02_wrapper_slot46_v2_20261118_actual_01/packet.json').read_bytes());rel=q['price_release']['A']
start=time.monotonic();result={'kind':'E02_ONE_CATALOG_A_DIAGNOSTIC_RESULT','observed_at_utc':datetime.now(timezone.utc).isoformat(),'fetch_invocations':0,'model_POSTs':0,'retry_allowed':False}
try:
 result['fetch_invocations']=1
 raw,meta=_fetch_public_catalog(rel['terms']['model'])
 (SCOPE/'catalog.raw.json').write_bytes(raw);(SCOPE/'metadata.local.json').write_text(json.dumps(meta))
 result.update(fetch_status='RETURNED_BOUNDED_CATALOG',raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest())
 checked=semantic(raw,rel['interpretation'])
 result.update(semantic_status='PARSED',actual_semantic_sha256=canonical_hash(checked),historical_semantic_sha256=rel['terms']['metadata_semantic_hash'],semantic_unchanged=canonical_hash(checked)==rel['terms']['metadata_semantic_hash'])
 # Public endpoint terms only; no requests, respondents, keys or publisher content.
 (SCOPE/'semantic.local.json').write_text(json.dumps(checked,indent=2))
except Exception as e:
 result.update(status='DIAGNOSTIC_REFUSAL',error_type=type(e).__name__)
 msg=str(e);result['safe_code']=msg if len(msg)<=160 and all(c.isalnum() or c in ' _-/+.,:;()' for c in msg) else 'OMITTED'
result['elapsed_seconds']=time.monotonic()-start
with (ROOT/'reports/E02_CATALOG_DIAGNOSTIC_RESULT_20261118.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result));signal.alarm(0)
