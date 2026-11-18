"""Pure exact candidate joins/compiler, no owner constructor or network."""
import os,sys,time,signal,resource,json,hashlib,math,decimal,ssl,http.client,urllib.request,subprocess
from pathlib import Path
START=time.monotonic();resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(59,60))
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('OFFLINE120')));signal.alarm(120)
ROOT=Path.cwd();BASE=ROOT/'data/processed/e02_canary_packet_candidate_20261117_01'
refs={
 BASE/'packet.candidate.json':(6201,'a28d31add2793eb241a5c4e54708a5c07eb1ebe89c3373d2cd1d381a14e8edbf'),
 BASE/'lead-release.candidate.json':(341,'6e52e0ead3bb19cb002a1febf738bc38907c66019443b8c189ddd1987a7c5cfc'),
 BASE/'caller-review.candidate.json':(3112,'ee762ead54a37b9ed21e6ad5c3878aa3fd8a69f3013e1a4ed336db8ca5d0bb3e'),
 ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/post-run-owner-export.local.json':(3893676,'ba726232dbc1375f5e7c48d5f96f3bdec70a9812a25cacfe3c00640197aa6f66'),
 ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/packet.local.json':(7339,'3b29761579efaabee4ef03c6c71ae5f476ced64980fa6d362c5eea55489457ec'),
 ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_price_01/catalog-A.json':(2359,'59c4fcc5ec213b8aae3019949267bd0f27f6bdfc95bee436c06a85ffc8ef9ee9'),
 ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_price_01/catalog-B.json':(3569,'59c512102ac025f51b2e8a0b038170b5f29901a4a68421dec926d074f9a02237')}
closure_path=ROOT/'reports/evidence_e02_canary_closed_replay_code_v1_20261117/EXACT_CLOSURE_WITH_HELPER.json'
raw=closure_path.read_bytes();assert hashlib.sha256(raw).hexdigest()=='f703e5dd9178c2558ba4b62c13846412257fd093d9448a78612c8ed829439750'
closure=json.loads(raw);permitted={ROOT/p['path'] for p in closure['project_pins']}|set(refs)
permitted|={ROOT/'scripts/launch_e02_canary_with_saved_key_20261117.py'}
stdlib=Path(os.__file__).resolve().parent;meter={'read_bytes':len(raw),'denials':0}
def audit(event,args):
    if event.startswith(('socket.','subprocess.','ctypes.')) or event in {'os.system','os.fork','os.posix_spawn','os.exec'}:
        meter['denials']+=1;raise PermissionError('NO_EXTERNAL')
    if event=='open':
        name,mode,flags=args
        if type(name) is int:raise PermissionError('NO_DESCRIPTOR')
        p=Path(os.fsdecode(name)).absolute()
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('NO_WRITES')
        if p.name.startswith('.env') or 'Application Support/SyntheticSocietyLab' in str(p):raise PermissionError('NO_KEY_CURRENT_OWNER')
        if p not in permitted and not p.is_relative_to(stdlib):
            # -B may probe nonexistent bytecode, but it cannot read such files.
            if not (p.suffix=='.pyc' and not p.exists()):
                meter['denials']+=1;raise PermissionError('UNLISTED_INPUT')
        if p.is_file():meter['read_bytes']+=p.stat().st_size+1
        if meter['read_bytes']>33554432:raise RuntimeError('READ_BOUND')
cache=ROOT/'reports/evidence_independent_e02_exact_canary_packet_20261117_01/UNCREATED_PYC_CACHE'
assert not cache.exists() and not cache.is_symlink()
sys.pycache_prefix=str(cache)
sys.addaudithook(audit)
data={}
for p,(size,expected) in refs.items():
    b=p.read_bytes();assert len(b)==size and hashlib.sha256(b).hexdigest()==expected
    data[p]=b
sys.path.insert(0,str(ROOT/'src'))
from civiclab.common import canonical_hash,canonical_bytes
from civiclab.e02 import wrapper_crossmodel_canary_v1 as p
from civiclab.e02.wrapper_crossmodel_canary_v1_client import validate_release
from civiclab.e02.wrapper_crossmodel_canary_v1_owner import ANCHOR,parent_binding
q=json.loads(data[BASE/'packet.candidate.json']);release=json.loads(data[BASE/'lead-release.candidate.json']);caller=json.loads(data[BASE/'caller-review.candidate.json'])
validate_release(release,q,refs[BASE/'packet.candidate.json'][1],refs[BASE/'lead-release.candidate.json'][1])
export=json.loads(data[ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/post-run-owner-export.local.json'])
old=json.loads(data[ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/packet.local.json'])
assert q['expected_head']==export['head'] and q['parent_binding']==ANCHOR==parent_binding(export)
assert q['owner_id']==export['header']['owner_id'] and q['parent_key']==p.identity(q['owner_id'])
assert canonical_hash(old)==p.PARENT_PACKET_SHA and canonical_hash(export['wrapper_crossmodel']['packet'])==p.PARENT_PACKET_SHA
for role in ('A','B'):
    raw=data[ROOT/f'data/processed/e02_wrapper_crossmodel_v1_20261115_price_01/catalog-{role}.json']
    expected=p.lease_historical_catalog(raw,old['price_release'][role],expected_release_hash=canonical_hash(old['price_release'][role]),valid_from=q['valid_from_utc'],valid_until=q['valid_until_utc'])
    assert expected==q['price_release'][role]
compiled,baseline=p.compile_slot(export['wrapper_crossmodel'],q['price_release']['B']['terms'])
assert baseline==caller['baseline13_sha256']==ANCHOR['baseline13']
assert compiled['envelope']==caller['compiled_envelope']
assert compiled['payload_sha256']==canonical_hash(compiled['payload'])
assert compiled['execution_order']==45 and compiled['pair_seed']==2315288556
assert compiled['payload']['model']=='qwen/qwen3-30b-a3b-instruct-2507'
assert compiled['payload']['provider']['allow_fallbacks'] is False and compiled['payload']['provider']['only']==['nebius/fp8']
assert compiled['payload']['tools']==[] and compiled['payload']['plugins']==[] and compiled['payload']['tool_choice']=='none'
assert compiled['payload']['stream'] is False and compiled['payload']['max_completion_tokens']==256
assert q['bounds']==p.BOUNDS==caller['bounds'] and caller['original_slot']==45 and caller['pair_seed']==p.SEED
for v in caller['external_caller_pins']:
    raw=(ROOT/v['path']).read_bytes();assert len(raw)==v['bytes'] and hashlib.sha256(raw).hexdigest()==v['sha256']
assert caller['packet_sha256']==canonical_hash(q) and caller['lead_release_candidate_sha256']==canonical_hash(release)
assert caller['review_id']==q['review']['review_id']
reserve=compiled['envelope']['reserved_microusd'];assert reserve==1003<=1785
assert export['consumed']['total']==16149 and len(export['rows'])==194 and len(export['history'])==1180
assert sorted(r['charged'] for r in export['rows'].values() if r['status']!='PHASE_COMMITTED')==[340,340,775,788,1008]
assert export['wrapper_crossmodel']['stopped'] is True
result={'kind':'INDEPENDENT_EXACT_CANARY_PACKET_OFFLINE_CHECK','status':'OFFLINE_JOINS_PASS_LIVE_NOT_EXECUTED',
 'packet_sha256':canonical_hash(q),'release_sha256':canonical_hash(release),'caller_sha256':canonical_hash(caller),
 'payload_sha256':compiled['payload_sha256'],'baseline13_sha256':baseline,'compiled_envelope':compiled['envelope'],
 'code_hash':q['code_hash'],'window':{'from':q['valid_from_utc'],'until':q['valid_until_utc']},
 'new_reservation_microusd':reserve,'conservative_total_if_reserved':16149+reserve,'original_closed_exposure_microusd':16149,
 'old5holds_preserved':True,'new_model_calls':0,'owner_constructor_calls':0,'key_reads':0,'network_calls':0,
 'guard':meter,'wall_seconds':time.monotonic()-START,'runtime':sys.version.split()[0],
 'fresh_current_owner':'NOT_RUN_RUNTIME_LOCKED_OPEN_REQUIRED','fresh_catalog':'NOT_RUN_TWO_COUNTED_GETS_REQUIRED'}
print(json.dumps(result,sort_keys=True))
