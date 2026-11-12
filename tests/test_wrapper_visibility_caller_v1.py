"""Caller provenance and one-shot credential lifetime; entirely offline."""
from contextlib import contextmanager
from pathlib import Path
import os
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch,Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_wrapper_visibility_once as m
from run_e02_continuation_once import read as real_read
from civiclab.common import canonical_bytes,canonical_hash
from civiclab.production_admission_v4 import _Credential
from civiclab.e02 import wrapper_visibility_client_v1 as client
from test_production_price_v4 import T0


@contextmanager
def case():
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp).resolve()
        e={'head':{},'history':[],'rows':{},'study':{},'continuation':{},'alignment_followup':{},'issue_cue_crossmodel':{},'issue_cue_crossmodel_recovery':{},'consumed':{},'statistics_claims':[]}
        prior={'head':{},'history_hash':canonical_hash([]),'rows_hash':canonical_hash({}),
            'study_hash':canonical_hash({}),'continuation_hash':canonical_hash({}),'alignment_hash':canonical_hash({}),'crossmodel_hash':canonical_hash({}),'recovery_hash':canonical_hash({}),
            'claims_hash':canonical_hash([]),'consumed':{}}
        b={'policy':{'run_id':m.RUN,'valid_from_utc':'2026-11-03T11:59:00+00:00',
            'valid_until_utc':'2026-11-03T13:00:00+00:00','predecessor':prior}}
        def read(path,*args):
            if path.name=='packet.local.json':return canonical_bytes(b)
            if path.name=='post-run-owner-export.local.json':return canonical_bytes(e)
            return b'{}'
        with patch.object(m,'BASE',base),patch.object(m,'read',side_effect=read), \
             patch.object(m,'validate_packet',side_effect=lambda x,**kw:x), \
             patch.object(m,'new_operation_time',return_value=T0), \
             patch.object(m,'_credential',return_value=_Credential('AUTHORED_ONLY_KEY_123456')) as secret, \
             patch.object(client,'execute_wrapper_visibility',return_value={'status':'MOCK_DONE'}) as execute:
            yield base,b,secret,execute


class CallerTests(unittest.TestCase):
    def test_exact_large_prior_export_crosses_default_reader_cap_safely(self):
        for mode in ('exact','over_limit','wrong_hash'):
            with self.subTest(mode=mode),case() as (base,b,secret,execute):
                old=base/'old';old.mkdir()
                e={'head':{},'history':[],'rows':{},'study':{},'continuation':{},
                   'alignment_followup':{},'issue_cue_crossmodel':{},
                   'issue_cue_crossmodel_recovery':{},'consumed':{},'statistics_claims':[],
                   'authored_padding':''}
                e['authored_padding']='X'*(m.EXPORT_BYTES-len(canonical_bytes(e)))
                raw=canonical_bytes(e);self.assertEqual(len(raw),2285561)
                path=old/'post-run-owner-export.local.json';path.write_bytes(raw)
                digest=hashlib.sha256(raw).hexdigest()
                with self.assertRaises(m.ExecutionBlocked):real_read(path,digest)
                if mode=='over_limit':path.write_bytes(raw+b' ')
                if mode=='wrong_hash':digest='0'*64
                stub=m.read.side_effect
                def reader(p,*args):
                    return real_read(p,*args) if p==path else stub(p,*args)
                m.read.side_effect=reader
                with patch.object(m,'OLD',old),patch.object(m,'EXPORT_SHA',digest):
                    if mode=='exact':
                        self.assertEqual(m.main('a'*64,'b'*64),{'status':'MOCK_DONE'})
                        secret.assert_called_once();execute.assert_called_once()
                    else:
                        with self.assertRaises(m.ExecutionBlocked):m.main('a'*64,'b'*64)
                        secret.assert_not_called();execute.assert_not_called()
                        self.assertFalse((base/'execution-intent.local.json').exists())

    def test_one_intent_consumed_and_environment_restored(self):
        with case() as (base,b,secret,execute),patch.dict(os.environ,{'OPENROUTER_API_KEY':'PRIOR_AUTHORED_VALUE'}):
            self.assertEqual(m.main('a'*64,'b'*64),{'status':'MOCK_DONE'})
            self.assertEqual(os.environ['OPENROUTER_API_KEY'],'PRIOR_AUTHORED_VALUE')
            with self.assertRaises(FileExistsError):m.main('a'*64,'b'*64)
            secret.assert_called_once();execute.assert_called_once()

    def test_wrong_source_or_lease_blocks_before_credentials(self):
        for change in ('source','lease'):
            with self.subTest(change=change),case() as (base,b,secret,execute):
                if change=='source':b['policy']['predecessor']['history_hash']='0'*64
                else:b['policy']['valid_until_utc']='2026-11-03T12:00:01+00:00'
                with self.assertRaises(m.ExecutionBlocked):m.main('a'*64,'b'*64)
                secret.assert_not_called();execute.assert_not_called()

    def test_execution_error_still_restores_environment_and_consumes_intent(self):
        with case() as (base,b,secret,execute),patch.dict(os.environ,{},clear=True):
            execute.side_effect=RuntimeError('authored failure')
            with self.assertRaises(RuntimeError):m.main('a'*64,'b'*64)
            self.assertNotIn('OPENROUTER_API_KEY',os.environ)
            self.assertTrue((base/'execution-intent.local.json').exists())

    def test_read_rejects_wrong_bytes_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp).resolve()/'input';p.write_bytes(b'{}')
            self.assertEqual(m.read(p,canonical_hash({})),b'{}')
            with self.assertRaises(m.ExecutionBlocked):m.read(p,'0'*64)
            q=p.parent/'link';q.symlink_to(p)
            with self.assertRaises(m.ExecutionBlocked):m.read(q,canonical_hash({}))


if __name__=='__main__':unittest.main()
