"""One explicit recovery GET to exact saved public OSF download capability.

Signed queries remain private. No refresh, alternate URL, further redirect,
retry or other file. Verify expected822bytes/hash before any interpretation.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import http.client
import json
import ssl
import time
from urllib.parse import urlsplit,parse_qsl

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
CACHE=ROOT/'data/processed/e02_human_anchor_datainfo_continuation_v1_20261116'
OLD=ROOT/'data/processed/e02_human_anchor_datainfo_v1_20261116/02-REDIRECT.json'
EXPECTED_HEADER_SHA='8714cb67570a290ba74f3f53731803fdf9ace33847c3a5f4e71ea13aef8d218b'
EXPECTED_PATH_SHA='e8a0c8bb5c3e48da6b64dfb71763ca6303c6b975e654ae4268579630814abdbf'
EXPECTED_HOST='idvyorynw6xy.compat.objectstorage.us-ashburn-1.oraclecloud.com'
EXPECTED_FILE_SHA='05fb2df6d9a028537068ad0659ad15b8405a604807745272f9e3a8c29213f354'
LIMIT=16384


def sha(raw):return hashlib.sha256(raw).hexdigest()


def save_new(path,value):
    raw=value if isinstance(value,bytes) else (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    with open(path,'xb') as stream:stream.write(raw)


def main():
    assert not list(E.glob('*-RESERVED.json')) and not list(CACHE.iterdir()),'NEW_SCOPE_ONLY_NO_RETRY'
    assert sha((ROOT/'reports/E02_HUMAN_ANCHOR_DATAINFO_V1_20261116.json').read_bytes())=='dface3f5084dce220aeeaa30b38a044687f67ae511e699f94b1625932c0da420','OLD_STOP_CHANGED'
    raw=OLD.read_bytes();saved=json.loads(raw)
    assert sha(saved['location'].encode())==EXPECTED_HEADER_SHA,'SAVED_LOCATION_CHANGED'
    url=saved['resolved_destination'];parts=urlsplit(url);query=parse_qsl(parts.query,keep_blank_values=True);values=dict(query)
    assert parts.scheme=='https' and parts.hostname==EXPECTED_HOST and parts.port in (None,443),'UNEXPECTED_STORAGE_DESTINATION'
    assert parts.username is None and parts.password is None and not parts.fragment,'EMBEDDED_ACCOUNT_OR_FRAGMENT'
    assert sha(parts.path.encode())==EXPECTED_PATH_SHA,'SAVED_OBJECT_PATH_CHANGED'
    assert set(values)=={'X-Amz-Algorithm','X-Amz-Credential','X-Amz-Date','X-Amz-Expires','X-Amz-Signature','X-Amz-SignedHeaders','response-content-disposition'},'UNEXPECTED_QUERY_FIELDS'
    assert len(query)==len(values),'DUPLICATE_QUERY_FIELDS'
    assert values['X-Amz-Algorithm']=='AWS4-HMAC-SHA256' and values['X-Amz-SignedHeaders']=='host','UNEXPECTED_PUBLIC_SIGNATURE_SCHEME'
    assert 'jitp_datainfo.md' in values['response-content-disposition'],'WRONG_FILE_DISPOSITION'
    # Exact URL came from the previously anonymous TLS-verified OSF object
    # response. Its service-generated read capability is reused only verbatim
    # at its intended storage host; no owner/account/API credentials are read.
    save_new(CACHE/'EXACT_DESTINATION.json',{'url':url,'source_path':str(OLD.relative_to(ROOT)),'source_sha256':sha(raw),'location_header_sha256':EXPECTED_HEADER_SHA})
    record={'kind':'E02_DATAINFO_CONTINUATION_V1_REQUEST','scope_ordinal':1,'combined_ordinal':13,'method':'GET','destination_url_sha256':sha(url.encode()),'source_location_header_sha256':EXPECTED_HEADER_SHA,'destination_kind':'EXACT_SAVED_PUBLIC_OSF_OBJECT_STORAGE_REDIRECT','destination_path_sha256':EXPECTED_PATH_SHA,'url_private_ref':str((CACHE/'EXACT_DESTINATION.json').relative_to(ROOT)),'signed_query_values_public':False,'owner_or_account_credentials_supplied':False,'timeout_seconds':20,'body_limit_bytes':LIMIT,'redirect_following':False,'retry_count':0,'retrieval_start_utc':datetime.now(timezone.utc).isoformat()}
    save_new(E/'01-RESERVED.json',record)
    connection=None;body=b'';started=time.monotonic();status='STOPPED_NO_DOCUMENT'
    try:
        connection=http.client.HTTPSConnection(parts.hostname,timeout=20,context=ssl.create_default_context())
        connection.request('GET',parts.path+('?' +parts.query if parts.query else ''),headers={'User-Agent':'SyntheticSocietyLab-PublicDocumentationCheck/1.0','Accept':'text/plain, text/markdown;q=0.9','Accept-Encoding':'identity'})
        response=connection.getresponse();record['http_status']=response.status
        headers=dict((k.lower(),v) for k,v in response.getheaders())
        record['headers']={k:v for k,v in headers.items() if k in {'content-type','content-length','content-disposition','date','etag','last-modified'}}
        if headers.get('location'):
            save_new(CACHE/'UNFOLLOWED_LOCATION.json',{'location':headers['location']})
            record['unfollowed_location_sha256']=sha(headers['location'].encode())
        while True:
            remaining=LIMIT-len(body)
            if remaining<=0:record['body_status']='BOUND_REACHED_NOT_COMPLETE';break
            chunk=response.read(min(4096,remaining))
            if not chunk:record['body_status']='COMPLETE';break
            body+=chunk
        record['body_bytes']=len(body);record['body_sha256']=sha(body)
        save_new(CACHE/'01-RESPONSE.bin',body)
        record['private_response_ref']={'path':str((CACHE/'01-RESPONSE.bin').relative_to(ROOT)),'bytes':len(body),'sha256':sha(body)}
        if response.status==200 and record['body_status']=='COMPLETE':
            if len(body)==822 and sha(body)==EXPECTED_FILE_SHA:status='EXACT822BYTE_DOCUMENT_VERIFIED_PRIVATE_ONLY'
            else:status='STOPPED_DOCUMENT_SIZE_OR_HASH_MISMATCH'
        elif response.status in {301,302,303,307,308}:status='STOPPED_FURTHER_REDIRECT_NOT_FOLLOWED'
        elif response.status in {401,403,429}:status='STOPPED_ACCESS_DENIAL_NO_RETRY'
        else:status='STOPPED_HTTP_ERROR_NO_RETRY'
    except BaseException as error:
        record['error_type']=type(error).__name__;status='STOPPED_TRANSPORT_OR_BOUNDS_NO_RETRY'
    finally:
        if connection is not None:connection.close()
        record['elapsed_seconds']=time.monotonic()-started;record['retrieval_end_utc']=datetime.now(timezone.utc).isoformat();record['public_body_saved']=False
        save_new(E/'01-OBSERVATION.json',record)
    summary={'kind':'E02_DATAINFO_CONTINUATION_V1_CLOSED','status':status,'requests':1,'response_body_bytes':len(body),'interpretation_allowed':status=='EXACT822BYTE_DOCUMENT_VERIFIED_PRIVATE_ONLY','expected_document_bytes':822,'expected_document_sha256':EXPECTED_FILE_SHA,'observation':record,'prior_consumed_requests':12,'prior_consumed_response_body_bytes':4569948,'combined_actual_requests':13,'combined_actual_response_body_bytes':4569948+len(body),'combined_max_requests':13,'combined_max_response_body_bytes':20971520+16384,'linked_file_downloads':0,'no_retry_or_refresh':True,'cost_usd':0}
    save_new(E/'CLOSED_CONTINUATION.json',summary)
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
