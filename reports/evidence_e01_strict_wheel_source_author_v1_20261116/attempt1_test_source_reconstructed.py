"""Collectible pure tests; standalone-only global guards, no payload execution."""
import sys


def _install_standalone_early_guard():
    def deny(event,args):
        if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty',
            'os.posix_spawn','os.system','os.exec','os.spawn','ctypes.dlopen'}:
            raise AssertionError('PURE_SOURCE_NO_NETWORK_PROCESS_NATIVE')
        if event=='import' and args and args[0].split('.')[0] in {
            'pip','installer','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser','ssl_fixture_payload'}:
            raise AssertionError('PURE_SOURCE_NO_TOOL_OR_PAYLOAD_IMPORT')
    sys.addaudithook(deny)


if __name__=='__main__':_install_standalone_early_guard()

import ast
import base64
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import signal
import stat
import struct
import unittest
import warnings
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'scripts/e01_strict_wheel_source_candidate_v1_20261116.py'
spec=importlib.util.spec_from_file_location('pure_strict_wheel_source',CANDIDATE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ENTRYPOINT=bytes.fromhex('5b636f6e736f6c655f736372697074735d0a666978747572652d636c69203d2073736c5f666978747572655f7061796c6f61643a6d61696e0a')
INSTALLER_METADATA=bytes.fromhex('73796e7468657469632d736f63696574792d6c61622d666978747572652d6f6e6c793b20696e7374616c6c65723d312e312e300a')


def bodies():
    return {m.PAYLOAD:b'raise AssertionError("FIXTURE_PAYLOAD_MUST_NEVER_EXECUTE")\ndef main(): return 0\n',
        m.DIST+'METADATA':b'Metadata-Version: 2.1\nName: ssl_fixture_payload\nVersion: 1.0.0\nRequires-Python: >=3.10\n\n',
        m.DIST+'WHEEL':b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
        m.DIST+'entry_points.txt':ENTRYPOINT}


def record_rows(data):
    return [[name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b'=').decode(),str(len(body))]
            for name,body in sorted(data.items())]+[[m.DIST+'RECORD','','']]


def make_wheel(data=None,rows=None,*,extra=(),compression=zipfile.ZIP_STORED):
    data=bodies() if data is None else dict(data)
    rows=record_rows(data) if rows is None else rows
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(rows)
    data[m.DIST+'RECORD']=stream.getvalue().encode()
    raw=io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',UserWarning)
        with zipfile.ZipFile(raw,'w',compression=compression) as archive:
            for name,body in sorted(data.items()):
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=compression
                info.external_attr=(stat.S_IFREG|0o644)<<16
                archive.writestr(info,body)
            for name,body,mode in extra:
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.external_attr=mode<<16
                archive.writestr(info,body)
    return raw.getvalue()


def validate(raw,budget=None):
    return m.validate_wheel(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),filename=m.FILENAME,
                            budget=m.ReadBudget(1048576) if budget is None else budget)


