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
    initial=json.loads((E/'INITIAL_PUBLIC_METADATA.json').read_text())
    assert len(list(E.glob('*-RESERVED.json')))==initial['counts']['requests']==3
    counts.update(initial['counts']);stopped.update(initial['denied_or_failed_routes_stopped'])
    stopped.add('OSF_API')  # Node404 is left unresolved; no repeated API guesses.
    requests=[('https://osf.io/6dzeu/','OSF_PUBLIC_LINK','Resolve the supplied public replication reference, metadata only; no login or bypass.'),('https://sites.dartmouth.edu/nyhan/publications/','AUTHOR_PUBLICATIONS','Author bibliography metadata and target replication-link association only.')]
    summaries=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(fetch,*request) for request in requests]
        for request,future in zip(requests,futures):
            record,body=future.result();row={'request':record,'public_metadata':None}
            if body and record.get('body_read_status')=='COMPLETE' and request[1]=='AUTHOR_PUBLICATIONS':
                from html.parser import HTMLParser
                from urllib.parse import urljoin
                class Groups(HTMLParser):
                    def __init__(self):super().__init__();self.stack=[];self.rows=[]
                    def handle_starttag(self,tag,attrs):
                        if tag in {'p','li'}:self.stack.append({'tag':tag,'text':[],'links':[]})
                        if tag=='a':
                            value=dict(attrs).get('href')
                            if value:
                                for group in self.stack:group['links'].append(urljoin(request[0],value))
                    def handle_data(self,text):
                        for group in self.stack:group['text'].append(text)
                    def handle_endtag(self,tag):
                        if self.stack and self.stack[-1]['tag']==tag:
                            group=self.stack.pop();text=' '.join(''.join(group['text']).split())
                            if 'platform penalty' in text.lower():self.rows.append({'element':tag,'target_title_match':True,'links':group['links']})
                text=body.decode('utf-8','replace');parser=Groups();parser.feed(text)
                row['public_metadata']={'target_title_present':'platform penalty' in text.lower(),'target_short_replication_url_present':'osf.io/6dzeu' in text.lower(),'target_bibliography_blocks':parser.rows,'response_saved':False}
            summaries.append(row);del body
    new_json(E/'FOLLOWUP_PUBLIC_METADATA.json',{'kind':'PUBLIC_REPLICATION_REFERENCE_AUTHOR_BIBLIOGRAPHY_FOLLOWUP','observations':summaries,'cumulative_counts':counts,'stopped_routes':sorted(stopped),'body_saved':False})
    print(json.dumps({'cumulative_counts':counts,'routes_stopped':sorted(stopped),'observations':summaries},sort_keys=True))


if __name__=='__main__':main()
