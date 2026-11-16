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
    assert parts.hostname in {'api.osf.io','osf.io','api.crossref.org','bpb-us-e1.wpmucdn.com'}
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
    requests=[('https://api.osf.io/v2/nodes/6dzeu/','OSF_API','Public project metadata and license/file relationships, no respondent data.'),('https://api.crossref.org/works/10.1080%2F19331681.2022.2105465','CROSSREF','Public DOI bibliographic/license metadata only.'),('https://bpb-us-e1.wpmucdn.com/sites.dartmouth.edu/dist/5/2293/files/2022/08/social_media_effects_credibility.pdf','AUTHOR_PAPER','Read-only author methods/version/replication reference. No retained text or PDF body.')]
    summaries=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures=[executor.submit(fetch,*request) for request in requests]
        for request,future in zip(requests,futures):
            record,body=future.result();row={'request':record,'public_metadata':None}
            if body and record.get('body_read_status')=='COMPLETE':
                try:
                    if request[1]=='CROSSREF':
                        data=json.loads(body)['message']
                        wanted=('DOI','URL','title','author','container-title','publisher','published','published-online','published-print','created','deposited','indexed','license','link','relation','type','volume','issue','page')
                        row['public_metadata']={key:data[key] for key in wanted if key in data}
                    elif request[1]=='OSF_API':
                        data=json.loads(body)
                        # Project-level JSON only; never user records, data files
                        # or full descriptions that may reproduce source text.
                        node=data.get('data',{});attrs=node.get('attributes',{})
                        row['public_metadata']={'id':node.get('id'),'type':node.get('type'),'attributes':{key:attrs[key] for key in ('title','public','category','date_created','date_modified','registration','preprint','tags','license') if key in attrs},'relationships':node.get('relationships',{}),'links':node.get('links',{})}
                    elif request[1]=='AUTHOR_PAPER':
                        # Existing legacy project dependency, author-PDF in RAM.
                        from pypdf import PdfReader
                        paper=PdfReader(io.BytesIO(body));text='\n'.join(page.extract_text() or '' for page in paper.pages)
                        row['public_metadata']={'pages':len(paper.pages),'pdf_metadata':{key:str(value) for key,value in (paper.metadata or {}).items() if key in {'/Title','/Author','/CreationDate','/ModDate','/Producer'}},'replication_url_present':'osf.io/6dzeu' in text,'license_notice_tokens_present':{'creative_commons':'creative commons' in text.lower(),'copyright':'copyright' in text.lower(),'all_rights_reserved':'all rights reserved' in text.lower()},'methods_keyword_observations':{label:term.lower() in text.lower() for label,term in [('MTurk','Mechanical Turk'),('N3008','3,008'),('credibility','credibility'),('website','website'),('Facebook','Facebook')]},'pdf_or_text_saved':False}
                        # Display narrow context for in-session inspection only;
                        # no text excerpts are written to owned evidence files.
                        snippets=[]
                        for needle in ('osf.io','Creative Commons','©','copyright','Data availability','replication'):
                            at=text.lower().find(needle.lower())
                            if at>=0:snippets.append({'term':needle,'context':text[max(0,at-100):at+230]})
                        print(json.dumps({'author_methods_readonly_session_context_not_saved':snippets}))
                except BaseException as error:row['metadata_parse_error_type']=type(error).__name__
            summaries.append(row)
            # Discard body; respondent data and stimulus text never requested.
            del body
    new_json(E/'INITIAL_PUBLIC_METADATA.json',{'kind':'BOUNDED_PUBLIC_METADATA_AUTHOR_METHODS_INITIAL_BATCH','observations':summaries,'counts':counts,'denied_or_failed_routes_stopped':sorted(stopped),'no_response_bodies_saved':True,'cost_usd':0})
    print(json.dumps({'counts':counts,'routes_stopped':sorted(stopped),'statuses':[{'url':r['request']['url'],'status':r['request'].get('http_status'),'error':r['request'].get('transport_error_type'),'metadata':r['public_metadata']} for r in summaries]},sort_keys=True))


if __name__=='__main__':main()