class ValidationTests(unittest.TestCase):
    def setUp(self):self.raw=make_wheel()
    def refuse(self,raw,pattern):
        with self.assertRaisesRegex(m.WheelRefused,pattern):validate(raw)
    def test_valid_fixture_and_manifest_bound_to_same_immutable_bytes(self):
        token=validate(self.raw)
        self.assertEqual(token.filename,m.FILENAME);self.assertEqual(token.sha256,hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(token.archive_size,len(self.raw));self.assertIsInstance(token.members,tuple)
        self.assertEqual({row[0] for row in token.members},m.MEMBERS)
        with token.open() as stream:
            self.assertEqual(stream.read(),self.raw)
        print(json.dumps({'kind':'PURE_STRICT_FIXED_WHEEL_VALIDATION','archive_bytes':len(self.raw),
            'sha256':token.sha256,'members':len(token.members),'charged_logical_read_bytes':token.read_bytes_used,
            'tool_or_payload_execution':0},sort_keys=True))
    def test_normative_LF_bytes_match_successor_contract(self):
        self.assertEqual((len(ENTRYPOINT),ENTRYPOINT.count(b'\n'),hashlib.sha256(ENTRYPOINT).hexdigest()),
                         (57,2,'7c681c48ff47ebff69a7725580e9f612320498b6a27ecdcb7540237eed6978bb'))
        self.assertEqual((len(INSTALLER_METADATA),INSTALLER_METADATA.count(b'\n'),hashlib.sha256(INSTALLER_METADATA).hexdigest()),
                         (52,1,'a25d1b0c7e51bf5e0dd2aa45bf85e03faf1101a0bbd8a92347ce5dc3d913e2dd'))
    def test_sha256_and_filename_mismatch_refuse(self):
        with self.assertRaisesRegex(m.WheelRefused,'ARCHIVE_HASH'):
            m.validate_wheel(self.raw,expected_sha256='0'*64,filename=m.FILENAME,budget=m.ReadBudget(1048576))
        with self.assertRaisesRegex(m.WheelRefused,'FILENAME_BINDING'):
            m.validate_wheel(self.raw,expected_sha256=hashlib.sha256(self.raw).hexdigest(),filename='OTHER.whl',budget=m.ReadBudget(1048576))
    def test_mutable_and_subclass_inputs_refuse_before_hashing(self):
        class SubBytes(bytes):pass
        for raw in (bytearray(self.raw),memoryview(self.raw),SubBytes(self.raw)):
            with self.assertRaisesRegex(m.WheelRefused,'IMMUTABLE_BYTES_REQUIRED'):
                m.validate_wheel(raw,expected_sha256='0'*64,filename=m.FILENAME,budget=m.ReadBudget(1048576))
    def test_duplicate_RECORD_row_is_not_last_wins(self):
        rows=record_rows(bodies());rows.append(rows[0][:]);self.refuse(make_wheel(rows=rows),'RECORD_UNIQUE_SCHEMA')
    def test_extra_RECORD_name_is_not_ignored(self):
        rows=record_rows(bodies());rows.append(['orphan.py','sha256='+'A'*43,'1'])
        self.refuse(make_wheel(rows=rows),'RECORD_EXTRA_NAME')
    def test_missing_RECORD_row_refuses(self):
        rows=record_rows(bodies());rows.pop(0);self.refuse(make_wheel(rows=rows),'RECORD_MISSING_NAME')
    def test_missing_or_hashed_self_row_refuses(self):
        rows=record_rows(bodies());rows.pop();self.refuse(make_wheel(rows=rows),'RECORD_MISSING_NAME')
        rows=record_rows(bodies());rows[-1][1]='sha256='+'A'*43;self.refuse(make_wheel(rows=rows),'RECORD_SELF_EXCEPTION')
    def test_wrong_member_hash_and_noncanonical_hash_refuse(self):
        for replacement in ('sha256='+'A'*43,'md5='+'A'*43,'sha256='+'A'*43+'='):
            rows=record_rows(bodies());rows[0][1]=replacement;self.refuse(make_wheel(rows=rows),'RECORD_HASH')
    def test_wrong_missing_negative_or_padded_size_refuses(self):
        for replacement in ('9999','','-1','01'):
            rows=record_rows(bodies());rows[0][2]=replacement;self.refuse(make_wheel(rows=rows),'RECORD_SIZE')
    def test_malformed_record_schema_refuses(self):
        rows=record_rows(bodies());rows[0].append('EXTRA');self.refuse(make_wheel(rows=rows),'RECORD_UNIQUE_SCHEMA')
    def test_extra_or_missing_archive_file_refuses(self):
        data=bodies();data['extra.py']=b'NEVER EXECUTE';self.refuse(make_wheel(data),'MEMBER_SUBSET')
        data=bodies();del data[m.PAYLOAD];self.refuse(make_wheel(data),'MEMBER_SET')
    def test_duplicate_archive_and_casefold_alias_refuse(self):
        for name in (m.PAYLOAD,m.PAYLOAD.upper()):
            self.refuse(make_wheel(extra=[(name,b'NEVER EXECUTE',stat.S_IFREG|0o644)]),'ZIP_DUPLICATE|MEMBER_SUBSET')
    def test_absolute_parent_backslash_colon_and_control_paths_refuse(self):
        for name in ('/outside.py','../outside.py','x\\outside.py','x:outside.py','x\noutside.py'):
            self.refuse(make_wheel(extra=[(name,b'NEVER EXECUTE',stat.S_IFREG|0o644)]),'ZIP_PATH')
    def test_symlink_type_alias_and_executable_member_refuse(self):
        for mode,pattern in ((stat.S_IFLNK|0o777,'ZIP_TYPE_OR_FEATURE'),
                             (stat.S_IFDIR|0o755,'ZIP_TYPE_ALIAS'),
                             (stat.S_IFREG|0o755,'EXECUTABLE_MEMBER')):
            data=bodies();del data[m.PAYLOAD]
            self.refuse(make_wheel(data,extra=[(m.PAYLOAD,b'NEVER EXECUTE',mode)]),pattern)
    def test_raw_archive_and_member_size_caps(self):
        self.refuse(self.raw+b'x'*m.MAX_ARCHIVE,'ARCHIVE_SIZE_CAP')
        data=bodies();data[m.PAYLOAD]=b'x'*(m.MAX_MEMBER+1)
        self.refuse(make_wheel(data,compression=zipfile.ZIP_DEFLATED),'MEMBER_SIZE_CAP')
    def test_declared_inflation_cap_before_member_read(self):
        # Mutate five central declared lengths; local data/CRC is never read.
        raw=bytearray(self.raw);cursor=raw.find(b'PK\x01\x02')
        for _ in range(5):
            self.assertEqual(raw[cursor:cursor+4],b'PK\x01\x02')
            struct.pack_into('<I',raw,cursor+24,8192)
            n,e,c=struct.unpack_from('<3H',raw,cursor+28);cursor+=46+n+e+c
        self.refuse(bytes(raw),'INFLATION_CAP')
    def test_entry_count_cap_before_zip_construction(self):
        raw=bytearray(self.raw);end=len(raw)-22
        struct.pack_into('<HH',raw,end+8,33,33)
        self.refuse(bytes(raw),'ZIP_LAYOUT')
    def test_malformed_directory_and_comment_refuse(self):
        raw=bytearray(self.raw);cursor=raw.find(b'PK\x01\x02');raw[cursor]=0
        self.refuse(bytes(raw),'ZIP_DIRECTORY')
        self.refuse(self.raw+b'COMMENT','ZIP_EOCD')
    def test_metadata_and_entrypoint_subset_are_frozen(self):
        data=bodies();data[m.DIST+'METADATA']=data[m.DIST+'METADATA'].replace(b'1.0.0',b'2.0.0')
        self.refuse(make_wheel(data),'METADATA_IDENTITY')
        data=bodies();data[m.DIST+'WHEEL']=data[m.DIST+'WHEEL'].replace(b'true',b'false')
        self.refuse(make_wheel(data),'WHEEL_IDENTITY')
        data=bodies();data[m.DIST+'entry_points.txt']=ENTRYPOINT.replace(b'\n',b'\\n')
        self.refuse(make_wheel(data),'ENTRYPOINT_SUBSET')
    def test_deflate_validity_same_content_and_no_execution(self):
        token=validate(make_wheel(compression=zipfile.ZIP_DEFLATED))
        self.assertEqual({row[0] for row in token.members},m.MEMBERS)
    def test_simple_stdlib_oracle_matches_member_hashes(self):
        token=validate(self.raw)
        # Simpler independent test oracle: ordinary BytesIO/ZipFile reads data.
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive:
            expected=tuple(sorted((name,len(archive.read(name)),hashlib.sha256(archive.read(name)).hexdigest())
                                  for name in archive.namelist()))
        self.assertEqual(token.members,expected)
    def test_primary_hash_exception_is_not_replaced(self):
        error=RuntimeError('AUTHORED_PRIMARY_HASH_ERROR');original=m._digest
        def fail(raw):raise error
        try:
            m._digest=fail
            with self.assertRaises(RuntimeError) as caught:validate(self.raw)
            self.assertIs(caught.exception,error)
        finally:m._digest=original


class ReadOnlyAndBudgetTests(unittest.TestCase):
    def setUp(self):self.raw=make_wheel();self.budget=m.ReadBudget(1048576);self.token=validate(self.raw,self.budget)
    def test_stdlib_zipfile_accepts_named_seekable_stream(self):
        with self.token.open() as stream:
            self.assertEqual(stream.name,m.FILENAME)
            with zipfile.ZipFile(stream) as archive:
                self.assertEqual(archive.filename,m.FILENAME)
                self.assertEqual(archive.read(m.PAYLOAD),bodies()[m.PAYLOAD])
    def test_read_seek_readinto_and_eof(self):
        with self.token.open() as stream:
            self.assertTrue(stream.readable());self.assertTrue(stream.seekable());self.assertFalse(stream.writable())
            self.assertEqual(stream.read(4),self.raw[:4]);self.assertEqual(stream.tell(),4)
            self.assertEqual(stream.seek(-4,2),len(self.raw)-4)
            target=bytearray(8);self.assertEqual(stream.readinto(target),4);self.assertEqual(target[:4],self.raw[-4:])
            self.assertEqual(stream.read(),b'');self.assertEqual(stream.seek(0),0)
    def test_every_public_write_or_buffer_escape_refuses(self):
        stream=self.token.open()
        for operation in (lambda:stream.write(b'BAD'),lambda:stream.writelines([b'BAD']),lambda:stream.truncate(0),
                          stream.getbuffer,stream.fileno,stream.detach):
            with self.assertRaises(io.UnsupportedOperation):operation()
        with self.assertRaises(TypeError):memoryview(stream)
        with self.assertRaises(TypeError):io.BytesIO.write(stream,b'BAD')
        self.assertEqual(stream.getvalue(),self.raw);stream.close()
    def test_bytes_return_values_cannot_mutate_source(self):
        stream=self.token.open();value=stream.getvalue();self.assertIs(type(value),bytes)
        self.assertTrue(memoryview(value).readonly)
        modified=bytearray(value);modified[0]^=1
        self.assertEqual(stream.getvalue(),self.raw);stream.close()
    def test_token_and_filename_properties_are_readonly(self):
        for obj,name,value in ((self.token,'filename','OTHER'),(self.token,'sha256','0'*64),
                               (self.token,'members',()),(self.token.open(),'name','OTHER')):
            with self.assertRaises(AttributeError):setattr(obj,name,value)
        with self.assertRaises(TypeError):self.token.members[0][0]='OTHER'
    def test_closed_stream_refuses_and_context_preserves_primary(self):
        stream=self.token.open();error=RuntimeError('AUTHORED_PRIMARY')
        with self.assertRaises(RuntimeError) as caught:
            with stream:raise error
        self.assertIs(caught.exception,error);self.assertTrue(stream.closed)
        with self.assertRaises(ValueError):stream.read()
        stream.close()
    def test_validation_budget_exhaustion_is_sticky(self):
        budget=m.ReadBudget(len(self.raw)-1)
        with self.assertRaisesRegex(m.WheelRefused,'READ_BUDGET_EXHAUSTED'):validate(self.raw,budget)
        self.assertTrue(budget.failed);self.assertEqual(budget.used,0)
        with self.assertRaisesRegex(m.WheelRefused,'READ_BUDGET_FAILED'):validate(self.raw,budget)
    def test_shared_budget_cannot_be_reset_by_open_or_seek(self):
        budget=m.ReadBudget(1048576);token=validate(self.raw,budget);before=budget.used
        one,two=token.open(),token.open();one.read(5);two.read(7);one.seek(0);one.read(5)
        self.assertEqual(budget.used,before+17);one.close();two.close()
        with self.assertRaises(AttributeError):budget.limit=2000000
    def test_failed_read_preserves_cursor_and_destination(self):
        budget=m.ReadBudget(3);stream=m.ReadOnlyWheelStream(b'abcdef',m.FILENAME,budget)
        target=bytearray(b'UNCHANGED')
        with self.assertRaisesRegex(m.WheelRefused,'READ_BUDGET_EXHAUSTED'):stream.readinto(target)
        self.assertEqual(stream.tell(),0);self.assertEqual(target,b'UNCHANGED');self.assertEqual(budget.used,0)
    def test_readinto_readonly_target_and_invalid_seek_do_not_consume(self):
        stream=self.token.open();before=self.budget.used
        with self.assertRaises(TypeError):stream.readinto(b'FIXED')
        with self.assertRaisesRegex(m.WheelRefused,'SEEK_RANGE'):stream.seek(-1)
        with self.assertRaisesRegex(m.WheelRefused,'READ_SIZE'):stream.read(True)
        self.assertEqual(self.budget.used,before);self.assertEqual(stream.tell(),0);stream.close()
    def test_no_mutable_input_or_budget_subclass_in_stream(self):
        class FakeBudget(m.ReadBudget):pass
        with self.assertRaisesRegex(m.WheelRefused,'STREAM_BINDING'):
            m.ReadOnlyWheelStream(bytearray(b'abc'),m.FILENAME,self.budget)
        with self.assertRaisesRegex(m.WheelRefused,'READ_BUDGET_TYPE'):
            m.ReadOnlyWheelStream(b'abc',m.FILENAME,FakeBudget(20))


class ImportAndScopeTests(unittest.TestCase):
    def test_candidate_contains_no_filesystem_payload_execution_or_thirdparty_import(self):
        tree=ast.parse(CANDIDATE.read_bytes())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module)
        self.assertFalse(set(imports)&{'installer','pip','os','sys','subprocess','socket','pathlib'})
        calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
        self.assertFalse(calls & {'open','exec','eval','compile','__import__'})
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in {'extract','extractall'} for n in ast.walk(tree)))
    def test_test_guards_are_only_installed_by_standalone_entrypoint(self):
        tree=ast.parse(Path(__file__).read_bytes())
        direct=[n for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)]
        self.assertFalse(any(isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='addaudithook' for n in direct))
        calls=[n for n in tree.body if isinstance(n,ast.If) and '__name__' in ast.unparse(n.test)
               and any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name)
                       and x.func.id=='_install_standalone_early_guard' for x in ast.walk(n))]
        self.assertEqual(len(calls),1)


