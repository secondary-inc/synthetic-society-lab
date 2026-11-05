"""Exact caller refusal/credential-lifetime tests; every external boundary fake."""
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import _Credential
from test_production_price_v4 import T0

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
if str(SCRIPTS) not in sys.path:sys.path.insert(0,str(SCRIPTS))
import run_e02_reviewed_once as caller


@contextmanager
def fake_call():
    export={'header':{'authored':True},'head':{'authored':True},'history':[],
            'active_approval_hash':'0'*64,'rows':{},'statistics_claims':[]}
    prior={'header_hash':canonical_hash(export['header']),'head':export['head'],
           'history_hash':canonical_hash([]),'active_approval_hash':'0'*64,
           'rows_hash':canonical_hash({}),'statistics_claims_hash':canonical_hash([])}
    stats={'data':{'authored':True}}
    q={'policy':{'kind':'LIMITED_PILOT_RECOVERY_POLICY_V1','run_id':caller.RUN,
        'predecessor':prior,'valid_from_utc':'2026-11-03T00:00:00+00:00',
        'valid_until_utc':'2026-11-06T00:00:00+00:00','recovery':{
            'source_export_sha256':caller.SOURCES['export'][1],
            'evidence_audit_sha256':caller.SOURCES['audit'][1],
            'model_identity_source_sha256':caller.SOURCES['identity'][1],
            'statistics_raw_sha256':caller.SOURCES['statistics'][1],'statistics':stats}}}
    source={caller.ROOT/path:canonical_bytes(export if name=='export' else stats if name=='statistics' else {})
            for name,(path,sha) in caller.SOURCES.items()}
    def read(path,sha,limit=524288):
        if path==caller.BASE/'packet.local.json':return canonical_bytes(q)
        if path==Path(caller.__file__).resolve():return b'AUTHORED_CALLER'
        return source[path]
    with patch.object(caller,'_read',side_effect=read) as reader, \
         patch.object(caller,'validate_packet',side_effect=lambda p,**kw:deepcopy(p)), \
         patch.object(caller,'new_operation_time',return_value=T0), \
         patch.object(caller,'_write') as write, \
         patch.object(caller,'_credential',return_value=_Credential('AUTHORED_ONLY_NO_REAL_KEY')) as credential, \
         patch.object(caller,'execute_authored',return_value={'status':'AUTHORED_COMPLETE'}) as execute, \
         patch.dict(os.environ,{'OPENROUTER_API_KEY':'AUTHORED_PREVIOUS'},clear=False):
        yield q,reader,write,credential,execute,read


class CallerTests(unittest.TestCase):
    def test_changed_caller_packet_or_any_source_precedes_key_execution(self):
        paths=([Path(caller.__file__).resolve(),caller.BASE/'packet.local.json']+
            [caller.ROOT/path for path,sha in caller.SOURCES.values()])
        for target in paths:
            with self.subTest(target=target),fake_call() as (q,reader,write,key,execute,native):
                def changed(path,*args,**kwargs):
                    if path==target:raise ExecutionBlocked('authored source mismatch')
                    return native(path,*args,**kwargs)
                reader.side_effect=changed
                with self.assertRaises(ExecutionBlocked):caller.main('0'*64,'1'*64)
                write.assert_not_called();key.assert_not_called();execute.assert_not_called()

    def test_foreign_provenance_and_expired_window_precede_intent_key(self):
        for name in ('export','audit','identity','statistics','predecessor','expiry','run'):
            with self.subTest(name=name),fake_call() as (q,reader,write,key,execute,_):
                p=q['policy'];r=p['recovery']
                if name in ('export','audit','identity','statistics'):
                    field={'export':'source_export_sha256','audit':'evidence_audit_sha256',
                           'identity':'model_identity_source_sha256','statistics':'statistics_raw_sha256'}[name]
                    r[field]='0'*64
                elif name=='predecessor':p['predecessor']['rows_hash']='0'*64
                elif name=='expiry':p['valid_until_utc']='2000-01-01T00:00:00+00:00'
                else:p['run_id']='FOREIGN'
                with self.assertRaises(ExecutionBlocked):caller.main('0'*64,'1'*64)
                write.assert_not_called();key.assert_not_called();execute.assert_not_called()

    def test_consumed_intent_precedes_credential_or_runner(self):
        with fake_call() as (_,reader,write,key,execute,_):
            write.side_effect=FileExistsError('AUTHORED_CONSUMED')
            with self.assertRaises(FileExistsError):caller.main('0'*64,'1'*64)
            key.assert_not_called();execute.assert_not_called()

    def test_process_environment_restored_success_and_exception(self):
        for fails in (False,True):
            with self.subTest(fails=fails),fake_call() as (_,reader,write,key,execute,_):
                def run(*args,**kwargs):
                    self.assertEqual(os.environ['OPENROUTER_API_KEY'],'AUTHORED_ONLY_NO_REAL_KEY')
                    self.assertEqual(kwargs['response_provenance'],'EXPLORATORY_REAL_MODEL')
                    if fails:raise ExecutionBlocked('AUTHORED_STOP')
                    return {'status':'AUTHORED_COMPLETE'}
                execute.side_effect=run
                if fails:
                    with self.assertRaises(ExecutionBlocked):caller.main('0'*64,'1'*64)
                else:self.assertEqual(caller.main('0'*64,'1'*64)['status'],'AUTHORED_COMPLETE')
                self.assertEqual(os.environ['OPENROUTER_API_KEY'],'AUTHORED_PREVIOUS')
                key.assert_called_once();execute.assert_called_once();write.assert_called_once()


if __name__=='__main__':unittest.main()
