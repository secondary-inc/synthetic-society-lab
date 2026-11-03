"""Two finite reviewed wrapper calls only. Never rerun this script."""
from pathlib import Path
import datetime,hashlib,json,time,sys
root=Path.cwd().absolute()
sys.path.insert(0,str(root/'src'))
out=root/'reports/E01_AL_OFFICE_CONTEXT_V1_1_ACTUAL_EXECUTION_RESULT.json'
phase='AUTHORITY_ADMISSION';primary=None;replay=None;calls=0;observations=[]
def digest(raw):return hashlib.sha256(raw).hexdigest()
def safe_metadata(path):
 raw=path.read_bytes();assert len(raw)<=4194304
 return json.loads(raw),digest(raw),len(raw)
def metadata_receipt(path):
 ledger,ledger_sha,ledger_bytes=safe_metadata(path/'checksums.json')
 seal,seal_sha,seal_bytes=safe_metadata(path/'al_release.json')
 payloads,payloads_sha,_=safe_metadata(path/'al_payload_hashes.json')
 public,public_sha,_=safe_metadata(path/'al_document_diagnostics.json')
 summary,summary_sha,_=safe_metadata(path/'summary.json')
 assert seal['checksums_sha256']==ledger_sha and seal['external_release_sha256']==expected
 assert ledger['al_payload_hashes.json']==payloads_sha and ledger['al_document_diagnostics.json']==public_sha and ledger['summary.json']==summary_sha
 assert set(payloads)=={'al_document_observations.local.json','al_document_diagnostics.json','al_release_provenance.json'}
 assert all(ledger[k]==h for k,h in payloads.items())
 payload=public['payload']
 assert public['schema_version']==payload['schema_version']==2 and public['execution_kind']=='LOCAL_ACTUAL'
 assert payload['accepted_coverage_promoted'] is False and payload['source_adoption'] is False and payload['final_ballots_accepted']==0
 assert payload['cost_usd']==payload['model_calls']==0
 controls=root/'data/processed/e01_al_release_controls'/expected
 started,started_sha,started_bytes=safe_metadata(controls/(summary['phase']+'.started.local.json'))
 ack,ack_sha,ack_bytes=safe_metadata(controls/(summary['phase']+'.completed.local.json'))
 assert ack['run_id']==path.name and ack['seal_sha256']==seal_sha and ack['external_release_sha256']==expected
 assert started['phase']==summary['phase'] and started['external_release_sha256']==expected and started['retry_authorized'] is False
 return {'run_id':path.name,'path':str(path.relative_to(root)),'phase':summary['phase'],
  'ledger':{'sha256':ledger_sha,'bytes':ledger_bytes,'entries':ledger},'final_seal':{'sha256':seal_sha,'bytes':seal_bytes},
  'payload_hashes_from_verified_metadata_not_private_readback':payloads,
  'controls':{'started':{'sha256':started_sha,'bytes':started_bytes},'completed':{'sha256':ack_sha,'bytes':ack_bytes}},
  'normal_observations':{'caller_returned_normally':True,'summary_status':summary['status'],'seal_status':seal['status'],
   'schema_version':payload['schema_version'],'source_count':payload['source_count'],'physical_page_count':payload['physical_page_count'],
   'senate_occurrence_count':payload['senate_occurrence_count'],'document_supported_name_group_count':payload['document_supported_name_group_count'],
   'historical_occurrence_count':payload['historical_occurrence_count'],'office_literal_form_count':payload['office_literal_form_count'],
   'cross_literal_exception_count':payload['cross_literal_exception_count'],'typed_unknown_count':len(payload['typed_unknowns']),
   'office_family_rule_sha256':payload['office_family_rule_sha256'],'source_adoption':False,'accepted_coverage_promoted':False,'final_ballots_accepted':0,'model_calls':0,'cost_usd':0}}
