"""Oregon offered-link acquisition: max4GETs,5MiB bodies,30s hard timer, no retry.

No source parser/adoption; raw captures stay private. URLs must be exact offered
anchors of the verified cached official index or a prior successful index body.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import signal
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from urllib.error import HTTPError

CACHE='data/raw/e01_ballots_batch03_v1/or_filing_index.html'
CACHE_SHA='7cc4aa618fcc2fbcb66bf4c81e7aeb29aeb6183062366b0f1fc44fd5de34b7e6'
INDEX='https://sos.oregon.gov/elections/pages/candidate-filings-local-measures.aspx'
SCOPE='data/raw/e01_oregon_offered_links_v1'
MAX_BYTES=5*1024*1024


def now():return datetime.now(timezone.utc).isoformat()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write_once(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.href=None;self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.href=dict(attrs).get('href');self.text=[]
    def handle_data(self,data):
        if self.href is not None:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href is not None:self.links.append((self.href,' '.join(' '.join(self.text).split())));self.href=None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent',required=True);p.add_argument('--parent-sha',required=True);p.add_argument('--url',required=True);p.add_argument('--source-id',required=True);args=p.parse_args()
    root=Path.cwd();scope=root/SCOPE
    assert args.source_id and all(x.isalnum() or x=='_' for x in args.source_id)
    assert not any(x.is_symlink() for x in (scope,*scope.parents))
    scope.mkdir(parents=True,exist_ok=True)
    assert not (scope/'STOP.local.json').exists(),'TERMINAL_STOP_NO_ALTERNATES'
    started=list(scope.glob('*_started.local.json'));assert len(started)<4,'FOUR_GET_LIMIT'
    assert all(json.loads(x.read_text())['url']!=args.url for x in started),'NO_RETRY_SAME_URL'
    parent=root/args.parent;raw=parent.read_bytes();assert sha(raw)==args.parent_sha
    if args.parent==CACHE:
        assert args.parent_sha==CACHE_SHA;parent_url=INDEX
    else:
        assert parent.parent==scope and parent.suffix=='.body'
        matches=[json.loads(x.read_text()) for x in scope.glob('*_receipt.local.json') if json.loads(x.read_text()).get('body_path')==args.parent]
        assert len(matches)==1 and matches[0]['status']==200 and matches[0]['body_complete'] and 'text/html' in matches[0]['headers'].get('Content-Type','')
        parent_url=matches[0]['url']
    parser=Links();parser.feed(raw.decode('utf-8'))
    offered=[{'href_literal':href,'url':urljoin(parent_url,href),'label':label} for href,label in parser.links]
    matches=[x for x in offered if x['url']==args.url];assert matches,'URL_NOT_OFFERED'
    parsed=urlsplit(args.url)
    assert parsed.scheme=='https' and parsed.hostname in {'sos.oregon.gov','secure.sos.state.or.us'} and not parsed.username and not parsed.password
    assert 'login' not in parsed.path.lower(),'LOGIN_ROUTE_NOT_PERMITTED'
    number=len(started)+1;prefix=f'{number:02d}_{args.source_id}'
    receipt={'source_id':args.source_id,'url':args.url,'retrieved_at_utc':now(),'parent_index':{'path':args.parent,'sha256':args.parent_sha,'url':parent_url},'offered_link':matches[0],
             'request_number':number,'max_requests':4,'max_body_bytes':MAX_BYTES,'max_request_seconds':30,'retries':0,
             'redirects_followed':0,'credentials_used':False,'request_method':'GET','status':None,'headers':{},'body_path':None,'bytes':0,'sha256':None,'body_complete':False,
             'capture_kind':'HTTP_RESPONSE_BODY_BYTES_AS_EXPOSED_BY_URLLIB_NOT_WIRE_OR_BROWSER_DOM','error_type':None,'started_at_utc':now()}
    write_once(scope/(prefix+'_started.local.json'),{'url':args.url,'started_at_utc':now(),'attempt':number,'retry_authorized':False})
    body=scope/(prefix+'.body')
    def timeout(*_):raise TimeoutError('BOUNDED_REQUEST_DEADLINE')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,30)
    try:
        opener=build_opener(ProxyHandler({}),NoRedirect())
        try:response=opener.open(Request(args.url,method='GET'),timeout=30)
        except HTTPError as error:
            receipt['status']=error.code
            receipt['headers']={k:error.headers[k] for k in ['Date','Last-Modified','Content-Type','Content-Length','Location','Content-Encoding','ETag'] if k in error.headers}
            error.close();raise RuntimeError('HTTP_NON200_STOP_WITHOUT_ERROR_BODY_READ') from None
        with response:
            receipt['status']=response.status
            receipt['headers']={k:response.headers[k] for k in ['Date','Last-Modified','Content-Type','Content-Length','Location','Content-Encoding','ETag'] if k in response.headers}
            assert response.status==200,'NON200_STOP'
            assert response.geturl()==args.url,'UNEXPECTED_REDIRECT_STOP'
            length=response.headers.get('Content-Length')
            if length is not None:assert int(length)<=MAX_BYTES,'DECLARED_OVERSIZE_STOP'
            with body.open('xb') as f:
                remaining=MAX_BYTES
                while remaining:
                    block=response.read(min(65536,remaining))
                    if not block:receipt['body_complete']=True;break
                    f.write(block);remaining-=len(block)
                if length is not None and body.stat().st_size==int(length):receipt['body_complete']=True
            if not receipt['body_complete']:raise RuntimeError('BODY_LIMIT_OR_COMPLETENESS_UNKNOWN_STOP')
            assert response.headers.get('Content-Encoding','identity').lower()=='identity','UNSUPPORTED_ENCODED_REPRESENTATION_STOP'
    except BaseException as error:
        receipt['error_type']=type(error).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
    if body.exists():
        data=body.read_bytes();assert len(data)<=MAX_BYTES
        receipt.update(body_path=str(body.relative_to(root)),bytes=len(data),sha256=sha(data))
    receipt['completed_at_utc']=now()
    write_once(scope/(prefix+'_receipt.local.json'),receipt)
    if receipt['error_type'] is not None:write_once(scope/'STOP.local.json',{'status':'STOP_NO_RETRY_OR_ALTERNATE','request_number':number,'http_status':receipt['status'],'error_type':receipt['error_type']})
    print(json.dumps({k:receipt[k] for k in ['source_id','request_number','status','bytes','sha256','body_complete','error_type','body_path']}))


if __name__=='__main__':main()
