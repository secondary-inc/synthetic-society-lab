"""Authored HTTP responses and temporary roots only; no actual source access."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/e01_clerk_documents_capture_v1.py'
spec=importlib.util.spec_from_file_location('authored_clerk_capture',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Response:
    def __init__(self,body=b'%PDF-authored-not-parsed',status=200,headers=None,fail_read=False,fail_close=False):
        self.body=io.BytesIO(body);self.status=status;self.calls=0;self.fail_read=fail_read;self.fail_close=fail_close
        self.headers={'Content-Type':'application/pdf','Content-Length':str(len(body))} if headers is None else headers
    def getheader(self,name):return self.headers.get(name)
    def read(self,n):
        self.calls+=1
        if self.fail_read and self.calls>1:raise OSError('AUTHORED_BODY_INTERRUPTED')
        return self.body.read(min(n,5) if self.fail_read else n)
    def close(self):
        if self.fail_close:raise OSError('AUTHORED_CLOSE_ERROR')

class Connection:
    def __init__(self,response,requests):self.response=response;self.requests=requests
    def request(self,method,path,headers):self.requests.append((method,path,headers))
    def getresponse(self):return self.response
    def close(self):pass

class ClerkCaptureTests(unittest.TestCase):
    def plan(self,root):
        # This is an AUTHORED review-shaped record in a fake root, not authority.
        review={'status':'PASS_BOUNDED_CLERK_DOCUMENT_CAPTURE_V1_CODE','auditor_role':'independent_auditor',
            'code_sha256':m.code_sha(),'source_policy_sha256':m.digest(m.canonical({'sources':m.SOURCES,'limits':m.LIMITS})),
            'fixture_marker':'AUTHORED_NOT_REAL_REVIEW'}
        ref=root/'reports/AUTHORED_REVIEW.json';ref.parent.mkdir();ref.write_bytes(m.canonical(review))
        p={'schema_version':1,'kind':'CLERK_DOCUMENT_CAPTURE_RELEASE_V1','root_sha256':m.digest(str(root).encode()),
            'code_sha256':m.code_sha(),'sources':m.SOURCES,'limits':m.LIMITS,
            'code_review':{'path':'reports/AUTHORED_REVIEW.json','sha256':m.digest(ref.read_bytes())}}
        return p,m.digest(m.canonical(p))
    def run_case(self,root,plan,expected,responses):
        requests=[];pending=iter(responses)
        def factory(host,timeout):
            self.assertEqual(host,'clerk.house.gov');self.assertEqual(timeout,15)
            return Connection(next(pending),requests)
        with patch.object(m.http.client,'HTTPSConnection',side_effect=factory):
            result=m.capture(root,plan,expected)
        return result,requests
    def test_exact_two_successful_bodies_and_once_only_scope(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root)
            result,requests=self.run_case(root,p,h,[Response(),Response()])
            self.assertTrue(result['status'].startswith('CAPTURED'))
            self.assertEqual(len(requests),2)
            self.assertTrue(all(r['pdf_admitted'] and r['body_complete'] for r in result['records']))
            for method,path,headers in requests:
                self.assertEqual(method,'GET');self.assertEqual(headers['Accept-Encoding'],'identity')
                self.assertNotIn('Authorization',headers);self.assertNotIn('Cookie',headers)
            scope=root/m.SCOPE
            self.assertEqual((scope.stat().st_mode & 0o777),0o700)
            self.assertTrue(all((f.stat().st_mode & 0o777)==0o600 for f in scope.iterdir()))
            with patch.object(m.http.client,'HTTPSConnection') as network:
                with self.assertRaises(FileExistsError):m.capture(root,p,h)
                network.assert_not_called()
    def test_changed_plan_code_root_or_source_refused_before_scope_or_network(self):
        for field in ('root_sha256','code_sha256','sources','limits'):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as t:
                root=Path(t).resolve();p,h=self.plan(root);p=json.loads(json.dumps(p))
                p[field]='AUTHORED_MUTATION'
                with patch.object(m.http.client,'HTTPSConnection') as network:
                    with self.assertRaises(ValueError):m.capture(root,p,m.digest(m.canonical(p)))
                    network.assert_not_called();self.assertFalse((root/m.SCOPE).exists())
    def test_status_redirect_encoding_and_length_refuse_without_second_source(self):
        cases=[Response(status=403),Response(status=302),
            Response(headers={'Content-Encoding':'gzip'}),
            Response(headers={'Content-Length':str(m.LIMITS['body_bytes_each']+1)}),
            Response(headers={'Content-Length':'-1'}),
            Response(headers={'Content-Type':'text/html','Content-Length':'22'})]
        for response in cases:
            with self.subTest(response=response.headers),tempfile.TemporaryDirectory() as t:
                root=Path(t).resolve();p,h=self.plan(root);result,requests=self.run_case(root,p,h,[response])
                self.assertEqual(result['status'],'STOPPED_NO_RETRY');self.assertEqual(len(requests),1)
                self.assertFalse(result['records'][0]['pdf_admitted']);self.assertTrue((root/m.SCOPE/'STOP.local.json').is_file())
                self.assertEqual(len(list((root/m.SCOPE).glob('*.intent.local.json'))),1)
    def test_partial_read_retains_bytes_and_full_reservation(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root)
            result,requests=self.run_case(root,p,h,[Response(fail_read=True)])
            row=result['records'][0];self.assertEqual(row['body_bytes'],5);self.assertFalse(row['body_complete'])
            self.assertEqual((root/m.SCOPE/'clerk2020_statistics.part').read_bytes(),b'%PDF-')
            stop=json.loads((root/m.SCOPE/'STOP.local.json').read_text())
            self.assertEqual(stop['reserved_body_bytes'],16777216);self.assertEqual(len(requests),1)
    def test_unknown_length_below_cap_eof_accepted_but_at_cap_without_probe_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root)
            response=Response(headers={'Content-Type':'application/pdf'})
            result,requests=self.run_case(root,p,h,[response,Response()])
            self.assertTrue(result['records'][0]['body_complete']);self.assertEqual(response.calls,2)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root)
            response=Response(body=b'%PDF-'+b'x'*(8388608-5),headers={'Content-Type':'application/pdf'})
            result,requests=self.run_case(root,p,h,[response])
            self.assertEqual(result['status'],'STOPPED_NO_RETRY');self.assertEqual(response.calls,128)
            self.assertEqual(result['records'][0]['body_bytes'],8388608)
            self.assertFalse(result['records'][0]['body_complete'])
    def test_verified_length_exact_cap_and_close_failure_kept_separate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root)
            response=Response(body=b'%PDF-'+b'x'*(8388608-5))
            result,requests=self.run_case(root,p,h,[response,Response()])
            self.assertTrue(result['records'][0]['pdf_admitted']);self.assertEqual(response.calls,128)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root)
            result,requests=self.run_case(root,p,h,[Response(fail_close=True)])
            self.assertEqual(result['status'],'STOPPED_NO_RETRY')
            self.assertTrue(result['records'][0]['body_complete']);self.assertFalse(result['records'][0]['pdf_admitted'])
            self.assertTrue((root/m.SCOPE/'clerk2020_statistics.part').is_file())
    def test_review_change_scope_alias_and_pending_start_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root);review=root/p['code_review']['path'];review.write_text('{}')
            with patch.object(m.http.client,'HTTPSConnection') as network:
                with self.assertRaises(ValueError):m.capture(root,p,h)
                network.assert_not_called()
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root);scope=root/m.SCOPE;scope.parent.mkdir(parents=True)
            scope.symlink_to(root/'reports',target_is_directory=True)
            with self.assertRaises(ValueError):self.run_case(root,p,h,[])
    def test_nested_deadline_preserves_earlier_parent_remaining_time(self):
        previous=lambda *_:None
        with patch.object(m.signal,'signal',return_value=previous),patch.object(m.signal,'getitimer',return_value=(3,0)),\
             patch.object(m.signal,'setitimer') as timer,patch.object(m.time,'monotonic',side_effect=[10,12]):
            with m.deadline(45):pass
        self.assertEqual(timer.call_args_list[0].args,(m.signal.ITIMER_REAL,3))
        self.assertEqual(timer.call_args_list[-1].args,(m.signal.ITIMER_REAL,1,0))
    def test_plan_metadata_path_and_duplicate_keys_do_not_read_other_files(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve()
            for name in ('../outside.json','/absolute.json','.env','data/raw/source.json'):
                with self.assertRaises(ValueError):m.load_plan(root,name)
            p=root/'data/processed/e01_clerk_capture_plans/AUTHORED.json';p.parent.mkdir(parents=True)
            p.write_text('{"same":1,"same":2}')
            with self.assertRaises(ValueError):m.load_plan(root,str(p.relative_to(root)))
            p.write_text('{"n":NaN}')
            with self.assertRaises(ValueError):m.load_plan(root,str(p.relative_to(root)))
    def test_legitimate_access_time_change_is_not_metadata_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t).resolve()/'AUTHORED.json';p.write_bytes(b'{}');s=p.stat()
            stable={k:getattr(s,k) for k in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')}
            with patch.object(m.os,'fstat',side_effect=[SimpleNamespace(**stable,st_atime=1),SimpleNamespace(**stable,st_atime=2)]):
                self.assertEqual(m.metadata_bytes(p,10),b'{}')
    def test_cancellation_retains_observed_bytes_and_stops_remaining_source(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root);response=Response()
            with patch.object(response,'read',side_effect=[b'%PDF-',KeyboardInterrupt()]):
                result,requests=self.run_case(root,p,h,[response])
            self.assertEqual(len(requests),1);self.assertEqual(result['status'],'STOPPED_NO_RETRY')
            self.assertEqual(result['records'][0]['error_type'],'KeyboardInterrupt')
            self.assertEqual(result['records'][0]['body_bytes'],5)
            self.assertFalse((root/m.SCOPE/'COMPLETED.local.json').exists())
    def test_pending_or_empty_existing_scope_never_resets(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root);(root/m.SCOPE).mkdir(parents=True)
            with patch.object(m.http.client,'HTTPSConnection') as network:
                with self.assertRaises(FileExistsError):m.capture(root,p,h)
                network.assert_not_called()
    def test_receipt_persistence_failure_after_body_does_not_dispatch_second_source(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();p,h=self.plan(root);requests=[];original=m.write_once
            def fail_receipt(path,value):
                if path.name.endswith('.receipt.local.json'):raise OSError('AUTHORED_RECEIPT_EIO')
                return original(path,value)
            with patch.object(m,'write_once',side_effect=fail_receipt),\
                 patch.object(m.http.client,'HTTPSConnection',return_value=Connection(Response(),requests)):
                with self.assertRaises(OSError):m.capture(root,p,h)
            self.assertEqual(len(requests),1)
            self.assertTrue((root/m.SCOPE/'STARTED.local.json').is_file())
            self.assertFalse((root/m.SCOPE/'COMPLETED.local.json').exists())
            with patch.object(m.http.client,'HTTPSConnection') as network:
                with self.assertRaises(FileExistsError):m.capture(root,p,h)
                network.assert_not_called()

if __name__=='__main__':unittest.main()
