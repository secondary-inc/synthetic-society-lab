"""Private PARTIAL_WY pilot; authored capability or separately reviewed actual release."""
import json
from pathlib import Path
from ..common import canonical_hash,sha256_file
from .national_budget import Blocked
from .national_population import supervise_fixture
from .f_actual_admission_v1_1 import require_admission,admit_actual
from .f_actual_ledger_v1_1 import PilotLedger
from .f_wy_source_v1_1 import inspect_source,parse_source,validate_part,identity
from .full_adult_types_v1_2 import AdultMatrix,strict_json
from .full_adult_analysis_v1_2 import mandatory_analysis
from .full_adult_codec_v1_2 import validate_uncertainty_container


def execute_actual(*args,**kwargs):
    admission=admit_actual(*args,**kwargs)
    return PartialWYPilot(admission).run()
def admit_public_output(*args,**kwargs):raise Blocked('PARTIAL_WY output is private; no viewer/package/disclosure/fit admission')


def unchanged(a,expected):
    if identity(a.path)!=expected or sha256_file(a.path)!=a.manifest['archive_sha256'] or identity(a.path)!=expected:raise Blocked('parent post-work source replacement/drift')


class PartialWYPilot:
    def __init__(self,admission):
        self.a=require_admission(admission);self.c=admission.config;self.root=admission.root;self.ledger=PilotLedger(admission);self.resources=[]
    def _perform(self,key,work,write,*,hook=lambda event:None):
        reserved=self.ledger.reserve(key,hook=hook);self.active_reservation=(key,canonical_hash(reserved));hook('after_reservation')
        try:
            result,res=supervise_fixture(work,seconds=self.c['limits']['state_processing_seconds'],rss_bytes=self.c['limits']['rss_stop_bytes'],poll_seconds=self.c['limits']['watchdog_poll_seconds'])
            self.resources.append({'stage':key,**res});hook('after_worker_before_checkpoint')
            proof=write(result);hook('after_artifact_before_commit')
            expected=result['identity'] if key=='ENROLL' else result['source_identity']
            unchanged(self.a,expected);self.ledger.commit(key,proof,hook=hook);return result
        except BaseException as error:
            # No exception value/row dump. Failure write may itself fail, leaving
            # the full durable reservation/torn evidence untouched and blocked.
            try:
                self.ledger.storage.json(self.root/(key+'.failure.local.json'),{'schema':'E02_F_WY_FAILURE_V1','stage':key,'error_type':type(error).__name__,'origin':self.a.origin,'actual_person_rows_processed':None if self.a.origin=='ACTUAL' else 0,'GETs':0,'model_calls':0,'accepted_aggregate':False})
                self.ledger.fail(key)
            except BaseException:pass
            raise Blocked('private pilot work failed; inspect structured local state') from None
    def enroll(self,*,hook=lambda event:None):
        return self._perform('ENROLL',lambda:inspect_source(self.a,reservation=self.active_reservation),lambda result:self._write('ENROLL.local.json',result),hook=hook)
    def _write(self,name,value):
        path=self.root/name;self.ledger.storage.json(path,value);return path
    def parse(self,sweep,*,hook=lambda event:None):
        if sweep not in ('PRIMARY','REPLAY'):raise Blocked('sweep vocabulary')
        return self._perform(sweep,lambda:parse_source(self.a,reservation=self.active_reservation,expected_identity=strict_json((self.root/'ENROLL.local.json').read_text())['identity']),lambda result:self._write(sweep+'.local.json',result),hook=hook)
    def finalize(self,sweep,*,hook=lambda event:None):
        if sweep not in ('PRIMARY','REPLAY'):raise Blocked('sweep vocabulary')
        part_path=self.root/(sweep+'.local.json')
        # Dependency/reservation precedes reads/work; _proof validates the stage
        # against the immutable source as part of reservation replay.
        def work():
            part=strict_json(part_path.read_text());matrix=validate_part(part,self.a);uncertainty,summaries=mandatory_analysis(matrix,self.c['spec'])
            validate_uncertainty_container(uncertainty,self.c['spec'])
            return {'source_identity':part['source_identity'],'source_manifest_sha256':part['source_manifest_sha256'],'primitive_bundle':part['primitive_bundle'],'uncertainty':uncertainty,'summaries':summaries,'part_sha256':sha256_file(part_path)}
        def write(result):
            folder=self.root/sweep;files={}
            for name,hex_value in result['primitive_bundle'].items():files[name]=self.ledger.storage.write(folder/name,bytes.fromhex(hex_value))
            files['uncertainty.local.json']=self.ledger.storage.json(folder/'uncertainty.local.json',result['uncertainty'])
            files['summaries.local.json']=self.ledger.storage.json(folder/'summaries.local.json',result['summaries'])
            manifest={'schema':'E02_F_PARTIAL_WY_'+self.a.origin+'_BENCHMARK_V1','origin':self.a.origin,'scope':'PARTIAL_WY_LOCAL_ENGINEERING_ONLY','state_coverage':['56'],'unknown_states':[s for s in self.c['states'] if s!='56'],'source_manifest_sha256':canonical_hash(self.a.manifest),'source_part_sha256':result['part_sha256'],'runtime_config_sha256':canonical_hash(self.c),'spec_sha256':self.c['spec_sha256'],'files':files,'known_F_cells':72,'unknown_F_cells':3600,'known_C_cells':12,'unknown_C_cells':600,'actual_person_rows_processed':self.a.manifest['expected_rows'] if self.a.origin=='ACTUAL' else 0,'political_priors':'NOT_IDENTIFIED_BY_PUMS','disclosure':'PRIVATE_NOT_ADMITTED','fit':'NOT_AUTHORIZED','national':'BLOCKED_MISSING_SOURCE','acceptance':'PENDING_INDEPENDENT_ACTUAL_REVIEW' if self.a.origin=='ACTUAL' else 'MOCK_NOT_RESEARCH'}
            path=folder/'manifest.local.json';self.ledger.storage.json(path,manifest)
            proof={'schema':'E02_F_PARTIAL_WY_FINAL_PROOF_V1','origin':self.a.origin,'sweep':sweep,'source_manifest_sha256':canonical_hash(self.a.manifest),'manifest_path':str(path.relative_to(self.root)),'manifest_sha256':sha256_file(path),'observed_logical_ops':result['uncertainty']['logical_units_observed']}
            return self._write('FINALIZE_'+sweep+'.local.json',proof)
        return self._perform('FINALIZE_'+sweep,work,write,hook=hook)
    def run(self):
        self.enroll()
        for w in ('PRIMARY','REPLAY'):self.parse(w)
        for w in ('PRIMARY','REPLAY'):self.finalize(w)
        primary=read_partial(self.a,'PRIMARY');replay=read_partial(self.a,'REPLAY')
        if primary[0].blobs()!=replay[0].blobs() or primary[2]!=replay[2]:raise Blocked('partial replay differs')
        return primary,replay


