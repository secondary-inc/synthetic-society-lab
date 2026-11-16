"""Offline verification of the stopped documentation scope; no network."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
s=json.loads((E/'CLOSED_DOCUMENT_READ.json').read_text())
assert s['status']=='STOPPED_REDIRECT_DESTINATION_OR_BUDGET'
assert s['accounting']=={'requests':2,'response_bytes':0,'redirects_followed':1,'interpretation_allowed':False}
rows=[]
for n in (1,2):
    r=json.loads((E/f'{n:02d}-RESERVED.json').read_text())
    o=json.loads((E/f'{n:02d}-OBSERVATION.json').read_text())
    b=(ROOT/o['private_body_ref']['path']).read_bytes()
    assert r['scope_ordinal']==o['scope_ordinal']==n and o['combined_ordinal']==10+n
    assert r['url']==o['url'] and o['http_status']==302 and o['body_bytes']==len(b)==0
    assert hashlib.sha256(b).hexdigest()==o['body_sha256']
    assert o['credentials'] is False and o['automatic_redirects'] is False
    rows.append({'scope_ordinal':n,'combined_ordinal':10+n,'url':o['url'],'status':302,'body_bytes':0,'redirect_header_sha256':o['redirect_header_sha256'],'retrieval_start_utc':o['retrieval_start_utc'],'retrieval_end_utc':o['retrieval_end_utc']})
assert s['combined_actual']=={'requests':12,'response_bytes':4569948}
assert 'permitted_observed_location' in s['observations'][0]
assert s['observations'][1]['redirect_disposition']=='UNEXPECTED_OR_CREDENTIAL_DESTINATION_STOP'
assert 'permitted_observed_location' not in s['observations'][1]
for path,digest in {'reports/E02_HUMAN_ANCHOR_REPLICATION_AVAILABILITY_20261116.json':'2c744473a592db12ece850305e453860510493ef23296b819476c0ae934448ee','reports/E02_HUMAN_ANCHOR_RIGHTS_METADATA_V1_20261116.json':'873ec538a935039791762630b954358331418b34c232eabb37559eb6f25575bf'}.items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
print(json.dumps({'kind':'DATAINFO_STOP_LOCAL_ACCOUNTING_ONLY','decision':'PASS_STOP_AND_NO_INTERPRETATION_NOT_RIGHTS_ACCEPTANCE','scope_requests':2,'scope_response_body_bytes':0,'redirects_followed':1,'combined_requests':12,'combined_response_body_bytes':4569948,'document_verification':'NOT_RUN_NO_FINAL200DOCUMENT','interpretation':False,'old_scopes_unchanged':True,'ledger':rows},indent=2,sort_keys=True))
