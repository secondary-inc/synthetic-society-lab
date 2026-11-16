"""Read-only local evidence accounting. No HTTP/import of project modules."""
from pathlib import Path
import hashlib
import json

E=Path(__file__).resolve().parent
reservations=sorted(E.glob('*-RESERVED.json'));observations=sorted(E.glob('*-OBSERVATION.json'))
assert len(reservations)==len(observations)==8
rows=[]
for index,(rp,op) in enumerate(zip(reservations,observations),1):
    r=json.loads(rp.read_text());o=json.loads(op.read_text())
    assert r['ordinal']==o['ordinal']==index and r['url']==o['url']
    assert r['method']=='GET' and r['credentials'] is False and r['respondent_or_stimulus_download'] is False
    assert o['body_saved'] is False and o['body_read_status']=='COMPLETE'
    rows.append({'ordinal':index,'url':o['url'],'status':o['http_status'],'bytes':o['body_bytes'],'response_sha256':o['body_sha256'],'retrieval_start_utc':o['retrieval_start_utc'],'retrieval_end_utc':o['retrieval_end_utc']})
assert sum(r['bytes'] for r in rows)==4561042<16777216
final=json.loads((E/'CORRECT_REPLICATION_LISTING_METADATA.json').read_text())
assert final['cumulative_counts']=={'requests':8,'response_bytes':4561042}
assert final['public_metadata']['listing_total']==2 and final['public_metadata']['next_page'] is None
items=final['public_metadata']['items'];assert {r['name'] for r in items}=={'20180509AB_survey.pdf','Replication'}
assert all(row['content_acquired'] is False for row in items)
assert not any(p.suffix.lower() in {'.pdf','.zip','.dta','.csv','.tsv','.html'} for p in E.iterdir())
print(json.dumps({'kind':'LOCAL_PUBLIC_METADATA_EVIDENCE_ACCOUNTING','status':'PASS_ACCOUNTING_ONLY_NOT_RESEARCH_ACCEPTANCE','requests':len(rows),'response_bytes':sum(r['bytes'] for r in rows),'remaining_request_allowance':0,'respondent_stimulus_or_PDF_contents_acquired_as_files':0,'rows':rows},indent=2,sort_keys=True))
