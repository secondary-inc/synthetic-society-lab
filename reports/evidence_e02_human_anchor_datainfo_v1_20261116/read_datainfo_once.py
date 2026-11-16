"""One exact documentation object, <=2GET/16KiB, no retries/linked downloads.

No document interpretation before the final exact size/hash check. Publicly
observed HTTPS redirect may be followed once only if destination stays the exact
known OSF object route, with no login/credential/signed-token path or query.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import http.client
import json
import ssl
import time
from urllib.parse import urlsplit,urljoin,parse_qsl

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
CACHE=ROOT/'data/processed/e02_human_anchor_datainfo_v1_20261116'
START='https://osf.io/download/c59u8/'
EXPECTED_SIZE=822
EXPECTED_SHA='05fb2df6d9a028537068ad0659ad15b8405a604807745272f9e3a8c29213f354'
MAX_REQUESTS=2;MAX_BYTES=16384
state={'requests':0,'response_bytes':0,'redirects_followed':0,'interpretation_allowed':False}
context=ssl.create_default_context()


def save_new(path,value):
    raw=value if isinstance(value,bytes) else (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    with open(path,'xb') as stream:stream.write(raw)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def allowed_destination(url):
    parts=urlsplit(url)
    if parts.scheme!='https' or parts.username is not None or parts.password is not None:return False
    if parts.port not in (None,443):return False
    # Public route identity is bounded to the cataloged object, not a wildcard
    # cloud bucket, arbitrary OSF file, account/login or archive.
    paths={
      'osf.io':{'/download/c59u8/','/download/c59u8'},
      'files.osf.io':{'/v1/resources/xe28y/providers/osfstorage/62cf3d2e1bb7a51aaa1f3720','/v1/resources/xe28y/providers/osfstorage/62cf3d2e1bb7a51aaa1f3720/'},
      'api.osf.io':{'/v2/files/62cf3d2e1bb7a51aaa1f3720/download/','/v2/files/62cf3d2e1bb7a51aaa1f3720/download'}}
    if parts.hostname not in paths or parts.path not in paths[parts.hostname]:return False
    return all(k in {'action','direct','version','mode'} and v in {'','download','1'} for k,v in parse_qsl(parts.query,keep_blank_values=True))


def fetch(url):
    assert state['requests']<MAX_REQUESTS and allowed_destination(url)
    assert state['response_bytes']<MAX_BYTES
    state['requests']+=1;n=state['requests'];started=time.monotonic()
    record={'scope_ordinal':n,'combined_ordinal':10+n,'url':url,'method':'GET','retrieval_start_utc':datetime.now(timezone.utc).isoformat(),'response_allowance_remaining_before_request':MAX_BYTES-state['response_bytes'],'credentials':False,'automatic_redirects':False,'purpose':'Exact822-byte jitp_datainfo.md documentation only, not mixed replication archive or linked files.'}
    save_new(E/f'{n:02d}-RESERVED.json',record)
    body=b'';connection=None
    try:
        parts=urlsplit(url);connection=http.client.HTTPSConnection(parts.hostname,timeout=20,context=context)
        connection.request('GET',parts.path+('?' +parts.query if parts.query else ''),headers={'User-Agent':'SyntheticSocietyLab-PublicDocumentationCheck/1.0','Accept':'text/plain, text/markdown;q=0.9','Accept-Encoding':'identity'})
        response=connection.getresponse();record['http_status']=response.status
        # Location is public only after destination passes strict validation;
        # otherwise preserve the raw header privately and expose hash/reason.
        headers=dict((k.lower(),v) for k,v in response.getheaders())
        record['headers']={k:v for k,v in headers.items() if k in {'content-type','content-length','content-disposition','date','etag','last-modified'}}
        location=headers.get('location')
        if location is not None:
            destination=urljoin(url,location)
            save_new(CACHE/f'{n:02d}-REDIRECT.json',{'location':location,'resolved_destination':destination})
            record['redirect_header_sha256']=sha(location.encode())
            if allowed_destination(destination):record['permitted_observed_location']=destination
            else:record['redirect_disposition']='UNEXPECTED_OR_CREDENTIAL_DESTINATION_STOP'
        while True:
            remaining=MAX_BYTES-state['response_bytes']
            if remaining<=0:record['body_status']='BOUND_REACHED_NOT_COMPLETE';break
            chunk=response.read(min(4096,remaining))
            if not chunk:record['body_status']='COMPLETE';break
            body+=chunk;state['response_bytes']+=len(chunk)
        record['body_bytes']=len(body);record['body_sha256']=sha(body)
        save_new(CACHE/f'{n:02d}-RESPONSE.bin',body)
        record['private_body_ref']={'path':str((CACHE/f'{n:02d}-RESPONSE.bin').relative_to(ROOT)),'bytes':len(body),'sha256':sha(body)}
        if response.status in {401,403,429}:record['route_disposition']='ACCESS_DENIAL_STOP_NO_RETRY'
    except BaseException as error:
        record['error_type']=type(error).__name__
        record['route_disposition']='TRANSPORT_OR_BOUND_STOP_NO_RETRY'
    finally:
        if connection is not None:connection.close()
        record['retrieval_end_utc']=datetime.now(timezone.utc).isoformat();record['elapsed_seconds']=time.monotonic()-started
        record['public_body_saved']=False
        save_new(E/f'{n:02d}-OBSERVATION.json',record)
    return record,body


def main():
    assert not list(E.glob('*-RESERVED.json')) and not list(CACHE.iterdir()),'SCOPE_ALREADY_USED'
    old_reports={'reports/E02_HUMAN_ANCHOR_REPLICATION_AVAILABILITY_20261116.json':'2c744473a592db12ece850305e453860510493ef23296b819476c0ae934448ee','reports/E02_HUMAN_ANCHOR_RIGHTS_METADATA_V1_20261116.json':'873ec538a935039791762630b954358331418b34c232eabb37559eb6f25575bf'}
    for path,digest in old_reports.items():assert sha((ROOT/path).read_bytes())==digest,'PREDECESSOR_CHANGED'
    records=[];record,body=fetch(START);records.append(record)
    status='STOPPED_NO_VERIFIED_DOCUMENT'
    if record.get('http_status') in {301,302,303,307,308} and record.get('body_status')=='COMPLETE':
        destination=record.get('permitted_observed_location')
        if destination and state['requests']<MAX_REQUESTS and state['response_bytes']<MAX_BYTES:
            state['redirects_followed']+=1;record,body=fetch(destination);records.append(record)
    if record.get('http_status')==200 and record.get('body_status')=='COMPLETE':
        if len(body)==EXPECTED_SIZE and sha(body)==EXPECTED_SHA:
            state['interpretation_allowed']=True;status='EXACT_DOCUMENT_VERIFIED_PRIVATE_ONLY'
        else:status='STOPPED_DOCUMENT_SIZE_OR_HASH_MISMATCH'
    elif record.get('http_status') in {301,302,303,307,308}:
        status='STOPPED_REDIRECT_DESTINATION_OR_BUDGET'
    elif record.get('http_status') in {401,403,429}:
        status='STOPPED_ACCESS_DENIAL'
    summary={'kind':'E02_HUMAN_ANCHOR_DATAINFO_DOCUMENT_READ_V1','status':status,'accounting':state,'limits':{'requests':MAX_REQUESTS,'response_bytes':MAX_BYTES},'expected_document':{'url':START,'name':'jitp_datainfo.md','bytes':EXPECTED_SIZE,'sha256':EXPECTED_SHA},'observations':records,'prior_scopes':{'requests':10,'response_bytes':4569948},'combined_actual':{'requests':10+state['requests'],'response_bytes':4569948+state['response_bytes']},'file_links_or_other_contents_followed':0,'no_retry':True,'cost_usd':0}
    save_new(E/'CLOSED_DOCUMENT_READ.json',summary)
    print(json.dumps(summary,sort_keys=True))
    # Never emit the document text. A later local read may interpret only after
    # this exact verification flag/status and hash have been checked again.


if __name__=='__main__':main()
