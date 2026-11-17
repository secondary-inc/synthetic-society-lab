"""Finite exact-file design measurement. No candidate/tool import or execution."""
from pathlib import Path
import hashlib
import io
import json
import os
import resource
import signal
import stat
import sys
import time
import zipfile

ROOT=Path.cwd();OUT=ROOT/'reports/evidence_e01_pypa_fixture_g03_integration_design_v1_20261116'
START=time.monotonic();CPU=time.process_time();read_bytes=0;refs={};cache={}
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def timeout(*_):raise RuntimeError('DESIGN_TIME_CAP')
signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
def guard(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','ctypes.dlopen'}:raise RuntimeError('DESIGN_NO_NETWORK_PROCESS_NATIVE')
 if event=='import' and args and args[0].split('.')[0] in {'installer','pip','ssl_fixture_payload','pypdf','PIL','cryptography','cffi','_cffi_backend'}:raise RuntimeError('DESIGN_NO_TOOL_IMPORT')
sys.addaudithook(guard)
def reserve(n):
 global read_bytes
 if type(n) is not int or n<0 or read_bytes+n>67108864:raise RuntimeError('DESIGN_CONTENT_READ_CAP')
 read_bytes+=n
 if time.monotonic()-START>120 or time.process_time()-CPU>120:raise RuntimeError('DESIGN_TIME_CAP')
def read(path,maximum=1048576):
 path=Path(path)
 if path in cache:return cache[path]
 if not path.is_absolute():raise RuntimeError('DESIGN_ABSOLUTE_INPUT')
 if '.venv-e01' in str(path) or path.name.startswith('.env'):raise RuntimeError('DESIGN_NO_OLD_TARGET_OR_KEY')
 if any(p.is_symlink() for p in (path,*path.parents)):raise RuntimeError('DESIGN_ALIAS')
 before=path.stat()
 if not stat.S_ISREG(before.st_mode) or before.st_size>maximum:raise RuntimeError('DESIGN_INPUT_BOUND')
 reserve(before.st_size+1)
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  with os.fdopen(fd,'rb') as stream:
   opened=os.fstat(stream.fileno());raw=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
 except BaseException:raise
 ident=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
 if ident(before)!=ident(opened) or ident(opened)!=ident(after) or len(raw)!=before.st_size:raise RuntimeError('DESIGN_INPUT_CHANGED')
 refs[str(path)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};cache[path]=raw;return raw
runtime=Path('/Users/joshua/.cache/codex-runtimes/codex-primary-runtime/dependencies/python')
if Path(sys.base_prefix)!=runtime or sys.version.split()[0]!='3.12.14':raise RuntimeError('DESIGN_HELPER_RUNTIME')
known={
 'runtime_executable':runtime/'bin/python3.12',
 'parent_caller':ROOT/'scripts/e01_pypa_fixture_g03_caller_candidate_v1_1_20261116.py',
 'harness':ROOT/'scripts/e01_pypa_fixture_harness_candidate_v1_1_20261116.py',
 'strict_source':ROOT/'scripts/e01_strict_wheel_source_candidate_v1_20261116.py',
 'original_policy':ROOT/'scripts/install_e01_pypdf701_runtime_v1_5.py',
 'directory_guard':ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py',
 'harness_review':ROOT/'reports/INDEPENDENT_AUDIT_E01_PYPA_FIXTURE_HARNESS_V1_1_20261116.json',
 'parent_review':ROOT/'reports/INDEPENDENT_AUDIT_E01_PYPA_FIXTURE_G03_PREPARATION_V1_1_20261116.json',
 'source_review':ROOT/'reports/INDEPENDENT_AUDIT_E01_PYPA_INSTALLER_SOURCE_ACQUISITION_20261116.json',
 'validator_review':ROOT/'reports/INDEPENDENT_AUDIT_E01_STRICT_WHEEL_SOURCE_PURE_V1_20261116.json',
 'bytes_review':ROOT/'reports/INDEPENDENT_AUDIT_E01_PYPA_INSTALLER_FIXTURE_BYTES_V1_1_20261116.json',
 'tool_archive':ROOT/'data/processed/e01_installer_tool_source_v1_20261116/2-RESPONSE.bin',
 'dataclasses_source':runtime/'lib/python3.12/dataclasses.py',
}
for name,path in known.items():read(path,20971520 if name=='runtime_executable' else 1048576)
assert refs[str(known['runtime_executable'])]=={'bytes':18058560,'sha256':'9d1335796350848c36dc2711a3298e096deebee18c85f1ab36edd8747fdf85eb'}
assert refs[str(known['harness'])]=={'bytes':52778,'sha256':'1c55c942b061452f741d1242640fd1b85a8f11b398a30fea6c391525006b20b8'}
assert refs[str(known['parent_caller'])]=={'bytes':18224,'sha256':'1d956931da7d11cf58cfc540cd7b6b8634aecffc34e5c9b9aa4373be92879abc'}
assert refs[str(known['parent_review'])]=={'bytes':53113,'sha256':'10c8a3fb13b2ef31f69a740dcd1acb4cd62658f9dcb758033a2d0f9aec8f37da'}
assert refs[str(known['harness_review'])]=={'bytes':47690,'sha256':'b05c35ca8df6dedf0cb43508a0fd43422efbdccd35c3e7d7aeed4d1597ce88c4'}
assert refs[str(known['tool_archive'])]=={'bytes':464466,'sha256':'f55f5728ff61d3dd54dbc5a397cf3f7307cb64b180c20b72afbebf01c9e2c8a0'}
stdlib=runtime/'lib/python3.12'
# An explicit source-evidence list, NOT a recursive library walk or a claimed
# complete runtime/import closure. These files address the exact open questions.
source_names=['importlib/_bootstrap.py','importlib/_bootstrap_external.py','encodings/__init__.py',
 'encodings/aliases.py','encodings/utf_8.py','codecs.py','zipimport.py']
stdlib_evidence={}
for name in source_names:
 path=stdlib/name;raw=read(path);lines=raw.decode().splitlines()
 stdlib_evidence[name]={'ref':{'path':str(path),**refs[str(path)]},
  'relevant_lines':[{'line':i+1,'text':line.strip()} for i,line in enumerate(lines)
   if ('pycache_prefix' in line or 'get_code(' in line or 'get_data(' in line or 'source_to_code(' in line or 'get_source(' in line or 'compile(' in line or 'read_code' in line or 'cache_from_source(' in line)][:30]}
raw=cache[known['tool_archive']];tool_members={};tool_imports={}
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
 for info in archive.infolist():
  if info.filename.endswith('.py'):
   reserve(info.file_size);body=archive.read(info.filename)
   tool_members[info.filename]={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
   tool_imports[info.filename]=[{'line':i+1,'text':line.strip()} for i,line in enumerate(body.decode().splitlines()) if line.startswith(('import ','from '))]
# CRC/decompression reads of these exact small Python members only. No exe
# launchers/resources are read or extracted; no source is parsed/evaluated.
strict=cache[known['strict_source']].decode().splitlines()
readbudget_evidence=[{'line':i+1,'text':line} for i,line in enumerate(strict) if 42<=i+1<=65]
metadata={}
for name in ['_sha2','resource','_hashlib','_ssl','_socket','select','_posixsubprocess']:
 path=stdlib/'lib-dynload'/(name+'.cpython-312-darwin.so')
 metadata[str(path)]={'exists':path.exists(),'bytes':path.stat().st_size if path.exists() else None,'content_hashed':False}
c_sources={}
for name in ['Python/pylifecycle.c','Python/initconfig.c','Python/import.c','Modules/main.c','Modules/getpath.py']:
 path=runtime/name;c_sources[str(path)]={'exists':path.exists(),'body_read':False}
fixed_parent=sum(refs[str(path)]['bytes']+1 for path in known.values())
explicit_stdlib=sum(refs[str(stdlib/name)]['bytes']+1 for name in source_names)
MiB=1048576
allocation={'parent_preflight':20*MiB,'trusted_bootstrap_reserve':8*MiB,'child_filesystem':32*MiB,'strict_memory':4*MiB}
assert sum(allocation.values())==64*MiB
result={'kind':'G03_BOUNDED_READ_ONLY_MEASUREMENT','helper_runtime':sys.version.split()[0],
 'helper_builtin_names':list(sys.builtin_module_names),'helper_flags':{'isolated':sys.flags.isolated,'no_site':sys.flags.no_site,'dont_write_bytecode':sys.dont_write_bytecode},
 'fixed_parent_inputs':{name:{'path':str(path),**refs[str(path)]} for name,path in known.items()},
 'fixed_parent_logical_read_charge_bytes':fixed_parent,'parent20MiB_remaining_before_unknown_closure_and_child_adapter':20*MiB-fixed_parent,
 'explicit_stdlib_source_evidence':stdlib_evidence,'explicit_stdlib_source_charge_bytes':explicit_stdlib,
 'parent20MiB_remaining_if_the_seven_evidence_sources_also_rehashed':20*MiB-fixed_parent-explicit_stdlib,
 'tool_python_source_members':tool_members,'tool_python_source_total_bytes':sum(v['bytes'] for v in tool_members.values()),'tool_import_statements_not_complete_transitive_closure':tool_imports,
 'ReadBudget_source_evidence':readbudget_evidence,
 'specific_extension_metadata_only':metadata,'local_CPython_startup_source_presence':c_sources,
 'proposed_partitions_bytes':allocation,'allocation_sum_bytes':sum(allocation.values()),
 'allocation_status':{'parent20MiB':'KNOWN_SUBSET_FITS_COMPLETE_CLOSURE_NOT_PROVEN','bootstrap8MiB':'UNSUBSTANTIATED_NO_STARTUP_TRACE_OR_C_INITIALIZATION_SOURCE_PROOF',
  'child_filesystem32MiB':'ENFORCEABLE_MONOTONE_CAP_NOT_A_SUCCESSFUL_RUNTIME_READ_COUNT','strict_memory4MiB':'VALID_SMALLER_EXACT_ReadBudget_CONSTRUCTOR_RANGE_ENFORCEMENT_REQUIRES_NEW_ADAPTER'},
 'helper_accounting':{'content_read_charge_bytes':read_bytes,'cap_bytes':67108864,'CPU_seconds':time.process_time()-CPU,
  'wall_seconds':time.monotonic()-START,'CPU_wall_cap_seconds':120,'source_read_boundary':'Explicit read() plus exact decompressed tool-Python member charges; helper interpreter/stdlib bootstrap is outside this meter, no whole-process IO claim.'},
 'no_actual_actions':{'fixture_children':0,'actual_backend_calls':0,'candidate_or_tool_import_compile_execute':0,'global_candidate_hook_installations':0,
  'old_targets_PDF_research_raw':0,'network_model_credentials_ledger':0,'production_Git_STATUS_changes':0},
 'conclusion':'BLOCKED_EXACT_BOOTSTRAP_BOUND_AND_CODE_CLOSURE_NOT_SUBSTANTIATED.8MiB is an arithmetic reserve, not verified usage or a proven upper bound. Complete parent closure also lacks that immutable artifact.'}
path=OUT/'MEASURED_FACTS.json';body=json.dumps(result,indent=2,sort_keys=True).encode()+b'\n'
if len(body)>1048576:raise RuntimeError('DESIGN_OUTPUT_BOUND')
with path.open('xb') as stream:stream.write(body)
print(json.dumps({'result_ref':{'path':str(path.relative_to(ROOT)),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()},
 'fixed_parent_charge':fixed_parent,'parent_remaining':20*MiB-fixed_parent,'explicit_stdlib_charge':explicit_stdlib,
 'allocation_sum':sum(allocation.values()),'helper_read_bytes':read_bytes,'helper_CPU_seconds':time.process_time()-CPU,
 'decision':'BLOCKED_BOOTSTRAP_BOUND_NOT_SUBSTANTIATED'},sort_keys=True))
