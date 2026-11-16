"""Independent in-memory pure-component probes; never tool/fixture installation."""
import sys

def deny(event,args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn','ctypes.dlopen'}:
        raise AssertionError('AUDITOR_NO_NETWORK_PROCESS_NATIVE')
    if event=='import' and args and args[0].split('.')[0] in {'pip','installer','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser','ssl_fixture_payload'}:
        raise AssertionError('AUDITOR_NO_TOOL_PAYLOAD_IMPORT')
sys.addaudithook(deny)
import base64,csv,hashlib,io,json,os,resource,signal,stat,struct,time,types,zipfile
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def timeout(*_):raise AssertionError('AUDITOR_PROBE_DEADLINE')
signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
ROOT=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab');SOURCE=ROOT/'scripts/e01_strict_wheel_source_candidate_v1_20261116.py';ME=Path(__file__).resolve();STDLIB=Path(sys.base_prefix)/'lib';read_bytes=[0]
def readonly(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.path.realpath(args[0]));flags=args[2]
        if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError('AUDITOR_NO_FILESYSTEM_WRITE')
        if not(p in {SOURCE,ME} or (p.is_relative_to(STDLIB) and 'site-packages' not in p.parts)):raise AssertionError('AUDITOR_UNAPPROVED_READ')
        try:size=p.stat().st_size
        except FileNotFoundError:size=0
        read_bytes[0]+=size+1
        if read_bytes[0]>67108864:raise AssertionError('AUDITOR_READ_CAP')
    if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.truncate','os.chmod'}:raise AssertionError('AUDITOR_NO_FILESYSTEM_MUTATION')
sys.addaudithook(readonly)
rawsource=SOURCE.read_bytes();source_sha=hashlib.sha256(rawsource).hexdigest();assert source_sha==sys.argv[1]
m=types.ModuleType('auditor_pure_strict_wheel');m.__file__=str(SOURCE);exec(compile(rawsource,str(SOURCE),'exec'),m.__dict__)
D='ssl_fixture_payload-1.0.0.dist-info/';P='ssl_fixture_payload/__init__.py';FN='ssl_fixture_payload-1.0.0-py3-none-any.whl'
def fixture(duplicate=False,orphan=False):
    data={P:b'raise AssertionError("DO_NOT_IMPORT_AUDITOR_PAYLOAD")\ndef main(): return 0\n',D+'METADATA':b'Metadata-Version: 2.1\nName: ssl_fixture_payload\nVersion: 1.0.0\nRequires-Python: >=3.10\n\n',D+'WHEEL':b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n',D+'entry_points.txt':b'[console_scripts]\nfixture-cli = ssl_fixture_payload:main\n'}
    rows=[[n,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(b).digest()).rstrip(b'=').decode(),str(len(b))] for n,b in sorted(data.items())]
    rows.append([D+'RECORD','',''])
    if duplicate:rows.append(rows[0][:])
    if orphan:rows.append(['not-in-archive','sha256='+'A'*43,'0'])
    t=io.StringIO(newline='');csv.writer(t,lineterminator='\n').writerows(rows);data[D+'RECORD']=t.getvalue().encode();zbuf=io.BytesIO()
    with zipfile.ZipFile(zbuf,'w',compression=zipfile.ZIP_STORED) as z:
        for name,body in sorted(data.items()):
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.external_attr=(stat.S_IFREG|0o644)<<16;z.writestr(info,body)
    return zbuf.getvalue(),data
checks=[]
def ok(name,value):assert value,name;checks.append(name)
def validate(raw,budget=None):return m.validate_wheel(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),filename=FN,budget=budget or m.ReadBudget(65536))
raw,data=fixture();budget=m.ReadBudget(65536);token=validate(raw,budget);ok('independent authored valid source',token.sha256==hashlib.sha256(raw).hexdigest() and token.filename==FN)
with token.open() as s:
    with zipfile.ZipFile(s) as z:
        ok('independent member oracle',{n:z.read(n) for n in z.namelist()}==data)
