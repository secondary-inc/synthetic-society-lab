"""Offline closed-stop integrity review. Never prints private URL/query/body data."""
import sys
def early(event,args):
    if event.startswith(('socket.','ctypes.')) or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn'}:
        raise AssertionError('NO_NETWORK_PROCESS_NATIVE')
sys.addaudithook(early)
from pathlib import Path
from datetime import datetime
from urllib.parse import urlsplit,urljoin,parse_qsl,quote
from xml.etree import ElementTree
import hashlib,json,re,resource,signal,time

ROOT=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
OUT=ROOT/'reports/evidence_e02_human_anchor_datainfo_stops_independent_20261116'
A=ROOT/'reports/evidence_e02_human_anchor_datainfo_v1_20261116'
B=ROOT/'reports/evidence_e02_human_anchor_datainfo_continuation_v1_20261116'
P=ROOT/'data/processed/e02_human_anchor_datainfo_v1_20261116'
Q=ROOT/'data/processed/e02_human_anchor_datainfo_continuation_v1_20261116'
start=time.monotonic();cpu=time.process_time();checks=[];cache={};refs={};read_bytes=1048576
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def deadline(*_):raise AssertionError('OWN_WALL_CAP')
signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,120)
def check(name,value):
    checks.append({'name':name,'pass':bool(value)})
    if not value:raise AssertionError(name)
def read(path):
    global read_bytes
    p=Path(path);p=p if p.is_absolute() else ROOT/p
    if p not in cache:
        size=p.stat().st_size
        check('bounded technical read: '+p.name,read_bytes+size<=8388608)
        z=p.read_bytes();read_bytes+=len(z);cache[p]=z
        refs[str(p.relative_to(ROOT))]={'path':str(p.relative_to(ROOT)),'bytes':len(z),'sha256':hashlib.sha256(z).hexdigest()}
    return cache[p]
def doc(path):return json.loads(read(path))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(row):
    z=read(row['path']);check('exact pin: '+Path(row['path']).name,len(z)==row['bytes'] and sha(z)==row['sha256']);return z
firstpath='reports/E02_HUMAN_ANCHOR_DATAINFO_V1_20261116.json'
nextpath='reports/E02_HUMAN_ANCHOR_DATAINFO_CONTINUATION_V1_20261116.json'
pin({'path':firstpath,'bytes':13528,'sha256':'dface3f5084dce220aeeaa30b38a044687f67ae511e699f94b1625932c0da420'})
pin({'path':nextpath,'bytes':13676,'sha256':'4db4fb82a697bf458de6520ae061c8514f345a140e0407f5c9f2a4d09ba94082'})
first=doc(firstpath);second=doc(nextpath)
for row in first['OUTPUT_ARTIFACTS']+second['OUTPUT_ARTIFACTS']+first['retention']['private_ignored_cache_refs']+second['privacy_and_retention']['private_cache_refs']+first['budget_accounting']['old_scopes_unchanged']+second['authority_and_ancestry']['prior_reports_unchanged']:pin(row)
old8=doc(first['budget_accounting']['old_scopes_unchanged'][0]['path']);old2=doc(first['budget_accounting']['old_scopes_unchanged'][1]['path'])
ledger=old8['request_accounting'];metadata=old2['request_accounting']
check('old eight request receipt sum',ledger['actual_requests']==len(ledger['request_ledger'])==8 and sum(v['bytes'] for v in ledger['request_ledger'])==ledger['actual_response_bytes']==4561042)
check('metadata two request receipt sum',metadata['new_scope_actual_requests']==len(metadata['requests'])==2 and sum(v['response_bytes'] for v in metadata['requests'])==metadata['new_scope_actual_response_bytes']==8906)
check('ancestral ten and body bytes',8+2==metadata['combined_actual_requests']==10 and 4561042+8906==metadata['combined_actual_response_bytes']==4569948)
c1=doc(A/'CLOSED_DOCUMENT_READ.json');c2=doc(B/'CLOSED_CONTINUATION.json')
check('two initial reservation and observation files',len(list(A.glob('*-RESERVED.json')))==len(list(A.glob('*-OBSERVATION.json')))==2)
check('one continuation reservation and observation',len(list(B.glob('*-RESERVED.json')))==len(list(B.glob('*-OBSERVATION.json')))==1)
observations=[]
for i in (1,2):
    reserved=doc(A/f'{i:02d}-RESERVED.json');observed=doc(A/f'{i:02d}-OBSERVATION.json');observations.append(observed)
    check('initial reservation retained '+str(i),all(observed.get(k)==v for k,v in reserved.items()))
    check('initial closed observation equality '+str(i),observed==c1['observations'][i-1])
    check('initial status ordinal body '+str(i),observed['method']=='GET' and observed['http_status']==302 and observed['scope_ordinal']==i and observed['combined_ordinal']==10+i and observed['body_status']=='COMPLETE' and observed['body_bytes']==0)
    check('initial empty body hash '+str(i),pin(observed['private_body_ref'])==b'' and observed['body_sha256']==sha(b''))
    check('initial no automatic redirect/credentials '+str(i),observed['automatic_redirects'] is False and observed['credentials'] is False and observed['public_body_saved'] is False)
    check('initial timestamp ordering '+str(i),datetime.fromisoformat(observed['retrieval_end_utc'])>=datetime.fromisoformat(observed['retrieval_start_utc']) and observed['elapsed_seconds']>=0)
