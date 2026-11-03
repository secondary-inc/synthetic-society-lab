"""Separate F local admission; checked-in actual gates null; fresh release required."""
from copy import deepcopy
import csv
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import zipfile
from ..common import canonical_hash,sha256_file,atomic_json
from .national_budget import Blocked
from .full_adult_types_v1_2 import strict_json

ROOT=Path(__file__).resolve().parents[3]
_TOKEN=object()
_ACTUAL_TOKEN=object()


def detached(value):
    """Built-in value tree only, captured BEFORE validation or any I/O."""
    t=type(value)
    if t is dict:
        if any(type(k) is not str for k in value):raise Blocked('string metadata keys required')
        return {k:detached(v) for k,v in value.items()}
    if t is list:return [detached(v) for v in value]
    if t in (str,int,bool) or value is None:return value
    if t is float:
        import math
        if math.isfinite(value):return value
    raise Blocked('non-built-in/nonfinite metadata input refused')


def _bound_bytes(path,expected=None):
    # Hash AND parse the same bounded byte snapshot; never hash then reread.
    with Path(path).open('rb') as stream:data=stream.read(8*1024**2+1)
    if len(data)>8*1024**2 or expected is not None and hashlib.sha256(data).hexdigest()!=expected:raise Blocked('metadata snapshot changed/oversized')
    return bytes(data)


def _load_frozen():
    from .full_adult_types_v1_2 import strict_json
    c=detached(strict_json(_bound_bytes(ROOT/'configs/e02_F_WY_LOCAL_IMPLEMENTATION_v1.json')));refs={}
    for name,h in c['required_files'].items():
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or path.relative_to(ROOT).parts[0] not in ('configs','docs','reports','src','tests'):raise Blocked('metadata reference escapes code/document domain')
        refs[name]=_bound_bytes(path,h)
    if c['proposal'] not in refs:raise Blocked('source contract must be a frozen reference')
    proposal=detached(strict_json(refs[c['proposal']]))
    if c['limits']!=proposal['native_limits_unchanged'] or c['storage']!=proposal['native_F_storage_unchanged']:raise Blocked('native limits changed')
    if any(v is not None for v in c['actual_approvals'].values()) or c['actual_authority']!=0:raise Blocked('checked-in actual release remains null')
    return c,refs


def load_config():return _load_frozen()[0]


def _release(config):
    config=detached(config)
    if type(config) is not dict or type(config.get('actual_authority')) is not int or config.get('actual_authority')!=1 or config.get('scope')!='NEW_F_WY_LOCAL_ACTUAL_ENGINEERING':raise Blocked('fresh F actual release absent')
    approvals=config.get('actual_approvals',{})
    if set(approvals)!={'adapter_code','exact_source','execution','disclosure','fit'} or approvals['disclosure'] is not None or approvals['fit'] is not None or not all(type(approvals[k]) is dict for k in ('adapter_code','exact_source','execution')):raise Blocked('fresh F code/source/execution approvals required')
    baseline,reference_bytes=_load_frozen();baseline=detached(baseline)
    if any(type(v) is not bytes for v in reference_bytes.values()):raise Blocked('frozen reference bytes required')
    reference_bytes={k:v for k,v in reference_bytes.items()};excluded={'actual_authority','actual_approvals','scope'}
    design={k:v for k,v in config.items() if k not in excluded}
    if design!={k:v for k,v in baseline.items() if k not in excluded}:raise Blocked('actual release changes frozen code/source/resource design')
    statuses={'adapter_code':'PASS_F_WY_LOCAL_ADAPTER_CODE_AND_AUTHORED_FIXTURES','exact_source':'PASS_F_WY_EXACT_CACHE_SOURCE_ADMISSION_ONLY','execution':'APPROVE_F_WY_ONE_SOURCE_TWO_SWEEP_LOCAL_EXECUTION'};records={}
    for key in statuses:
        ref=approvals[key]
        if set(ref)!={'path','sha256'} or type(ref['path']) is not str or not ref['path'].startswith('reports/'):raise Blocked('new approval reference domain')
        path=(ROOT/ref['path']).resolve()
        if not path.is_relative_to(ROOT/'reports'):raise Blocked('fresh F approval outside metadata domain')
        audit=detached(strict_json(_bound_bytes(path,ref['sha256'])))
        if audit.get('status')!=statuses[key] or audit.get('auditor_role')!='independent_auditor' or audit.get('reviewed_design_sha256')!=canonical_hash(design) or audit.get('reviewed_required_files')!=config['required_files']:raise Blocked('new F approval status/design/code mismatch; old C approval does not transfer')
        records[key]=audit
    execution=records['execution']
    if execution.get('adapter_code_approval_sha256')!=approvals['adapter_code']['sha256'] or execution.get('exact_source_approval_sha256')!=approvals['exact_source']['sha256'] or execution.get('source_contract_sha256')!=hashlib.sha256(reference_bytes[config['proposal']]).hexdigest() or execution.get('network_requests_authorized')!=0 or execution.get('model_calls_authorized')!=0 or execution.get('disclosure_authorized') is not False or execution.get('fit_authorized') is not False:raise Blocked('one-source release transitive scope mismatch')
    expected=detached(strict_json(reference_bytes[config['proposal']])['source'])
    if records['exact_source'].get('archive_sha256')!=expected['archive']['sha256'] or records['exact_source'].get('header_sha256')!=expected['header']['sha256']:raise Blocked('fresh exact-cache/header source binding')
    identity=records['exact_source'].get('source_identity')
    if type(identity) is not dict or set(identity)!={'device','inode','bytes','mtime_ns','ctime_ns'} or any(type(v) is not int or v<0 for v in identity.values()) or identity['bytes']!=expected['archive']['bytes']:raise Blocked('fresh source stat admission required')
    if not records['adapter_code'].get('fixture_tests_passed') is True:raise Blocked('actual adapter fixture admission absent')
    return records,expected


