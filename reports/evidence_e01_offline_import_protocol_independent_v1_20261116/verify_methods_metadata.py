from pathlib import Path
import configparser,csv,hashlib,io,json,resource,signal,time,zipfile
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent;READS=0;START=time.monotonic();checks=[];refs={}
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def stop(*a):raise RuntimeError('METADATA_REVIEW_DEADLINE')
signal.signal(signal.SIGALRM,stop);signal.setitimer(signal.ITIMER_REAL,120)
def need(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
def read(s):
 global READS
 p=ROOT/s;need(all(not q.is_symlink() for q in (p,*p.parents)),'no_alias:'+s);size=p.stat().st_size;READS+=size+1;need(READS<=67108864,'source_zip_read_cap:'+s)
 b=p.read_bytes();need(len(b)==size,'size:'+s);refs[s]={'path':s,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def pin(r):b=read(r['path']);need(refs[r['path']]==r,'pin:'+r['path']);return b
def js(s):return json.loads(read(s))
rp='reports/E01_OFFLINE_IMPORT_PROTOCOL_METHODS_V1_20261116.json';r=json.loads(pin({'path':rp,'bytes':20047,'sha256':'cfe2118b1ca647510bd719c2c5fd0f07ba00642157aab359e70c0c7a8d796867'}))
for path,d in r['OUTPUT_ARTIFACTS'].items():pin({'path':path,**d})
source={}
for path,d in r['SOURCE_DATA_AND_LICENSE_NOTES']['static_source_refs'].items():source[path]=pin({'path':path,**d}).decode()
meta=js('reports/evidence_e01_offline_import_protocol_methods_v1_20261116/wheel_format_metadata.json');gridraw=read('reports/evidence_e01_offline_import_protocol_methods_v1_20261116/matched_results.json');grid=json.loads(gridraw)
need(grid==r['TESTS_RUN_AND_RESULTS']['results'] and hashlib.sha256(gridraw).hexdigest()==r['TESTS_RUN_AND_RESULTS']['results_sha256']=='7722bfd2e0e292d3a2a7064db26fb42160cb3bb63837372895664ad38f693209','report_six_grid_bytes_exact')
need(len(grid['rows'])==6 and len({(x['request'],x['variant']) for x in grid['rows']})==6,'two_requests_three_variants_no_duplicate_rows')
for name in ['312','311']:
 p='reports/evidence_e01_offline_import_protocol_independent_v1_20261116/review_'+name+'.txt';b=read(p);text=b.decode();line=next(x for x in text.splitlines() if x.startswith('{"fixed_inputs":'));need(line.encode()==gridraw,'independent_grid_bytes_match:'+name)
 receipt=json.loads(text.splitlines()[-1]);need(receipt['exit_code']==0 and receipt['expected_checks']==28 and receipt['sys_meta_path_unchanged'] and not receipt['socket_imported'],'independent_suite_closed_pass:'+name)
pin(meta['source_hashlock'])
results=[];zipbytes=entries=uncompressed=native=metadata_bytes=0
for w in meta['wheels']:
 raw=pin(w['archive_ref']);zipbytes+=len(raw)
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  infos=archive.infolist();need(len(infos)<=4096 and len(infos)==w['entries'],'bounded_directory_count:'+w['name'])
  names=[x.filename for x in infos];file_names={x.filename for x in infos if not x.is_dir()};need(len(names)==len(set(names)),'no_duplicate_archive_names:'+w['name'])
  need(sum(x.file_size for x in infos)==w['uncompressed_bytes'],'declared_inflation_metadata:'+w['name'])
  need(sum(x.is_dir() for x in infos)==w['archive_directory_entries'],'directory_entries:'+w['name'])
  need(sum(any(p.endswith('.data') for p in name.split('/')) for name in names)==w['data_paths']==0,'no_data_paths:'+w['name'])
  need(sum(name.lower().endswith('.pth') for name in names)==w['pth_paths']==0,'no_pth_paths:'+w['name'])
  n=sum(name.lower().endswith(('.so','.dylib','.dll')) for name in names);need(n==w['native_members'],'native_filenames_only:'+w['name'])
  bodies={}
  for name,d in w['metadata_refs'].items():
   info=archive.getinfo(name);need(not info.is_dir() and info.file_size==d['bytes']<=1048576,'metadata_file_bound:'+name)
   READS+=info.file_size+1;need(READS<=67108864,'combined_zip_metadata_cap')
   with archive.open(info,'r') as stream:b=stream.read(info.file_size+1)
   need(len(b)==d['bytes'] and hashlib.sha256(b).hexdigest()==d['sha256'],'metadata_bytes_hash:'+name);bodies[name]=b;metadata_bytes+=len(b)
  record_name=next(name for name in bodies if name.endswith('/RECORD'));rows=list(csv.reader(io.StringIO(bodies[record_name].decode())))
  need(len(rows)==w['record_rows'] and all(len(x)==3 for x in rows),'record_format_only:'+w['name'])
  record_names={x[0] for x in rows};need(len(record_names)==len(rows),'record_unique_names:'+w['name'])
  need((record_names==set(names))==w['record_names_match_archive'] and record_names==file_names and w['record_names_match_archive_files'] is True,'record_file_coverage_not_hash_verification:'+w['name'])
  need(len(record_names-file_names)==w['RECORD_names_without_archive_file']==0 and len(file_names-record_names)==w['file_names_missing_from_RECORD']==0,'record_bidirectional_name_coverage:'+w['name'])
  need(sorted({x[1].split('=',1)[0] for x in rows if x[1]})==w['record_hash_algorithms'],'record_declared_algorithms_only:'+w['name'])
  wheel_name=next(name for name in bodies if name.endswith('/WHEEL'));pure=[line.split(':',1)[1].strip() for line in bodies[wheel_name].decode().splitlines() if line.startswith('Root-Is-Purelib:')];need(pure==w['root_is_purelib'],'wheel_purelib_metadata:'+w['name'])
  groups={};entrycount=0
  for name in w['entry_points_files']:
   parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str;parser.read_string(bodies[name].decode());groups[name]={section:sorted(parser[section].keys()) for section in parser.sections()};entrycount+=sum(len(parser[s]) for s in parser.sections() if s in {'console_scripts','gui_scripts'})
  need(groups==w['entry_point_group_keys'] and entrycount==w['console_or_gui_entrypoint_count'],'entrypoint_metadata_only:'+w['name'])
  results.append({'name':w['name'],'archive_bytes':len(raw),'directory_entries':w['archive_directory_entries'],'entries':len(infos),'native_filename_count':n,'root_is_purelib':pure,'console_gui_count':entrycount,'metadata_sha_refs_verified':len(bodies),'record_payload_hashes_verified':False,'extracted_or_executed':False})
  entries+=len(infos);uncompressed+=sum(x.file_size for x in infos);native+=n
need(zipbytes==9430688 and entries==373 and uncompressed==25657393 and native==28,'five_wheel_totals')
need(len(results)==5 and sum(x['console_gui_count'] for x in results)==1,'five_wheels_one_console_script')
pipwheel=source['.venv/lib/python3.12/site-packages/pip/_internal/operations/install/wheel.py'];need('make_multiple' in pipwheel and 'RECORD' in pipwheel,'pinned_pip_installer_has_script_generation_and_RECORD_logic')
adapter=source['scripts/e01_offline_ipv6_adapter_v1_1_20261116.py'];six=source['.venv/lib/python3.12/site-packages/pip/_vendor/urllib3/packages/six.py'];need('self.previous_finders = tuple(sys.meta_path)' in adapter and 'for finder in self.previous_finders:' in adapter and 'sys.meta_path.append(_importer)' in six and 'class _SixMetaPathImporter' in six,'static_finder_append_snapshot_fact_not_cause')
result={'status':'PASS_MATCHED_FABRICATED_METHODS_AND_STATIC_WHEEL_METADATA_ONLY','count':len(checks),'checks':checks,'evidence_refs':refs,'wheel_results':results,'archive_bytes':zipbytes,'archive_entries':entries,'declared_uncompressed_bytes':uncompressed,'native_filename_count':native,'metadata_uncompressed_bytes_read':metadata_bytes,'application_source_zip_metadata_read_bytes_charged':READS,'elapsed_seconds':time.monotonic()-START,'payload_RECORD_hash_verification':False,'extraction_package_native_loading':False,'actual_cause':'UNKNOWN','security_or_installation_route_qualification':False,'cost_USD':0}
(OUT/'metadata_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':len(checks),'read_bytes':READS,'archive_bytes':zipbytes,'metadata_bytes':metadata_bytes}))
