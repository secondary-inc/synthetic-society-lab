"""Fixed P1 artifact collector. No extraction, installation or package imports.

CLI is root-scheduled only after independent methods/code/particular review.
Tests supply memory transports; importing this module performs no network IO.
"""
import argparse
import base64
from datetime import datetime, timezone
from email.parser import BytesParser
from email import policy as email_policy
from email.utils import parsedate_to_datetime
import hashlib
import http.client
import io
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import ssl
import stat
import struct
import time
from urllib.parse import urlsplit,parse_qsl
import zipfile

VERSIONS={'pypdf':'7.0.1','cffi':'2.1.1','cryptography':'50.0.2','pillow':'13.0.0','pycparser':'3.12'}
CAPS={'GET':13,'metadata_GET':8,'wheel_GET':5,'metadata_each':2097152,'metadata_total':8388608,
      'wheel_each':16777216,'wheel_total':67108864,'network_total':75497472,
      'request_seconds':20,'wall_seconds':300,'CPU_seconds':60,'owned_write_bytes':83886080,
      'control_write_bytes':8388608,'ZIP_entries':4096,'ZIP_uncompressed_bytes':268435456,
      'ZIP_entry_bytes':67108864,'ZIP_directory_bytes':4194304,'ZIP_ratio':200,'journal_events':64}
TARGET={'implementation':'CPython','python':'3.12.14','architecture':'arm64','OS':'macOS','macOS_version':'26.6'}
OUTPUT='data/processed/e01_pypdf701_build_v1/acquisition-v1-20261115'
METHODS='configs/e01_pypdf701_acquisition_v1_20261115.json'
API='https://api.github.com/repos/py-pdf/pypdf/security-advisories?state=published&per_page=100&sort=published&direction=asc'
PROVENANCE='https://pypi.org/integrity/pypdf/7.0.1/pypdf-7.0.1-py3-none-any.whl/provenance'
PYPDF={'filename':'pypdf-7.0.1-py3-none-any.whl','size':416136,
       'sha256':'6131b764b046282357037309e7ef2a1b7679d4a5c53eed3db2bfbf7c673ddc2b',
       'url':'https://files.pythonhosted.org/packages/d5/a9/ae11deef21eaac5113f8c3848da1c42423b7abeca0abc349bfec7abf4c4e/pypdf-7.0.1-py3-none-any.whl'}

class Refused(RuntimeError):pass

def need(value,reason):
    if not value:raise Refused(reason)