red1=doc(P/'01-REDIRECT.json');red2=doc(P/'02-REDIRECT.json')
check('first location equals permitted followed URL',urljoin(observations[0]['url'],red1['location'])==red1['resolved_destination']==observations[0]['permitted_observed_location']==observations[1]['url'])
check('initial location hashes match',sha(red1['location'].encode())==observations[0]['redirect_header_sha256'] and sha(red2['location'].encode())==observations[1]['redirect_header_sha256'])
check('initial stopped second redirect',c1['status']=='STOPPED_REDIRECT_DESTINATION_OR_BUDGET' and c1['accounting']=={'interpretation_allowed':False,'redirects_followed':1,'requests':2,'response_bytes':0} and not first['request_and_redirect_result']['second_redirect_followed'])
check('initial twelve requests consumed',c1['combined_actual']=={'requests':12,'response_bytes':4569948} and first['budget_accounting']['combined_remaining_requests']==0)
check('first has no access denial',first['request_and_redirect_result']['HTTP_access_denial_observed'] is False)
record=doc(B/'01-OBSERVATION.json');reserved=doc(B/'01-RESERVED.json')
check('continuation reservation retained',all(record.get(k)==v for k,v in reserved.items()))
check('continuation closed observation equality',record==c2['observation'])
exact=doc(Q/'EXACT_DESTINATION.json');url=exact['url'];parts=urlsplit(url);query=parse_qsl(parts.query,keep_blank_values=True);values=dict(query)
check('saved second location exact verbatim',exact['source_path']==str((P/'02-REDIRECT.json').relative_to(ROOT)) and exact['source_sha256']==sha(read(P/'02-REDIRECT.json')) and url==red2['resolved_destination']==red2['location'])
check('continuation URL and header hash bind ancestor',sha(url.encode())==exact['location_header_sha256']==record['destination_url_sha256']==record['source_location_header_sha256']==observations[1]['redirect_header_sha256']==second['exact_destination_binding']['requested_url_sha256'])
check('saved path hash and public object transport',sha(parts.path.encode())==record['destination_path_sha256']==second['exact_destination_binding']['requested_path_sha256'] and parts.scheme=='https' and parts.port in (None,443) and parts.username is None and parts.password is None and not parts.fragment)
check('finite presigned query names only',len(query)==len(values)==7 and set(values)=={'X-Amz-Algorithm','X-Amz-Credential','X-Amz-Date','X-Amz-Expires','X-Amz-Signature','X-Amz-SignedHeaders','response-content-disposition'})
check('service scheme and intended file',values['X-Amz-Algorithm']=='AWS4-HMAC-SHA256' and values['X-Amz-SignedHeaders']=='host' and 'jitp_datainfo.md' in values['response-content-disposition'])
check('continuation one GET403',record['http_status']==403 and record['method']=='GET' and record['scope_ordinal']==1 and record['combined_ordinal']==13 and record['body_status']=='COMPLETE')
check('no follow retry credentials',record['redirect_following'] is False and record['retry_count']==0 and record['owner_or_account_credentials_supplied'] is False and record['signed_query_values_public'] is False)
check('no redirected or refreshed request receipt',not (Q/'UNFOLLOWED_LOCATION.json').exists() and second['retrieval_result']['redirects_followed']==second['retrieval_result']['refresh_requests']==second['retrieval_result']['retries']==second['retrieval_result']['alternate_urls']==0)
body=pin(record['private_response_ref'])
check('217 byte error integrity',len(body)==record['body_bytes']==c2['response_body_bytes']==217 and sha(body)==record['body_sha256']==second['retrieval_result']['response_body_sha256'])
tree=ElementTree.fromstring(body);code=tree.findtext('Code');message=tree.findtext('Message','')
check('safe error classification only',code=='AccessDenied' and 'expir' in message.lower())
classification=doc(B/'access-error-classification.json')
check('classification matches retained XML',classification['storage_error_code']==code and classification['error_message_contains_expiration_word'] is True and classification['source_bytes']==217 and classification['raw_message_or_query_values_public'] is False)
check('continuation time observation within20seconds',0<=record['elapsed_seconds']<record['timeout_seconds']==20 and datetime.fromisoformat(record['retrieval_end_utc'])>=datetime.fromisoformat(record['retrieval_start_utc']))
check('combined thirteen body accounting',c2['combined_actual_requests']==second['accounting']['combined_actual_requests']==13 and c2['combined_actual_response_body_bytes']==4569948+217==second['accounting']['combined_actual_response_body_bytes']==4570165)
check('caps and no reset',c2['combined_max_requests']==13 and c2['combined_max_response_body_bytes']==20971520+16384==20987904 and second['accounting']['combined_remaining_requests']==0 and second['accounting']['old_scopes_reset'] is False and c2['no_retry_or_refresh'])
expected='05fb2df6d9a028537068ad0659ad15b8405a604807745272f9e3a8c29213f354'
check('822 byte target hash unchanged',first['authorized_document']['expected_bytes']==second['document_verification']['expected_bytes']==c1['expected_document']['bytes']==c2['expected_document_bytes']==822 and first['authorized_document']['expected_sha256']==second['document_verification']['expected_sha256']==c1['expected_document']['sha256']==c2['expected_document_sha256']==expected)
check('no target obtained or interpreted',not c1['accounting']['interpretation_allowed'] and not c2['interpretation_allowed'] and not first['verification_and_interpretation']['documentation_text_read'] and not first['verification_and_interpretation']['document_acquired'] and not second['document_verification']['document_content_acquired'] and not second['document_verification']['interpretation_allowed'])
check('target hash verification correctly NOT_RUN',first['verification_and_interpretation']['final_document_hash_check']=='NOT_RUN_NO_FINAL_DOCUMENT' and second['document_verification']['hash_check']=='NOT_RUN_NO200DOCUMENT' and second['document_verification']['rights_or_package_paraphrase'] is None)
check('no other linked file receipt',c1['file_links_or_other_contents_followed']==c2['linked_file_downloads']==0)
check('private cache inventory exact',{p.name for p in P.iterdir()}=={'01-REDIRECT.json','02-REDIRECT.json','01-RESPONSE.bin','02-RESPONSE.bin'} and {p.name for p in Q.iterdir()}=={'01-RESPONSE.bin','EXACT_DESTINATION.json'})
check('processed cache ignore rule retained','data/processed/' in read('.gitignore').decode().splitlines())
public_files=[ROOT/firstpath,ROOT/nextpath,*[p for folder in (A,B) for p in folder.iterdir() if p.is_file()]]
for path in public_files:
    raw=read(path);text=raw.decode()
    check('no full private URL in public '+path.name,url not in text and red2['location'] not in text)
    check('no signed query values in public '+path.name,re.search(r'X-Amz-(?:Signature|Credential)=[A-Za-z0-9%/]',text) is None)
    for key in ('X-Amz-Signature','X-Amz-Credential'):
        value=values[key]
        check('no exact private capability value in public '+path.name,all(v not in text for v in {value,quote(value,safe='')}))
    check('no model/owner API key pattern '+path.name,re.search(r'sk-or-v\d-[a-fA-F0-9]{32,}|EAA[A-Za-z0-9]{50,}',text) is None)
