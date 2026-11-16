"""Read-only audit of the exact historical actual technical acquisition; no dispatch."""
from pathlib import Path
import hashlib,json,os,stat,sys,importlib.util,io,zipfile
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
ROOT=Path.cwd();BASE=ROOT/'data/processed/e01_pypdf701_build_v1/acquisition-v1_4-20261116'
read_total=0

def read(path,limit=16777216):
 global read_total
 assert not any(p.is_symlink() for p in (path,*path.parents))
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as f:
  s=os.fstat(f.fileno());assert stat.S_ISREG(s.st_mode) and s.st_size<=limit
  read_total+=s.st_size;assert read_total<=33554432
  raw=f.read(limit+1);assert len(raw)==s.st_size
 return raw

def digest(raw):return hashlib.sha256(raw).hexdigest()
def guard(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.fork','os.kill','os.killpg','ctypes.dlopen'}:raise AssertionError('NO_NETWORK_PROCESS_NATIVE_SIGNAL')
sys.addaudithook(guard)
code=ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1_4.py';assert digest(read(code))=='7b749585397e6a8f609bd809f5f1a54e5124077a8d90cc6ae0c5530c3616f749'
spec=importlib.util.spec_from_file_location('reviewed_collector',code);w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);c=w.c
methods_raw=read(ROOT/w.METHODS);assert digest(methods_raw)=='c5e158306d145e0fe646268103e5e0e1716b475c1f23eea93cdb2fcd7b65fd4f';methods=json.loads(methods_raw)
terminal_raw=read(BASE/'TERMINAL.json');terminal=json.loads(terminal_raw);bodies={}
for ref in terminal['artifacts']:
 path=ref['path'];assert not Path(path).is_absolute() and '..' not in Path(path).parts and path not in bodies
 raw=read(BASE/path);assert len(raw)==ref['bytes'] and digest(raw)==ref['sha256'];bodies[path]=raw
assert {str(p.relative_to(BASE)) for p in BASE.rglob('*') if p.is_file()}==set(bodies)|{'TERMINAL.json'}
start=json.loads(bodies['STARTED.json']);lock=json.loads(bodies['hashlock.json']);receipt=json.loads(bodies['fresh-metadata-receipt.json'])
assert digest(bodies['hashlock.json'])=='05d2713fcd22848bb52132af3ab5d6370a3e3927334cd56b40366f9e25ae0d73'
assert start['code_sha256']==digest(read(code)) and start['methods_sha256']==digest(methods_raw)==lock['methods_sha256']
assert terminal['status']=='ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION' and terminal['reason'] is None and terminal['current_request'] is None
assert start['prior_cumulative']==terminal['prior_cumulative']==methods['prior_cumulative']
a,b,d=map(datetime.fromisoformat,(start['time_utc'],terminal['last_observed_utc'],terminal['absolute_operation_deadline_utc']))
assert a<=b<d and 0<(d-a).total_seconds()<=120
now=datetime.now(timezone.utc)
collector=w.Collector(ROOT,methods,None,operation_deadline_utc=now+timedelta(seconds=120))
selected,cache,historical_bytes=collector.predecessor() # Read-only real ancestry, no scope writes/fetch/run.
assert historical_bytes==start['historical_read_bytes_charged']
assert cache==bodies['wheels/'+c.PYPDF['filename']]
events=[json.loads(bodies['events/'+str(i)+'.json']) for i in range(21,55)]
assert [e['sequence'] for e in events]==list(range(21,55))
reserved=[e for e in events if e['kind']=='REQUEST_RESERVED'];headers=[e for e in events if e['kind']=='RAW_HTTP_HEADER_DECISION'];responses=[e for e in events if e['kind']=='RESPONSE_RECORDED']
assert len(reserved)==len(headers)==len(responses)==11
assert [e['url'] for e in reserved]==[e['url'] for e in headers]==[e['url'] for e in responses]
assert [e['url'] for e in reserved[:7]]==[f'https://pypi.org/pypi/{n}/{v}/json' for n,v in c.VERSIONS.items()]+[c.API,c.PROVENANCE]
assert [e['url'] for e in reserved[7:]]==[x['url'] for x in lock['wheels'][1:]]
for i,(request,header,response) in enumerate(zip(reserved,headers,responses),1):
 assert request['budget']['attempts']['GET']==10+i and response['budget']['attempts']['GET']==10+i
 assert request['budget']['outstanding_body_hold']>0 and response['budget']['outstanding_body_hold']==0
 assert header['decision']['status']=='ACCEPTED'
 h=header['raw_headers'];assert abs((parsedate_to_datetime(h['date'])-a).total_seconds())<=300
 if i<=7:
  assert header['decision']['policy']=='ORIGINAL_METADATA_AGE_3600'
 else:
  assert header['decision']['policy']=='FIXED_IMMUTABLE_ARTIFACT_UNIQUE_MAX_AGE'
  assert header['raw_cache_control_field_values']==['max-age=365000000, immutable, public']
  assert 3600<int(h['age'])<365000000
 if h['content-length'] is not None:assert int(h['content-length'])==len(bodies[response['ref']['path']])
 assert response['ref']==next(r for r in terminal['artifacts'] if r['path']==response['ref']['path'])