def _actual_manifest(config,records,expected):
    m={'origin':'ACTUAL_WY_EXACT_LOCAL_V1','period':config['period'],'state':'56','archive_bytes':expected['archive']['bytes'],'archive_sha256':expected['archive']['sha256'],'person':expected['person_member']['name'],'companion':expected['companion']['name'],'members':[],'header_bytes':expected['header']['bytes'],'header_sha256':expected['header']['sha256'],'columns':285,'expected_rows':expected['person_member']['expected_all_age_rows'],'metadata_hashes':config['metadata_hashes'],'parent_provenance':config['parent_provenance'],'expected_identity':records['exact_source']['source_identity']}
    for member in expected['literal_members']:
        name=member['name'];h=expected['person_member']['sha256'] if name==m['person'] else expected['companion']['sha256']
        m['members'].append({'name':name,'bytes':member['declared_uncompressed_bytes'],'compressed_bytes':member['compressed_bytes'],'crc32':member['crc32'],'sha256':h})
    return m


def admit_actual(config=None,**kwargs):
    # The null default and all caller path/flag shortcuts refuse BEFORE any I/O.
    if kwargs:raise Blocked('no caller source path/flag/old-permission override')
    config=detached(config)
    records,expected=_release(config)
    relative=records['execution'].get('output_directory','')
    if type(relative) is not str or not relative.startswith('data/processed/e02_F_wy_private/') or '..' in Path(relative).parts:raise Blocked('private exact output admission required')
    root=(ROOT/relative).resolve()
    if not root.is_relative_to(ROOT/'data/processed/e02_F_wy_private') or root.exists():raise Blocked('new admitted output directory required; no reset')
    # Source filesystem work belongs to reserved/supervised ENROLL, even
    # after release. A fixed lexical path is not opened/stat/resolved here.
    path=ROOT/expected['archive']['path']
    m=_actual_manifest(config,records,expected)
    root.mkdir(parents=True);(root/'.F_WY_ACTUAL_LOCAL_ONLY').write_text('ACTUAL_F_WY_PRIVATE_ENGINEERING_V1\n')
    a=ActualAdmission(root,path,json.dumps(m,sort_keys=True),json.dumps(config,sort_keys=True),_ACTUAL_TOKEN)
    atomic_json(root/'admission.local.json',{'schema':'E02_F_WY_ACTUAL_ADMISSION_V1','config':config,'manifest':m,'actual_person_rows_processed':0,'GETs':0})
    return a


@dataclass(frozen=True)
class FixtureAdmission:
    root: Path
    path: Path
    manifest_json: str
    config_json: str
    token: object
    @property
    def origin(self):return 'AUTHORED'
    @property
    def manifest(self):return json.loads(self.manifest_json)
    @property
    def config(self):return json.loads(self.config_json)


@dataclass(frozen=True)
class ActualAdmission(FixtureAdmission):
    @property
    def origin(self):return 'ACTUAL'


def require_admission(a):
    if type(a) is FixtureAdmission:
        if a.token is not _TOKEN or a.path.parent!=a.root/'inputs' or a.manifest['origin']!='AUTHORED_WY_LOCAL_V1':raise Blocked('minted authored source required')
        if not (a.root/'.F_WY_AUTHORED_ONLY').is_file() or (a.root/'.F_WY_AUTHORED_ONLY').read_text()!='MOCK_F_WY_LOCAL_V1\n':raise Blocked('authored marker lost; no rebootstrap')
    elif type(a) is ActualAdmission:
        if a.token is not _ACTUAL_TOKEN or a.manifest['origin']!='ACTUAL_WY_EXACT_LOCAL_V1':raise Blocked('new actual capability required')
        _,expected=_release(a.config)
        marker=a.root/'.F_WY_ACTUAL_LOCAL_ONLY'
        if not marker.is_file() or marker.read_text()!='ACTUAL_F_WY_PRIVATE_ENGINEERING_V1\n':raise Blocked('actual private marker lost')
        if a.path!=ROOT/expected['archive']['path']:raise Blocked('actual source path binding')
    else:raise Blocked('flag/old approval is not F source admission')
    return a