try:
 assert not out.exists(),'EXISTING_RESULT_STOP'
 ap='reports/E01_AL_OFFICE_CONTEXT_V1_1_ACTUAL_EXECUTION_AUTHORIZATION.json';araw=(root/ap).read_bytes();auth=json.loads(araw)
 assert auth['decision_id']=='AL_OFFICE_CONTEXT_EXEC_20261103_01' and auth['kind']=='LEAD_FINITE_AL_OFFICE_CONTEXT_V1_1_EXECUTION'
 assert auth['approved'] is True and auth['automatic_retry_or_reset'] is False
 assert auth['maximum_calls']==2 and auth['phases']==['primary','replay'] and auth['replay_only_after_successful_primary'] is True
 assert auth['entrypoint']=='civiclab.e01.alabama_recorded_preflight_v1_1.record'
 assert auth['model_calls']==auth['experimental_spend_usd']==0 and auth['coverage_promotion'] is False
 assert auth['particular_review']['sha256']=='2a520512895b56e6956f10930c92d96ac13dd21283eb573a744bb09c4a92be1c'
 ref=auth['outer_manifest'];expected='25d043afa6ebd3ba9344c07b93853e911b279b39b60af6c01627823a276d4977'
 assert ref=={'path':'data/processed/e01_al_office_context_v1_1_release/outer_manifest.local.json','sha256':expected,'bytes':2605}
 with (root/ref['path']).open('rb') as stream:outer=stream.read(2606)
 assert len(outer)==2605 and digest(outer)==expected
 # All runtime/code/review/history/source binding checks happen inside these
 # reviewed entrypoint calls. No separate preflight or saved-reader invocation.
 from civiclab.e01.alabama_recorded_preflight_v1_1 import record
 phase='primary';calls=1;started=time.monotonic()
 primary=record(root,outer,expected_sha=expected,phase='primary')
 observations.append({'phase':'primary','returned_normally':True,'seconds':round(time.monotonic()-started,6),'run_id':primary.name})
 phase='replay';calls=2;started=time.monotonic()
 replay=record(root,outer,expected_sha=expected,phase='replay')
 observations.append({'phase':'replay','returned_normally':True,'seconds':round(time.monotonic()-started,6),'run_id':replay.name})
 phase='SAFE_POSTRUN_METADATA_HANDOFF'
 one=metadata_receipt(primary);two=metadata_receipt(replay)
 assert one['phase']=='primary' and two['phase']=='replay'
 same={name:one['payload_hashes_from_verified_metadata_not_private_readback'][name]==two['payload_hashes_from_verified_metadata_not_private_readback'][name] for name in ['al_document_observations.local.json','al_document_diagnostics.json']}
 assert all(same.values())
 result={'schema_version':1,'status':'TWO_NORMAL_RECORDED_PHASE_RETURNS_PENDING_INDEPENDENT_SAVED_OUTPUT_REVIEW',
  'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'lead_execution_decision_id':auth['decision_id'],
  'lead_execution_authorization_ref':{'path':ap,'sha256':digest(araw),'bytes':len(araw)},'particular_review_ref':auth['particular_review'],
  'outer_manifest_ref':ref,'entrypoint':auth['entrypoint'],'actual_record_invocations':calls,'phase_observations':observations,
  'runs':[one,two],'primary_replay_recorded_payload_hashes_equal':same,
  'source_limits':{'scope':auth['source_read_scope'],'declared_static_success_path':auth['success_path_static_raw_limits'],'observed_syscall_IO_counters':'NOT_INSTRUMENTED_NOT_CLAIMED'},
  'worker_extra_runtime_calls':{'standalone_preflight_prepare_read_released_read_verified_sourceonly':0,'manual_source_PDF_PNG_stat_hash_read_or_view':0,'monkeypatches_or_source_changes':0,'network_GET_model_key_calls':0,'retry_reset_newroot':0},
  'postrun_scope':'Only newly returned run ledger/seal/payload-hash/public-diagnostics/summary metadata and exact phase controls read. No private observation payload readback, source sweep or extra helper/saved-reader.',
  'api_spend_usd':0,'development_compute':'UNPRICED','global_status_unchanged':{'typed_document_states':13,'unfinished_source_jobs':20,'legacy_roster_states':12,'final_ballots_accepted':0},
  'limits':['Normal caller returns and linked metadata observed, not independent source/content/science acceptance.','Payload equality is comparison of recorded hashes; independent auditor must inspect original private saved bytes under separate scope.','Static416 source verifications/eightpasses/3167718568byte ceiling are reviewed code-path specifications, not observed OS I/O measurements.','No source/coverage/adoption/geography/final-ballot/latest/forecast/dashboard/publication change.'],
  'next_gate':'STOP for independent exact original saved-output review. No further source/helper/reader/record calls.'}
 with out.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
 print(json.dumps({'status':result['status'],'runs':[{'run_id':x['run_id'],'phase':x['phase'],'ledger_sha256':x['ledger']['sha256'],'seal_sha256':x['final_seal']['sha256'],'payloads':x['payload_hashes_from_verified_metadata_not_private_readback'],'controls':x['controls']} for x in result['runs']],
  'observations':observations,'result_ref':{'path':str(out.relative_to(root)),'sha256':digest(out.read_bytes())}},indent=2))
except BaseException as exc:
 kind=getattr(exc,'error_type',type(exc).__name__)
 failure={'schema_version':1,'status':'STOP_FINITE_EXECUTION_OR_POSTRUN_METADATA_FAILURE_NO_RETRY','phase':phase,'error_type':kind,
 'wrapper_calls_attempted':calls,'completed_normal_phase_observations':observations,
 'returned_primary_run_id':primary.name if primary else None,'returned_replay_run_id':replay.name if replay else None,
 'no_retry_reset_newroot_nextphase':'ENFORCED','api_spend_usd':0,'next':'Independent read-only retained-evidence resolution; no extra source/helper/reader/record calls.'}
 if not out.exists():
  with out.open('x') as stream:json.dump(failure,stream,indent=2,sort_keys=True);stream.write('\n')
 print(json.dumps(failure,indent=2));sys.exit(1)
