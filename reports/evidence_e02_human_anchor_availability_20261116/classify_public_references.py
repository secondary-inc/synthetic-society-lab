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
    from html.parser import HTMLParser
    from urllib.parse import urljoin
    previous=json.loads((E/'FOLLOWUP_PUBLIC_METADATA.json').read_text())
    assert len(list(E.glob('*-RESERVED.json')))==previous['cumulative_counts']['requests']==5
    counts.update(previous['cumulative_counts']);stopped.update(previous['stopped_routes'])
    observations=[]
    class Metadata(HTMLParser):
        def __init__(self):super().__init__();self.in_title=False;self.title=[];self.meta=[];self.links=[];self.anchor=None;self.blocks=[];self.stack=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='title':self.in_title=True
            if tag in {'p','li'}:self.stack.append({'tag':tag,'text':[],'anchors':[]})
            if tag=='a':self.anchor={'href':attrs.get('href'),'text':[]}
            if tag=='meta':
                name=attrs.get('property',attrs.get('name',''))
                if name in {'og:title','og:url','citation_title','citation_doi','citation_date'}:self.meta.append({'name':name,'content':attrs.get('content')})
            if tag=='link' and attrs.get('rel') in {'canonical','license'}:self.links.append({'rel':attrs['rel'],'href':attrs.get('href')})
        def handle_data(self,value):
            if self.in_title:self.title.append(value)
            if self.anchor is not None:self.anchor['text'].append(value)
            for block in self.stack:block['text'].append(value)
        def handle_endtag(self,tag):
            if tag=='title':self.in_title=False
            if tag=='a' and self.anchor is not None:
                anchor={'href':self.anchor['href'],'label':' '.join(''.join(self.anchor['text']).split())}
                for block in self.stack:block['anchors'].append(anchor)
                self.anchor=None
            if self.stack and self.stack[-1]['tag']==tag:
                block=self.stack.pop()
                if 'platform penalty' in ''.join(block['text']).lower():self.blocks.append(block['anchors'])
    for url,route,purpose in [
        ('https://osf.io/6dzeu/','OSF_PUBLIC_LINK','Classify previously received200 HTML as resource metadata versus access challenge; no JS/login or retry after denial.'),
        ('https://sites.dartmouth.edu/nyhan/publications/','AUTHOR_PUBLICATIONS','Record labels and exact public replication/preregistration links in target citation block.')]:
        record,body=fetch(url,route,purpose)
        row={'request':record,'public_metadata':None}
        if body and record.get('body_read_status')=='COMPLETE':
            text=body.decode('utf-8','replace');parser=Metadata();parser.feed(text)
            row['public_metadata']={'html_title':' '.join(parser.title),'public_head_metadata':parser.meta,'public_canonical_or_license_links':parser.links,'target_bibliography_anchor_blocks':parser.blocks,'response_saved':False}
            if route=='OSF_PUBLIC_LINK':
                flags={term:term in text.lower() for term in ('verify you are human','just a moment','access denied','captcha','page not found')}
                row['public_metadata']['access_or_error_keyword_indicators_not_a_license_finding']=flags
                print(json.dumps({'osf_title':row['public_metadata']['html_title'],'osf_head_metadata':parser.meta,'flags':flags}))
                if any(flags[k] for k in ('verify you are human','just a moment','access denied','captcha')):
                    stopped.add(route);row['public_metadata']['route_disposition']='ACCESS_CHALLENGE_STOP_NO_BYPASS'
            print(json.dumps({'url':url,'metadata':row['public_metadata']}))
        observations.append(row);del body
    new_json(E/'REFERENCE_CLASSIFICATION_METADATA.json',{'kind':'PUBLIC_METADATA_REFERENCE_CLASSIFICATION','observations':observations,'cumulative_counts':counts,'stopped_routes':sorted(stopped),'all_response_bodies_saved':False})
    print(json.dumps({'cumulative_counts':counts,'routes_stopped':sorted(stopped)}))


if __name__=='__main__':main()
