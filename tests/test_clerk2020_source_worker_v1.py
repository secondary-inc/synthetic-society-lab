"""Adverse memory/wire/runtime tests on authored files; no actual PDF library."""
import base64
import copy
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

from civiclab.e01 import clerk2020_source_worker_v1 as w
from civiclab.e01 import clerk2020_source_job_v1 as j
import test_clerk2020_source_job_v1 as fixtures


class SourceWorkerTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.SourceJobTests();self.fixture.setUp();self.root=self.fixture.root
        boot=self.fixture.boot();self.assertEqual(boot['status'],'BOOT_PREPARED_NO_SOURCE')
        store=j.n.FixedStore(self.root);prepared=j.decode(store.read('prepared_metadata',2049)[0])
        cache=j.decode(store.read('runtime_stat_cache',65537)[0])
        qualified=j.metadata_json((self.root/self.fixture.qualified['path']).read_bytes(),131072)
        self.catalog=j.reconstruct_catalog(qualified,cache)
        self.sid='clerk2020_statistics'
        self.snapshot=(self.root/(j.DATA_ROOT+self.sid+'.pdf')).read_bytes()
        self.context=j.sha(b'AUTHORED_CONTEXT')
        self.request=j.child_request(self.sid,self.snapshot,self.catalog,self.fixture.spec,self.context,
                                    {'sha256':j.sha(b'AUTHORED_RESERVATION')},{'label':'MOCK_DECISION'})
    def tearDown(self):self.fixture.tearDown()

    def test_request_roundtrip_is_bound_exactly(self):
        p,snapshot=w.parse_request(self.request,j.sha(self.request))
        self.assertEqual(snapshot,self.snapshot);self.assertEqual(p['source_id'],self.sid)
        with self.assertRaises(j.n.Refused):w.parse_request(self.request,'f'*64)

    def test_bad_base64_source_hash_chunk_order_or_extra_fields_refused(self):
        original=j.decode(self.request,950272)
        mutations=[('source_chunks_b64',['NOT BASE64!']),('source_id','UNLISTED'),
                   ('source_chunks_b64',[base64.b64encode(b'WRONG').decode()]),
                   ('EXTRA','UNREVIEWED')]
        for key,value in mutations:
            p=copy.deepcopy(original);p[key]=value;raw=j.canonical(p)
            with self.assertRaises((j.n.Refused,ValueError)):w.parse_request(raw,j.sha(raw))

    def test_oversize_input_and_chunk_rejected(self):
        raw=b'X'*950273
        with self.assertRaises(j.n.Refused):w.parse_request(raw,j.sha(raw))
        p=j.decode(self.request,950272);p['source_chunks_b64']=['A'*65540];raw=j.canonical(p)
        with self.assertRaises(j.n.Refused):w.parse_request(raw,j.sha(raw))

    def test_catalog_alias_duplicate_unknown_path_and_negative_identity_rejected(self):
        for kind in ['alias','duplicate','source','identity']:
            p=j.decode(self.request,950272)
            if kind=='alias':p['runtime_catalog'][0][0]='PYTHON_BASE/../ESCAPE'
            elif kind=='duplicate':p['runtime_catalog'].append(p['runtime_catalog'][0])
            elif kind=='source':p['runtime_catalog'][0][0]='REPO/data/raw/FORBIDDEN'
            else:p['runtime_catalog'][0][3][0]=-1
            raw=j.canonical(p)
            with self.assertRaises(j.n.Refused):w.parse_request(raw,j.sha(raw))

    def runtime_fixture(self,backend=True,extra=False):
        base=self.fixture.base;exe=base/'AUTHORED_EXECUTABLE';exe.write_bytes(b'AUTHORED_NOT_REAL_INTERPRETER')
        profile=copy.deepcopy(w.q.PROFILE)
        native=self.root/profile['native_backend']['path'];native.parent.mkdir(parents=True,exist_ok=True)
        native.write_bytes(b'AUTHORED_NOT_REAL_NATIVE_BINARY')
        profile['native_backend'].update(bytes=native.stat().st_size,sha256=j.sha(native.read_bytes()))
        modules={}
        if backend:
            module=ModuleType('_cffi_backend');module.__file__=str(native);modules['_cffi_backend']=module
        catalog=[]
        for label,path in [('PYTHON_BASE/AUTHORED_EXECUTABLE',exe),('REPO/'+profile['native_backend']['path'],native)]:
            if backend or path==exe:
                catalog.append([label,path.stat().st_size,j.sha(path.read_bytes()),list(j.n.file_identity(path.stat()))])
        if extra:
            missing=base/'AUTHORED_NOT_LOADED';missing.write_bytes(b'UNOBSERVED')
            catalog.append(['PYTHON_BASE/AUTHORED_NOT_LOADED',missing.stat().st_size,j.sha(missing.read_bytes()),list(j.n.file_identity(missing.stat()))])
        catalog.sort()
        return base,exe,profile,modules,catalog

    def capture(self,backend=True,extra=False):
        base,exe,profile,modules,catalog=self.runtime_fixture(backend,extra)
        with patch.object(w.q,'PROFILE',profile),patch.object(w.sys,'base_prefix',str(base)),\
             patch.object(w.sys,'executable',str(exe)),patch.object(w.sys,'modules',modules):
            warmup=w.SourceWarmup(self.root);warmup.transition('WARMUP');warmup.transition('HASH')
            return w.runtime_capture(self.root,warmup,catalog)

    def test_runtime_capture_authored_backend_hash_and_exact_nonproject_closure(self):
        rows,indices,actual,reserved,backend=self.capture()
        self.assertTrue(backend);self.assertEqual(len(rows),2)
        self.assertEqual(reserved,actual+2);self.assertEqual(len(indices),2)

    def test_worker_missing_nonproject_or_backend_fails_before_actual_parse(self):
        for backend,extra in [(True,True),(False,False)]:
            with self.assertRaises(j.n.Refused):self.capture(backend,extra)

    def valid_receipt(self):
        return self.fixture.fake_dispatch(self.root,self.request,0)[0]

    def test_parent_refuses_backend_false_unknown_metadata_or_missing_nonproject(self):
        raw=self.valid_receipt();j.validate_child(raw,self.sid,self.context,self.catalog)
        for kind in ['backend','unknown','missing']:
            obj=j.decode(raw,262144)
            if kind=='backend':obj['metadata']['native_backend_hash_matched']=False
            elif kind=='unknown':obj['metadata']['UNREVIEWED']='SECRET'
            else:
                indices=obj['metadata']['runtime_indices']
                remove=next(i for i in indices if self.catalog[i][0].startswith('PYTHON_BASE/'))
                indices.remove(remove);rows=[self.catalog[i][:3] for i in indices]
                obj['metadata'].update(runtime_manifest_sha256=j.digest(rows),
                    runtime_hash_bytes_observed=sum(r[1] for r in rows),runtime_hash_bytes_reserved=sum(r[1]+1 for r in rows))
            changed=j.canonical(obj)
            with self.assertRaises(j.n.Refused):j.validate_child(changed,self.sid,self.context,self.catalog)

    def test_unknown_public_excerpt_or_private_hash_mismatch_refused(self):
        raw=self.valid_receipt()
        for kind in ['excerpt','private_hash','context','counter']:
            obj=j.decode(raw,262144)
            if kind=='excerpt':obj['metadata']['public_diagnostics']['excerpt']='UNPERMITTED_TEXT'
            elif kind=='private_hash':obj['metadata']['private_projection_sha256']='f'*64
            elif kind=='context':obj['metadata']['context_sha256']='f'*64
            else:obj['metadata']['warmup']['reader_attempts']=3
            with self.assertRaises(j.n.Refused):j.validate_child(j.canonical(obj),self.sid,self.context,self.catalog)

    def test_output_truncation_oversize_and_chunk_tamper_refused(self):
        raw=self.valid_receipt()
        with self.assertRaises(j.n.Refused):j.validate_child(raw[:-1],self.sid,self.context,self.catalog)
        with self.assertRaises(j.n.Refused):j.validate_child(b'X'*262145,self.sid,self.context,self.catalog)
        obj=j.decode(raw,262144);obj['private_projection_chunks_b64']=['!']
        with self.assertRaises((j.n.Refused,ValueError)):j.validate_child(j.canonical(obj),self.sid,self.context,self.catalog)

    def test_maximum_catalog_and_source_sizes_fit_exact_wire_caps(self):
        original=j.decode(self.request,950272)
        catalog=[]
        index=0
        while True:
            label='PYTHON_BASE/AUTHORED_MODULE_'+str(index).zfill(4)+'_'+('x'*100)+'.py'
            candidate=[label,100,j.sha(b'AUTHORED'),[16777233,4294016335,33188,100,1700000000000000000,1700000000000000000]]
            if len(j.canonical(catalog+[candidate]))>w.CATALOG_CAP:break
            catalog.append(candidate);index+=1
        declarations=copy.deepcopy(j.adapter.SOURCES)
        for sid,count in [('clerk2020_statistics',602172),('clerk2026_nominees',257739)]:
            data=b'A'*count;declarations[sid].update(bytes=count,sha256=j.sha(data))
        with patch.object(j.adapter,'SOURCES',declarations):
            for sid in j.SOURCE_ORDER:
                data=b'A'*declarations[sid]['bytes']
                request=j.child_request(sid,data,catalog,self.fixture.spec,self.context,
                    {'sha256':j.sha(b'AUTHORED_RESERVATION')},{'label':'MOCK_DECISION'})
                self.assertLessEqual(len(request),w.INPUT_CAPS[sid])
                parsed,snapshot=w.parse_request(request,j.sha(request))
                self.assertEqual(len(snapshot),len(data))



if __name__=='__main__':unittest.main()
