"""Once-only source acquisition; never import/extract/execute installer code."""
import ast
import base64
import csv
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import stat
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).absolute().parents[1]
SCOPE = 'data/processed/e01_installer_tool_source_v1_20261116'
GATE = 'reports/E01_PYPA_INSTALLER_SOURCE_GATE_20261116.json'
LIMITS = {'CPU_seconds':20, 'archive_declared_uncompressed_bytes':8388608,
    'archive_entries':1024, 'combined_http_body_bytes':2097152,
    'console_bytes':32768, 'each_http_body_bytes':1048576,
    'fetch_and_static_validation_wall_seconds':60, 'per_request_timeout_seconds':15,
    'single_archive_member_bytes':1048576, 'source_scope_write_bytes':4194304}
REVIEW = {'path':'reports/INDEPENDENT_AUDIT_E01_OFFLINE_INSTALLER_ROUTE_FEASIBILITY_20261116.json',
    'bytes':15228,'sha256':'9edbf3a1b5d0073e665ce837445afc2e7b3e09b0e1814ac39e9873c233edd218'}


class Refused(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(value, code):
    if not value: raise Refused(code)


def packed(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(raw): return hashlib.sha256(raw).hexdigest()


def no_alias(path):
    need(not any(p.is_symlink() for p in (path,*path.parents)), 'SOURCE_PATH_ALIAS')


def json_body(raw):
    def pairs(items):
        result = {}
        for key,value in items:
            need(key not in result,'SOURCE_JSON_DUPLICATE')
            result[key] = value
        return result
    def constant(_): raise Refused('SOURCE_JSON_CONSTANT')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)


def compatible(spec):
    need(type(spec) is str and 0 < len(spec) <= 256,'SOURCE_REQUIRES_PYTHON_UNKNOWN')
    terms = spec.split(',')
    need(1 <= len(terms) <= 8,'SOURCE_REQUIRES_PYTHON_UNKNOWN')
    for version in ((3,11,17),(3,12,14)):
        for term in terms:
            match = re.fullmatch(r'\s*(>=|<=|==|!=|>|<)\s*([0-9]+(?:\.[0-9]+){0,2})\s*',term)
            need(match is not None,'SOURCE_REQUIRES_PYTHON_UNSUPPORTED')
            bound = tuple(int(x) for x in match[2].split('.'))
            bound += (0,)*(3-len(bound))
            op = match[1]
            need({'<':version<bound,'>':version>bound,'<=':version<=bound,
                  '>=':version>=bound,'==':version==bound,'!=':version!=bound}[op],
                 'SOURCE_PYTHON_INCOMPATIBLE')
    return spec


def select(metadata):
    info,urls = metadata.get('info'),metadata.get('urls')
    need(type(info) is dict and info.get('name','').lower() == 'installer'
         and type(urls) is list and len(urls) <= 1024,'SOURCE_PROJECT_METADATA')
    version = info.get('version')
    need(type(version) is str and re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}',version),
         'SOURCE_LATEST_STABLE_AMBIGUOUS')
    requires = compatible(info.get('requires_python'))
    pattern = 'installer-'+re.escape(version)+r'-(?:[0-9][A-Za-z0-9_.]*-)?py3-none-any\.whl'
    wheels = [item for item in urls if type(item) is dict
        and item.get('packagetype') == 'bdist_wheel'
        and type(item.get('filename')) is str and re.fullmatch(pattern,item['filename'])
        and item.get('yanked') is False]
    need(len(wheels) == 1,'SOURCE_WHEEL_SELECTION_AMBIGUOUS')
    item = wheels[0]
    filename = item['filename']
    need(item.get('python_version') == 'py3','SOURCE_WHEEL_PYTHON_TAG')
    compatible(item.get('requires_python'))
    size,hash_value,url = item.get('size'),item.get('digests',{}).get('sha256'),item.get('url')
    need(type(size) is int and 0 < size <= LIMITS['each_http_body_bytes']
         and type(hash_value) is str and re.fullmatch('[0-9a-f]{64}',hash_value),
         'SOURCE_WHEEL_SIZE_HASH')
    need(type(url) is str and len(url) <= 2048,'SOURCE_WHEEL_URL')
    parts = urllib.parse.urlsplit(url)
    need(parts.scheme == 'https' and parts.netloc == 'files.pythonhosted.org'
         and parts.username is None and parts.password is None and not parts.query
         and not parts.fragment and parts.path.endswith('/'+filename), 'SOURCE_WHEEL_HOST')
    return {'name':'installer','version':version,'requires_python':requires,
        'file_requires_python':item['requires_python'],'filename':filename,
        'size':size,'sha256':hash_value,'url':url,'yanked':False}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None


