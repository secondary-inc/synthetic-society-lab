"""Fresh PREP-02 finite operation: two public audit reads (metadata+copy). Never imports civiclab or invokes runtime."""
from pathlib import Path
import copy,datetime,hashlib,json,os,stat,subprocess,sys
root=Path.cwd().absolute()
result_path=root/'reports/E01_AL_OFFICE_CONTEXT_V1_1_PREPARATION_RESULT_02.json'
step='INITIAL_PUBLIC_METADATA';created=[];counts={'original_transcript_byte_hash_verifications':0,'public_literal_audit_copy_source_reads':0,'private_files_created':0}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf8')
def public_ref(ref,limit=1048576):
 p=root/ref['path'];assert not str(ref['path']).startswith('data/')
 with p.open('rb') as stream:raw=stream.read(limit+1)
 assert len(raw)<=limit and digest(raw)==ref['sha256']
 if 'bytes' in ref:assert len(raw)==ref['bytes']
 return raw

def path_guard(p):
 assert p.is_relative_to(root)
 for q in [*reversed(p.parents),p]:
  try:s=q.lstat()
  except FileNotFoundError:continue
  assert not stat.S_ISLNK(s.st_mode),'SYMLINK_PATH_REFUSED'

def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def write_once(p,raw):
 path_guard(p)
 p.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 created.append({'path':str(p.relative_to(root)),'sha256':digest(raw),'bytes':len(raw)})
 try:
  offset=0
  while offset<len(raw):
   n=os.write(fd,raw[offset:]);assert n>0;offset+=n
  os.fsync(fd);assert os.fstat(fd).st_size==len(raw)
 finally:os.close(fd)
 counts['private_files_created']+=1

