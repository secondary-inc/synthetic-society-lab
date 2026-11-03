"""Distinct prospective elapsed allocation; no native resource allowance added."""
from datetime import datetime,timezone
import math
import platform
from pathlib import Path
import subprocess
import time
from ..common import canonical_hash
from .national_budget import Blocked

KIND='E02_N2B_PROSPECTIVE_WINDOW_GRANT_V1_2'
FIELDS={'kind','realm','issuer_role','issued','effective_at_unix','effective_at_utc','expires_at_unix','expires_at_utc','methods_review_sha256','policy_sha256','source_sha256','root','old_history_sha256','capacity_sha256','preflight_sha256','nonce'}

def tick():
 try:
  if platform.system()=='Darwin':boot=subprocess.run(['/usr/sbin/sysctl','-n','kern.boottime'],capture_output=True,text=True,check=True,timeout=2).stdout.strip()
  elif platform.system()=='Linux':boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
  else:raise Blocked('unsupported clock platform')
  if not boot:raise Blocked('boot clock unavailable')
  return {'wall':time.time(),'mono':time.monotonic(),'boot':boot}
 except Exception:raise Blocked('boot/clock unavailable') from None

def stamp(x):
 if type(x) is not dict or set(x)!={'wall','mono','boot'} or type(x['boot']) is not str or not x['boot'] or len(x['boot'])>1024 or any(type(x[k]) not in (int,float) or not math.isfinite(x[k]) or x[k]<0 for k in ('wall','mono')):raise Blocked('closed finite boot clock')
 return x

def elapsed(first,last):
 stamp(first);stamp(last)
 if first['boot']!=last['boot']:raise Blocked('bootstrap continuity changed')
 dw=last['wall']-first['wall'];dm=last['mono']-first['mono']
 if min(dw,dm)<0 or abs(dw-dm)>2:raise Blocked('clock rollback/discontinuity')
 return max(dw,dm)

def utc(t):
 if type(t) not in (int,float) or not math.isfinite(t) or t<0:raise Blocked('finite UTC timestamp')
 try:return datetime.fromtimestamp(t,timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
 except (ValueError,OverflowError,OSError):raise Blocked('UTC timestamp range') from None

def validate(g,*,now,realm,root,policy_sha,source_sha,history,capacity,methods_review_sha,preflight_sha):
 if type(g) is not dict or set(g)!=FIELDS or g['kind']!=KIND or g['realm']!=realm or g['issuer_role']!='lead' or type(g['nonce']) is not str or len(g['nonce'])!=32 or any(c not in '0123456789abcdef' for c in g['nonce']):raise Blocked('closed prospective grant identity/type')
 issued=stamp(g['issued']);stamp(now)
 if g['effective_at_unix']!=issued['wall'] or type(g['effective_at_unix']) not in (int,float) or type(g['expires_at_unix']) not in (int,float) or not math.isfinite(g['expires_at_unix']) or g['expires_at_unix']-g['effective_at_unix']!=10800:raise Blocked('new dated10800 elapsed allocation only')
 if g['effective_at_utc']!=utc(g['effective_at_unix']) or g['expires_at_utc']!=utc(g['expires_at_unix']):raise Blocked('UTC/Unix grant mismatch')
 if g['root']!=str(root) or g['policy_sha256']!=policy_sha or g['source_sha256']!=source_sha or g['old_history_sha256']!=canonical_hash(history) or g['capacity_sha256']!=canonical_hash(capacity) or g['methods_review_sha256']!=methods_review_sha or g['preflight_sha256']!=preflight_sha:raise Blocked('prospective grant exact binding')
 elapsed(issued,now)
 if not g['effective_at_unix']<=now['wall']<g['expires_at_unix']:raise Blocked('prospective window future/expired')
 return g

def admission_deadline(g,created):
 elapsed(g['issued'],created)
 if created['wall']<g['effective_at_unix'] or created['wall']+1500>g['expires_at_unix']:raise Blocked('complete1500 sequence cannot fit prospective window')
 return min(created['wall']+1500,g['expires_at_unix'])

def history_observations(g,history,created,observed):
 elapsed(created,observed)
 wy=history['WY_original_deadline_unix'];dc=history['N2a_DC_original_t0']['wall']+10800;origin=history['WY_original_t0']['wall']
 return {'original_WY_genesis':history['WY_original_t0'],'original_WY_deadline':wy,'original_DC_genesis':history['N2a_DC_original_t0'],'original_DC_deadline':dc,'new_issued':g['issued'],'effective_at_unix':g['effective_at_unix'],'effective_at_utc':g['effective_at_utc'],'expires_at_unix':g['expires_at_unix'],'expires_at_utc':g['expires_at_utc'],'added_elapsed_window_seconds':10800,'historical_gap_after_WY_seconds':max(0,g['effective_at_unix']-wy),'extension_relative_WY_seconds':g['expires_at_unix']-wy,'positive_extension_relative_DC_seconds':max(0,g['expires_at_unix']-dc),'cumulative_elapsed_at_new_expiry_seconds':g['expires_at_unix']-origin,'cumulative_elapsed_at_observation_seconds':observed['wall']-origin,'sequence_created':created,'observed':observed,'sequence_elapsed_seconds':elapsed(created,observed),'pauses_count':True,'native_processing_added':0}
