"""N2b five-stage private execution, separate from frozen WY/N2a runtimes."""
import json
import os
import time
from . import n2b_metrics_v1_1 as metrics
from ..common import canonical_hash
from . import n2b_admission_v1_1 as a
from .n2b_control_v1_1 import Control
from .n2b_source_v1_1 import inspect_source,parse_state
from .n2b_parts_v1_1 import from_saved_wy,validate
from .n2b_assembly_v1_1 import matched
from .full_adult_types_v1_2 import strict_json
from .f_wy_bootstrap_v1_1 import _open_no_follow,_identity
from .national_budget import Blocked


def _saved(c,phase):
 a.require(c);ref=c.config['saved_parts'].get(phase)
 if ref is None:raise Blocked('accepted saved WY reference missing')
 f,dfd,chain=_open_no_follow(c.root/ref['relative_path'])
 try:
  with f:before=_identity(os.fstat(f.fileno()));blob=metrics.read_stream(f,6291457)
 finally:os.close(dfd)
 current,cd,current_chain=_open_no_follow(c.root/ref['relative_path'])
 try:
  with current:
   if chain!=current_chain or _identity(os.fstat(current.fileno()))!=before:raise Blocked('savedpart lexical replacement')
 finally:os.close(cd)
 if len(blob)>6291456 or a.sha(blob)!=ref['sha256']:raise Blocked('accepted savedpart bytes/hash')
 return from_saved_wy(strict_json(blob),c.binding['spec'],ref,realm=c.realm.kind,spec_sha256=c.config['specification']['sha256'])


def _load_part(c,control,phase):
 a.require(c);p=control.path/(phase+'_part')/'part.json';f,dfd,chain=_open_no_follow(p)
 try:
  with f:before=_identity(os.fstat(f.fileno()));blob=metrics.read_stream(f,6291457)
 finally:os.close(dfd)
 if len(blob)>6291456:raise Blocked('part byte cap')
 receipt=strict_json(metrics.read_text(control.path/'core'/(phase+'.receipt.json')))['result']
 if a.sha(blob)!=receipt['artifact']['sha256']:raise Blocked('committed sourcepart changed')
 part=strict_json(blob);validate(part,c.binding['spec'],expected_state=c.config['active_state'],expected_source=c.binding['source_sha256'],expected_spec=c.config['specification']['sha256']);return part


def run(context):
 c=a.require(context);control=Control(c,create=not c.output.exists())
 # No continuation/retry after any existing stage; this is a one-shot sequence.
 if control.snapshot()['stages']:raise Blocked('existing N2b history; no automatic resume')
 def bind():
  source=inspect_source(c,control,'BIND');wy={p:canonical_hash(_saved(c,p)) for p in ('PRIMARY','REPLAY')}
  return {'source':source,'WY_saved_parts':wy,'rows_read':0,'GETs':0,'model_calls':0}
 control.run_stage('BIND',bind)
 for phase in ('DC_PRIMARY','DC_REPLAY'):
  def parse(phase=phase):
   primary=_load_part(c,control,'DC_PRIMARY') if phase=='DC_REPLAY' else None
   part=parse_state(c,control,phase,primary_person_sha256=None if primary is None else primary['person_sha256'])
   if primary is not None and {k:v for k,v in primary.items() if k!='lineage'}!={k:v for k,v in part.items() if k!='lineage'}:raise Blocked('PRIMARY/REPLAY data mismatch')
   artifact=control.json(phase+'_part','part.json',part)
   return {'artifact':artifact,'part_sha256':canonical_hash(part),'first_person_sha256':part['person_sha256'],'rows':part['rows'],'import_science_accepted':False}
  control.run_stage(phase,parse)
 for cohort in ('PRIMARY','REPLAY'):
  phase='ASSEMBLE_'+cohort
  def assemble_work(cohort=cohort,phase=phase):
   wy=_saved(c,cohort);dc=_load_part(c,control,'DC_'+cohort);items=[wy,dc]
   matrix,uncertainty,summaries,evidence=matched(items,c.binding['spec'],guard=lambda:control.guard(phase),evaluation_order=c.config['evaluation_schedule'][cohort],record_failure=lambda e:control.json('core',phase+'.comparison_failure.json',e))
   if cohort=='REPLAY':
    p=control.path/'core/ASSEMBLE_PRIMARY.receipt.json';prior=strict_json(metrics.read_text(p))['result']
    if prior['comparison']['primitive_hashes']!=evidence['primitive_hashes'] or prior['comparison']['registry_uncertainty_sha256']!=evidence['registry_uncertainty_sha256']:raise Blocked('assembled primary/replay mismatch')
   target=phase+'_canonical_data';files={name:control.write(target,name,blob) for name,blob in matrix.blobs().items()}
   files['uncertainty.json']=control.json(target,'uncertainty.json',uncertainty);files['views.json']=control.json(target,'views.json',{'summaries':summaries,'scope':'WY_DC_PARTIAL_NOT_NATIONAL','political_priors':'NOT_IDENTIFIED_BY_PUMS'})
   manifest={'schema':'E02_N2B_PARTIAL_ASSEMBLY_V1','realm':c.realm.kind,'design':c.binding['design_sha256'],'spec_sha256':c.config['specification']['sha256'],'cohort':cohort,'files':files,'input_part_hashes':evidence['input_parts'],'known_F_cells':sum(matrix.present),'unknown_F_cells':3672-sum(matrix.present),'scope':'ENGINEERING_ONLY_PRIVATE_NO_FIT_DISCLOSURE'}
   artifact=control.json(target,'manifest.json',manifest)
   return {'manifest':artifact,'comparison':evidence,'GETs':0,'model_calls':0}
  def assemble(cohort=cohort,phase=phase):
   common=metrics.Meter();started=time.perf_counter()
   with metrics.activity(common):result=assemble_work(cohort,phase)
   scope=time.perf_counter()-started;variants=result['comparison']['resource_evidence']['variants'];variant_scope=sum(v['total_scope_seconds'] for v in variants)
   result['comparison']['resource_evidence']['stage_common']={'scope_seconds':scope,'variant_scopes_seconds':variant_scope,'common_wall_seconds':max(0.,scope-variant_scope),'bookkeeping':common.snapshot(),'scope':'ASSEMBLY_INPUT_LOAD_HASH_COMPARISON_REVERSE_SOURCE_CHECK_AND_PAYLOAD_PERSISTENCE; EXCLUDES FINAL CONTROL_RECEIPT_COMMIT/GUARD; sampler costs may overlap'}
   return result
  control.run_stage(phase,assemble)
 s=control.snapshot();return {'realm':c.realm.kind,'label':'MOCK_AUTHORED_ONLY_NOT_POPULATION' if c.realm.kind=='TEST_ONLY' else 'ACTUAL_ENGINEERING_ONLY_PENDING_AUDIT','status':'PRIVATE_N2B_ENGINEERING_CLOSED_PENDING_INDEPENDENT_REVIEW','stages':{k:v['status'] for k,v in s['stages'].items()},'reservation':s['reservation'],'history':s['history'],'GETs':0,'model_calls':0,'fit':False,'disclosure':False}


def run_actual(config=None):return run(a.admit(config))
def run_fixture(realm,config):return run(a.admit_fixture(realm,config))

def project_outputs(*args,**kwargs):raise Blocked('N2b private outputs require separate disclosure review')