def sha(body):return hashlib.sha256(body).hexdigest()
def packed(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def normalized(name):return re.sub(r'[-_.]+','-',name).lower()
def version(text):
    need(type(text) is str and re.fullmatch(r'(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,2}',text),'UNKNOWN_VERSION')
    parts=tuple(map(int,text.split('.')));return parts+(0,)*(3-len(parts))
def matches(expression,candidate):
    need(type(expression) is str and 0<len(expression)<=256,'UNKNOWN_RANGE')
    clauses=expression.split(',');need(1<=len(clauses)<=8,'UNKNOWN_RANGE');v=version(candidate)
    checks=[]
    for clause in clauses:
        found=re.fullmatch(r'\s*(<=|>=|==|!=|<|>)\s*([0-9]+(?:\.[0-9]+){0,2})\s*',clause)
        need(found is not None,'UNKNOWN_RANGE');op,text=found.groups();other=version(text)
        checks.append({'<':v<other,'>':v>other,'<=':v<=other,'>=':v>=other,'==':v==other,'!=':v!=other}[op])
    return all(checks)
def json_body(raw):
    def pairs(items):
        out={}
        for key,val in items:need(key not in out,'DUPLICATE_JSON_KEY');out[key]=val
        return out
    def invalid(_):raise Refused('NONFINITE_JSON')
    try:obj=json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    except (ValueError,UnicodeError,RecursionError):raise Refused('JSON_SCHEMA') from None
    left=[50000]
    def walk(item,depth):
        left[0]-=1;need(left[0]>=0 and depth<=24,'JSON_COMPLEXITY')
        if type(item) is float:need(math.isfinite(item),'NONFINITE_JSON')
        if isinstance(item,dict):
            for value in item.values():walk(value,depth+1)
        elif isinstance(item,list):
            for value in item:walk(value,depth+1)
    walk(obj,0);return obj

def utc_parse(text):
    need(type(text) is str and len(text)<=40,'TIME_SCHEMA')
    try:value=datetime.fromisoformat(text.replace('Z','+00:00'))
    except ValueError:raise Refused('TIME_SCHEMA') from None
    need(value.tzinfo is not None,'TIME_SCHEMA');return value

def select_wheel(name,doc):
    need(type(doc) is dict and type(doc.get('info')) is dict and type(doc.get('urls')) is list,'PYPI_SCHEMA')
    info=doc['info'];need(normalized(info.get('name',''))==name and info.get('version')==VERSIONS[name],'PACKAGE_IDENTITY')
    need(info.get('yanked') is False and matches(info.get('requires_python'),TARGET['python']),'PACKAGE_COMPATIBILITY')
    need(1<=len(doc['urls'])<=1024,'PYPI_SCHEMA');choices=[];names=set()
    for row in doc['urls']:
        need(type(row) is dict and type(row.get('filename')) is str,'PYPI_SCHEMA')
        filename=row['filename'];need(filename not in names,'DUPLICATE_ARTIFACT');names.add(filename)
        if row.get('packagetype')!='bdist_wheel':continue
        need(type(row.get('yanked')) is bool,'PYPI_SCHEMA')
        if row['yanked']:continue
        need(type(row.get('requires_python')) in {str,type(None)},'PYPI_SCHEMA')
        if row['requires_python'] is not None and not matches(row['requires_python'],TARGET['python']):continue
        rank=wheel_rank(name,filename)
        if rank is None:continue
        need(type(row.get('size')) is int and 0<row['size']<CAPS['wheel_each'],'WHEEL_SIZE')
        need(type(row.get('digests')) is dict and re.fullmatch('[0-9a-f]{64}',row['digests'].get('sha256','')),'WHEEL_DIGEST')
        url=row.get('url');need(type(url) is str,'WHEEL_URL');validate_url(url,'wheel',filename)
        picked={'name':name,'version':VERSIONS[name],'filename':filename,'url':url,'size':row['size'],
                'sha256':row['digests']['sha256'],'requires_python':info['requires_python'],
                'file_requires_python':row['requires_python'],'yanked':False}
        choices.append((rank,filename,picked))
    need(bool(choices),'NO_COMPATIBLE_WHEEL')
    best=max(x[0] for x in choices);winners=[x for x in choices if x[0]==best]
    need(len(winners)==1,'AMBIGUOUS_WHEEL_SELECTION');picked=winners[0][2]
    if name=='pypdf':need(all(picked[k]==v for k,v in PYPDF.items()),'FROZEN_PYPDF_IDENTITY')
    return picked

def wheel_rank(name,filename):
    if not filename.endswith('.whl'):return None
    bits=filename[:-4].split('-')
    if len(bits) not in {5,6}:return None
    dist,ver=bits[:2]
    if normalized(dist)!=name or ver!=VERSIONS[name]:return None
    if len(bits)==6 and not re.fullmatch('[0-9]+[A-Za-z0-9_]*',bits[2]):return None
    py,abi,platform=bits[-3:]
    if name in {'pypdf','pycparser'}:
        return (1,0,0) if (py,abi,platform)==('py3','none','any') else None
    ranks=[]
    for p in py.split('.'):
        for a in abi.split('.'):
            for target in platform.split('.'):
                found=re.fullmatch(r'macosx_([0-9]+)_([0-9]+)_(arm64|universal2)',target)
                if found is None:continue
                major,minor,arch=found.groups()
                if (int(major),int(minor))>tuple(map(int,TARGET['macOS_version'].split('.'))):continue
                if name in {'cffi','pillow'} and (p,a)!=('cp312','cp312'):continue
                if name=='cryptography' and not(a=='abi3' and p in {'cp38','cp39','cp310','cp311','cp312'}):continue
                ranks.append((2 if arch=='arm64' else 1,int(p[2:]),int(major)*100+int(minor)))
    return max(ranks) if ranks else None

def validate_url(url,kind,filename=None):
    part=urlsplit(url)
    need(part.scheme=='https' and part.port in {None,443} and part.username is None and part.password is None and not part.fragment,'URL_POLICY')
    if kind=='metadata':
        allowed={f'https://pypi.org/pypi/{n}/{v}/json' for n,v in VERSIONS.items()}|{PROVENANCE}
        if url not in allowed:validate_advisory_url(url)
    else:
        need(part.netloc=='files.pythonhosted.org' and not part.query and type(filename) is str,'URL_POLICY')
        need(re.fullmatch(r'/packages/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{60}/'+re.escape(filename),part.path) is not None,'URL_POLICY')


def validate_advisory_url(url):
    part=urlsplit(url);pairs=parse_qsl(part.query,keep_blank_values=True)
    need(part.scheme=='https' and part.netloc=='api.github.com' and not part.fragment
         and part.path=='/repos/py-pdf/pypdf/security-advisories' and len(url)<=2048,'URL_POLICY')
    need(len({k for k,_ in pairs})==len(pairs),'URL_POLICY');query=dict(pairs)
    for key,value in {'state':'published','per_page':'100','sort':'published','direction':'asc'}.items():
        need(query.pop(key,None)==value,'URL_POLICY')
    need(set(query)<={'after','before'} and len(query)<=1,'URL_POLICY')
    if query:need(re.fullmatch(r'[A-Za-z0-9_+/=-]{1,256}',next(iter(query.values()))) is not None,'URL_POLICY')


def next_advisory(headers,rows,page):
    need(type(rows) is list and len(rows)<=100,'ADVISORY_SCHEMA')
    links=headers.get('link','');next_url=None;relations=set()
    if links:
        for item in links.split(','):
            match=re.fullmatch(r'\s*<([^>]+)>; rel="(next|prev|first|last)"\s*',item)
            need(match is not None,'PAGINATION_SCHEMA');url,relation=match.groups()
            need(relation not in relations,'PAGINATION_SCHEMA');relations.add(relation);validate_advisory_url(url)
            if relation=='next':
                need('after' in dict(parse_qsl(urlsplit(url).query)),'PAGINATION_SCHEMA');next_url=url
    if next_url is None:need(len(rows)<100,'ADVISORY_TRUNCATION_UNKNOWN')
    else:need(page==1,'ADVISORY_PAGE_CAP')
    return next_url


def assess_advisories(pages):
    rows=[];ids=set()
    for page in pages:
        need(type(page) is list and len(page)<=100,'ADVISORY_SCHEMA')
        for advisory in page:
            need(type(advisory) is dict and advisory.get('state')=='published','ADVISORY_SCHEMA')
            ident=advisory.get('ghsa_id');need(type(ident) is str and re.fullmatch(r'GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}',ident),'ADVISORY_SCHEMA')
            need(ident not in ids,'DUPLICATE_ADVISORY');ids.add(ident)
            utc_parse(advisory.get('updated_at'));utc_parse(advisory.get('published_at'))
            need('withdrawn_at' in advisory,'ADVISORY_SCHEMA');withdrawn=advisory['withdrawn_at']
            if withdrawn is not None:utc_parse(withdrawn)
            vulnerabilities=advisory.get('vulnerabilities');need(type(vulnerabilities) is list and 1<=len(vulnerabilities)<=32,'ADVISORY_SCHEMA')
            relevant=[]
            for vuln in vulnerabilities:
                need(type(vuln) is dict and type(vuln.get('package')) is dict,'ADVISORY_SCHEMA')
                package=vuln['package'];need(type(package.get('name')) is str and type(package.get('ecosystem')) is str,'ADVISORY_SCHEMA')
                if normalized(package['name'])!='pypdf':continue
                need(package['ecosystem']=='pip','ADVISORY_SCHEMA')
                applies=matches(vuln.get('vulnerable_version_range'),VERSIONS['pypdf'])
                need('patched_versions' in vuln,'ADVISORY_SCHEMA');patch=vuln['patched_versions'];need(type(patch) in {str,type(None)},'ADVISORY_SCHEMA')
                if patch:
                    # Repository API reports patched_versions, not the distinct
                    # global-advisory first_patched_version schema.
                    patched=matches(patch if re.match(r'\s*[<>=!]',patch) else '=='+patch,VERSIONS['pypdf'])
                    need(not(applies and patched),'INCONSISTENT_ADVISORY')
                relevant.append({'range':vuln['vulnerable_version_range'],'patched_versions':patch,
                                 'candidate_affected':applies,'withdrawn':withdrawn is not None})
            need(bool(relevant),'ADVISORY_PACKAGE_MISSING')
            rows.append({'ghsa_id':ident,'published_at':advisory['published_at'],'updated_at':advisory['updated_at'],'assessments':relevant})
    need(bool(rows),'EMPTY_ADVISORY_COVERAGE')
    blocked=any(a['candidate_affected'] and not a['withdrawn'] for row in rows for a in row['assessments'])
    return {'candidate':'7.0.1','not_latest':True,'lead_observed_newer_release':'7.1.0 (2026-11-13)',
            'status':'BLOCKED_APPLICABLE_ADVISORY' if blocked else 'NO_APPLICABLE_ISSUE_IN_CAPTURED_MAINTAINER_PAGES',
            'coverage':'Bounded complete captured maintainer published-advisory listing; not proof of zero vulnerabilities.',
            'advisories':rows}


def provenance_binding(doc):
    need(type(doc) is dict and type(doc.get('attestation_bundles')) is list and 1<=len(doc['attestation_bundles'])<=8,'PROVENANCE_SCHEMA')
    bound=False
    for bundle in doc['attestation_bundles']:
        need(type(bundle) is dict and type(bundle.get('publisher')) is dict,'PROVENANCE_SCHEMA')
        publisher=bundle['publisher']
        need(publisher.get('kind')=='GitHub' and publisher.get('repository')=='py-pdf/pypdf'
             and publisher.get('workflow')=='publish-to-pypi.yaml','PROVENANCE_PUBLISHER')
        attestations=bundle.get('attestations');need(type(attestations) is list and 1<=len(attestations)<=8,'PROVENANCE_SCHEMA')
        for att in attestations:
            need(type(att) is dict and type(att.get('version')) is int and att['version']==1 and type(att.get('envelope')) is dict,'PROVENANCE_SCHEMA')
            statement=att['envelope'].get('statement');need(type(statement) is str and len(statement)<=262144,'PROVENANCE_SCHEMA')
            try:raw=base64.b64decode(statement,validate=True)
            except ValueError:raise Refused('PROVENANCE_ENCODING') from None
            data=json_body(raw)
            need(type(data) is dict and data.get('_type')=='https://in-toto.io/Statement/v1'
                 and data.get('predicateType')=='https://docs.pypi.org/attestations/publish/v1','PROVENANCE_SCHEMA')
            subjects=data.get('subject');need(type(subjects) is list and 1<=len(subjects)<=8,'PROVENANCE_SCHEMA')
            for subject in subjects:
                need(type(subject) is dict and type(subject.get('digest')) is dict,'PROVENANCE_SCHEMA')
                if subject.get('name')==PYPDF['filename']:
                    need(subject['digest'].get('sha256')==PYPDF['sha256'],'PROVENANCE_DIGEST');bound=True
    need(bound,'PROVENANCE_SUBJECT')
    return 'PYPI_HTTPS_PUBLISHER_AND_SUBJECT_BINDING_ONLY_NOT_LOCAL_SIGNATURE_VERIFICATION'


def inspect_wheel(raw,name,filename,budget=None,entries_left=None,bytes_left=None):
    """Bound central records before ZipFile construction; stream CRC, never extract."""
    entries_left=CAPS['ZIP_entries'] if entries_left is None else entries_left
    bytes_left=CAPS['ZIP_uncompressed_bytes'] if bytes_left is None else bytes_left
    end=raw.rfind(b'PK\x05\x06',max(0,len(raw)-65557));need(end>=0 and end+22<=len(raw),'ZIP_EOCD')
    disk,cd_disk,count_disk,count,size,offset,comment=struct.unpack_from('<4H2IH',raw,end+4)
    need(disk==cd_disk==0 and count==count_disk and count<65535 and end+22+comment==len(raw),'ZIP_LAYOUT')
    need(0<count<=entries_left and size<=CAPS['ZIP_directory_bytes'] and offset+size<=end,'ZIP_DIRECTORY')
    cursor=offset;seen=0
    while cursor<offset+size:
        need(raw[cursor:cursor+4]==b'PK\x01\x02' and cursor+46<=offset+size,'ZIP_DIRECTORY')
        n,e,c=struct.unpack_from('<3H',raw,cursor+28);cursor+=46+n+e+c;seen+=1
        need(seen<=CAPS['ZIP_entries'] and cursor<=offset+size,'ZIP_DIRECTORY')
    need(cursor==offset+size and seen==count,'ZIP_DIRECTORY')
    declared=0;members=[];names=set();captured={};dist=name+'-'+VERSIONS[name]+'.dist-info/'
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos=archive.infolist();need(len(infos)==count,'ZIP_DIRECTORY')
        for info in infos:
            path=info.filename;clean=path[:-1] if info.is_dir() else path
            need(path==info.orig_filename and len(path.encode())<=240 and all(32<=ord(ch)<127 for ch in path),'ZIP_PATH')
            parts=clean.split('/');need(not path.startswith('/') and all(p not in {'','.','..'} for p in parts)
                 and '\\' not in path and ':' not in path,'ZIP_PATH')
            need(not(parts[0].endswith('.dist-info') and parts[0]+'/'!=dist),'UNEXPECTED_DISTRIBUTION_METADATA')
            need(clean.casefold() not in names,'ZIP_DUPLICATE');names.add(clean.casefold())
            need(not any(p.lower().endswith(('.pth','.data')) for p in parts),'ZIP_EXECUTABLE_PATH')
            mode=stat.S_IFMT(info.external_attr>>16)
            need(mode in {0,stat.S_IFREG,stat.S_IFDIR} and not info.flag_bits&1,'ZIP_SPECIAL_ENTRY')
            need(info.compress_type in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED},'ZIP_COMPRESSION')
            need(0<=info.file_size<=CAPS['ZIP_entry_bytes'] and info.file_size<=max(1,info.compress_size)*CAPS['ZIP_ratio'],'ZIP_INFLATION')
            declared+=info.file_size;need(declared<=bytes_left,'ZIP_INFLATION')
        for info in infos:
            if budget is not None:budget.check()
            actual=0;chunks=[];capture=info.filename in {dist+'METADATA',dist+'WHEEL'}
            if capture:need(info.file_size<=131072,'WHEEL_METADATA_SIZE')
            with archive.open(info) as source:
                while True:
                    if budget is not None:budget.check()
                    chunk=source.read(min(65536,info.file_size-actual+1))
                    if not chunk:break
                    actual+=len(chunk);need(actual<=info.file_size,'ZIP_INFLATION')
                    if capture:chunks.append(chunk)
            need(actual==info.file_size,'ZIP_SIZE')
            if capture:captured[info.filename]=b''.join(chunks)
            members.append([info.filename,info.file_size,info.CRC])
    need(set(captured)=={dist+'METADATA',dist+'WHEEL'},'WHEEL_METADATA_MISSING')
    meta=BytesParser(policy=email_policy.default).parsebytes(captured[dist+'METADATA'])
    wheel=BytesParser(policy=email_policy.default).parsebytes(captured[dist+'WHEEL'])
    need(all(len(meta.get_all(key,[]))==1 for key in ['Name','Version','Requires-Python'])
         and all(len(wheel.get_all(key,[]))==1 for key in ['Wheel-Version','Root-Is-Purelib']),'DUPLICATE_WHEEL_METADATA')
    need(normalized(meta.get('Name',''))==name and meta.get('Version')==VERSIONS[name],'WHEEL_METADATA_IDENTITY')
    need(meta.get('Requires-Python') is not None and matches(str(meta['Requires-Python']),TARGET['python']),'WHEEL_PYTHON')
    need(wheel.get('Wheel-Version')=='1.0' and wheel.get('Root-Is-Purelib') in {'true','false'} and bool(wheel.get_all('Tag')),'WHEEL_SCHEMA')
    py,abi,platform=filename[:-4].split('-')[-3:]
    expected_tags={p+'-'+a+'-'+t for p in py.split('.') for a in abi.split('.') for t in platform.split('.')}
    need(set(wheel.get_all('Tag'))==expected_tags,'WHEEL_TAG_MISMATCH')
    return {'entries':count,'uncompressed_bytes':declared,'member_manifest_sha256':sha(packed(members)),
            'requires_dist':meta.get_all('Requires-Dist',[]),'wheel_tags':wheel.get_all('Tag')}