def read_partial(admission,sweep):
    a=require_admission(admission)
    if sweep not in ('PRIMARY','REPLAY'):raise Blocked('sweep vocabulary')
    ledger=PilotLedger(a);s=ledger.snapshot();key='FINALIZE_'+sweep;stage=s['stages'].get(key,{})
    if stage.get('status')!='COMMITTED':raise Blocked('uncommitted partial output')
    proof=ledger._proof(key,stage['proof']);folder=a.root/sweep;manifest=strict_json((folder/'manifest.local.json').read_text())
    if manifest['schema']!='E02_F_PARTIAL_WY_'+a.origin+'_BENCHMARK_V1' or manifest['origin']!=a.origin or manifest['scope']!='PARTIAL_WY_LOCAL_ENGINEERING_ONLY' or manifest['source_manifest_sha256']!=canonical_hash(a.manifest) or manifest['runtime_config_sha256']!=canonical_hash(a.config) or manifest['state_coverage']!=['56'] or manifest['unknown_states']!=[x for x in a.config['states'] if x!='56'] or manifest['actual_person_rows_processed']!=(a.manifest['expected_rows'] if a.origin=='ACTUAL' else 0) or manifest['disclosure']!='PRIVATE_NOT_ADMITTED':raise Blocked('partial source/scope/actual origin binding')
    expected=set(AdultMatrix().blobs())|{'uncertainty.local.json','summaries.local.json'}
    if set(manifest['files'])!=expected or {p.name for p in folder.iterdir()}!=expected|{'manifest.local.json'}:raise Blocked('partial file vocabulary')
    for name,h in manifest['files'].items():
        if Path(name).name!=name or sha256_file(folder/name)!=h:raise Blocked('partial file hash')
    matrix=AdultMatrix.decode({name:(folder/name).read_bytes() for name in AdultMatrix().blobs()},a.config['spec'])
    source_part=strict_json((a.root/(sweep+'.local.json')).read_text());expected_matrix=validate_part(source_part,a)
    if sha256_file(a.root/(sweep+'.local.json'))!=manifest['source_part_sha256'] or matrix.blobs()!=expected_matrix.blobs():raise Blocked('partial matrix/source closure')
    uncertainty=strict_json((folder/'uncertainty.local.json').read_text());validate_uncertainty_container(uncertainty,a.config['spec']);summaries=strict_json((folder/'summaries.local.json').read_text())
    if summaries['F_NATIONAL'][0] is not None or summaries['C_NATIONAL'][0] is not None:raise Blocked('partial cannot become national')
    return matrix,manifest,uncertainty