def require_fixture(a):
    if type(a) is not FixtureAdmission:raise Blocked('authored fixture capability required')
    return require_admission(a)


def create_fixture(root,rows,*,edit=None,config=None):
    """Mint from authored row dictionaries, NEVER accept/copy an external archive."""
    baseline=load_config()
    if config is not None and config!=baseline:raise Blocked('fixture config cannot override native pins/limits/authority')
    c=deepcopy(baseline);root=Path(root).resolve()
    if root.exists():raise Blocked('new authored workspace required; no reset')
    if any(v is not None for v in c['actual_approvals'].values()) or c['actual_authority']!=0:raise Blocked('fixture cannot carry actual authority')
    root.mkdir(parents=True);(root/'inputs').mkdir();(root/'.F_WY_AUTHORED_ONLY').write_text('MOCK_F_WY_LOCAL_V1\n')
    atomic_json(root/'runtime-config.local.json',c)
    fields=c['required_fields']+['SERIALNO']+['UNUSED'+str(i) for i in range(193)]
    if len(fields)!=285:raise Blocked('frozen91-field projection')
    if edit and edit[0]=='header':fields[-1]=fields[0]
    records=[fields]+[[r.get(f,'') for f in fields] for r in rows]
    if edit and edit[0] in ('missing','extra'):
        mode,index=edit
        if mode=='missing':records[index+1]=records[index+1][:-1]
        else:records[index+1].append('PRIVATE_F_EXTRA, "quoted"')
    output=io.StringIO();csv.writer(output).writerows(records);body=output.getvalue().encode()
    if edit and edit[0]=='quoting':body=body.split(b'\n',1)[0]+b'\n"unterminated'
    pdf=b'%PDF-AUTHORED-F-WY-ONLY-NOT-EXECUTED';person='psam_p56.csv';companion='ACS2020_2024_PUMS_README.pdf';path=root/'inputs/authored-WY.zip'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr(zipfile.ZipInfo(person,(2026,1,1,0,0,0)),body)
        z.writestr(zipfile.ZipInfo(companion,(2026,1,1,0,0,0)),pdf)
        if edit and edit[0]=='member':z.writestr('../extra',b'PRIVATE')
    members=[]
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            raw=z.read(info.filename);members.append({'name':info.filename,'bytes':len(raw),'compressed_bytes':info.compress_size,'crc32':info.CRC,'sha256':hashlib.sha256(raw).hexdigest()})
    m={'origin':'AUTHORED_WY_LOCAL_V1','period':c['period'],'state':'56','archive_bytes':path.stat().st_size,'archive_sha256':sha256_file(path),'person':person,'companion':companion,'members':members,'header_bytes':len(body.splitlines(keepends=True)[0]),'header_sha256':hashlib.sha256(body.splitlines(keepends=True)[0]).hexdigest(),'columns':285,'expected_rows':len(rows),'metadata_hashes':c['metadata_hashes'],'parent_provenance':c['parent_provenance']}
    a=FixtureAdmission(root,path,json.dumps(m,sort_keys=True),json.dumps(c,sort_keys=True),_TOKEN)
    atomic_json(root/'fixture-admission.local.json',{'kind':'MOCK_AUTHORED_CAPABILITY_NOT_ACTUAL_APPROVAL','manifest':m,'config_sha256':canonical_hash(c)})
    return a


def reopen_actual_for_review(config=None):
    """Reopen one admitted existing private run, never recreate/reset its ledger."""
    config=detached(config)
    records,expected=_release(config);relative=records['execution'].get('output_directory','')
    if type(relative) is not str or not relative.startswith('data/processed/e02_F_wy_private/') or '..' in Path(relative).parts:raise Blocked('fixed existing private review directory required')
    root=(ROOT/relative).resolve()
    if not root.is_relative_to(ROOT/'data/processed/e02_F_wy_private') or not root.is_dir():raise Blocked('existing private run absent')
    data=detached(strict_json(_bound_bytes(root/'admission.local.json')));m=_actual_manifest(config,records,expected)
    if data['config']!=config or data['manifest']!=m:raise Blocked('recorded release/manifest changed')
    a=ActualAdmission(root,ROOT/expected['archive']['path'],json.dumps(m,sort_keys=True),json.dumps(config,sort_keys=True),_ACTUAL_TOKEN)
    require_admission(a)
    if not (root/'.F_WY_LEDGER_INITIALIZED').is_file() or not (root/'ledger/state.json').is_file():raise Blocked('review cannot initialize a missing ledger')
    from .f_actual_ledger_v1 import PilotLedger
    PilotLedger(a).snapshot();return a