ok('manifest independent SHA256 oracle',dict((n,(size,h)) for n,size,h in token.members)==dict((n,(len(b),hashlib.sha256(b).hexdigest())) for n,b in data.items()))
a,b=token.open(),token.open();used=budget.used;ok('two streams independent cursor',a.read(7)==raw[:7] and b.read(5)==raw[:5] and a.tell()==7 and b.tell()==5 and budget.used-used==12);a.seek(0);dest=bytearray(9);ok('readinto copies outward only',a.readinto(dest)==9 and dest==raw[:9]);a.close();b.close()
for label,kw in [('duplicate RECORD',{'duplicate':True}),('orphan RECORD',{'orphan':True})]:
    bad,_=fixture(**kw)
    try:validate(bad);raise AssertionError(label+' admitted')
    except m.WheelRefused:checks.append(label+' independently refused')
# Corrupt actual member bytes without updating its CRC; preserve original parser exception.
corrupt=bytearray(raw);index=corrupt.index(data[P]);corrupt[index]^=1
try:validate(bytes(corrupt));raise AssertionError('CRC corruption admitted')
except zipfile.BadZipFile:checks.append('primary CRC exception unchanged')
# Preconstruction boundary: use a constructor spy, never parse an unsafe member.
eocd=raw.rfind(b'PK\x05\x06');cd=struct.unpack_from('<I',raw,eocd+16)[0];positions=[];cursor=cd
while cursor<eocd:
    positions.append(cursor);n,e,c=struct.unpack_from('<3H',raw,cursor+28);cursor+=46+n+e+c
mutations=[]
for label,offset,fmt,value in [('encrypted flags',8,'<H',1),('unsupported compression',10,'<H',12),('per-member inflation',24,'<I',8193),('compressed range',20,'<I',len(raw)+1),('multidisk member',34,'<H',1)]:
    bad=bytearray(raw);struct.pack_into(fmt,bad,cd+offset,value);mutations.append((label,bytes(bad)))
bad=bytearray(raw)
for pos in positions:struct.pack_into('<I',bad,pos+24,8192)
mutations.append(('aggregate inflation',bytes(bad)))
original=zipfile.ZipFile
for label,bad in mutations:
    calls=[]
    def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('UNSAFE_ZIP_CONSTRUCTOR_REACHED')
    zipfile.ZipFile=forbidden
    try:
        try:validate(bad);raise AssertionError(label+' admitted')
        except m.WheelRefused:pass
        ok(label+' refused before ZipFile',not calls)
    finally:zipfile.ZipFile=original
# Shared budget poisoning across all reopened streams, without private-state edits.
small=m.ReadBudget(32768);t=validate(raw,small);one=t.open();exhausted=False
for _ in range(100):
    try:one.getvalue()
    except m.WheelRefused:exhausted=True;break
ok('bounded repeated rereads exhaust budget',exhausted and small.failed and small.used<=small.limit)
for label,call in [('existing stream zero read',lambda:one.read(0)),('new token stream',t.open),('getvalue',one.getvalue)]:
    try:call();raise AssertionError(label+' bypasses failed budget')
    except m.WheelRefused:checks.append(label+' remains poisoned')
ok('returned bytes immutable',type(raw) is bytes and isinstance(token.members,tuple))
out={'kind':'INDEPENDENT_PURE_COMPONENT_ADVERSE_PROBE','status':'PASS','Python':sys.version.split()[0],'source_sha256':source_sha,'checks':len(checks),'names':checks,'authored_archive_sha256':hashlib.sha256(raw).hexdigest(),'budget_used_before_poisoning':budget.used,'poisoned_budget_used':small.used,'technical_read_bytes':read_bytes[0],'actual_tool_imports_install_calls_extractions_targets_network_owner_credential_actions':0};encoded=json.dumps(out,sort_keys=True);assert len(encoded.encode())<=262144;print(encoded);signal.setitimer(signal.ITIMER_REAL,0)
