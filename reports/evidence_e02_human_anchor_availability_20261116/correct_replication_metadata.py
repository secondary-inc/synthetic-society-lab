"""One bounded public metadata/author-methods batch, no automatic retries.

Never follow file download links or save response bodies. Do not replay this
batch: existing reservation records make reuse fail. All network routes stop at
access denial. Redirects count as separate requests and are not auto-followed.
"""
from pathlib import Path
from datetime import datetime,timezone
import concurrent.futures
import hashlib
import http.client
import io
import json
import ssl
import threading
import time
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
LIMIT_REQUESTS=8;LIMIT_BYTES=16777216
lock=threading.Lock();counts={'requests':0,'response_bytes':0};stopped=set()
context=ssl.create_default_context()

def new_json(path,value):
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    with open(path,'xb') as stream:stream.write(raw)

def fetch(url,route,purpose,maximum=4194304):
    parts=urlsplit(url)
    assert parts.scheme=='https' and parts.username is None and parts.password is None
    assert parts.hostname in {'api.osf.io','osf.io','api.crossref.org','bpb-us-e1.wpmucdn.com','sites.dartmouth.edu','www.dartmouth.edu','nyhan.dartmouth.edu'}
    with lock:
        assert route not in stopped,'DENIED_ROUTE_NOT_RETRIED'
        assert counts['requests']<LIMIT_REQUESTS,'REQUEST_CAP'
        counts['requests']+=1;ordinal=counts['requests']
        reservation={'ordinal':ordinal,'url':url,'route':route,'purpose':purpose,'method':'GET','retrieval_start_utc':datetime.now(timezone.utc).isoformat(),'response_byte_bound':maximum,'redirects':'NOT_AUTOMATICALLY_FOLLOWED','credentials':False,'respondent_or_stimulus_download':False}
        new_json(E/f'{ordinal:02d}-RESERVED.json',reservation)
    connection=None;record=dict(reservation);body=b'';started=time.monotonic()
    try:
        connection=http.client.HTTPSConnection(parts.hostname,timeout=20,context=context)
        connection.request('GET',parts.path+('?' +parts.query if parts.query else ''),headers={'User-Agent':'SyntheticSocietyLab-PublicMetadataCheck/1.0','Accept-Encoding':'identity','Accept':'application/json, application/pdf, text/html;q=0.5'})
        response=connection.getresponse()
        record['http_status']=response.status
        allowed_headers={'content-type','content-length','location','last-modified','etag','date','content-disposition','link','cache-control'}
        record['headers']={k.lower():v for k,v in response.getheaders() if k.lower() in allowed_headers}
        if response.status in {401,403,429}:
            with lock:stopped.add(route)
            record['route_status']='ACCESS_DENIAL_STOP_NO_RETRY'
        while True:
            with lock:remaining=min(maximum-len(body),LIMIT_BYTES-counts['response_bytes'])
            if remaining<=0:
                record['body_read_status']='BOUND_REACHED_NOT_COMPLETE';break
            chunk=response.read(min(65536,remaining))
            if not chunk:
                record['body_read_status']='COMPLETE';break
            with lock:
                counts['response_bytes']+=len(chunk)
                assert counts['response_bytes']<=LIMIT_BYTES
            body+=chunk
        record['body_bytes']=len(body);record['body_sha256']=hashlib.sha256(body).hexdigest()
        record['body_saved']=False
        if response.status!=200:body=b''
    except BaseException as error:
        record['transport_error_type']=type(error).__name__
        record['http_status']=None
        record['body_bytes_received_before_error']=len(body)
        record['route_status']='TRANSPORT_STOP_NO_RETRY'
        with lock:stopped.add(route)
        body=b''
    finally:
        if connection is not None:connection.close()
        record['elapsed_seconds']=time.monotonic()-started
        record['retrieval_end_utc']=datetime.now(timezone.utc).isoformat()
        new_json(E/f'{ordinal:02d}-OBSERVATION.json',record)
    return record,body




def main():
    previous=json.loads((E/'REFERENCE_CLASSIFICATION_METADATA.json').read_text())
    assert len(list(E.glob('*-RESERVED.json')))==previous['cumulative_counts']['requests']==7
    counts.update(previous['cumulative_counts']);stopped.update(previous['stopped_routes'])
    url='https://api.osf.io/v2/nodes/xe28y/files/osfstorage/?page%5Bsize%5D=100'
    record,body=fetch(url,'AUTHOR_IDENTIFIED_REPLICATION_METADATA','Metadata listing for xe28y: author bibliography explicitly labels this replication data/code. Different source from the preregistration6dzeu; no respondent/stimulus contents or download links followed.')
    metadata=None
    if body and record.get('body_read_status')=='COMPLETE':
        try:
            value=json.loads(body);files=[]
            for item in value.get('data',[]):
                attrs=item.get('attributes',{})
                files.append({'id':item.get('id'),'type':item.get('type'),'attributes':{key:attrs[key] for key in ('name','kind','path','materialized_path','date_created','date_modified','size','provider','current_version','extra','tags') if key in attrs},'links':item.get('links',{}),'relationships':item.get('relationships',{})})
            metadata={'file_metadata':files,'page_links':value.get('links',{}),'pagination_meta':value.get('meta',{}),'contents_downloaded':False,'associated_author_link':'https://osf.io/xe28y/','preregistration_is_separate':'https://osf.io/6dzeu','rights_scope':'Listing accessibility does not establish license or permission for respondent data, instrument or news stimuli.'}
        except BaseException as error:metadata={'parse_error_type':type(error).__name__}
    new_json(E/'CORRECT_REPLICATION_LISTING_METADATA.json',{'kind':'AUTHOR_IDENTIFIED_REPLICATION_METADATA_FINAL_REQUEST','observation':record,'public_metadata':metadata,'cumulative_counts':counts,'stopped_routes':sorted(stopped),'request_budget_exhausted':True,'response_body_saved':False})
    print(json.dumps({'request':record,'metadata':metadata,'cumulative_counts':counts,'request_budget_exhausted':True},sort_keys=True))


if __name__=='__main__':main()
