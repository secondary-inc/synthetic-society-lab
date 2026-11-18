"""One bounded metadata-only review. Never invokes the actual reader."""
from pathlib import Path
import sys,os,json,hashlib,ast,time,resource,signal,types,inspect,importlib.metadata
resource.setrlimit(resource.RLIMIT_CPU,(30,30));signal.alarm(60)
root=Path.cwd();out=root/'reports/evidence_independent_e01_saved_json_particular_20261118';t=time.monotonic();reads=0;checks={};refs=[];errors=[]
packetpath=root/'data/processed/e01_saved_json_one_call_packets/packet_20261118_01.json';profilepath=root/'data/processed/e01_saved_json_actual_preparation_20261118_01/runtime-profile.local.json';manifestpath=profilepath.parent/'manifest.candidate.json'
allow={packetpath,profilepath,manifestpath,root/'src/civiclab/e01/saved_json_job_ledger_v1.py',root/'src/civiclab/e01/saved_json_entry_v1.py',root/'scripts/run_e01_saved_json_entry_v1_20261117.py',root/'reports/INDEPENDENT_AUDIT_E01_SAVED_JSON_ENTRY_V1_1_20261117.json',root/'reports/INDEPENDENT_AUDIT_E01_SAVED_JSON_READ_FAMILY_FIX_V1_1_20261117.json'}
stdlib=Path(os.__file__).resolve().parent
# Block actual data bodies and all network/process execution, retaining stdlib loads.
def audit(event,args):
 if event.startswith(('socket.','ctypes.')) or event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','os.exec'):raise PermissionError('EXTERNAL_FORBIDDEN')
 if event=='import' and (args[0]=='civiclab' or args[0].startswith('civiclab.')):raise PermissionError('ACTUAL_PROJECT_IMPORT_FORBIDDEN')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(os.fsdecode(args[0])).absolute();flags=args[2]
  if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
   if p.parent!=out:raise PermissionError('WRITE_SCOPE')
  elif p.is_relative_to(root) and p not in allow:raise PermissionError('ACTUAL_BODY_READ_FORBIDDEN')
sys.addaudithook(audit)
def read(p):
 global reads
 b=p.read_bytes();reads+=len(b);assert reads<=67108864;return b
def digest(b):return hashlib.sha256(b).hexdigest()
def can(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def check(k,v):checks[k]=bool(v)
def reference(p,b):return {'path':str(p.relative_to(root)) if p.is_relative_to(root) else str(p),'bytes':len(b),'sha256':digest(b)}
try:
 raw=read(packetpath);p=json.loads(raw);check('exact_packet_pin',len(raw)==8238 and digest(raw)=='745f6531ebf35e8fbd47595558a21fd8755334ef3b64cb070011d741220e7e74')
 check('packet_mode0600_owner',packetpath.stat().st_mode&0o777==0o600 and packetpath.stat().st_uid==os.getuid())
 check('exact_scope',p['scope_id']=='e01-saved-json-0f14f1bcd9364b49a88ebd4271954a02');check('window',p['issued_at']==1794979854 and p['expires_at']==1794983454 and p['issued_at']<=time.time()<=p['expires_at'])
 check('armed_only_root',p['armed'] is True and p['issued_by']=='ROOT_REVIEWED_ONE_CALL')
 refs.append(reference(packetpath,raw))
 controls={}
 for group in ('code_refs','review_refs'):
  for key,r in p[group].items():
   path=root/r['path'];allow.add(path);b=read(path);check('pin:'+r['path'],len(b)==r['bytes'] and digest(b)==r['sha256']);refs.append(reference(path,b));controls[r['path']]=b
 mraw=read(manifestpath);m=json.loads(mraw);check('manifest_candidate_identical',m==p['manifest']);check('manifest_candidate_pin',len(mraw)==6713 and digest(mraw)=='a9322441fb8e52790df29d3df343e527bafea4dab52681c03f823d5bf2cedd1f')
 profile_raw=read(profilepath);profile=json.loads(profile_raw);check('selected_runtime_profile_pin',len(profile_raw)==1786 and digest(profile_raw)=='c4708c0dc62ffc2bde49c58838fbafb5955819dd24523b1cdb6a7fe9fd08bea7')
 check('packet_runtime_sha',p['runtime_sha256']==digest(profile_raw))
 corepath='src/civiclab/e01/saved_json_job_ledger_v1.py';helperpath='src/civiclab/e01/saved_json_entry_v1.py';launcherpath='scripts/run_e01_saved_json_entry_v1_20261117.py'
 check('accepted_core_exact',digest(controls[corepath])=='684eb291c1d462afe07d994b7c940290fa26e5fb89907212e75dc69085562010')
 check('accepted_helper_exact',digest(controls[helperpath])=='50700d8c5d288a626731e1bd230f9718ddac2e1cdacc2110127cad0979ac9677')
 check('accepted_launcher_exact',digest(controls[launcherpath])=='cece6007ac3c43fae3b16d67a0e9a4d8c7c2e1d64207e330c869e1eedc148115')
 C=types.ModuleType('independent_metadata_core');C.__file__=str(root/corepath);exec(compile(controls[corepath],C.__file__,'exec'),C.__dict__)
 E=types.ModuleType('independent_metadata_entry');E.__file__=str(root/helperpath);exec(compile(controls[helperpath],E.__file__,'exec'),E.__dict__)
 E.packet(raw,digest(raw),False,time.time);check('closed_packet_validator',True)
 C.validate_actual_metadata(m);check('actual_metadata_validator',True)
 runtime=C.RuntimePin();check('selected_native_runtime_matches',runtime.sha256==p['runtime_sha256'])
 # RuntimePin hashes selected trusted files; charge metadata-described sizes as well.
 profile_info={'type':type(profile).__name__,'keys':list(profile) if isinstance(profile,dict) else None}
 check('no_preexisting_civiclab_modules',not any(n=='civiclab' or n.startswith('civiclab.') for n in sys.modules))
 check('exact_limits',p['limits']=={'wall_seconds':60,'work_seconds':57,'cleanup_seconds':2,'finalization_seconds':1,'CPU_seconds':30,'saved_JSON_bytes':8388608,'project_source_bytes':1048576,'write_bytes':2097152,'public_bytes':131072,'console_bytes':16384,'reader_calls':1,'retries':0})
 control=root/E.CONTROL/p['scope_id'];check('scope_not_consumed',not control.exists())
 check('independent_review_passes',all(json.loads(controls[r['path']])['status']=='PASS' for r in p['review_refs'].values()))
 # Metadata contains private references, never their sixteen payload bodies.
 metadata_summary={'manifest_keys':list(m),'runtime_profile':profile_info,'limits':p['limits'],'code_ref_count':len(p['code_refs']),'review_ref_count':len(p['review_refs'])}
except BaseException as error:
 errors.append(type(error).__name__);metadata_summary={'failure_stage_check_count':len(checks)}
result={'kind':'INDEPENDENT_E01_PARTICULAR_METADATA_REVIEW','status':'PASS' if checks and all(checks.values()) and not errors else 'BLOCKED','checks':checks,'errors_types_only':errors,'refs':refs,'metadata':metadata_summary,'explicit_read_bytes':reads,'runtime_rehash_bytes_additional':'Selected RuntimePin origin files; bounded by fixed accepted profile. No whole-startup IO certificate.','wall_seconds':time.monotonic()-t,'actual16_body_reads':0,'actual_reader_calls':0,'subprocesses':0,'network_calls':0,'model_calls':0,'cost_usd':0}
(out/'PARTICULAR_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,sort_keys=True))
