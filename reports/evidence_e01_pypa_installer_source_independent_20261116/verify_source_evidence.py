import sys
from pathlib import Path
import os,resource,signal,time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent;START=time.monotonic();READS=0
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def stop(*a):raise RuntimeError('SOURCE_REVIEW_DEADLINE')
signal.signal(signal.SIGALRM,stop);signal.signal(signal.SIGXCPU,stop);signal.setitimer(signal.ITIMER_REAL,120)
def audit(event,args):
 global READS
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn','os.exec','os.fork','os.forkpty','ctypes.dlopen'}:raise RuntimeError('SOURCE_REVIEW_NO_ACTUAL_NETWORK_EXECUTION')
 if event=='import' and args and args[0].split('.')[0] in {'installer','pip','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:raise RuntimeError('SOURCE_REVIEW_NO_TOOL_TARGET_IMPORT')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  path=Path(os.fsdecode(args[0])).absolute();flags=args[2]
  if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
   if not path.is_relative_to(OUT):raise RuntimeError('SOURCE_REVIEW_WRITE_SCOPE')
  else:
   if path.is_relative_to(ROOT/'data/raw') or path.name.startswith('.env'):raise RuntimeError('SOURCE_REVIEW_RAW_CREDENTIAL_READ')
   try:size=path.stat().st_size
   except FileNotFoundError:size=0
   READS+=size+1
   if READS>67108864:raise RuntimeError('SOURCE_REVIEW_READ_CAP')
sys.addaudithook(audit)
import ast,base64,csv,hashlib,io,json,re,stat,struct,zipfile
from datetime import datetime
from email.parser import BytesParser
checks=[];refs={}
def need(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
def read(s):
 p=ROOT/s;need(all(not q.is_symlink() for q in (p,*p.parents)),'no_alias:'+s);b=p.read_bytes();refs[s]={'path':s,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def pin(r):b=read(r['path']);need(refs[r['path']]==r,'pin:'+r['path']);return b
def js(s):return json.loads(read(s))
rp='reports/E01_PYPA_INSTALLER_SOURCE_ACQUISITION_20261116.json';r=json.loads(pin({'path':rp,'bytes':18994,'sha256':'7ba764a1f037c5f2dafab98f76bf1cbc3f4940ec872c7323d63bf6a2a62fd22f'}))
for section in ['INPUT_ARTIFACTS','OUTPUT_ARTIFACTS']:
 for name,v in r[section].items():pin({'path':name,**v})
gate=js('reports/E01_PYPA_INSTALLER_SOURCE_GATE_20261116.json');helper=read('scripts/acquire_e01_installer_tool_source_v1_20261116.py').decode();scope=r['private_scope']['path']+'/'
need(stat.S_IMODE((ROOT/scope).stat().st_mode)==0o700,'private_scope_mode0700')
files={}
for path in sorted((ROOT/scope).iterdir()):
 need(path.is_file() and not path.is_symlink() and stat.S_IMODE(path.stat().st_mode)==0o600,'private_regular_mode0600:'+path.name)
 files[path.name]=pin({'path':scope+path.name,**r['private_scope']['scope_refs'][path.name]})
need(len(files)==10 and sum(map(len,files.values()))==514575<4194304,'ten_files_full_scope514575')
st=json.loads(files['STARTED.json']);t=json.loads(files['TERMINAL.json']);selection=json.loads(files['SELECTED.json']);analysis=json.loads(files['SOURCE_ANALYSIS.json']);metadata=json.loads(files['1-RESPONSE.bin'])
need(st['gate_sha256']==refs['reports/E01_PYPA_INSTALLER_SOURCE_GATE_20261116.json']['sha256'] and st['helper_sha256']==refs['scripts/acquire_e01_installer_tool_source_v1_20261116.py']['sha256'] and st['review_ref']==gate['prerequisite_review_ref'],'started_exact_gate_helper_review')
need(st['limits']==t['limits']==gate['limits'] and st['no_retry'] is True and t['no_retry'] is True,'same_source_limits_no_retry')
need(t['status']=='SOURCE_ACQUIRED_STATIC_INTEGRITY_ONLY' and t['error'] is None and t['phase']=='AST_INSPECT','closed_source_success_only')
need(t['package_imports_or_execution']==t['extracted_files']==t['new_installation_children']==t['cost_USD']==0 and t['installation_or_runtime_or_P3_accepted'] is False,'no_execution_target_or_qualification')
need(t['installation_allocation_fully_consumed_unchanged']==gate['installation_allocation_unchanged_fully_consumed']=={'main_children':12,'observed_CPU_seconds':180,'wall_seconds':450},'actual450_180_12unchanged')
need(len(t['artifacts'])==9 and t['source_scope_write_bytes_before_terminal']==sum(len(files[x['path']]) for x in t['artifacts'])==511294 and 511294+len(files['TERMINAL.json'])==514575,'terminal_self_inclusive_scope_accounting')
for x in t['artifacts']:need(refs[scope+x['path']]=={'path':scope+x['path'],'bytes':x['bytes'],'sha256':x['sha256']},'terminal_artifact_exact:'+x['path'])
need([x['path'] for x in t['artifacts']]==['STARTED.json','1-REQUEST_RESERVED.json','1-RESPONSE.bin','1-REQUEST_RESULT.json','SELECTED.json','2-REQUEST_RESERVED.json','2-RESPONSE.bin','2-REQUEST_RESULT.json','SOURCE_ANALYSIS.json'],'reservation_result_artifact_order')
for n in [1,2]:
 res=json.loads(files[str(n)+'-REQUEST_RESERVED.json']);done=json.loads(files[str(n)+'-REQUEST_RESULT.json']);body=files[str(n)+'-RESPONSE.bin']
 need(res['number']==done['number']==n and res['method']==done['method']=='GET' and res['url']==done['url'] and res['status'] is None and res['body_bytes']==0,'reserved_before_result:'+str(n))
 need(done==t['requests'][n-1] and done['status']==200 and done['body_bytes']==done['content_length']==len(body)<=1048576 and done['body_sha256']==hashlib.sha256(body).hexdigest() and done['retries_allowed']==done['redirects_allowed']==0,'closed_get_result_hash_cap:'+str(n))
need(t['HTTP_body_bytes']==len(files['1-RESPONSE.bin'])+len(files['2-RESPONSE.bin'])==493674<2097152,'two_body_total')
interval=(datetime.fromisoformat(t['UTC'])-datetime.fromisoformat(st['UTC'])).total_seconds()
need(0<interval<15 and 0<t['elapsed_fetch_static_seconds']<15 and abs(interval-t['elapsed_fetch_static_seconds'])<0.01 and t['observed_CPU_seconds']<20,'actual_entire_stage_under15_without_general_request_guarantee')
info=metadata['info'];version=info['version'];need(info['name'].lower()=='installer' and version=='1.1.0' and info['requires_python']=='>=3.10','retained_metadata_project_latest_at_fetch')
candidates=[x for x in metadata['urls'] if x.get('packagetype')=='bdist_wheel' and x.get('filename')=='installer-'+version+'-py3-none-any.whl' and x.get('yanked') is False];need(len(candidates)==1,'exact_one_non_yanked_universal_candidate')
x=candidates[0];need(selection==r['SOURCE_DATA_AND_LICENSE_NOTES']['selected']==t['selection']==analysis['selected'],'same_selection_all_closed_records')
need(x['digests']['sha256']==selection['sha256'] and x['size']==selection['size']==464466 and x['url']==selection['url']==t['requests'][1]['url'] and x['requires_python']=='>=3.10' and x['python_version']=='py3','selected_exact_metadata_file_identity')
need((3,11,17)>=(3,10,0) and (3,12,14)>=(3,10,0),'declared_numeric_python_range_only')
raw=files['2-RESPONSE.bin'];need(len(raw)==selection['size'] and hashlib.sha256(raw).hexdigest()==selection['sha256']=='f55f5728ff61d3dd54dbc5a397cf3f7307cb64b180c20b72afbebf01c9e2c8a0','archive_sha_size')
end=raw.rfind(b'PK\x05\x06',max(0,len(raw)-65557));need(end>=0,'EOCD_present');disk,cddisk,countdisk,count,cdsize,offset,comment=struct.unpack_from('<4H2IH',raw,end+4);need(disk==cddisk==0 and countdisk==count==23 and end+22+comment==len(raw) and offset+cdsize==end,'single_disk_nonzip64_directory_layout')
members={};memberrefs={};trees={};nodes=0;imports=set();native=[]
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
 infos=archive.infolist();need(len(infos)==23 and sum(i.file_size for i in infos)==978081<8388608 and max(i.file_size for i in infos)==182784<1048576,'23_entries_978081_declaredinflation')
 folded=set()
 for item in infos:
  name=item.filename;parts=name.rstrip('/').split('/');need(name==item.orig_filename and name and len(name.encode())<=240 and all(32<=ord(c)<127 for c in name) and not name.startswith('/') and '\\' not in name and ':' not in name and all(p not in {'','.','..'} for p in parts),'bounded_safe_path:'+name)
  need(name.rstrip('/').casefold() not in folded,'casefold_unique:'+name);folded.add(name.rstrip('/').casefold())
  kind=stat.S_IFMT(item.external_attr>>16);need(kind in {0,stat.S_IFREG,stat.S_IFDIR} and not item.flag_bits&1 and item.compress_type in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED},'entry_type_compression:'+name)
  need(not item.is_dir(),'all23_entries_are_files')
  READS+=item.file_size+1;need(READS<=67108864,'member_read_budget')
  with archive.open(item) as stream:body=stream.read(item.file_size+1)
  need(len(body)==item.file_size,'bounded_member_size:'+name);members[name]=body;memberrefs[name]={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
  need(memberrefs[name]==analysis['member_refs'][name],'source_analysis_member_ref:'+name)
  if name.endswith('.exe'):native.append(name)
  if name.endswith('.py'):
   tree=ast.parse(body,filename='INDEPENDENT_STATIC_SOURCE_ONLY');trees[name]=tree;nodes+=sum(1 for _ in ast.walk(tree))
   need(memberrefs[name]==r['SOURCE_DATA_AND_LICENSE_NOTES']['source_hashes'][name],'report_python_source_pin:'+name)
   for node in ast.walk(tree):
    if isinstance(node,ast.Import):imports.update(a.name.split('.')[0] for a in node.names)
    elif isinstance(node,ast.ImportFrom) and node.level==0 and node.module:imports.add(node.module.split('.')[0])
for name in members:
 need(not any('/'.join(name.split('/')[:i]) in members for i in range(1,len(name.split('/')))),'no_file_parent_alias:'+name)
dist='installer-1.1.0.dist-info/';rows=list(csv.reader(io.StringIO(members[dist+'RECORD'].decode())));seen=set();verified=0
for row in rows:
 need(len(row)==3 and row[0] not in seen and row[0] in members,'RECORD_unique_coverage_row');name,h,size=row;seen.add(name)
 if name==dist+'RECORD':need(h==size=='','only_self_empty_exception')
 else:
  expected='sha256='+base64.urlsafe_b64encode(hashlib.sha256(members[name]).digest()).rstrip(b'=').decode();need(h==expected and re.fullmatch(r'0|[1-9][0-9]*',size) and int(size)==len(members[name]),'RECORD_payload_sha_size:'+name);verified+=1
need(seen==set(members) and len(rows)==23 and verified==22 and analysis['record_coverage_files']==23 and analysis['other_record_exceptions']==[],'complete23_22hash_selfonly')
md=BytesParser().parsebytes(members[dist+'METADATA']);wh=BytesParser().parsebytes(members[dist+'WHEEL'])
need(md['Name']=='installer' and md['Version']=='1.1.0' and md['Requires-Python']=='>=3.10' and md.get_all('Requires-Dist',[])==[] and md['License-Expression']=='MIT','declared_metadata_no_requires_dist')
need(wh.get_all('Tag')==['py3-none-any'] and wh.get_all('Root-Is-Purelib')==['true'] and wh.get_all('Wheel-Version')==['1.0'],'universal_purelib_metadata_not_runtimeproof')
lic=r['SOURCE_DATA_AND_LICENSE_NOTES']['declared_license'];need(memberrefs[lic['license_file']]=={'bytes':lic['bytes'],'sha256':lic['sha256']} and lic['bytes']==1057 and b'Permission is hereby granted' in members[lic['license_file']] and b'copyright notice' in members[lic['license_file']].lower(),'MIT_declared_license_bytes_retained_no_legalcertification')
need(len(trees)==10 and nodes==analysis['AST_nodes']==5681 and len(native)==8,'tenPython5681nodes_eightEXEresources_hashonly')
need(sorted(imports)==r['static_findings']['imports_syntax_only'],'absolute_import_roots_syntax_only')
# Verify selected API signatures/callsite summaries without executing any member.
for name,items in analysis['selected_API_syntax_only'].items():
 for item in items:
  matching=[n for n in ast.walk(trees[name]) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==item['name'] and n.lineno==item['line']];need(len(matching)==1,'API_AST_identity:'+name+':'+str(item['line']));node=matching[0];calls=sorted({ast.unparse(c.func) for c in ast.walk(node) if isinstance(c,ast.Call)});need(node.end_lineno==item['end_line'] and ast.unparse(node.args)==item['arguments'] and calls==item['calls'] and not item['arguments_truncated'] and not item['calls_truncated'],'API_AST_args_calls_full:'+name+':'+str(item['line']))
def function(name,func,klass=None):
 tree=trees[name];body=next(n.body for n in tree.body if isinstance(n,ast.ClassDef) and n.name==klass) if klass else tree.body
 return next(n for n in body if isinstance(n,ast.FunctionDef) and n.name==func)
record_validate=function('installer/records.py','validate_stream','RecordEntry');source_validate=function('installer/sources.py','validate_record','WheelFile');install=function('installer/_core.py','install');compile_bc=function('installer/destinations.py','_compile_bytecode','SchemeDictionaryDestination');path_func=function('installer/destinations.py','_path_with_destdir','SchemeDictionaryDestination')
need('Path(os.devnull).open' in {ast.unparse(n.func) for n in ast.walk(record_validate) if isinstance(n,ast.Call)},'STATIC_guard_mismatch_devnull_write')
need(any(isinstance(n,ast.Call) and ast.unparse(n.func)=='Path(os.devnull).open' and any(isinstance(a,ast.Constant) and a.value=='wb' for a in n.args) for n in ast.walk(record_validate)),'devnull_open_mode_wb_not_read')
need(any(isinstance(n,ast.DictComp) for n in ast.walk(source_validate)) and 'record_mapping.pop' in {ast.unparse(n.func) for n in ast.walk(source_validate) if isinstance(n,ast.Call)},'STATIC_RECORD_mapping_lastwins_and_pop')
need('source.validate_record' not in {ast.unparse(n.func) for n in ast.walk(install) if isinstance(n,ast.Call)} and {'destination.write_script','destination.write_file','destination.finalize_installation'}<={ast.unparse(n.func) for n in ast.walk(install) if isinstance(n,ast.Call)},'core_no_automatic_full_RECORD_validation')
need('compileall.compile_file' in {ast.unparse(n.func) for n in ast.walk(compile_bc) if isinstance(n,ast.Call)} and isinstance(compile_bc.body[1],ast.If) and isinstance(compile_bc.body[1].body[0],ast.Return),'bytecode_early_exit_before_compileall_import')
need('file.is_relative_to' in {ast.unparse(n.func) for n in ast.walk(path_func) if isinstance(n,ast.Call)},'destination_normalized_containment_present_not_symlinkproof')
guard=read('scripts/install_e01_pypdf701_runtime_v1_5.py').decode();need("if not self.owned(path): self.refuse('GUEST_WRITE_OUTSIDE_OWNED')" in guard and "Path('/dev/null')" in guard,'frozen_guard_devnull_readonly_not_write_allowance')
need('opener.open(request,timeout=15)' in helper and 'signal.setitimer(signal.ITIMER_REAL,60)' in helper,'socket15_and_stage60_distinct_not_whole_request15')
console=read('reports/evidence_e01_pypa_installer_source_acquisition_20261116/acquisition_console.txt');need(len(console)==306 and json.loads(console)['status']==t['status'],'closed306B_console_status')
result={'status':'PASS_ACQUIRED_SOURCE_EVIDENCE_INTEGRITY_UNMODIFIED_FULL_RECORD_API_GUARD_FIT_BLOCKED','count':len(checks),'checks':checks,'evidence_refs':refs,'archive_member_refs':memberrefs,'python_AST_nodes':nodes,'Python_sources':10,'EXE_resource_names_only':native,'RECORD_hashed_rows':verified,'RECORD_self_exception':dist+'RECORD','scope_bytes':514575,'body_bytes':493674,'closed_UTC_interval_seconds':interval,'closed_monotonic_seconds':t['elapsed_fetch_static_seconds'],'review_logical_source_member_reads_charged':READS,'review_elapsed_seconds':time.monotonic()-START,'package_or_helper_import_execution':0,'source_gate_actual_limit_acceptance':'Observedactualunderlimits only; consumedhelper notgenerallycertified/reusable','integration_blockers':['RecordEntry.validate_stream writes /dev/null under full validation; originalguardwriteonlyowned denies it.','RECORD dict collapses duplicates; validate_record does not assert empty remainingmapping, so no standalonebidirectionalcoverage guarantee.','Destination existencecheck/open(wb) notexclusive/nofollowsymlink defense; preserve originalguard/writer policy.','Explicit empty bytecode levels needed; compileall path otherwisepresent.'],'cost_USD':0}
rawout=(json.dumps(result,indent=2)+'\n').encode();need(len(rawout)<4194304,'audit_output_cap');(OUT/'source_checks.json').write_bytes(rawout);print(json.dumps({'status':result['status'],'checks':len(checks),'source_member_read_bytes':READS,'scope_bytes':514575,'archive_rows_hashed':verified,'review_elapsed_seconds':time.monotonic()-START}))