def guarded_main():
    reads=[0];output=[0]
    stdlib=Path(sys.base_prefix)/'lib'
    allowed_files={Path(__file__).resolve(),CANDIDATE}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path=Path(os.path.realpath(args[0]));flags=args[2]
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                raise AssertionError('PURE_SOURCE_NO_FILESYSTEM_WRITES')
            allowed=path in allowed_files or (path.is_relative_to(stdlib) and 'site-packages' not in path.parts)
            if not allowed:raise AssertionError('PURE_SOURCE_UNAPPROVED_FILE_READ')
            try:size=path.stat().st_size
            except FileNotFoundError:size=0
            reads[0]+=size+1
            if reads[0]>67108864:raise AssertionError('PURE_SOURCE_READ_CAP')
        if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.truncate','os.chmod'}:
            raise AssertionError('PURE_SOURCE_NO_FILESYSTEM_MUTATION')
    sys.addaudithook(audit)
    class Output:
        def __init__(self,stream):self.stream=stream
        def __getattr__(self,name):return getattr(self.stream,name)
        def write(self,value):
            output[0]+=len(value.encode())
            if output[0]>262144:raise AssertionError('PURE_SOURCE_OUTPUT_CAP')
            return self.stream.write(value)
    sys.stdout=Output(sys.stdout);sys.stderr=Output(sys.stderr)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    def timeout(*_):raise AssertionError('PURE_SOURCE_WALL_CAP')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
    unittest.main(failfast=True,verbosity=2)


if __name__=='__main__':guarded_main()
