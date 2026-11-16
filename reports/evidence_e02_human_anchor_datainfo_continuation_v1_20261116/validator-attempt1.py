"""Offline closed-scope/secret-redaction verification; no HTTP."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
CACHE=ROOT/'data/processed/e02_human_anchor_datainfo_continuation_v1_20261116'
s=json.loads((E/'CLOSED_CONTINUATION.json').read_text());o=s['observation']
assert s['status']=='STOPPED_ACCESS_DENIAL_NO_RETRY' and s['requests']==1 and s['interpretation_allowed'] is False
assert o['http_status']==403 and o['body_bytes']==217 and o['body_status']=='COMPLETE'
body=(CACHE/'01-RESPONSE.bin').read_bytes();assert len(body)==217 and hashlib.sha256(body).hexdigest()==o['body_sha256']
saved=json.loads((CACHE/'EXACT_DESTINATION.json').read_text());old=json.loads((ROOT/saved['source_path']).read_text())
assert saved['url']==old['resolved_destination']
assert hashlib.sha256(saved['url'].encode()).hexdigest()==o['destination_url_sha256']
assert o['redirect_following'] is False and o['retry_count']==0 and o['owner_or_account_credentials_supplied'] is False
assert o['elapsed_seconds']<20 and s['response_body_bytes']<16384
assert s['combined_actual_requests']==13 and s['combined_actual_response_body_bytes']==4570165
assert len(list(E.glob('*-RESERVED.json')))==len(list(E.glob('*-OBSERVATION.json')))==1
for p in E.iterdir():
    if p.is_file():
        raw=p.read_text()
        assert 'X-Amz-Signature=' not in raw and 'X-Amz-Credential=' not in raw,'SIGNED_QUERY_PUBLICLY_SAVED'
for name,digest in {'reports/E02_HUMAN_ANCHOR_REPLICATION_AVAILABILITY_20261116.json':'2c744473a592db12ece850305e453860510493ef23296b819476c0ae934448ee','reports/E02_HUMAN_ANCHOR_RIGHTS_METADATA_V1_20261116.json':'873ec538a935039791762630b954358331418b34c232eabb37559eb6f25575bf','reports/E02_HUMAN_ANCHOR_DATAINFO_V1_20261116.json':'dface3f5084dce220aeeaa30b38a044687f67ae511e699f94b1625932c0da420'}.items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
print(json.dumps({'kind':'DATAINFO_CONTINUATION_CLOSED_STOP_ACCOUNTING','decision':'PASS_STOP_ACCOUNTING_NOT_DOCUMENT_OR_RIGHTS_ACCEPTANCE','requests':1,'http_status':403,'response_body_bytes':217,'exact_saved_url_used':True,'no_signed_query_values_public':True,'no_redirect_or_retry':True,'prior_three_reports_unchanged':True,'combined_requests':13,'combined_response_body_bytes':4570165,'document_hash_verification':'NOT_RUN_NO200DOCUMENT','interpretation':False},indent=2,sort_keys=True))
