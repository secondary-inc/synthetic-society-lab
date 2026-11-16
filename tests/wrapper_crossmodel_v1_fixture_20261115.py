"""Wholly authored fixture retention/reuse; real registrations and guards stay on.

Opt-in development evidence only. Reuse requires an exact manifest pin, same UID
and unchanged source/protocol. Nothing can import this into the actual owner.
"""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from unittest.mock import patch
from civiclab.common import canonical_bytes,canonical_hash,sha256_file
from civiclab.e02.wrapper_crossmodel_v1_owner import WrapperCrossmodelOwnerV1,code_contract,PROTOCOL
from test_production_admission_v4 import account
import test_wrapper_visibility_execution_v1 as prior
ROOT=Path(__file__).resolve().parents[1]

def _base():
    value=os.environ.get('SSL_WRAPPER_CROSSMODEL_V1_EVIDENCE')
    if value is None:return None
    p=Path(value)
    assert p.is_absolute() and p==p.resolve() and p.parent==ROOT/'data/processed'
    assert p.name.startswith('e02_wrapper_crossmodel_v1_20261115_authored_')
    assert p.is_dir() and not p.is_symlink()
    return p

def _write(path,value):
    with path.open('xb') as f:f.write(canonical_bytes(value))

def _home(owner):
    parts=owner.directory.parts;assert 'AUTHORED_OS_HOME' in parts
    p=Path(*parts[:parts.index('AUTHORED_OS_HOME')+1]);assert p.name=='AUTHORED_OS_HOME'
    assert not any(q.is_symlink() for q in (p,*p.parents))
    return p

def _copy_home(owner,dest):
    source=_home(owner)
    assert owner.registration.is_relative_to(source) and owner.directory.is_relative_to(source)
    assert all(not p.is_symlink() for p in source.rglob('*'))
    shutil.copytree(source,dest/'AUTHORED_OS_HOME')