assert receipt['fresh_metadata_GETs']==7 and receipt['metadata_GETs_cumulative']==15
assert receipt['fresh_metadata_refs']==[e['ref'] for e in responses[:7]]
metadata_bytes=sum(len(v) for k,v in bodies.items() if k.startswith('metadata/'))
companions=sum(x['size'] for x in lock['wheels'][1:]);budget=terminal['budget']
assert budget=={'attempts':{'GET':21,'metadata_GET':15,'wheel_GET':6},'body_bytes_charged':{'metadata':948771+metadata_bytes,'wheel':33554432+companions},'outstanding_body_hold':0}
assert terminal['cumulative_owned_write_bytes_charged_before_terminal']==3041964+sum(map(len,bodies.values()))
checks=[];entries=inflated=0
for i,item in enumerate(lock['wheels']):
 raw=bodies[item['artifact_ref']['path']];assert len(raw)==item['size'] and digest(raw)==item['sha256']
 fresh=c.select_wheel(item['name'],json.loads(bodies[item['metadata_ref']['path']]))
 assert all(fresh[k]==item[k]==selected[i][k] for k in ('name','version','filename','url','size','sha256'))
 inspection=c.inspect_wheel(raw,item['name'],item['filename']);assert inspection==item['inspection']
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  infos=z.infolist();assert len(infos)==inspection['entries'] and sum(i.file_size for i in infos)==inspection['uncompressed_bytes']
 entries+=inspection['entries'];inflated+=inspection['uncompressed_bytes']
 checks.append({'name':item['name'],'bytes':len(raw),'sha256':digest(raw),'entries':inspection['entries'],'uncompressed_bytes':inspection['uncompressed_bytes']})
assessment=w.n.assess_advisories([json.loads(bodies['metadata/advisories-current.json'])]);assessment['fresh_current_response']=True
assert c.packed(assessment)==bodies['advisory-assessment.json'] and digest(bodies['advisory-assessment.json'])==lock['advisory_assessment_sha256']
assert assessment['status']=='NO_APPLICABLE_ISSUE_IN_CAPTURED_MAINTAINER_PAGES'
assert len(json.loads(bodies['metadata/advisories-current.json']))<100
assert c.provenance_binding(json.loads(bodies['metadata/pypdf-provenance.json']))==lock['provenance_scope']
assert lock['ready_for_install'] is False and lock['qualification_or_source_authority'] is False
print(json.dumps({'status':'PASS_ACTUAL_TECHNICAL_ACQUISITION_ONLY','read_bytes_charged_direct':read_total,'historical_ref_bytes_plus_one':historical_bytes,'new_scope_files':len(bodies)+1,'new_scope_bytes':sum(map(len,bodies.values()))+len(terminal_raw),'events':34,'new_GETs':11,'budget':budget,'wheels':checks,'ZIP_entries':entries,'ZIP_uncompressed_bytes':inflated,'captured_logical_seconds':(b-a).total_seconds(),'terminal_sha256':digest(terminal_raw),'hashlock_sha256':digest(bodies['hashlock.json']),'model_calls':0,'cost_USD':0,'actual_network_by_reviewer':0,'package_imports_extraction_installation':False},sort_keys=True))