class Budget:
    def __init__(self,clock,cpu):
        self.clock=clock;self.cpu=cpu;self.started=self.prior=clock();self.initial_cpu=self.prior_cpu=cpu()
        self.attempts={'GET':0,'metadata_GET':0,'wheel_GET':0};self.bytes={'metadata':0,'wheel':0};self.held=0
    def check(self):
        now=self.clock();cpu=self.cpu()
        need(now>=self.prior and cpu>=self.prior_cpu,'CLOCK_REGRESSION')
        self.prior=now;self.prior_cpu=cpu
        need(now-self.started<CAPS['wall_seconds'] and cpu-self.initial_cpu<CAPS['CPU_seconds'],'STAGE_RESOURCE_LIMIT')
    def begin(self,kind):
        self.check();key=kind+'_GET'
        need(self.attempts['GET']<CAPS['GET'] and self.attempts[key]<CAPS[key] and self.held==0,'REQUEST_CAP')
        cap=min(CAPS[kind+'_each'],CAPS[kind+'_total']-self.bytes[kind],CAPS['network_total']-sum(self.bytes.values()))
        need(cap>1,'BODY_CAP');self.attempts['GET']+=1;self.attempts[key]+=1;self.held=cap;return cap
    def settle(self,kind,size=None):
        self.bytes[kind]+=self.held if size is None else size;self.held=0
    def record(self):return {'attempts':dict(self.attempts),'body_bytes_charged':dict(self.bytes),'outstanding_body_hold':self.held}


