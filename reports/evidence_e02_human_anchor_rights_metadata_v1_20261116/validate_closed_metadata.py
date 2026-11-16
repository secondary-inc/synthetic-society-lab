"""Local metadata/budget verification only; no network or package imports."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
CACHE=ROOT/'data/processed/e02_human_anchor_rights_metadata_v1_20261116'
closed=json.loads((E/'CLOSED_METADATA.json').read_text())
reservations=sorted(E.glob('*-RESERVED.json'));observations=sorted(E.glob('*-OBSERVATION.json'))
assert len(reservations)==len(observations)==closed['accounting']['requests']==2
rows=[]
for n,(rp,op) in enumerate(zip(reservations,observations),1):
    r=json.loads(rp.read_text());o=json.loads(op.read_text());body=(ROOT/o['private_body_cache']['path']).read_bytes()
    assert r['scope_ordinal']==o['scope_ordinal']==n and r['combined_ordinal']==8+n
    assert r['url']==o['url'] and r['method']=='GET' and o['http_status']==200
    assert len(body)==o['body_bytes'] and hashlib.sha256(body).hexdigest()==o['body_sha256']
    assert o['file_content_download'] is False and o['redirect_following'] is False and o['credentials'] is False
    rows.append({'scope_ordinal':n,'combined_ordinal':8+n,'url':o['url'],'status':o['http_status'],'response_bytes':o['body_bytes'],'body_sha256':o['body_sha256'],'retrieval_start_utc':o['retrieval_start_utc'],'retrieval_end_utc':o['retrieval_end_utc']})
assert sum(row['response_bytes'] for row in rows)==8906<4194304
assert closed['combined_actual']=={'requests':10,'response_bytes':4569948}
node=json.loads((CACHE/'01-RESPONSE.json').read_text())['data']
assert 'node_license' in node['attributes'] and node['attributes']['node_license'] is None
assert 'license' not in node.get('relationships',{})
assert closed['folder_pages'][0]['pagination']['next'] is None
assert {item['name'] for item in closed['file_inventory']}=={'jitp_datainfo.md','replication_jitp.zip'}
assert all(item['contents_acquired'] is False for item in closed['file_inventory'])
assert hashlib.sha256((ROOT/'reports/E02_HUMAN_ANCHOR_REPLICATION_AVAILABILITY_20261116.json').read_bytes()).hexdigest()=='2c744473a592db12ece850305e453860510493ef23296b819476c0ae934448ee'
print(json.dumps({'kind':'E02_RIGHTS_METADATA_LOCAL_ACCOUNTING','decision':'PASS_LOCAL_ACCOUNTING_ONLY_NOT_RIGHTS_OR_RESEARCH_ACCEPTANCE','requests_this_scope':2,'response_bytes_this_scope':8906,'requests_combined':10,'response_bytes_combined':4569948,'new_scope_remaining_requests':2,'node_license_explicitly_null':True,'linked_license_absent':True,'next_metadata_page':None,'file_downloads':0,'predecessor_report_unchanged':True,'requests':rows},indent=2,sort_keys=True))
