"""One accepted V1.2 ZIP preflight; no optional reader or numeric extraction."""
from pathlib import Path
import hashlib
import json
import os
import re
import resource
import signal
import sys
import sysconfig
import time
import types
import zipfile

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'data/raw/e01_fec2020_workbook_20261118/federalelections2020.xlsx'
PARSER=ROOT/'src/civiclab/e01/fec2020_parser_v1.py'
SOURCE_SHA='5073b6d2c76c86c941508dfb1a11cc497e8529b0068c5132aceb0f385c19352e'
PARSER_SHA='0795e2012be6b0cd36bb7c2a4805320c773f654260bfd764f9ae039740c1a2dc'


def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(59,60))
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('diagnostic60seconds')))
    signal.setitimer(signal.ITIMER_REAL,60)
    start=time.monotonic();usage={'file_read_reservation_bytes':0,'inflated_member_bytes':0}
    stdlib=Path(sysconfig.get_path('stdlib')).resolve()
    def charge(k,n):
        usage[k]+=n
        if sum(usage.values())>67108864:raise RuntimeError('DIAGNOSTIC_READ_BOUND')
    def audit(event,args):
        if event.startswith('socket.') or event in ('subprocess.Popen','os.fork','os.system','os.posix_spawn','sqlite3.connect','ctypes.dlopen'):
            raise RuntimeError('DIAGNOSTIC_NO_EXTERNAL')
        if event=='open' and not isinstance(args[0],int):
            path=Path(os.fsdecode(args[0])).resolve();flags=args[2]
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise RuntimeError('NO_DISK_WRITES')
            if not(path in {SOURCE,PARSER} or path.is_relative_to(stdlib)):raise RuntimeError('DIAGNOSTIC_READ_SCOPE')
            if path.is_file():charge('file_read_reservation_bytes',path.stat().st_size)
    sys.addaudithook(audit)
    raw=PARSER.read_bytes()
    if len(raw)!=28665 or hashlib.sha256(raw).hexdigest()!=PARSER_SHA:raise RuntimeError('PARSER_PIN')
    p=types.ModuleType('_frozen_fec_v1_2_diagnostic');p.__file__=str(PARSER);sys.modules[p.__name__]=p
    exec(compile(raw,str(PARSER),'exec'),p.__dict__)
    with SOURCE.open('rb') as stream:raw=stream.read(6251111)
    if len(raw)!=6251110 or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise RuntimeError('SOURCE_PIN')
    current={'member':None,'relationship':None};reads=[]
    old_read=zipfile.ZipFile.read;old_target=p._NoDTDOrExternalRelationships
    def observed_read(self,name,*args,**kw):
        member=name.filename if isinstance(name,zipfile.ZipInfo) else name
        if not isinstance(member,str) or len(member)>256 or not re.fullmatch(r'[A-Za-z0-9_./\[\]-]+',member):
            raise RuntimeError('PUBLIC_MEMBER_METADATA_BOUND')
        current['member']=member;current['relationship']=None
        content=old_read(self,name,*args,**kw);charge('inflated_member_bytes',len(content));reads.append({'member':member,'bytes':len(content)})
        return content
    class ObservedTarget(old_target):
        def start(self,tag,attributes):
            if tag.rsplit('}',1)[-1]=='Relationship':
                kind=next((v for k,v in attributes.items() if k.rsplit('}',1)[-1]=='Type'),None)
                mode=next((v for k,v in attributes.items() if k.rsplit('}',1)[-1]=='TargetMode'),None)
                known={'hyperlink','worksheet','styles','sharedStrings','theme','printerSettings','officeDocument','externalLink','calcChain','core-properties','extended-properties'}
                leaf=kind.rsplit('/',1)[-1] if type(kind) is str else None
                current['relationship']={'type_label':leaf if leaf in known else 'UNKNOWN',
                    'type_sha256':hashlib.sha256(kind.encode()).hexdigest() if type(kind) is str else None,
                    'target_mode':'EXTERNAL' if type(mode) is str and mode.lower()=='external' else 'INTERNAL' if mode is None or mode=='Internal' else 'OTHER',
                    'target_value':'SUPPRESSED_NOT_RECORDED'}
            return super().start(tag,attributes)
    zipfile.ZipFile.read=observed_read;p._NoDTDOrExternalRelationships=ObservedTarget
    result={'kind':'INDEPENDENT_FEC_EXACT_PREFLIGHT_DIAGNOSTIC','scope':'ONE_PREFLIGHT_ONLY_NO_READER_NUMERIC_EXTRACTION','preflight_calls':1}
    try:
        archive=p.archive_preflight(raw)
    except p.ParserRefused as error:
        allowed={'WORKBOOK_SIZE','ARCHIVE_BOUND','DUPLICATE_ARCHIVE_MEMBER','ARCHIVE_MEMBER','EXTERNAL_LINK_OR_MACRO','ARCHIVE_DIRECTORY_PAYLOAD','OPAQUE_PART_PIN','XML_DTD_OR_ENTITY','EXTERNAL_RELATIONSHIP','INVALID_WORKBOOK_ARCHIVE'}
        code=error.args[0] if type(error) is p.ParserRefused and len(error.args)==1 and type(error.args[0]) is str and error.args[0] in allowed else 'UNRECOGNIZED_FIXED_CODE'
        tb=error.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code is p.archive_preflight.__code__:
                item=tb.tb_frame.f_locals.get('item')
                if type(item) is zipfile.ZipInfo and re.fullmatch(r'[A-Za-z0-9_./\[\]-]{1,256}',item.filename):current['member']=item.filename
            tb=tb.tb_next
        result.update({'status':'REFUSAL_IDENTIFIED','safe_refusal_code':code,'first_refusal_metadata':dict(current)})
    else:result.update({'status':'PREFLIGHT_PASSED','archive':archive,'root_actual_error_cause':'NOT_IDENTIFIED_BY_THIS_DIAGNOSTIC'})
    finally:
        zipfile.ZipFile.read=old_read;p._NoDTDOrExternalRelationships=old_target
    assert hashlib.sha256(PARSER.read_bytes()).hexdigest()==PARSER_SHA
    result.update({'source_sha256':SOURCE_SHA,'parser_sha256':PARSER_SHA,'original_validator_invocation':'Delegated unchanged archive_preflight once; ZipFile.read delegates once and records member/length; XML target delegates original start exactly once. No guard weakening.',
                   'members_read_before_first_refusal':reads,'read_usage':usage,'actual_workbook_reader_calls':0,'openpyxl_imported':'openpyxl' in sys.modules,'numeric_cell_values_extracted':0,'owner_key_network_model_install_calls':0,'wall_seconds':time.monotonic()-start})
    text=json.dumps(result,sort_keys=True)
    if len(text.encode())>65536:raise RuntimeError('PUBLIC_OUTPUT_BOUND')
    print(text)


if __name__=='__main__':main()
