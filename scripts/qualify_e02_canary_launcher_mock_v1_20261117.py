#!/usr/bin/env python3
"""L01 MOCK child: exact production main with inert private/network boundaries.

No actual owner/key/API. Real resource setters positive branch runs last.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import sys
import sysconfig
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
LAUNCHER=ROOT/'scripts/continue_e02_wrapper_crossmodel_canary_v1_20261117.py'
LAUNCHER_SHA='0ff0db64c9c89abc699b367b743945bf464e676f13278cacf5f76ece53be545d'
PHASE='START'
CLOSURE=ROOT/'reports/evidence_e02_canary_closed_replay_code_v1_20261117/EXACT_CLOSURE_WITH_HELPER.json'


def run(scratch,packet,release,launcher_sha):
    start=time.monotonic();counters={'owner':0,'key':0,'transport':0,'catalog':0,'execute':0};checks=[]
    def check(name,value):
        global PHASE
        PHASE=name
        checks.append({'case':name,'pass':bool(value)})
        if not value:raise AssertionError('MOCK_L01_CHECK_FAILED')
    scratch=scratch.resolve();assert scratch.is_dir()
    stdlib=Path(sysconfig.get_path('stdlib')).resolve()
    raw=LAUNCHER.read_bytes();assert hashlib.sha256(raw).hexdigest()==launcher_sha==LAUNCHER_SHA
    closure=json.loads(CLOSURE.read_bytes())
    allowed={ROOT/p['path'] for p in closure['project_pins']}|{LAUNCHER,Path(__file__).resolve()}
    reads=[len(raw)+CLOSURE.stat().st_size];writes=[0]
    def audit(event,args):
        if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','ctypes.dlopen'}:raise AssertionError('MOCK_NO_NETWORK_OR_CHILD')
        if event=='sqlite3.connect':raise AssertionError('MOCK_NO_OWNER_SQLITE')
        if event=='open' and not isinstance(args[0],int):
            path=Path(os.path.abspath(os.fsdecode(args[0])));resolved=path.resolve();flags=args[2]
            if path.name.startswith('.env') or 'SyntheticSocietyLab' in str(path):raise AssertionError('MOCK_NO_KEY_OR_OS_OWNER')
            if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                if not resolved.is_relative_to(scratch):raise AssertionError('MOCK_ONLY_AUTHORED_WRITES')
            else:
                if not (resolved in allowed or resolved.is_relative_to(scratch) or resolved.is_relative_to(stdlib)):raise AssertionError('MOCK_READ_SCOPE')
                if resolved.is_file():reads[0]+=resolved.stat().st_size
                if reads[0]>128*1024*1024:raise AssertionError('MOCK_READ_CAP')
    sys.addaudithook(audit)
    sys.pycache_prefix=str(scratch/'UNCREATED_PYC_CACHE')
    sys.path.insert(0,str(ROOT/'src'))
    from civiclab.common import canonical_bytes,canonical_hash
    from civiclab.e02 import wrapper_crossmodel_canary_v1 as pure
    from civiclab.e02 import wrapper_crossmodel_canary_v1_owner as owner_module
    from civiclab.e02 import wrapper_crossmodel_canary_v1_client as client
    from civiclab.e02 import exploratory_live_client_v1 as frozen
    namespace={'__name__':'AUTHORED_MOCK_LAUNCHER','__file__':str(LAUNCHER)}
    exec(compile(raw,str(LAUNCHER),'exec'),namespace)
    scope=scratch/'controls';scope.mkdir();namespace['SCOPE']=scope
    current={};sentinel_owner=object();sentinel_key=object();sentinel_transport=object();resource_observation={}
    def resources():
        remaining=signal.getitimer(signal.ITIMER_REAL)[0]
        return {'core':list(resource.getrlimit(resource.RLIMIT_CORE)),'CPU':list(resource.getrlimit(resource.RLIMIT_CPU)),'timer_near240':230<remaining<=240,'handler_callable':callable(signal.getsignal(signal.SIGALRM))}
    def fake_owner():
        counters['owner']+=1;resource_observation.update(resources())
        assert resource_observation=={'core':[0,0],'CPU':[59,60],'timer_near240':True,'handler_callable':True}
        return sentinel_owner
    def fake_key():counters['key']+=1;assert counters['owner']==1;return sentinel_key
    def fake_transport(key):counters['transport']+=1;assert key is sentinel_key;return sentinel_transport
    def fake_catalog(*_):counters['catalog']+=1;raise AssertionError('NO_CATALOG_IN_MOCK_MAIN')
    def fake_execute(q,**kw):
        counters['execute']+=1
        assert q==current['packet'] and kw['expected_packet_hash']==current['packet_sha'] and kw['expected_release_hash']==current['release_sha'] and kw['release']==current['release']
        assert kw['owner'] is sentinel_owner and kw['credential'] is sentinel_key and kw['transport'] is sentinel_transport and kw['catalog_fetch'] is fake_catalog
        assert kw['provenance']=='EXPLORATORY_REAL_MODEL'
        return {'kind':'MOCK_MAIN_ONLY','status':'MOCK_NO_INFERENCE','records':[]}
    def bind(q):
        q=deepcopy(q);q.pop('authority',None);q.pop('review',None)
        q['authority']={'kind':pure.AUTHORITY,'scope_hash':canonical_hash(q)}
        q['review']={'kind':'INDEPENDENT_WRAPPER_CANARY_REVIEW_V1','reviewer_role':'independent_auditor','review_id':'a'*32,'inputs_hash':canonical_hash(q)}
        l={'kind':'LEAD_WRAPPER_CANARY_RELEASE_V1','packet_sha256':canonical_hash(q),'code_hash':canonical_hash(pure.contract()),'review_sha256':canonical_hash(q['review']),'maximum_POSTs':1,'scope':'ORIGINAL45_ONLY_NOT_FULL80'}
        return q,l
    def controls(q,l):
        for name in ('packet.json','lead-release.json'):
            path=scope/name
            if path.exists() or path.is_symlink():path.unlink()
        qb=canonical_bytes(q);lb=canonical_bytes(l)
        (scope/'packet.json').write_bytes(qb);(scope/'lead-release.json').write_bytes(lb);writes[0]+=len(qb)+len(lb)
        current.update(packet=q,release=l,packet_sha=hashlib.sha256(qb).hexdigest(),release_sha=hashlib.sha256(lb).hexdigest())
    def invoke(packet_sha=None,release_sha=None):
        argv=[str(LAUNCHER),'--packet-sha256',packet_sha or current['packet_sha'],'--release-sha256',release_sha or current['release_sha']]
        with patch.object(sys,'argv',argv),patch.object(sys,'stdout',io.StringIO()):namespace['main']()
    def denied(name,call):
        before=dict(counters)
        try:call()
        except (ValueError,RuntimeError,OSError,AssertionError):blocked=True
        else:blocked=False
        check(name,blocked and counters==before and all(v==0 for v in counters.values()))
    with patch.object(owner_module,'CanaryOwnerV1',side_effect=fake_owner),patch.object(frozen,'_read_environment_key',side_effect=fake_key),patch.object(frozen,'_transport',side_effect=fake_transport),patch.object(frozen,'_fetch_public_catalog',fake_catalog),patch.object(client,'execute',side_effect=fake_execute):
        controls(packet,release)
        denied('packet_hash_before_boundaries',lambda:invoke(packet_sha='0'*64))
        denied('release_hash_before_boundaries',lambda:invoke(release_sha='0'*64))
        q,l=bind(dict(packet,extra_MOCK=True));controls(q,l)
        denied('packet_extra_schema_before_boundaries',invoke)
        q,l=bind(packet);q['review']['inputs_hash']='0'*64;l['packet_sha256']=canonical_hash(q);l['review_sha256']=canonical_hash(q['review']);controls(q,l)
        denied('review_binding_before_boundaries',invoke)
        q,l=bind(packet);q['owner_id']='b'*32;q,l=bind(q);controls(q,l)
        denied('owner_parent_binding_before_boundaries',invoke)
        controls(packet,release);(scope/'packet.json').write_bytes(b' '*65537);writes[0]+=65537
        denied('packet_oversize_before_boundaries',invoke)
        controls(packet,release);(scope/'packet.json').unlink();(scope/'packet.json').symlink_to(scope/'lead-release.json')
        denied('packet_symlink_before_boundaries',invoke)
        controls(packet,release);outside=scratch/'wrong-scope.json';outside.write_bytes(b'{}');writes[0]+=2
        denied('wrong_scope_read_exact',lambda:namespace['read_exact'](outside,hashlib.sha256(b'{}').hexdigest()))
        boundary=scope/'boundary.json';padded=b'{}'+b' '*65534;boundary.write_bytes(padded);writes[0]+=len(padded)
        check('read_exact_accepts_stable65536',namespace['read_exact'](boundary,hashlib.sha256(padded).hexdigest())=={})
        with patch.object(resource,'setrlimit',side_effect=OSError('AUTHORED_SETTER_FAILURE')):denied('resource_setter_failure_before_boundaries',invoke)
        with patch.object(resource,'setrlimit'),patch.object(signal,'signal'),patch.object(signal,'setitimer',side_effect=OSError('AUTHORED_TIMER_FAILURE')):denied('timer_failure_before_boundaries',invoke)
        # Execute the exact original __main__ AST block with routed globals.
        block=next(n for n in ast.parse(raw).body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='__name__')
        namespace['__name__']='__main__';captured=io.StringIO()
        with patch.object(sys,'argv',[str(LAUNCHER),'--packet-sha256','0'*64,'--release-sha256',current['release_sha']]),patch.object(sys,'stdout',captured):
            try:exec(compile(ast.Module(body=[block],type_ignores=[]),str(LAUNCHER),'exec'),namespace)
            except SystemExit as error:code=error.code
            else:code=0
        namespace['__name__']='AUTHORED_MOCK_LAUNCHER';failure=json.loads(captured.getvalue())
        check('generic_main_failure_closed_safe',code==1 and failure=={'status':'STOPPED_NO_RETRY','original_full80_analysis':'NOT_RUN_INCOMPLETE'} and 'Traceback' not in captured.getvalue() and all(v==0 for v in counters.values()))
        # Only positive main runs real irreversible CPU/core setters and real timer.
        invoke()
        check('positive_exact_main_inert_boundaries',counters=={'owner':1,'key':1,'transport':1,'catalog':0,'execute':1})
        handler=signal.getsignal(signal.SIGALRM)
        try:handler(signal.SIGALRM,None)
        except TimeoutError:expired=True
        else:expired=False
        check('actual_installed_timeout_handler',expired)
    # Disable only while leaving this disposable child. CPU/core remain unchanged.
    signal.setitimer(signal.ITIMER_REAL,0)
    return {'kind':'MOCK_L01_EXACT_MAIN_QUALIFICATION','response_provenance':'MOCK','checks':checks,'passed':all(c['pass'] for c in checks),'counters':counters,'real_resource_observation':resource_observation,'launcher_sha256':launcher_sha,'charged_read_bytes':reads[0],'authored_write_bytes':writes[0],'wall_seconds':time.monotonic()-start,'API_calls':0,'real_owner_constructor_calls':0,'real_key_reads':0,'inference_calls':0,'note':'Exact main passed EXPLORATORY_REAL_MODEL string into inert execute; no actual execution or release. Stable authored filesystem only.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch',type=Path,required=True);parser.add_argument('--launcher-sha256',required=True)
    args=parser.parse_args();scratch=args.scratch.resolve()
    packet=json.loads((scratch/'mock-packet.input.json').read_bytes());release=json.loads((scratch/'mock-release.input.json').read_bytes())
    result=run(scratch,packet,release,args.launcher_sha256)
    print(json.dumps(result,sort_keys=True));return 0 if result['passed'] else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except SystemExit:raise
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        print(json.dumps({'kind':'MOCK_L01_EXACT_MAIN_QUALIFICATION','status':'MOCK_STOPPED','phase':PHASE,'error_type':type(error).__name__ if type(error) in (AssertionError,ValueError,RuntimeError,OSError,TypeError) else 'OTHER','API_calls':0,'real_key_reads':0,'real_owner_calls':0}))
        raise SystemExit(1)