failure=doc(B/'local-validation-attempt1-failure.json');old_validator=read(B/'validator-attempt1.py').decode();new_validator=read(B/'validate_continuation_stop.py').decode()
check('original local validator failure retained',failure['attempt1_exitcode']==1 and failure['status']=='FAILED_FALSE_POSITIVE_PATTERN_LITERAL_SELF_MATCH' and read(B/'local-validation-attempt1.stdout')==b'')
check('literal scanner matched its own source',"'X-Amz-Signature='" in old_validator and "'X-Amz-Credential='" in old_validator)
normalized=old_validator.replace('import json\n','import json\nimport re\n').replace("assert 'X-Amz-Signature=' not in raw and 'X-Amz-Credential=' not in raw,'SIGNED_QUERY_PUBLICLY_SAVED'", "assert re.search(r'X-Amz-(?:Signature|Credential)=[A-Za-z0-9%/]',raw) is None,'SIGNED_QUERY_VALUES_PUBLICLY_SAVED'")
check('only local scanner normalization changed',normalized==new_validator)
local=doc(B/'local-stop-validation.json');check('retained validator successor scoped pass',local['requests']==1 and local['http_status']==403 and local['combined_requests']==13 and local['document_hash_verification']=='NOT_RUN_NO200DOCUMENT' and not local['interpretation'])
source1=read(A/'read_datainfo_once.py').decode();source2=read(B/'continue_exact_once.py').decode()
for label,source in [('initial',source1),('continuation',source2)]:
    check(label+' source exclusive reservations and new-scope stop',"'xb'" in source and 'RESERVED.json' in source and ('SCOPE_ALREADY_USED' in source or 'NEW_SCOPE_ONLY_NO_RETRY' in source))
    check(label+' source TLS/no auto redirect API', 'ssl.create_default_context()' in source and 'http.client.HTTPSConnection' in source and 'connection.request(\'GET\'' in source)
    check(label+' exact hash gate before interpretation',expected in source and ('EXACT_DOCUMENT_VERIFIED_PRIVATE_ONLY' in source or 'EXACT822BYTE_DOCUMENT_VERIFIED_PRIVATE_ONLY' in source))
