"""One unauthenticated HEAD of the already selected immutable wheel; no body read."""
import hashlib,http.client,json,os,ssl,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/processed/e01_cffi_freshness_diagnostic_20261115_01'
URL='https://files.pythonhosted.org/packages/54/7d/16e5a096677b5e313ca80cd5e5170efa3ea44624a82bb111925522da64b1/cffi-2.1.1-cp312-cp312-macosx_11_0_arm64.whl'
def save(name,value):
 raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode();assert len(raw)<=8192
 with (BASE/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def main():
 BASE.mkdir(exist_ok=False);start=time.monotonic()
 save('STARTED.json',{'HEAD_max':1,'body_reads':0,'GET_max':0,'retries':0,'HTTP_timeout_seconds':15,'url':URL,'time_utc':datetime.now(timezone.utc).isoformat()})
 connection=http.client.HTTPSConnection('files.pythonhosted.org',443,timeout=15,context=ssl.create_default_context());response=None
 result={'HEAD_attempts':1,'application_body_bytes_read':0,'GET_attempts':0,'model_calls':0,'cost_USD':0,'url':URL}
 try:
  connection.request('HEAD',URL.split('files.pythonhosted.org',1)[1],headers={'User-Agent':'SyntheticSocietyLab-header-diagnostic/1','Accept-Encoding':'identity'})
  response=connection.getresponse()
  result.update(status='HEAD_METADATA_ONLY_COMPLETE',HTTP_status=response.status,headers={name:response.getheader(name) for name in ['Date','Age','Cache-Control','Expires','Last-Modified','Content-Type','Content-Length','Content-Encoding','Location','ETag']})
 except Exception as error:result.update(status='STOPPED_NO_RETRY',error_type=type(error).__name__)
 finally:
  if response is not None:response.close()
  connection.close()
 result.update(elapsed_seconds=time.monotonic()-start,observed_at_utc=datetime.now(timezone.utc).isoformat())
 ref=save('TERMINAL.json',result);print(json.dumps({**result,'terminal_ref':ref},sort_keys=True))
if __name__=='__main__':main()