class HTTPTransport:
    """No redirects/retries/proxies/authorization; stdlib TLS only."""
    def open(self,url,timeout):
        part=urlsplit(url);conn=http.client.HTTPSConnection(part.hostname,443,timeout=timeout,context=ssl.create_default_context())
        response=None
        try:
            conn.request('GET',part.path+('?' + part.query if part.query else ''),headers={
                'User-Agent':'SyntheticSocietyLab-P1/1','Accept-Encoding':'identity',
                'X-GitHub-Api-Version':'2026-03-10',
                'Accept':'application/vnd.pypi.integrity.v1+json' if url==PROVENANCE else 'application/vnd.github+json' if part.hostname=='api.github.com' else 'application/json,application/octet-stream'})
            response=conn.getresponse();return HTTPResponse(conn,response)
        except BaseException:
            if response is not None:response.close()
            conn.close();raise
class HTTPResponse:
    def __init__(self,connection,response):
        self.connection=connection;self.response=response;self.status=response.status;self.headers={}
        for key,value in response.getheaders():
            key=key.lower()
            need(key not in self.headers or key not in {'content-length','content-type','content-encoding','date','age','link'},'DUPLICATE_HTTP_HEADER')
            self.headers[key]=value
    def read(self,size,timeout):
        if self.connection.sock is not None:self.connection.sock.settimeout(timeout)
        return self.response.read(size)
    def close(self):self.response.close();self.connection.close()