try:
 assert not result_path.exists(),'EXISTING_PUBLIC_RESULT_STOP'
 auth_path='reports/E01_AL_OFFICE_CONTEXT_V1_1_PREPARATION_AUTHORIZATION_02.json'
 auth_raw=(root/auth_path).read_bytes();auth=json.loads(auth_raw)
 assert auth['decision_id']=='E01_AL_V11_PREPARE_CORRECTED_METADATA_20261103_02'
 assert auth['kind']=='LEAD_FINITE_METADATA_PREPARATION_DECISION' and auth['scope']=='METADATA_PREPARATION_ONLY_NOT_SOURCE_ACCESS_OR_EXECUTION'
 assert auth['approved'] is True and auth['automatic_retry_or_reset'] is False and auth['create_once_no_overwrite'] is True
 assert auth['maximum_preparation_files']==6 and auth['model_calls_or_spend']==0
 plan_raw=public_ref(auth['plan_ref']);plan=json.loads(plan_raw)
 assert auth['plan_ref']['sha256']=='31a5e60292fa4091ca13c3f13b6d13f007dccfc02eb3267596a96a3069fc4593'
 recipe_raw=public_ref(auth['recipe_review_ref']);recipe=json.loads(recipe_raw)
 assert auth['recipe_review_ref']['sha256']=='f9e8652c096848281986f309ecc70763b8a7ae4c3deab7775efb76fbdd9cfa43'
 assert recipe['status']=='PASS_METHODS_METADATA_ONLY_AL_V1_1_ACTUAL_RUNTIME_RECIPE' and recipe['permission_issued_by_this_review'] is False
 code_raw=public_ref(auth['code_review_ref']);review=json.loads(code_raw)
 assert auth['code_review_ref']['sha256']=='793eb1494b64fc056d55c8ea62678b39fd8e3787c834db70748a25372836ead5' and len(code_raw)==16411
 assert review['status']=='PASS_BOUNDED_AL_OFFICE_CONTEXT_V1_1_CODE_PRIVACY' and review['scope']=='AUTHORED_CODE_PRIVACY_ONLY_NOT_ACTUAL_SOURCE_RELEASE'
 cfg=json.loads(public_ref(auth['candidate_ref']));assert cfg['metadata_pins'] and all(v is None for k,v in cfg.items() if k.startswith('actual_'))
 base=json.loads(public_ref(cfg['base_runtime']))
 assert review['reviewed_code_pins']==plan['new_five_code_pins']
 assert cfg['source_snapshot_sha256']==plan['source_snapshot_sha256']==review['source_snapshot_sha256']
 assert cfg['fixed_policy_sha256']==plan['fixed_source_policy_sha256']==review['source_policy_sha256']
 assert digest(canonical({k:base[k] for k in cfg['fixed_policy_keys']}))==cfg['fixed_policy_sha256']
 assert digest(canonical({k:base[k] for k in ['sources','pages','occurrence_slots','unknowns']}))==cfg['source_snapshot_sha256']
 checks=json.loads((root/'reports/E01_AL_OFFICE_CONTEXT_ACTUAL_RUNTIME_V1_1_PLAN_CHECKS.json').read_text())
 protected=checks['all17_original_committed_candidate_pins_unchanged'];assert len(protected)==17
 for p,h in protected.items():
  assert digest((root/p).read_bytes())==h==digest(subprocess.run(['git','show','7c4c518:'+p],check=True,capture_output=True).stdout)
 for p,h in plan['new_five_code_pins'].items():assert digest((root/p).read_bytes())==h
 for p,h in cfg['metadata_pins'].items():assert digest((root/p).read_bytes())==h
 for p,h in base['metadata_pins'].items():assert digest((root/p).read_bytes())==h
 assert plan['historical_provenance_only']==cfg['historical_source_only']
 trans_ref=auth['read_permissions']['original_transcript'];audit_ref=auth['read_permissions']['public_literal_audit']
 assert trans_ref==cfg['transcript_ref']==plan['original_transcript_ref']
 assert audit_ref==cfg['accepted_literal_audit_ref']==plan['genuine_six_occurrence_literal_audit_ref']
 assert auth['read_permissions']['original_transcript_byte_hash_verifications']==1
 assert auth['read_permissions']['exact_byte_audit_copies']==1 and auth['read_permissions']['transcript_copy_or_rewrite'] is False
 targets=auth['new_private_files_exact'];assert len(targets)==len(set(targets))==6
 expected=[cfg['runtime_audit_copy_area']+'/literal_audit.local.json']+['data/processed/e01_al_office_context_v1_1_release/grants/'+role+'.local.json' for role in ['source_read_authorization','runtime_code_acceptance_sha256','recorded_preflight_release_sha256']]+['data/processed/e01_al_office_context_v1_1_release/runtime.local.json','data/processed/e01_al_office_context_v1_1_release/outer_manifest.local.json']
 assert targets==expected
 for relative in targets:
  p=root/relative;path_guard(p)
  try:p.lstat()
  except FileNotFoundError:pass
  else:raise RuntimeError('EXISTING_PRIVATE_TARGET_STOP')
 # New preparation areas may contain no unexpected existing entries. No other
 # processed folder, source-only history or run/control area is enumerated.
 for area,allowed_names in [(cfg['runtime_audit_copy_area'],set()),('data/processed/e01_al_office_context_v1_1_release',{'grants'}),('data/processed/e01_al_office_context_v1_1_release/grants',set())]:
  directory=root/area
  try:s=directory.lstat()
  except FileNotFoundError:continue
  assert stat.S_ISDIR(s.st_mode)
  assert {entry.name for entry in directory.iterdir()}<=allowed_names,'UNEXPECTED_PREPARATION_ENTRY_STOP'
 step='BUILD_METADATA_IN_MEMORY'
 audit_raw=public_ref(audit_ref,65536);counts['public_literal_audit_copy_source_reads']=1
 literal_review=json.loads(audit_raw)
 assert set(literal_review)=={'schema_version','scope','status','source_snapshot_sha256','transcription_sha256','approved_occurrences'}
 assert literal_review['status']=='PASS_EXACT_TRANSCRIBED_OCCURRENCES_ONLY' and len(literal_review['approved_occurrences'])==6
 assert literal_review['transcription_sha256']==trans_ref['sha256'] and literal_review['source_snapshot_sha256']==cfg['source_snapshot_sha256']
 raw_files={targets[0]:audit_raw};grant_refs=[]
 for relative,role in zip(targets[1:4],['source_read_authorization','runtime_code_acceptance_sha256','recorded_preflight_release_sha256']):
  body={'schema_version':1,'role':role,'status':'AUTHORED_OR_SEPARATELY_RELEASED_EXACT_SNAPSHOT','source_snapshot_sha256':cfg['source_snapshot_sha256']}
  if role=='runtime_code_acceptance_sha256':body['module_sha256']=plan['new_five_code_pins']['src/civiclab/e01/alabama_documents_v1.py']
  definition=plan['grant_body_schemas_not_instances'][role]
  assert set(body)==set(definition['required_keys'])
  assert all(body[k]==v['const'] for k,v in definition['field_constraints'].items())
  raw=canonical(body);raw_files[relative]=raw
  grant_refs.append({'role':role,'path':relative,'sha256':digest(raw),'bytes':len(raw)})
 runtime=copy.deepcopy(base)
 runtime['scope']='RELEASED_LOCAL_AL_DOCUMENT_RECONCILIATION_ONLY'
 runtime['transcription']=copy.deepcopy(trans_ref)
 runtime['independent_transcription_audit']={'path':targets[0],'sha256':audit_ref['sha256'],'bytes':audit_ref['bytes']}
 runtime['release_documents']=grant_refs
 runtime['actual_execution_release']={'approved':True,'trusted_private_transcript_sha256':trans_ref['sha256'],'independent_literal_transcription_audit_sha256':audit_ref['sha256'],**{g['role']:g['sha256'] for g in grant_refs}}
 dynamic={'scope','actual_execution_release','release_documents','transcription','independent_transcription_audit'}
 assert set(runtime)==set(base) and canonical({k:v for k,v in runtime.items() if k not in dynamic})==canonical({k:v for k,v in base.items() if k not in dynamic})
 assert set(runtime['actual_execution_release'])==set(base['actual_execution_release'])
 raw_files[targets[4]]=canonical(runtime)
 runtime_ref={'path':targets[4],'sha256':digest(raw_files[targets[4]]),'bytes':len(raw_files[targets[4]])}
 outer={'schema_version':1,'mode':'AUDITED_RUNTIME_OFFICE_CONTEXT_V1_1','execution_kind':'LOCAL_ACTUAL','root_sha256':digest(str(root).encode()),
 'source_policy_sha256':cfg['fixed_policy_sha256'],'source_snapshot_sha256':cfg['source_snapshot_sha256'],'admission_config_sha256':auth['candidate_ref']['sha256'],
 'code_pins':copy.deepcopy(plan['new_five_code_pins']),'code_review':copy.deepcopy(plan['authority']['code_review_ref']),
 'output_scope':'data/processed/runs','visual_pages':copy.deepcopy(cfg['visual_pages']),'source_release':copy.deepcopy(cfg['historical_source_only']['manifest_ref']),
 'runtime':runtime_ref,'office_rule':copy.deepcopy(cfg['rule_ref']),'phase_limit':{'primary':1,'replay':1}}
 assert set(outer)=={'admission_config_sha256','code_pins','code_review','execution_kind','mode','office_rule','output_scope','phase_limit','root_sha256','runtime','schema_version','source_policy_sha256','source_release','source_snapshot_sha256','visual_pages'} and outer['code_review']['bytes']==len(code_raw)
 raw_files[targets[5]]=canonical(outer);outer_ref={'path':targets[5],'sha256':digest(raw_files[targets[5]]),'bytes':len(raw_files[targets[5]])}
 assert set(raw_files)==set(targets) and len(raw_files[targets[4]])<=262144 and len(raw_files[targets[5]])<=131072
 assert all(len(raw_files[p])<=65536 for p in targets[:4])
 # Fail closed on every attempted socket call, raw source open or research
 # runtime import. The sole pre-existing private input allowance is one read.
 transcript_path=root/trans_ref['path'];allowed_new={root/p for p in targets}
 def audit(event,args):
  if event.startswith('socket.'):raise RuntimeError('NETWORK_FORBIDDEN')
  if event=='import' and args and str(args[0]).startswith('civiclab'):raise RuntimeError('HELPER_IMPORT_FORBIDDEN')
  if event=='open' and args and isinstance(args[0],(str,bytes)):
   p=Path(os.fsdecode(args[0])).absolute()
   if p==root/'data/raw' or root/'data/raw' in p.parents or p.suffix.lower() in {'.pdf','.png'}:raise RuntimeError('RAW_SOURCE_OPEN_FORBIDDEN')
   if p==transcript_path:
    counts['original_transcript_byte_hash_verifications']+=1
    assert counts['original_transcript_byte_hash_verifications']==1
    assert args[2]&os.O_ACCMODE==os.O_RDONLY
   elif root/'data/processed' in p.parents and p not in allowed_new:raise RuntimeError('UNLISTED_PRIVATE_OPEN_FORBIDDEN')
 sys.addaudithook(audit)
 step='ONE_ORIGINAL_TRANSCRIPT_BYTE_HASH_VERIFICATION'
 path_guard(transcript_path);before=transcript_path.lstat();assert stat.S_ISREG(before.st_mode)
 fd=os.open(transcript_path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  assert identity(before)==identity(os.fstat(fd))
  raw=os.read(fd,trans_ref['bytes']+1)
  assert len(raw)==trans_ref['bytes'] and digest(raw)==trans_ref['sha256']
  assert identity(before)==identity(os.fstat(fd));del raw
 finally:os.close(fd)
 assert counts['original_transcript_byte_hash_verifications']==1
 step='CREATE_EXACT_SIX_PRIVATE_METADATA_FILES_ONCE'
 for relative in targets:write_once(root/relative,raw_files[relative])
 assert len(created)==counts['private_files_created']==6
 step='FINAL_PUBLIC_AND_STAT_ONLY_PROOF'
 for p,h in protected.items():assert digest((root/p).read_bytes())==h
 assert digest((root/auth_path).read_bytes())==digest(auth_raw)
 assert identity(before)==identity(transcript_path.lstat())
 for entry in created:
  s=(root/entry['path']).lstat();assert stat.S_ISREG(s.st_mode) and s.st_size==entry['bytes']
 # No reopening/reparsing the original transcript, source-only private history,
 # grants/runtime or new outer, nor any _prepare/admission/reader invocation.
 report={'schema_version':1,'status':'PREPARED_EXACT_METADATA_ONLY_STOP_FOR_INDEPENDENT_PARTICULAR_REVIEW',
 'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'lead_decision_id':auth['decision_id'],
 'lead_preparation_authorization_ref':{'path':auth_path,'sha256':digest(auth_raw),'bytes':len(auth_raw)},
 'plan_ref':auth['plan_ref'],'recipe_review_ref':auth['recipe_review_ref'],'code_review_ref':outer['code_review'],
 'six_private_files':created,'outer_manifest_ref':outer_ref,'outer_digest_for_external_lead_binding_only':outer_ref['sha256'],
 'execution_authority':'ABSENT_SEPARATE_INDEPENDENT_PARTICULAR_METADATA_REVIEW_AND_LEAD_EXEC_REQUIRED',
 'runtime_approved_flag_scope':'PREPARED_METADATA_ONLY_UNDER_EXPLICIT_PREP_DECISION_NOT_EXECUTION_AUTHORITY',
 'grant_issuer':auth['grant_issuer'],'grant_body_hashes':{g['role']:g['sha256'] for g in grant_refs},
 'binding_edges':plan['binding_dependency_edges'],'resolved_binding_refs':{'historical_source_manifest':outer['source_release'],'original_transcript':trans_ref,'exact_literal_audit_copy':runtime['independent_transcription_audit'],'three_grants':grant_refs,'runtime':runtime_ref,'new_outer':outer_ref,'new_code_review':outer['code_review']},
 'input_proof':{'original_transcript':trans_ref,'byte_hash_verifications':1,'transcript_parsed':False,'transcript_copied_or_rewritten':False,'before_after_file_identity_size_mtime_ctime_unchanged':True,'genuine_public_literal_audit':audit_ref,'copy_identical_to_single_copy_source_read':True,'public_literal_audit_total_reads':2,'public_literal_audit_metadata_pin_reads':1,'private_source_only_history_read':False},
 'all17_candidate_pins_unchanged_from_committed_7c4c518':protected,
 'metadata_construction_checks':['Accepted public hashes/statuses/scope/policy/snapshot/newfive refs agree.','Allnewtargetfiles absent; exact preparation areas contain no unexpected entries; regular/non-symlink path guards.','Three bodies have exact required4/5keys, source snapshot and frozenpure code constant; no issuer/review/runtime/outer/self-hash insidebody.','Runtime changesonly five dynamicfields; originaltranscriptref unchanged, auditcopy exact, approvedflag preparationonly.','Outer binds exact code-review/newfive/config/rule/source-only/runtime/root/output/phase metadata; expectedSHA not EXEC permission.','Six files written with O_EXCL/O_NOFOLLOW,0600,complete write,fsync,fstat size; no readback or helper admission.','Originaltranscript byte/hash checked once without parsing; same file identity/stat after preparation; no second hash claimed.','Candidate17 public bytes checked before/after and against original Git blobs; no originals or controls changed.'],
 'counts':{**counts,'source_pdf_png_stat_hash_open_or_views':0,'private_source_history_reads':0,'transcript_json_parses':0,'transcript_copy_or_write':0,'helper_admission_reconcile_record_RunStore_calls':0,'new_run_parents_or_controls':0,'GET_model_credential_calls':0,'api_spend_usd':0},
 'global_status_unchanged':{'typed_document_states':13,'unfinished_source_jobs':20,'legacy_roster_states':12,'final_ballots_accepted':0},
 'limitations':['Writes are verified from exact submitted buffers plus full writes/fsync/file-size/regularity checks; no readback of six newlyprepared files was performed. Independent particular reviewer must read and verify final bytes.','No source-only grant/run/control private bytes were reopened; historical consistency remains for independent review and separately released code admission.','A prepared runtime approved flag and outerdigest do not create execution authority.','Cooperating filesystem guard; no hostile-host/race/power-loss/durable-failure proof.','No source reading beyond the single authorized private transcript byte/hash check; no names or raw occurrences are emitted.','Development compute remains UNPRICED; no science/readiness/coverage/legal/latest/forecast/publication acceptance.'],
 'next_gate':'STOP. Independent exact particular metadata review, then separate finite lead EXEC decision. No retries/overwrites/resets or alternate preparation root.'}
 with result_path.open('x') as stream:stream.write(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':report['status'],'six_private_files':created,'outer_expected_sha256':outer_ref['sha256'],'public_result':{'path':str(result_path.relative_to(root)),'sha256':digest(result_path.read_bytes())},'counts':report['counts']},indent=2))
except BaseException as exc:
 failure={'schema_version':1,'status':'STOP_PREPARATION_FAILURE_NO_RETRY_OR_OVERWRITE','step':step,'error_type':type(exc).__name__,'created_private_files':created,'counts':counts,'source_runtime_execution':'NOT_AUTHORIZED_NOT_INVOKED','next':'Independent read-only resolution; no reset/retry/newroot.'}
 if not result_path.exists():
  with result_path.open('x') as stream:json.dump(failure,stream,indent=2,sort_keys=True);stream.write('\n')
 print(json.dumps(failure,indent=2));sys.exit(1)