class Acquisition:
    def __init__(self):
        self.started = time.monotonic()
        self.scope = ROOT/SCOPE
        self.phase = 'GATE_CHECK'
        self.writes = self.body_bytes = 0
        self.requests = []
        self.artifacts = []
    def check(self):
        need(time.monotonic()-self.started < 60,'SOURCE_WALL_LIMIT')
        usage = resource.getrusage(resource.RUSAGE_SELF)
        need(usage.ru_utime+usage.ru_stime < 20,'SOURCE_CPU_LIMIT')
    def save(self,name,value):
        need(type(name) is str and re.fullmatch('[A-Za-z0-9_.-]{1,80}',name), 'SOURCE_OUTPUT_NAME')
        raw = value if type(value) is bytes else packed(value)
        # Preserve64KiB terminal headroom on every preceding write.
        reserve = 0 if name == 'TERMINAL.json' else 65536
        need(self.writes+len(raw)+reserve <= 4194304,'SOURCE_WRITE_CAP')
        path = self.scope/name
        no_alias(path)
        fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        self.writes += len(raw)
        with os.fdopen(fd,'wb') as stream:
            need(stream.write(raw)==len(raw),'SOURCE_SHORT_WRITE');stream.flush();os.fsync(stream.fileno())
        fd = os.open(self.scope,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        ref = {'path':name,'bytes':len(raw),'sha256':digest(raw)}
        self.artifacts.append(ref)
        return ref
    def fetch(self,url,number,expected=None):
        self.check()
        need(number == len(self.requests)+1 and number <= 2,'SOURCE_REQUEST_CAP')
        record = {'number':number,'url':url,'method':'GET','status':None,
                  'body_bytes':0,'redirects_allowed':0,'retries_allowed':0}
        self.requests.append(record)
        self.save(str(number)+'-REQUEST_RESERVED.json',dict(record))
        body = bytearray()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        request = urllib.request.Request(url,headers={'Accept-Encoding':'identity',
            'User-Agent':'SyntheticSocietyLab-source-inspection/1','Accept':'application/json' if number==1 else 'application/octet-stream'})
        try:
            try:
                response = opener.open(request,timeout=15)
            except urllib.error.HTTPError as error:
                record['status'] = error.code if type(error.code) is int and 100 <= error.code <= 599 else None
                error.close()
                raise Refused('SOURCE_HTTP_STATUS') from None
            with response:
                record['status'] = response.status
                need(response.status == 200 and response.geturl() == url,'SOURCE_HTTP_IDENTITY')
                length = response.headers.get('Content-Length')
                need(type(length) is str and re.fullmatch('[0-9]{1,8}',length), 'SOURCE_CONTENT_LENGTH_REQUIRED')
                length = int(length)
                need(0 < length <= 1048576 and self.body_bytes+length <= 2097152,'SOURCE_HTTP_BODY_CAP')
                if expected is not None: need(length == expected,'SOURCE_HTTP_BOUND_SIZE')
                need(response.headers.get('Content-Encoding','identity').lower() == 'identity', 'SOURCE_HTTP_ENCODING')
                media = response.headers.get_content_type()
                need(media == 'application/json' if number==1 else media in {'application/octet-stream','application/zip'},
                     'SOURCE_HTTP_MEDIA')
                record['content_type'],record['content_length'] = media,length
                while len(body)<length:
                    self.check()
                    chunk = response.read(min(65536,length-len(body)))
                    need(chunk,'SOURCE_HTTP_TRUNCATED')
                    body.extend(chunk);self.body_bytes += len(chunk);record['body_bytes'] += len(chunk)
                    need(len(body) <= length and self.body_bytes <= 2097152,'SOURCE_HTTP_BODY_CAP')
            record['body_sha256'] = digest(body)
            self.save(str(number)+'-RESPONSE.bin',bytes(body))
            return bytes(body)
        except BaseException:
            if body:
                record['partial_body_ref'] = self.save(str(number)+'-PARTIAL.bin',bytes(body))
            raise
        finally:
            self.save(str(number)+'-REQUEST_RESULT.json',dict(record))


def inspect_archive(raw, selected, owner):
    owner.phase = 'ZIP_DIRECTORY'
    need(len(raw) == selected['size'] and digest(raw) == selected['sha256'], 'SOURCE_ARCHIVE_HASH')
    end = raw.rfind(b'PK\x05\x06',max(0,len(raw)-65557))
    need(end>=0 and end+22<=len(raw),'SOURCE_ZIP_EOCD')
    disk,cd_disk,count_disk,count,cd_size,offset,comment = struct.unpack_from('<4H2IH',raw,end+4)
    need(disk==cd_disk==0 and count_disk==count and 0<count<=1024
         and end+22+comment==len(raw) and offset+cd_size==end,'SOURCE_ZIP_LAYOUT')
    cursor,seen = offset,0
    while cursor<offset+cd_size:
        need(raw[cursor:cursor+4]==b'PK\x01\x02' and cursor+46<=end,'SOURCE_ZIP_DIRECTORY')
        n,e,c = struct.unpack_from('<3H',raw,cursor+28)
        cursor += 46+n+e+c; seen += 1
        need(cursor<=end and seen<=1024,'SOURCE_ZIP_DIRECTORY')
    need(cursor==end and seen==count,'SOURCE_ZIP_DIRECTORY')
    bodies,refs,folded = {},{},set()
    declared = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        need(len(infos)==count,'SOURCE_ZIP_DIRECTORY')
        for info in infos:
            owner.check()
            name = info.filename
            clean = name[:-1] if info.is_dir() else name
            need(name==info.orig_filename and 0<len(name.encode())<=240
                 and all(32<=ord(c)<127 for c in name) and not name.startswith('/')
                 and '\\' not in name and ':' not in name
                 and all(part not in {'','.','..'} for part in clean.split('/')),
                 'SOURCE_ZIP_PATH')
            need(clean.casefold() not in folded,'SOURCE_ZIP_DUPLICATE')
            folded.add(clean.casefold())
            kind = stat.S_IFMT(info.external_attr>>16)
            need(kind in {0,stat.S_IFREG,stat.S_IFDIR} and not info.flag_bits&1
                 and info.compress_type in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED},
                 'SOURCE_ZIP_SPECIAL_ENTRY')
            need(not (kind==stat.S_IFDIR and not info.is_dir())
                 and not (kind==stat.S_IFREG and info.is_dir()),'SOURCE_ZIP_TYPE_ALIAS')
            need(0<=info.file_size<=1048576,'SOURCE_MEMBER_CAP')
            declared += info.file_size
            need(declared<=8388608,'SOURCE_INFLATION_CAP')
        for info in infos:
            owner.check()
            with archive.open(info) as stream:
                body = bytearray()
                while len(body)<info.file_size:
                    owner.check()
                    part = stream.read(min(65536,info.file_size-len(body)))
                    need(part,'SOURCE_MEMBER_TRUNCATED');body.extend(part)
                need(stream.read(1)==b'','SOURCE_MEMBER_SIZE')
            need(len(body)==info.file_size,'SOURCE_MEMBER_SIZE')
            if not info.is_dir():
                bodies[info.filename] = bytes(body)
                refs[info.filename] = {'bytes':len(body),'sha256':digest(body)}
    for name in bodies:
        parts = name.split('/')
        need(not any('/'.join(parts[:i]) in bodies for i in range(1,len(parts))),
             'SOURCE_ZIP_FILE_PARENT_ALIAS')
    dist = 'installer-'+selected['version']+'.dist-info/'
    need({name.split('/')[0]+'/' for name in bodies if '.dist-info/' in name}=={dist},
         'SOURCE_DIST_INFO_IDENTITY')
    need(all(dist+name in bodies for name in ('METADATA','WHEEL','RECORD')),'SOURCE_METADATA_MISSING')
    owner.phase = 'RECORD_VERIFY'
    reader = csv.reader(io.StringIO(bodies[dist+'RECORD'].decode('utf-8'),newline=''))
    records = {}
    for row in reader:
        owner.check()
        need(len(row)==3 and row[0] not in records and row[0] in bodies,'SOURCE_RECORD_MEMBERSHIP')
        name,hash_text,size_text = row
        if name==dist+'RECORD':
            need(hash_text==size_text=='','SOURCE_RECORD_SELF_EXCEPTION')
        else:
            need(type(size_text) is str and re.fullmatch(r'0|[1-9][0-9]{0,9}',size_text)
                 and int(size_text)==refs[name]['bytes'],'SOURCE_RECORD_SIZE')
            expected = 'sha256='+base64.urlsafe_b64encode(bytes.fromhex(refs[name]['sha256'])).rstrip(b'=').decode()
            need(hash_text==expected,'SOURCE_RECORD_HASH')
        records[name] = True
    need(set(records)==set(bodies),'SOURCE_RECORD_COVERAGE')
    owner.phase = 'METADATA_VERIFY'
    metadata = BytesParser().parsebytes(bodies[dist+'METADATA'])
    wheel = BytesParser().parsebytes(bodies[dist+'WHEEL'])
    need(all(len(metadata.get_all(key,[]))==1 for key in ('Name','Version','Requires-Python'))
         and metadata['Name'].lower()=='installer' and metadata['Version']==selected['version'],
         'SOURCE_METADATA_IDENTITY')
    compatible(metadata['Requires-Python'])
    need(wheel.get_all('Wheel-Version')==['1.0'] and wheel.get_all('Root-Is-Purelib')==['true']
         and wheel.get_all('Tag')==['py3-none-any'],'SOURCE_WHEEL_TAGS')
    dependencies = metadata.get_all('Requires-Dist',[])
    need(len(dependencies)<=64 and all(len(item)<=2048 for item in dependencies),'SOURCE_DEPENDENCY_BOUNDS')
    license_refs = {name:ref for name,ref in refs.items() if name.startswith(dist)
        and Path(name).name.lower().startswith(('license','copying','notice'))}
    owner.phase = 'AST_INSPECT'
    python_sources,imports,api,risky_calls = {},{},{},{}
    wanted = {'install','validate_record','get_contents','write_to_fs','write_file',
              'write_script','finalize_installation','generate','_main','main'}
    node_total = 0
    for name,body in bodies.items():
        if not name.endswith('.py'):continue
        owner.check()
        tree = ast.parse(body,filename='STATIC_TOOL_SOURCE_ONLY')
        nodes = list(ast.walk(tree));node_total+=len(nodes)
        need(node_total<=100000,'SOURCE_AST_NODE_CAP')
        python_sources[name] = refs[name]
        imports[name] = []
        for node in nodes:
            if isinstance(node,ast.Import):
                imports[name].extend({'module':item.name,'alias':item.asname,'level':0} for item in node.names)
            elif isinstance(node,ast.ImportFrom):
                imports[name].append({'module':node.module,'level':node.level,
                    'names':[item.name for item in node.names]})
            elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in wanted:
                arguments = ast.unparse(node.args)
                calls = sorted({ast.unparse(item.func) for item in ast.walk(node) if isinstance(item,ast.Call)})
                api.setdefault(name,[]).append({'name':node.name,'line':node.lineno,'end_line':node.end_lineno,
                    'arguments':arguments[:1024],'arguments_truncated':len(arguments)>1024,
                    'calls':[item[:256] for item in calls[:128]],'full_distinct_call_count':len(calls),
                    'calls_truncated':len(calls)>128 or any(len(item)>256 for item in calls)})
            elif isinstance(node,ast.Call):
                target = ast.unparse(node.func)
                if target in {'exec','eval','__import__','compile','os.system'} or target.startswith(
                        ('socket.','subprocess.','ctypes.','urllib.','requests.','importlib.import_module','compileall.')):
                    risky_calls.setdefault(name,[]).append({'line':node.lineno,'callee':target[:256]})
    return {'kind':'SOURCE_ONLY_INSTALLER_ARCHIVE_INTEGRITY_AND_AST_V1','selected':selected,
        'archive_entries':count,'declared_uncompressed_bytes':declared,
        'member_refs':refs,'record_coverage_files':len(records),'record_hash_algorithm':'sha256',
        'record_self_exception':{'path':dist+'RECORD','hash':'','size':''},
        'other_record_exceptions':[],
        'metadata':{'name':metadata['Name'],'version':metadata['Version'],
            'requires_python':metadata['Requires-Python'],'requires_dist':dependencies,
            'license':metadata.get('License'),'license_expression':metadata.get('License-Expression'),
            'license_classifiers':[value for value in metadata.get_all('Classifier',[]) if value.startswith('License')],
            'license_refs':license_refs},
        'python_source_refs':python_sources,'imports_syntax_only':imports,
        'selected_API_syntax_only':api,'selected_risky_calls_syntax_only':risky_calls,
        'AST_nodes':node_total,'extracted_files':0,'package_imports_or_execution':0,
        'limitations':['AST names/calls are not resolved import closure or execution proof.',
            'Per-member archive integrity and declared compatibility do not qualify tool code or runtime/P3.',
            'All package bytes stayed in memory or the immutable wheel; no executable extraction.']}


