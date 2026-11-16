from pathlib import Path
from datetime import datetime
import hashlib,json,time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent;READS=0;checks=[];refs={}
def need(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
def read(s):
 global READS
 p=ROOT/s;size=p.stat().st_size;READS+=size+1;need(READS<=67108864,'local_technical_read_cap:'+s);b=p.read_bytes();need(len(b)==size,'read_size:'+s);refs[s]={'path':s,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def pin(x):b=read(x['path']);need(refs[x['path']]==x,'pin:'+x['path']);return b
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
rp='reports/E01_OFFLINE_INSTALLER_ROUTE_FEASIBILITY_20261116.json';r=json.loads(pin({'path':rp,'bytes':20844,'sha256':'4ca7a46e5d17cf96e95b38b152f5fbefbbabc36a96e82776410af5167f0166b1'}))
for section in ['OUTPUT_ARTIFACTS','INPUT_ARTIFACTS']:
 for name,d in r[section].items():pin({'path':name,**d})
obs=json.loads(read('reports/evidence_e01_offline_installer_route_feasibility_20261116/official_documentation_observations.json'));availability=json.loads(read('reports/evidence_e01_offline_installer_route_feasibility_20261116/local_availability.json'))
need(len(obs['documents'])==6 and obs['budget']['charged_requests']==6 and obs['budget']['usable_documents']==5 and obs['budget']['inaccessible_attempts']==1,'six_reported_author_logical_attempts_including_failure')
for a,b in zip(obs['documents'],r['SOURCE_DATA_AND_LICENSE_NOTES']['primary_sources']):
 need(a['id']==b['id'] and a['url']==b['url'] and a['retrieval']==b['retrieval'] and hashlib.sha256(canon(a)).hexdigest()==b['retained_observation_sha256'],'canonical_semantic_observation_hash:'+a['id'])
window=r['TESTS_RUN_AND_RESULTS']['research_window'];elapsed=(datetime.fromisoformat(window['assessment_verified_by_UTC'].replace('Z','+00:00'))-datetime.fromisoformat(window['start_UTC'].replace('Z','+00:00'))).total_seconds();need(elapsed==288<600,'reported_author_window_288s_under10min')
current=[]
for row in availability['checked_sites']:
 p=Path(row['directory']);exists=p.exists();entries=sorted(q.name for q in p.iterdir() if q.name.lower() in {'installer','installer.py'} or q.name.lower().startswith('installer-')) if exists else []
 vendored=(p/'pip/_vendor/installer').exists();need(exists==row['exists'] and entries==row['installer_package_module_or_distribution_entries'] and vendored==row['pip_vendored_installer_directory_exists'],'selected_current_site_metadata:'+str(p))
 current.append({'directory':str(p),'exists':exists,'installer_entries':entries,'pip_vendored_installer_exists':vendored})
for name,exists in availability['repository_package_candidates'].items():need(Path(name).exists()==exists,'selected_repo_candidate_metadata:'+name)
pyproject=pin(availability['pyproject_ref']).decode();need([line for line in pyproject.splitlines() if 'installer' in line.lower()]==availability['pyproject_installer_mentions']==[],'pyproject_no_installer_mention')
need(r['actual_authority']['new_actual_allowance']==0 and r['actual_authority']['archive_or_package_downloads']==0 and r['actual_authority']['package_imports']==0,'no_package_or_actual_authority_from_assessment')
result={'status':'PASS_RETAINED_ASSESSMENT_HASH_SCOPE_AND_SELECTED_LOCAL_METADATA','count':len(checks),'checks':checks,'evidence_refs':refs,'current_selected_sites':current,'local_technical_bytes_charged':READS,'no_import_resolution_attempted':True,'no_package_archive_download_import_or_tests':True,'semantic_hashes_not_origin_hashes':True,'author_actualretrieval_history':'Retainedreportconsistent, notindependentlyreplayed transporthistory','cost_USD':0}
(OUT/'local_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':len(checks),'local_read_bytes':READS}))