def _bounded_regular_bytes(path,limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>limit:
            raise ValueError('authored fixture regular-file/size bound')
        with os.fdopen(fd,'rb') as stream:
            fd=None;raw=stream.read(limit+1)
        if len(raw)>limit or len(raw)!=info.st_size:
            raise ValueError('authored fixture changed/bounded read')
        return raw
    finally:
        if fd is not None:os.close(fd)


def _manifest(dest):
    metadata={};total=0;entries=0
    for p in dest.rglob('*'):
        entries+=1
        if entries>8192:raise ValueError('authored fixture entry bound')
        info=p.lstat()
        if stat.S_ISDIR(info.st_mode):continue
        if not stat.S_ISREG(info.st_mode) or info.st_size>16000000:
            raise ValueError('authored fixture file type/size bound')
        metadata[str(p.relative_to(dest))]=info.st_size;total+=info.st_size
        if len(metadata)>4096 or total>134217728:
            raise ValueError('authored fixture file-count/total bound')
    # No file contents are read until all metadata bounds have passed.
    files={name:{'bytes':size,'sha256':hashlib.sha256(_bounded_regular_bytes(dest/name,size)).hexdigest()}
           for name,size in sorted(metadata.items())}
    value={'kind':'MOCK_AUTHORED_WRAPPER_CROSSMODEL_V1_FIXTURE_INDEX','account_uid':os.getuid(),
           'actual_owner_access':0,'actual_model_requests':0,'cost_USD':0,'files':files}
    _write(dest/'index.json',value)
    return sha256_file(dest/'index.json')


def retain_prefix(cls,owner):
    base=_base()
    if base is None:return
    dest=base/'prefix';dest.mkdir(exist_ok=False)
    # All connections/locks have closed before capturing the fully verified prefix.
    with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
    assert len(state['rows'])==149 and state['unfinished']==4 and 'wrapper_crossmodel' not in state
    _copy_home(owner,dest)
    _write(dest/'metadata.json',{'kind':'MOCK_AUTHORED_WRAPPER_CROSSMODEL_V1_VALID_PREFIX',
        'account_uid':os.getuid(),'owner_header':owner.header,'head':head,'proofs':cls.proofs,
        'packet':cls.packet,'protocol_sha256':sha256_file(PROTOCOL),
        'code_contract_hash':canonical_hash(code_contract()),'rows':149,'unfinished':4,
        'history_hash':canonical_hash(state['_prefix_events']),'rows_hash':canonical_hash(state['rows'])})
    _manifest(dest)
    active=base/'active-authored-scope.json'
    _write(active,{'kind':'MOCK_AUTHORED_ACTIVE_SCOPE','home':str(_home(owner)),
                   'directory':str(owner.directory),'owner_header':owner.header})
    # Preserve the last working case before ExitStack removes its fake home.
    cls.addClassCleanup(lambda: retain_final_working_home(owner,base))


def retain_final_working_home(owner,base):
    home=_home(owner)
    if not home.exists():return
    dest=base/'CLASS_END_PARTIAL_MOCK_HOME';dest.mkdir(exist_ok=False)
    _copy_home(owner,dest)
    _write(dest/'capture-kind.json',{'kind':'UNVERIFIED_FINAL_WORKING_MOCK_STATE_NOT_ACCEPTANCE',
                                   'actual_owner_access':0,'actual_model_requests':0})
    _manifest(dest)


def try_reuse_prefix(cls,bind):
    value=os.environ.get('SSL_WRAPPER_CROSSMODEL_V1_REUSE_PREFIX')
    if value is None:return False
    source=Path(value);expected=os.environ.get('SSL_WRAPPER_CROSSMODEL_V1_REUSE_SHA256')
    assert source.is_absolute() and source==source.resolve() and source.name=='prefix'
    assert source.parent.parent==ROOT/'data/processed'
    assert source.parent.name.startswith('e02_wrapper_crossmodel_v1_20261115_authored_')
    assert type(expected) is str and len(expected)==64
    index_raw=_bounded_regular_bytes(source/'index.json',1048576)
    assert hashlib.sha256(index_raw).hexdigest()==expected
    index=json.loads(index_raw)
    assert index['kind']=='MOCK_AUTHORED_WRAPPER_CROSSMODEL_V1_FIXTURE_INDEX' and index['account_uid']==os.getuid()
    actual={str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and p!=source/'index.json'}
    assert actual==set(index['files'])
    for name,ref in index['files'].items():
        path=source/name;assert path.is_relative_to(source) and not any(q.is_symlink() for q in (path,*path.parents))
        assert path.is_file() and path.stat().st_size==ref['bytes'] and sha256_file(path)==ref['sha256']
    meta=json.loads((source/'metadata.json').read_text())
    assert meta['kind']=='MOCK_AUTHORED_WRAPPER_CROSSMODEL_V1_VALID_PREFIX'
    assert meta['account_uid']==os.getuid() and meta['protocol_sha256']==sha256_file(PROTOCOL)
    assert meta['code_contract_hash']==canonical_hash(code_contract())
    cls.stack=ExitStack();cls.addClassCleanup(cls.stack.close)
    workspace=Path(cls.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
    home=workspace/'AUTHORED_OS_HOME';shutil.copytree(source/'AUTHORED_OS_HOME',home)
    cls.stack.enter_context(account(home))
    # Reproduce only the authored catalog fixture, never production validation.
    cls.stack.enter_context(patch.object(prior.prior.prior,'qwen_release',side_effect=prior.prior.qwen_release))
    owner=WrapperCrossmodelOwnerV1()  # real registration/header/UID checks, no overrides
    with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
    assert owner.header==meta['owner_header'] and head==meta['head']
    assert len(state['rows'])==149 and state['unfinished']==4
    assert canonical_hash(state['_prefix_events'])==meta['history_hash'] and canonical_hash(state['rows'])==meta['rows_hash']
    assert 'wrapper_crossmodel' not in state
    cls.before=deepcopy(state);cls.location=owner.directory;cls.proofs=meta['proofs'];cls.packet=meta['packet']
    # The packet is still a wholly authored unconsumed fixture for this prefix.
    bind(cls.packet)
    cache=workspace/'CLOSED_MOCK_PREFIX_COPY';shutil.copytree(cls.location,cache);cls.cache=cache
    retain_prefix(cls,owner)
    return True

def retain_case(test,owner,state,head):
    base=_base()
    if base is None:return
    case=base/test._testMethodName;case.mkdir(exist_ok=True)
    number=getattr(test,'_evidence_case_number',0)+1;test._evidence_case_number=number
    dest=case/f'{number:02d}';dest.mkdir(exist_ok=False)
    _copy_home(owner,dest)
    _write(dest/'owner-export.json',{'kind':'MOCK_AUTHORED_WRAPPER_CROSSMODEL_V1_OWNER_EXPORT',
        'header':owner.header,'head':head,'history':state['_prefix_events'],
        'rows':state['rows'],'consumed':state['consumed'],'unfinished':state['unfinished'],
        **{k:state.get(k) for k in ('study','continuation','alignment_followup','issue_cue_crossmodel',
                                   'issue_cue_crossmodel_recovery','wrapper_visibility','wrapper_crossmodel')}})
    _manifest(dest)
