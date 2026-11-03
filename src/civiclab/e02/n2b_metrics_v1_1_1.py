"""Bounded, explicitly scoped comparator metrics; no performance claims."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time
from .national_budget import Blocked

ACTIVE=ContextVar('N2B_RESOURCE_ACTIVITY',default=None)

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

class Meter:
 def __init__(self):self.lock=threading.Lock();self.values={'content_read_bytes':0,'content_read_calls':0,'content_write_bytes':0,'content_write_calls':0,'explicit_size_probes':0,'read_errors':0,'bookkeeping_seconds_sum':0.0}
 def add(self,k,v):
  with self.lock:self.values[k]+=v
 def snapshot(self):
  with self.lock:return dict(self.values)

@contextmanager
def activity(meter):
 token=ACTIVE.set(meter)
 try:yield
 finally:ACTIVE.reset(token)

def add(k,v):
 m=ACTIVE.get()
 if m is not None:m.add(k,v)

@contextmanager
def bookkeeping():
 t=time.perf_counter()
 try:yield
 finally:add('bookkeeping_seconds_sum',time.perf_counter()-t)

def read_stream(stream,limit):
 with bookkeeping():
  try:b=stream.read(limit)
  except BaseException:add('read_errors',1);raise
  add('content_read_calls',1);add('content_read_bytes',len(b));return b

def read_bytes(p,limit=8*1024**2+1):
 with Path(p).open('rb') as f:return read_stream(f,limit)
def read_text(p):return read_bytes(p).decode('utf-8')
def written(n):add('content_write_bytes',n);add('content_write_calls',1)
def stat_size(p):add('explicit_size_probes',1);return Path(p).stat().st_size

def current_rss():
 # One own-process observation. ps RSS is KiB on supported Darwin/Linux.
 try:
  r=subprocess.run(['ps','-o','rss=','-p',str(os.getpid())],capture_output=True,text=True,check=True,timeout=2)
  text=r.stdout.strip()
  if not text.isascii() or not text.isdigit():raise ValueError('RSS format')
  return int(text)*1024
 except Exception:raise Blocked('current RSS observation unavailable') from None

class VariantFailure(Blocked):
 def __init__(self,evidence):super().__init__('bounded matched variant failed; retain evidence');self.evidence=evidence

class Sampler:
 def __init__(self,meter,guard,limit):
  if type(limit) is not int or not 0<limit<=536870912:raise Blocked('fixed RSS bound')
  self.meter=meter;self.guard=guard;self.limit=limit;self.stop=threading.Event();self.samples=[];self.error=None;self.started=time.perf_counter();self.thread=None
 def sample(self):
  if len(self.samples)>=4096:raise Blocked('bounded RSS sample count')
  value=current_rss();self.samples.append((time.perf_counter()-self.started,value))
  if value>self.limit:raise Blocked('sampled current RSS cap')
  self.guard()
 def loop(self):
  with activity(self.meter):
   while not self.stop.wait(0.1):
    try:
     with bookkeeping():self.sample()
    except BaseException as e:self.error=type(e).__name__;return
 def start(self):
  self.sample();self.thread=threading.Thread(target=self.loop,daemon=True,name='N2b-RSS-sampler');self.thread.start()
 def finish(self):
  self.stop.set()
  if self.thread is not None:
   self.thread.join(3)
   if self.thread.is_alive():raise Blocked('sampler shutdown unknown')
  self.sample()
  if self.error is not None:raise Blocked('sampled guard or RSS failure')


def evaluate(name,fn,*,input_bytes,input_sha256,guard=lambda:None,max_rss=536870912):
 meter=Meter();start=time.perf_counter();sampler=Sampler(meter,guard,max_rss);evaluation_seconds=None;result=None;profile=None;error=None
 with activity(meter):
  try:
   with bookkeeping():sampler.start()
   t=time.perf_counter()
   try:result=fn()
   finally:evaluation_seconds=time.perf_counter()-t
   with bookkeeping():
    matrix,uncertainty,summaries=result;blobs=matrix.blobs();ub=canonical(uncertainty);sb=canonical(summaries)
    profile={'primitive_bytes':sum(len(b) for b in blobs.values()),'uncertainty_bytes':len(ub),'summary_bytes':len(sb),'primitive_hashes':{k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()},'uncertainty_sha256':hashlib.sha256(ub).hexdigest(),'summaries_sha256':hashlib.sha256(sb).hexdigest()}
  except BaseException as e:error=type(e).__name__
  finally:
   try:
    with bookkeeping():sampler.finish()
   except BaseException as e:error=error or type(e).__name__
 record={'variant':name,'status':'FAILED' if error else 'MEASURED_ENGINEERING_ONLY','error_type':error,'evaluation_started':evaluation_seconds is not None,'evaluation_seconds':evaluation_seconds,'sampler_shutdown_confirmed':sampler.thread is None or not sampler.thread.is_alive(),'total_scope_seconds':time.perf_counter()-start,'sampled_current_rss_peak_bytes':max((v for _,v in sampler.samples),default=None),'rss_samples':len(sampler.samples),'rss_sample_offsets_seconds':[round(t,6) for t,_ in sampler.samples],'rss_measurement':'OWN_PROCESS_PS_RSS_KIB_TO_BYTES_SAMPLED_NOT_EXCLUSIVE_VARIANT_ALLOCATION','target_poll_seconds':0.1,'sampling_limit_bytes':max_rss,'input_logical_bytes':input_bytes,'input_sha256':input_sha256,'output_logical_bytes':None if profile is None else sum(profile[k] for k in ('primitive_bytes','uncertainty_bytes','summary_bytes')),'output_profile':profile,'bookkeeping':meter.snapshot(),'physical_payload_file_read_bytes':0,'physical_payload_file_write_bytes':0,'scope':'IN_MEMORY_MERGE_AND_MANDATORY_PLUS_DECLARED_MEASUREMENT_AND_GUARD_METADATA_IO_NOT_FULL_SYSCALL_OR_WIRE_TRACE'}
 if error:raise VariantFailure(record)
 return result,record


def environment():return {'python':sys.version.split()[0],'platform':platform.system(),'machine':platform.machine(),'process_id':os.getpid(),'cache_policy':'SAME_PROCESS_UNFLUSHED_IDENTICAL_IMMUTABLE_INPUTS_REDECODED_PER_VARIANT_PRIOR_RESULT_RETAINED_FOR_EQUALITY','sampling_overhead':'INCLUDED_IN_SCOPE; background sample costs overlap evaluation, no subtract/add speed estimate'}
