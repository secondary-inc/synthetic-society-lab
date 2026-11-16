"""Authored ZIP/HTTP bytes in temporary trees. No real network/package imports."""
import base64
import copy
from datetime import datetime,timezone
from email.utils import format_datetime
import importlib.util
import io
import json
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('authored_p1_collector',ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
NOW=datetime(2026,11,15,12,0,tzinfo=timezone.utc)


def make_wheel(name,filename,extra=None,tag=None,requires='>=3.10',wrong_name=None):
    dist=name+'-'+c.VERSIONS[name]+'.dist-info/'
    py,abi,plat=filename[:-4].split('-')[-3:]
    wheel_tag=tag or py+'-'+abi+'-'+plat
    members={name+'/__init__.py':b'# AUTHORED_NOT_A_PACKAGE_RUNTIME\n',
        dist+'METADATA':f'Metadata-Version: 2.3\nName: {wrong_name or name}\nVersion: {c.VERSIONS[name]}\nRequires-Python: {requires}\n\n'.encode(),
        dist+'WHEEL':f'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: {wheel_tag}\n\n'.encode(),
        dist+'RECORD':b'AUTHORED_PLACEHOLDER_RECORD\n'}
    if extra:members.update(extra)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as z:
        for path,body in members.items():z.writestr(path,body)
    return out.getvalue()


def advisory(ident='GHSA-abcd-1234-efgh',affected='<7.0.1',patched='7.0.1'):
    return {'ghsa_id':ident,'state':'published','published_at':'2026-11-10T00:00:00Z',
        'updated_at':'2026-11-10T00:00:00Z','withdrawn_at':None,
        'vulnerabilities':[{'package':{'ecosystem':'pip','name':'pypdf'},'vulnerable_version_range':affected,'patched_versions':patched}]}


class Response:
    def __init__(self,body,kind='metadata',status=200,headers=None):
        self.body=body;self.offset=0;self.status=status;self.closed=False
        self.headers={'content-type':'application/json' if kind=='metadata' else 'application/octet-stream',
            'date':format_datetime(NOW,usegmt=True),'content-length':str(len(body))}
        if headers:self.headers.update(headers)
    def read(self,size,timeout):
        out=self.body[self.offset:self.offset+size];self.offset+=len(out);return out
    def close(self):self.closed=True


class Transport:
    def __init__(self,responses):self.responses=responses;self.calls=[];self.returned=[]
    def open(self,url,timeout):
        self.calls.append(url)
        value=self.responses[url]
        if isinstance(value,BaseException):raise value
        self.returned.append(value);return value


class ArtifactAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.time=[0.0];self.cpu=[0.0]
        self.methods={'kind':'E01_PYPDF701_ACQUISITION_METHODS_V1','versions':dict(c.VERSIONS),
            'caps':dict(c.CAPS),'target':dict(c.TARGET),'output':c.OUTPUT,'root_sha256':c.sha(str(self.root).encode())}
        self.files={};self.responses={}
        tags={'pypdf':'py3-none-any','pycparser':'py3-none-any','cffi':'cp312-cp312-macosx_11_0_arm64',
              'pillow':'cp312-cp312-macosx_13_0_arm64','cryptography':'cp311-abi3-macosx_10_9_universal2'}
        for name,ver in c.VERSIONS.items():
            filename=f'{name}-{ver}-{tags[name]}.whl';body=make_wheel(name,filename)
            url='https://files.pythonhosted.org/packages/aa/bb/'+('c'*60)+'/'+filename
            self.files[name]={'filename':filename,'size':len(body),'sha256':c.sha(body),'url':url}
            row={**self.files[name],'digests':{'sha256':c.sha(body)},'packagetype':'bdist_wheel','yanked':False,'requires_python':'>=3.10'}
            self.responses[f'https://pypi.org/pypi/{name}/{ver}/json']=Response(c.packed({
                'info':{'name':name,'version':ver,'requires_python':'>=3.10','yanked':False},'urls':[row]}))
            self.responses[url]=Response(body,'wheel')
        self.pypdf_patch=patch.object(c,'PYPDF',self.files['pypdf']);self.pypdf_patch.start()
        self.responses[c.API]=Response(c.packed([advisory()]))
        statement={'_type':'https://in-toto.io/Statement/v1','predicateType':'https://docs.pypi.org/attestations/publish/v1',
            'subject':[{'name':self.files['pypdf']['filename'],'digest':{'sha256':self.files['pypdf']['sha256']}}]}
        proof={'attestation_bundles':[{'publisher':{'kind':'GitHub','repository':'py-pdf/pypdf','workflow':'publish-to-pypi.yaml'},
            'attestations':[{'version':1,'envelope':{'statement':base64.b64encode(c.packed(statement)).decode(),'signature':'AUTHORED_NOT_VERIFIED'}}]}]}
        self.responses[c.PROVENANCE]=Response(c.packed(proof))
        self.transport=Transport(self.responses)
    def tearDown(self):self.pypdf_patch.stop();self.temp.cleanup()
    def collector(self):return c.Collector(self.root,self.methods,self.transport,clock=lambda:self.time[0],cpu=lambda:self.cpu[0],utc=lambda:NOW)
    def run_collect(self):return self.collector().run()
    def terminal(self):return json.loads((self.root/c.OUTPUT/'TERMINAL.json').read_bytes())
    def metadata(self,name):
        url=f'https://pypi.org/pypi/{name}/{c.VERSIONS[name]}/json';return url,json.loads(self.responses[url].body)
    def replace_metadata(self,name,doc):
        url,_=self.metadata(name);self.responses[url]=Response(c.packed(doc))

    def test_complete_five_artifacts_no_extraction_and_bound_hashlock(self):
        with patch.object(zipfile.ZipFile,'extractall',side_effect=AssertionError('NO_EXTRACTION')):
            result=self.run_collect()
        self.assertEqual(result['status'],'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
        self.assertEqual(len(self.transport.calls),12);self.assertTrue(all(r.closed for r in self.transport.returned))
        lock=json.loads((self.root/c.OUTPUT/'hashlock.json').read_bytes())
        self.assertEqual(len(lock['wheels']),5);self.assertFalse(lock['ready_for_install']);self.assertTrue(lock['not_latest'])
        for item in lock['wheels']:
            self.assertEqual(c.sha((self.root/c.OUTPUT/item['artifact_ref']['path']).read_bytes()),item['sha256'])
        self.assertEqual((self.root/c.OUTPUT/'STARTED.json').stat().st_mode&0o777,0o600)
        self.assertFalse((self.root/'pypdf').exists())

    def test_duplicate_scope_refuses_before_transport_or_marker_rewrite(self):
        self.run_collect();prior=(self.root/c.OUTPUT/'TERMINAL.json').read_bytes();self.transport.calls=[]
        with self.assertRaises(FileExistsError):self.run_collect()
        self.assertEqual(self.transport.calls,[]);self.assertEqual(prior,(self.root/c.OUTPUT/'TERMINAL.json').read_bytes())

    def test_wrong_methods_root_or_caps_have_zero_scope_effects(self):
        for field,value in [('root_sha256','f'*64),('caps',{}),('versions',{}),('target',{})]:
            with self.subTest(field=field):
                methods=copy.deepcopy(self.methods);methods[field]=value
                with self.assertRaises(c.Refused):c.Collector(self.root,methods,self.transport).run()
        self.assertFalse((self.root/c.OUTPUT).exists());self.assertEqual(self.transport.calls,[])

    def test_failed_request_reserved_durably_and_never_retried(self):
        first=next(iter(self.responses));self.responses[first]=TimeoutError('AUTHORED_PRIVATE_MESSAGE')
        result=self.run_collect();self.assertEqual(len(self.transport.calls),1)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY');self.assertEqual(result['reason'],'TimeoutError')
        self.assertEqual(result['budget']['body_bytes_charged']['metadata'],c.CAPS['metadata_each'])
        self.assertEqual(self.terminal()['current_request']['observed_partial_body_bytes'],0)
        body=(self.root/c.OUTPUT/'TERMINAL.json').read_bytes();self.assertNotIn(b'AUTHORED_PRIVATE_MESSAGE',body)
        self.assertTrue((self.root/c.OUTPUT/'events/01.json').exists())

    def test_http_status_redirect_or_compression_refuses_and_closes(self):
        for status,headers in [(302,{}),(429,{}),(200,{'content-encoding':'gzip'})]:
            with self.subTest(status=status,headers=headers),tempfile.TemporaryDirectory() as folder:
                self.root=Path(folder).resolve();self.methods['root_sha256']=c.sha(str(self.root).encode())
                first=next(iter(self.responses));self.responses[first]=Response(b'{}',status=status,headers=headers)
                self.transport=Transport(self.responses);result=self.run_collect()
                self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY');self.assertEqual(len(self.transport.calls),1)
                self.assertTrue(self.transport.returned[0].closed)

    def test_response_body_limit_and_declared_length_refuse(self):
        first=next(iter(self.responses));self.responses[first]=Response(b'x',headers={'content-length':str(c.CAPS['metadata_each'])})
        self.assertEqual(self.run_collect()['reason'],'CONTENT_LENGTH')
        self.assertEqual(self.transport.returned[0].offset,0)

    def test_stream_overflow_is_bounded_without_content_length(self):
        response=Response(b'x'*129);response.headers.pop('content-length')
        self.responses[next(iter(self.responses))]=response
        with patch.dict(c.CAPS,{'metadata_each':128}):
            self.methods['caps']=dict(c.CAPS);result=self.run_collect()
        self.assertEqual(result['reason'],'BODY_CAP');self.assertEqual(response.offset,128)

    def test_stale_or_unknown_http_date_refuses(self):
        first=next(iter(self.responses));self.responses[first]=Response(b'{}',headers={'date':'Fri, 01 Jan 2021 00:00:00 GMT'})
        self.assertEqual(self.run_collect()['reason'],'HTTP_FRESHNESS')

    def test_request_and_stage_deadlines_or_cpu_are_enforced(self):
        collector=self.collector();original=self.transport.open
        def late(url,timeout):
            response=original(url,timeout);self.time[0]=21;return response
        self.transport.open=late
        self.assertEqual(collector.run()['reason'],'REQUEST_TIMEOUT')
        budget=c.Budget(lambda:self.time[0],lambda:self.cpu[0]);self.time[0]+=301
        with self.assertRaises(c.Refused):budget.check()
        self.time[0]=0;budget=c.Budget(lambda:self.time[0],lambda:self.cpu[0]);self.cpu[0]=61
        with self.assertRaises(c.Refused):budget.check()

    def test_clock_regression_and_total_request_or_byte_caps(self):
        budget=c.Budget(lambda:self.time[0],lambda:self.cpu[0]);self.time[0]=-1
        with self.assertRaises(c.Refused):budget.check()
        self.time[0]=0;budget=c.Budget(lambda:self.time[0],lambda:self.cpu[0]);budget.attempts['GET']=13
        with self.assertRaises(c.Refused):budget.begin('metadata')
        budget.attempts['GET']=0;budget.bytes['metadata']=c.CAPS['metadata_total']
        with self.assertRaises(c.Refused):budget.begin('metadata')

    def test_wrong_package_version_yank_or_exact_python_requirement(self):
        _,doc=self.metadata('cffi')
        for field,value in [('name','other'),('version','999.0.0'),('yanked',True),('requires_python','<3.12.1')]:
            wrong=copy.deepcopy(doc);wrong['info'][field]=value
            with self.subTest(field=field),self.assertRaises(c.Refused):c.select_wheel('cffi',wrong)

    def test_arm64_abi3_universal2_and_macos_ceiling_are_explicit(self):
        self.assertIsNotNone(c.wheel_rank('cryptography','cryptography-50.0.2-cp311-abi3-macosx_10_9_universal2.whl'))
        self.assertIsNotNone(c.wheel_rank('pillow','pillow-13.0.0-cp312-cp312-macosx_26_0_arm64.whl'))
        for file in ['pillow-13.0.0-cp312-cp312-macosx_27_0_arm64.whl','pillow-13.0.0-cp312-cp312-macosx_11_0_x86_64.whl',
                     'pillow-13.0.0-cp313-cp313-macosx_11_0_arm64.whl']:
            self.assertIsNone(c.wheel_rank('pillow',file))

    def test_ambiguous_duplicate_bad_digest_or_url_refuses(self):
        _,doc=self.metadata('cffi')
        row=doc['urls'][0]
        for field,value in [('digests',{'sha256':'bad'}),('url','https://evil.invalid/other.whl')]:
            wrong=copy.deepcopy(doc);wrong['urls'][0][field]=value
            with self.assertRaises(c.Refused):c.select_wheel('cffi',wrong)
        doc['urls'].append(copy.deepcopy(row))
        with self.assertRaises(c.Refused):c.select_wheel('cffi',doc)
        doc['urls'][1]['filename']=row['filename'].replace('-cp312-','-1-cp312-',1)
        doc['urls'][1]['url']=row['url'].replace(row['filename'],doc['urls'][1]['filename'])
        with self.assertRaises(c.Refused):c.select_wheel('cffi',doc)

    def test_newer_applicable_advisory_blocks_before_wheel_or_provenance(self):
        self.responses[c.API]=Response(c.packed([advisory(affected='<7.1.0',patched='7.1.0')]))
        result=self.run_collect();self.assertEqual(result['reason'],'APPLICABLE_ADVISORY')
        self.assertEqual(len(self.transport.calls),6);self.assertFalse((self.root/c.OUTPUT/'hashlock.json').exists())
        self.assertEqual(json.loads((self.root/c.OUTPUT/'advisory-assessment.json').read_bytes())['status'],'BLOCKED_APPLICABLE_ADVISORY')

    def test_advisory_schema_unknown_range_or_empty_listing_refuses(self):
        for rows in [[],{},[dict(advisory(),state='draft')],[advisory(affected='~=7.0')],
                     [dict(advisory(),vulnerabilities=[{'package':{'ecosystem':'pip','name':'pypdf'}}])]]:
            with self.subTest(rows=rows),self.assertRaises(c.Refused):c.assess_advisories([rows])
        self.assertFalse(c.assess_advisories([[advisory()]])['advisories'][0]['assessments'][0]['candidate_affected'])

    def test_pagination_semantics_complete_second_page_or_truncation(self):
        url='https://api.github.com/repos/py-pdf/pypdf/security-advisories?after=abc&direction=asc&sort=published&per_page=100&state=published'
        self.assertEqual(c.next_advisory({'link':'<'+url+'>; rel="next"'},[advisory()],1),url)
        with self.assertRaises(c.Refused):c.next_advisory({'link':'<'+url+'>; rel="next"'},[advisory()],2)
        with self.assertRaises(c.Refused):c.next_advisory({},[advisory()]*100,1)
        with self.assertRaises(c.Refused):c.next_advisory({'link':'<https://evil.invalid/>; rel="next"'},[],1)

    def test_pagination_two_pages_uses_thirteenth_request_at_most(self):
        url=c.API+'&after=abc'
        self.responses[c.API]=Response(c.packed([advisory()]),headers={'link':'<'+url+'>; rel="next"'})
        self.responses[url]=Response(c.packed([advisory('GHSA-1234-abcd-5678')]))
        self.assertTrue(self.run_collect()['status'].startswith('ACQUISITION_COMPLETE'))
        self.assertEqual(len(self.transport.calls),13)

    def test_provenance_publisher_subject_or_schema_refuses(self):
        good=json.loads(self.responses[c.PROVENANCE].body)
        self.assertIn('NOT_LOCAL_SIGNATURE',c.provenance_binding(good))
        for key,value in [('kind','Other'),('repository','other/repo'),('workflow','evil.yaml')]:
            bad=copy.deepcopy(good);bad['attestation_bundles'][0]['publisher'][key]=value
            with self.assertRaises(c.Refused):c.provenance_binding(bad)
        bad=copy.deepcopy(good);bad['attestation_bundles'][0]['attestations'][0]['version']=True
        with self.assertRaises(c.Refused):c.provenance_binding(bad)
        with self.assertRaises(c.Refused):c.provenance_binding({'attestation_bundles':[]})

    def test_wheel_hash_size_or_internal_tag_name_mismatch_refuses(self):
        file=self.files['cffi']['filename']
        for kwargs in [{'tag':'cp313-cp313-any'},{'wrong_name':'other'},{'requires':'<3.12.1'}]:
            with self.assertRaises(c.Refused):c.inspect_wheel(make_wheel('cffi',file,**kwargs),'cffi',file)
        self.responses[self.files['cffi']['url']]=Response(b'NOT_A_WHEEL','wheel')
        self.assertEqual(self.run_collect()['reason'],'WHEEL_IDENTITY')

    def test_zip_paths_duplicates_symlink_pth_and_encryption_refuse(self):
        file=self.files['cffi']['filename']
        for name in ['../escape','/absolute','a\\b','A.pth','x.data/scripts/run']:
            with self.assertRaises(c.Refused):c.inspect_wheel(make_wheel('cffi',file,{name:b'AUTHORED'}),'cffi',file)
        body=make_wheel('cffi',file,{'CFFI/__INIT__.PY':b'DUPLICATE'})
        with self.assertRaises(c.Refused):c.inspect_wheel(body,'cffi',file)
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            info=zipfile.ZipInfo('symlink');info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'target')
        with self.assertRaises(c.Refused):c.inspect_wheel(out.getvalue(),'cffi',file)
        encrypted=bytearray(make_wheel('cffi',file));central=encrypted.find(b'PK\x01\x02')
        struct.pack_into('<H',encrypted,central+8,struct.unpack_from('<H',encrypted,central+8)[0]|1)
        with self.assertRaises(c.Refused):c.inspect_wheel(bytes(encrypted),'cffi',file)

    def test_two_wheel_aggregate_admission_precedes_second_payload(self):
        first=self.responses[self.files['cffi']['url']].body;second=self.responses[self.files['pillow']['url']].body
        admitted=c.inspect_wheel(first,'cffi',self.files['cffi']['filename'])
        second_admitted=c.inspect_wheel(second,'pillow',self.files['pillow']['filename'])
        aggregate_entry_limit=admitted['entries']+second_admitted['entries']-1
        aggregate_byte_limit=admitted['uncompressed_bytes']+second_admitted['uncompressed_bytes']-1
        with patch.object(zipfile.ZipFile,'open',side_effect=AssertionError('FORBIDDEN_SECOND_STREAM')) as stream:
            with self.assertRaises(c.Refused):c.inspect_wheel(second,'pillow',self.files['pillow']['filename'],entries_left=aggregate_entry_limit-admitted['entries'])
            stream.assert_not_called()
            with self.assertRaises(c.Refused):c.inspect_wheel(second,'pillow',self.files['pillow']['filename'],bytes_left=aggregate_byte_limit-admitted['uncompressed_bytes'])
            stream.assert_not_called()

    def test_zip_crc_and_central_directory_corruption_refuses(self):
        raw=bytearray(self.responses[self.files['cffi']['url']].body)
        pos=raw.find(b'AUTHORED_NOT_A_PACKAGE_RUNTIME');raw[pos]^=1
        with self.assertRaises((c.Refused,zipfile.BadZipFile)):c.inspect_wheel(bytes(raw),'cffi',self.files['cffi']['filename'])
        raw=bytearray(self.responses[self.files['cffi']['url']].body);raw[-22:-18]=b'NOPE'
        with self.assertRaises(c.Refused):c.inspect_wheel(bytes(raw),'cffi',self.files['cffi']['filename'])

    def test_budget_write_failure_preserves_started_and_terminal_headroom(self):
        collector=self.collector();original=collector.write
        def fail(name,body,control=True):
            if name.startswith('metadata/'):raise OSError('AUTHORED_DISK_FULL')
            return original(name,body,control)
        collector.write=fail;result=collector.run()
        self.assertEqual(result['reason'],'OSError');self.assertTrue((self.root/c.OUTPUT/'STARTED.json').exists())
        self.assertTrue((self.root/c.OUTPUT/'TERMINAL.json').exists());self.assertFalse((self.root/c.OUTPUT/'hashlock.json').exists())

    def test_output_scope_alias_refuses_before_requests(self):
        other=self.root/'AUTHORED_TARGET';other.mkdir();(self.root/'data').symlink_to(other,target_is_directory=True)
        with self.assertRaises(c.Refused):self.run_collect()
        self.assertEqual(self.transport.calls,[])

    def test_json_duplicate_or_complexity_and_ranges_are_fail_closed(self):
        with self.assertRaises(c.Refused):c.json_body(b'{"a":1,"a":2}')
        with self.assertRaises(c.Refused):c.json_body(b'{"a":NaN}')
        with self.assertRaises(c.Refused):c.json_body(b'{"a":1e999}')
        for expression in ['*','>=7.0rc1','<7.*','<7 || >8','']:
            with self.assertRaises(c.Refused):c.matches(expression,'7.0.1')
        self.assertTrue(c.matches('>=7.0.0, <7.1.0','7.0.1'))

def guarded_test_main():
    # Per-process authored runner only; never installed during global discovery.
    import builtins,importlib.abc,io,os,resource,signal,sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from e01_authored_dirfd_guard_v2_20261112 import DirectoryFdGuard
    writes=[0];read_bytes=[0];output=[0]
    class NoNative(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in {'pypdf','PIL','cryptography','_cffi_backend'}:raise AssertionError('NO_NATIVE_PACKAGE_IMPORT')
    sys.meta_path.insert(0,NoNative())
    def allowed(path,flags):
        real=Path(os.path.realpath(path));toolchain=ROOT/'data/processed/toolchains/cpython-3.11.17-macos-aarch64-none'
        if (real.is_relative_to(ROOT/'data') and not real.is_relative_to(toolchain)) or real.name.startswith('.env'):
            raise AssertionError('NO_ACTUAL_DATA_OWNER_OR_CREDENTIALS')
        if real.is_relative_to(ROOT) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            raise AssertionError('NO_REPOSITORY_MUTATION')
    fdguard=DirectoryFdGuard(allowed)
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path=fdguard.event_path(args[0]);flags=args[2];allowed(path,flags)
            if not flags&os.O_WRONLY:
                try:size=path.stat().st_size
                except FileNotFoundError:size=0
                read_bytes[0]+=size+1
                if read_bytes[0]>67108864:raise AssertionError('AUTHORED_READ_CAP')
        if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','ctypes.dlopen'}:
            raise AssertionError('NO_NETWORK_PROCESS_OR_NATIVE')
    sys.addaudithook(audit);os.open=fdguard.open;os.close=fdguard.close
    def charge(data):
        writes[0]+=len(data.encode('utf8')) if isinstance(data,str) else memoryview(data).nbytes
        if writes[0]>33554432:raise AssertionError('AUTHORED_WRITE_CAP')
    class File:
        def __init__(self,stream):self.stream=stream
        def __getattr__(self,name):return getattr(self.stream,name)
        def __enter__(self):self.stream.__enter__();return self
        def __exit__(self,*args):return self.stream.__exit__(*args)
        def __iter__(self):return self
        def __next__(self):return next(self.stream)
        def write(self,data):charge(data);return self.stream.write(data)
        def writelines(self,items):
            for item in items:self.write(item)
    def wrap(original):
        def opening(*args,**kwargs):
            stream=original(*args,**kwargs);return stream if isinstance(stream,File) else File(stream)
        return opening
    builtins.open=wrap(builtins.open);io.open=wrap(io.open);os.fdopen=wrap(os.fdopen)
    original_write=os.write
    def write_fd(fd,data):charge(data);return original_write(fd,data)
    os.write=write_fd
    class Output:
        def __init__(self,stream):self.stream=stream
        def __getattr__(self,name):return getattr(self.stream,name)
        def write(self,text):
            output[0]+=len(text.encode('utf8'))
            if output[0]>262144:raise AssertionError('AUTHORED_OUTPUT_CAP')
            return self.stream.write(text)
    sys.stdout=Output(sys.stdout);sys.stderr=Output(sys.stderr)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    def timeout(*_):raise AssertionError('AUTHORED_WALL_CAP')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
    unittest.main(failfast=True,verbosity=2)

if __name__=='__main__':guarded_test_main()
