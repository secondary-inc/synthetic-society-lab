"""One archive-only source preflight, no reader or numeric adoption."""
from pathlib import Path
import resource,signal,time,sys,os,json,hashlib,sysconfig
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(59,60));signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(60)
root=Path.cwd();sys.path.insert(0,str(root/'src'));start=time.monotonic()
from civiclab.e01 import fec2020_parser_v1 as p
source=root/'data/raw/e01_fec2020_workbook_20261118/federalelections2020.xlsx';used=0;member_reads=[]
def charge(n):
 global used
 used+=n;assert used<=67108864
stdlib=Path(sysconfig.get_path('stdlib')).resolve()
def audit(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','sqlite3.connect','ctypes.dlopen'):raise RuntimeError('NO_NETWORK_PROCESS_OWNER')
 if event=='open' and not isinstance(args[0],int):
  path=Path(args[0]).resolve();assert not args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND);assert path==source or path.is_relative_to(stdlib)
sys.addaudithook(audit)
raw=source.read_bytes();charge(len(raw));assert len(raw)==6251110 and hashlib.sha256(raw).hexdigest()=='5073b6d2c76c86c941508dfb1a11cc497e8529b0068c5132aceb0f385c19352e'
original=p.zipfile.ZipFile.read
def metered(self,item,*a,**kw):
 b=original(self,item,*a,**kw);charge(len(b));member_reads.append((item.filename,len(b)));return b
p.zipfile.ZipFile.read=metered
result=p.archive_preflight(raw)
assert result=={'members':65,'declared_expanded_bytes':51902709}
assert len(member_reads)==65 and max(n for _,n in member_reads)==41139508
assert 'openpyxl' not in sys.modules
print(json.dumps({'kind':'INDEPENDENT_FEC_V1_3_SOURCE_ARCHIVE_PREFLIGHT','status':'PASS_ARCHIVE_ONLY','source_bytes':len(raw),'source_sha256':hashlib.sha256(raw).hexdigest(),'archive':result,'member_reads':len(member_reads),'maximum_member_bytes':max(n for _,n in member_reads),'total_charged_source_plus_expanded_bytes':used,'CPU_seconds':sum(resource.getrusage(resource.RUSAGE_SELF)[:2]),'wall_seconds':time.monotonic()-start,'full_reader_numeric_cell_interpretation_or_adoption':0,'network_model_key_owner_calls':0,'cost_usd':0},sort_keys=True));signal.alarm(0)