check('no document rights or scientific promotion',second['rights_and_research_implications']['documentation_terms']=='UNKNOWN_NOT_READ' and 'does not establish' in second['rights_and_research_implications']['prohibition_not_inferred'] and 'No replication' in second['rights_and_research_implications']['protocol_results'])
check('zero model or financial activity in reports',first['paid_or_model_calls']==second['model_calls']==first['COST_USD_ACTUAL_OR_ZERO']==second['COST_USD_ACTUAL_OR_ZERO']==0)
check('own process limits',time.monotonic()-start<120 and time.process_time()-cpu<120)
receipt={'decision':'PASS_CLOSED_STOP_INTEGRITY_ONLY_DOCUMENT_RIGHTS_RESEARCH_NOT_RUN','checks_passed':len(checks),'checks':checks,'input_refs':list(refs.values()),'safe_summary':{'initial_GETs':2,'initial_statuses':[302,302],'initial_body_bytes':0,'initial_redirects_followed':1,'continuation_GETs':1,'continuation_status':403,'continuation_body_bytes':217,'continuation_redirects_retries_refreshes':0,'combined_requests':13,'combined_response_body_bytes':4570165,'target_expected_bytes':822,'target_hash_check':'NOT_RUN_NO200DOCUMENT','interpretation':False,'safe_error_classifier':{'Code':'AccessDenied','message_mentions_expiration':True,'broader_403_cause':'UNKNOWN'},'signed_query_values_emitted':False,'new_network_or_model_requests':0,'cost_USD':0},'accounting':{'technical_read_bytes_with_1MiB_initial_reserve':read_bytes,'CPU_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-start,'network_browser_model_research_reexecution':0},'limitations':['Retained request/source/body evidence only, not independent server attestation or wire-byte metering.','Old8+2 request totals verified from unchanged public reports; their original PDF/web/metadata bodies were not read or independently reattested.','The217byte XML is an access error, not the822byte documentation; expiration wording is a narrow classifier, not a definitive general403cause, rights restriction or availability finding.','Local validator first failure has preserved source/emptystdout/producer description; contemporaneous stderr was not saved. No independent claim to reconstruct its historical execution.','Ignore rule statically present; no Git command or current tracked-file inventory performed.','No signed URL/location/query values or raw XML message copied into public artifacts. No source content, license permission, human replication, model results or scientific milestone accepted.']}
raw=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode();check('owned write cap',len(raw)<4194304)
with (OUT/'checks.json').open('xb') as f:f.write(raw)
signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps({'decision':receipt['decision'],'checks':receipt['checks_passed'],'technical_read_bytes':read_bytes,'receipt_bytes':len(raw),'CPU_seconds':receipt['accounting']['CPU_seconds'],'wall_seconds':receipt['accounting']['wall_seconds'],'signed_values_printed':False}))