class Collector:
    def __init__(self,root,methods,transport,*,clock=time.monotonic,cpu=time.process_time,utc=lambda:datetime.now(timezone.utc),signals=False):
        self.root=Path(root).absolute();self.methods=methods;self.transport=transport;self.budget=Budget(clock,cpu);self.utc=utc;self.signals=signals
        self.scope=self.root/OUTPUT;self.written=self.control=0;self.events=0;self.refs=[];self.phase='START';self.current_request=None
    def write(self,name,body,control=True):
        if name!='TERMINAL.json':self.budget.check()
        need(type(body) is bytes and self.written+len(body)+(0 if name=='TERMINAL.json' else 32768)<=CAPS['owned_write_bytes'],'WRITE_CAP')
        if control:need(self.control+len(body)+(0 if name=='TERMINAL.json' else 32768)<=CAPS['control_write_bytes'],'CONTROL_CAP')
        self.written+=len(body);self.control+=len(body) if control else 0
        path=self.scope/name;need(path.is_relative_to(self.scope) and not any(p.is_symlink() for p in (path,*path.parents)),'OUTPUT_ALIAS')
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as out:need(out.write(body)==len(body),'SHORT_WRITE');out.flush();os.fsync(out.fileno())
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
        ref={'path':name,'bytes':len(body),'sha256':sha(body)};self.refs.append(ref);return ref
    def event(self,kind,details):
        need(self.events<CAPS['journal_events'],'JOURNAL_CAP');self.events+=1
        self.write('events/'+str(self.events).zfill(2)+'.json',packed({'sequence':self.events,'kind':kind,**details}))
    def fetch(self,url,kind,name,filename=None):
        validate_url(url,kind,filename);cap=self.budget.begin(kind);started=self.budget.clock();self.current_request={'url':url,'kind':kind,'cap':cap}
        self.event('REQUEST_RESERVED',{**self.current_request,'budget':self.budget.record()});response=None;body=bytearray()
        def remaining():
            self.budget.check();left=min(CAPS['request_seconds']-(self.budget.clock()-started),CAPS['wall_seconds']-(self.budget.clock()-self.budget.started))
            need(left>0,'REQUEST_TIMEOUT');return left
        try:
            if self.signals:signal.setitimer(signal.ITIMER_REAL,remaining())
            response=self.transport.open(url,remaining());headers=response.headers
            need(type(headers) is dict and all(type(k) is str and type(v) is str for k,v in headers.items()),'HTTP_HEADER_SCHEMA')
            need(type(response.status) is int,'HTTP_STATUS_SCHEMA');self.current_request['HTTP_status']=response.status
            need(response.status==200,'HTTP_STATUS');need(headers.get('content-encoding','identity')=='identity','CONTENT_ENCODING')
            media=headers.get('content-type','').split(';')[0].strip().lower()
            need(media in ({'application/json','application/vnd.pypi.integrity.v1+json'} if kind=='metadata' else {'application/octet-stream','application/zip'}),'CONTENT_TYPE')
            try:served=parsedate_to_datetime(headers.get('date',''))
            except (ValueError,TypeError):raise Refused('HTTP_DATE') from None
            need(served is not None and served.tzinfo is not None and abs((self.utc()-served).total_seconds())<=300,'HTTP_FRESHNESS')
            age=headers.get('age','0');need(re.fullmatch('[0-9]+',age) is not None and int(age)<=3600,'HTTP_FRESHNESS')
            length=headers.get('content-length')
            if length is not None:need(re.fullmatch('[0-9]+',length) is not None and int(length)<cap,'CONTENT_LENGTH')
            body=bytearray()
            while True:
                requested=min(65536,cap-len(body));chunk=response.read(requested,remaining())
                need(type(chunk) is bytes and len(chunk)<=requested,'TRANSPORT_SCHEMA')
                if not chunk:break
                body.extend(chunk);need(len(body)<cap,'BODY_CAP')
            remaining()
            if length is not None:need(len(body)==int(length),'CONTENT_LENGTH')
            body=bytes(body);ref=self.write(name,body,False);self.budget.settle(kind,len(body));self.current_request=None
            self.event('RESPONSE_RECORDED',{'url':url,'ref':ref,'budget':self.budget.record()});return body,headers,ref
        except BaseException:
            if self.current_request is not None:
                self.current_request.update(observed_partial_body_bytes=len(body),partial_body_sha256=sha(bytes(body)))
            if self.budget.held:self.budget.settle(kind)
            raise
        finally:
            if response is not None:response.close()
            if self.signals:signal.setitimer(signal.ITIMER_REAL,max(.001,CAPS['wall_seconds']-(self.budget.clock()-self.budget.started)))
    def run(self):
        need(self.methods.get('kind')=='E01_PYPDF701_ACQUISITION_METHODS_V1' and self.methods.get('versions')==VERSIONS
             and self.methods.get('caps')==CAPS and self.methods.get('target')==TARGET and self.methods.get('output')==OUTPUT
             and self.methods.get('root_sha256')==sha(str(self.root).encode()),'METHODS_IDENTITY')
        need(not any(p.is_symlink() for p in (self.scope,*self.scope.parents)),'OUTPUT_ALIAS')
        self.scope.parent.mkdir(parents=True,exist_ok=True,mode=0o700);self.scope.mkdir(mode=0o700,exist_ok=False)
        parent_fd=os.open(self.scope.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(parent_fd)
        finally:os.close(parent_fd)
        self.write('STARTED.json',packed({'kind':'P1_STARTED_NO_RETRY','methods_sha256':sha(packed(self.methods)),
            'root_sha256':sha(str(self.root).encode()),'code_sha256':sha(Path(__file__).read_bytes()),'caps':CAPS,'time_utc':self.utc().isoformat(),'no_retry':True}))
        status='FAILED_OR_UNKNOWN_NO_RETRY';reason=None;lock_ref=None
        try:
            self.phase='PACKAGE_METADATA';selected=[]
            for name,ver in VERSIONS.items():
                raw,_,ref=self.fetch(f'https://pypi.org/pypi/{name}/{ver}/json','metadata','metadata/'+name+'.json')
                item=select_wheel(name,json_body(raw));item['metadata_ref']=ref;selected.append(item)
            self.phase='ADVISORIES';pages=[]
            advisory_url=API
            for page in (1,2):
                raw,headers,_=self.fetch(advisory_url,'metadata','metadata/advisories-'+str(page)+'.json')
                rows=json_body(raw);pages.append(rows);next_url=next_advisory(headers,rows,page)
                if next_url is None:break
                advisory_url=next_url
            assessment=assess_advisories(pages);self.write('advisory-assessment.json',packed(assessment))
            need(assessment['status']!='BLOCKED_APPLICABLE_ADVISORY','APPLICABLE_ADVISORY')
            self.phase='PROVENANCE';raw,_,ref=self.fetch(PROVENANCE,'metadata','metadata/pypdf-provenance.json')
            proof=provenance_binding(json_body(raw));self.write('selected.prepared.json',packed({'candidate':'7.0.1','wheels':selected,'provenance_ref':ref,'provenance_scope':proof,'ready_for_install':False}))
            self.phase='WHEELS';entries=inflated=0
            for item in selected:
                raw,_,ref=self.fetch(item['url'],'wheel','wheels/'+item['filename'],item['filename'])
                need(len(raw)==item['size'] and sha(raw)==item['sha256'],'WHEEL_IDENTITY')
                self.budget.check();inspection=inspect_wheel(raw,item['name'],item['filename'],self.budget,CAPS['ZIP_entries']-entries,CAPS['ZIP_uncompressed_bytes']-inflated);self.budget.check()
                entries+=inspection['entries'];inflated+=inspection['uncompressed_bytes']
                need(entries<=CAPS['ZIP_entries'] and inflated<=CAPS['ZIP_uncompressed_bytes'],'ZIP_AGGREGATE_CAP')
                item.update(artifact_ref=ref,inspection=inspection)
            lock={'kind':'P1_FIVE_WHEEL_HASHLOCK_V1','schema_version':1,'methods_sha256':sha(packed(self.methods)),'target':TARGET,'wheels':selected,'advisory_assessment_sha256':sha(packed(assessment)),
                  'provenance_scope':proof,'not_latest':True,'ready_for_install':False,'qualification_or_source_authority':False}
            lock_ref=self.write('hashlock.json',packed(lock));status='ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION'
        except BaseException as exc:
            reason=str(exc) if type(exc) is Refused else type(exc).__name__
        finally:
            self.write('TERMINAL.json',packed({'kind':'P1_TERMINAL_V1','status':status,'phase':self.phase,'reason':reason,'budget':self.budget.record(),
                'current_request':self.current_request,'artifacts':self.refs,'no_retry':True,'model_calls':0,'cost_usd':0,
                'installation':False,'package_imports':False,'extraction':False,'source_or_campaign_authority':False}))
        return {'status':status,'scope':str(self.scope),'reason':reason,'budget':self.budget.record(),'hashlock_ref':lock_ref,'model_calls':0,'cost_usd':0}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--methods-sha256',required=True);args=parser.parse_args()
    root=Path.cwd().absolute();path=root/METHODS
    need(not any(p.is_symlink() for p in (path,*path.parents)) and stat.S_ISREG(path.stat().st_mode)
         and path.stat().st_size<=65536,'METHODS_SIZE_OR_ALIAS')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as source:raw=source.read(65537)
    need(len(raw)<=65536 and sha(raw)==args.methods_sha256,'METHODS_HASH')
    methods=json_body(raw);need(raw==packed(methods),'METHODS_NONCANONICAL');resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(59,60))
    def deadline(*_):raise Refused('DEADLINE_SIGNAL')
    signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline);signal.setitimer(signal.ITIMER_REAL,CAPS['wall_seconds'])
    result=Collector(root,methods,HTTPTransport(),signals=True).run();signal.setitimer(signal.ITIMER_REAL,0)
    print(packed(result).decode());return 0 if result['status'].startswith('ACQUISITION_COMPLETE') else 1
if __name__=='__main__':raise SystemExit(main())