def closed_type(error):
    for cls,label in ((Refused,'SOURCE_REFUSED'),(urllib.error.URLError,'URL_ERROR'),
            (TimeoutError,'TIMEOUT_ERROR'),(zipfile.BadZipFile,'BAD_ZIP_FILE'),
            (SyntaxError,'SYNTAX_ERROR'),(UnicodeDecodeError,'UNICODE_DECODE_ERROR'),
            (ValueError,'VALUE_ERROR'),(OSError,'OS_ERROR'),(KeyError,'KEY_ERROR'),
            (MemoryError,'MEMORY_ERROR'),(RecursionError,'RECURSION_ERROR')):
        if type(error) is cls:return label
    return 'UNKNOWN_ERROR_TYPE'


def main():
    owner = Acquisition()
    def wall(*_):raise Refused('SOURCE_WALL_LIMIT')
    def cpu(*_):raise Refused('SOURCE_CPU_LIMIT')
    signal.signal(signal.SIGALRM,wall);signal.signal(signal.SIGXCPU,cpu)
    signal.setitimer(signal.ITIMER_REAL,60)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(19,20))
    no_alias(ROOT/GATE);raw_gate=(ROOT/GATE).read_bytes()
    need(len(raw_gate)<=65536,'SOURCE_GATE_SIZE')
    gate=json_body(raw_gate)
    need(gate.get('kind')=='LEAD_FINITE_PYPA_INSTALLER_SOURCE_ONLY_ACQUISITION_GATE'
         and gate.get('scope')==SCOPE and gate.get('limits')==LIMITS
         and gate.get('maximum_requests')==2 and gate.get('redirects')==gate.get('retries')==0
         and gate.get('prerequisite_review_ref')==REVIEW
         and gate.get('installation_allocation_unchanged_fully_consumed')=={
             'main_children':12,'observed_CPU_seconds':180,'wall_seconds':450},'SOURCE_GATE_IDENTITY')
    no_alias(ROOT/REVIEW['path']);review_raw=(ROOT/REVIEW['path']).read_bytes()
    need(len(review_raw)==REVIEW['bytes'] and digest(review_raw)==REVIEW['sha256'], 'SOURCE_REVIEW_HASH')
    review=json_body(review_raw)
    need(type(review.get('status')) is str and review['status'].startswith('PASS'),'SOURCE_REVIEW_NOT_PASS')
    no_alias(owner.scope);need(not owner.scope.exists(),'SOURCE_SCOPE_ALREADY_CONSUMED')
    owner.scope.mkdir(mode=0o700,exist_ok=False)
    fd=os.open(owner.scope.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    owner.save('STARTED.json',{'kind':'INSTALLER_TOOL_SOURCE_STARTED_NO_RETRY',
        'UTC':datetime.now(timezone.utc).isoformat(),'gate_sha256':digest(raw_gate),
        'helper_sha256':digest(Path(__file__).read_bytes()),'review_ref':REVIEW,'limits':LIMITS,
        'package_execution':False,'no_retry':True,'actual_installation_allocation_change':0})
    status,error,selection,analysis_ref='FAILED_SOURCE_ONLY',None,None,None
    try:
        owner.phase='PYPI_METADATA_GET'
        raw=owner.fetch('https://pypi.org/pypi/installer/json',1)
        owner.phase='WHEEL_SELECT'
        selection=select(json_body(raw));owner.save('SELECTED.json',selection)
        owner.phase='PINNED_WHEEL_GET'
        raw=owner.fetch(selection['url'],2,selection['size'])
        analysis=inspect_archive(raw,selection,owner)
        analysis_ref=owner.save('SOURCE_ANALYSIS.json',analysis)
        owner.check();status='SOURCE_ACQUIRED_STATIC_INTEGRITY_ONLY'
    except BaseException as exc:
        error={'phase':owner.phase,'type':closed_type(exc),
            'code':exc.code if type(exc) is Refused else 'SOURCE_UNCLASSIFIED_ERROR',
            'HTTP_status':owner.requests[-1].get('status') if owner.requests else None}
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        usage=resource.getrusage(resource.RUSAGE_SELF)
        terminal={'kind':'INSTALLER_TOOL_SOURCE_TERMINAL_NO_RETRY','status':status,'error':error,
            'UTC':datetime.now(timezone.utc).isoformat(),'phase':owner.phase,'selection':selection,
            'analysis_ref':analysis_ref,'requests':owner.requests,'HTTP_body_bytes':owner.body_bytes,
            'source_scope_write_bytes_before_terminal':owner.writes,'artifacts':owner.artifacts,
            'elapsed_fetch_static_seconds':time.monotonic()-owner.started,
            'observed_CPU_seconds':usage.ru_utime+usage.ru_stime,'limits':LIMITS,
            'no_retry':True,'cost_USD':0,'package_imports_or_execution':0,'extracted_files':0,
            'new_installation_children':0,'installation_or_runtime_or_P3_accepted':False,
            'installation_allocation_fully_consumed_unchanged':{'wall_seconds':450,'observed_CPU_seconds':180,'main_children':12}}
        terminal_ref=owner.save('TERMINAL.json',terminal)
        output=packed({'status':status,'error':error,'selection_version':selection['version'] if selection else None,
            'requests':len(owner.requests),'HTTP_body_bytes':owner.body_bytes,'source_scope_write_bytes':owner.writes,
            'terminal_ref':terminal_ref,'cost_USD':0})
        need(len(output)<=32768,'SOURCE_CONSOLE_CAP')
        print(output.decode())
    return 0 if status=='SOURCE_ACQUIRED_STATIC_INTEGRITY_ONLY' else 1


if __name__=='__main__':
    try: result=main()
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        print(packed({'status':'REFUSED_NO_FALLBACK','phase':'GATE_OR_SCOPE_ENTRY',
            'type':closed_type(error),'code':error.code if type(error) is Refused else 'SOURCE_ENTRY_ERROR'}).decode())
        result=1
    raise SystemExit(result)
