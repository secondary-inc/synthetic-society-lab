"""Registry-configured bounded parser, first digest learned in PRIMARY only."""
import csv
from functools import wraps
import hashlib
import io
import os
from pathlib import Path
import stat
import zipfile
from ..common import canonical_hash
from . import n2b_admission_v1 as a
from . import n2b_parts_v1 as parts
from .f_wy_bootstrap_v1_1 import _open_no_follow,_identity
from .n2a_collector_v1 import _header_line
from .full_adult_types_v1_2 import AdultMatrix,parse_person
from .national_budget import Blocked


def owned_source(f):
 @wraps(f)
 def wrapper(c,control,*args,**kwargs):
  a.require(c)
  if control.c!=c or control.path!=c.output:raise Blocked('source/control exact context')
  try:
   with control.owner():return f(c,control,*args,**kwargs)
  except Blocked:raise
  except Exception:raise Blocked('bounded source metadata/stream refused') from None
 return wrapper

@owned_source
def inspect_source(c,control,stage):
 a.require(c);m=c.source;control.guard(stage);control.access(stage,'metadata');path=c.root/m['relative_path'];f,dfd,chain=_open_no_follow(path)
 try:
  with f:
   before=_identity(os.fstat(f.fileno()))
   if before!=m['identity'] or chain!=m['chain'] or before['bytes']!=m['archive_bytes']:raise Blocked('current full source identity')
   h=hashlib.sha256();n=0
   while True:
    control.guard(stage);chunk=f.read(min(65536,m['archive_bytes']-n+1))
    if not chunk:break
    n+=len(chunk);h.update(chunk)
    if n>m['archive_bytes']:raise Blocked('compressed length')
   if n!=m['archive_bytes'] or h.hexdigest()!=m['archive_sha256']:raise Blocked('compressed source hash')
   f.seek(0);expected={v['name']:v for v in m['members']}
   with zipfile.ZipFile(f) as z:
    infos=z.infolist()
    if len(infos)!=2 or set(i.filename for i in infos)!=set(expected) or len({i.filename.casefold() for i in infos})!=2:raise Blocked('literal membership')
    for i in infos:
     e=expected[i.filename]
     if Path(i.filename).name!=i.filename or '\\' in i.filename or stat.S_ISLNK(i.external_attr>>16) or i.flag_bits&1 or i.compress_type not in (0,8) or (i.file_size,i.compress_size,i.CRC,i.compress_type)!=(e['bytes'],e['compressed_bytes'],e['crc32'],e['compression']):raise Blocked('member CRC/size/type/layout')
    head=_header_line(f,z.getinfo(m['person']),m['archive_bytes'],65536,lambda:control.guard(stage))
    if len(head)!=m['header_bytes'] or a.sha(head)!=m['header_sha256']:raise Blocked('header bytes/hash')
    fields=next(csv.reader(io.StringIO(head.decode('utf-8-sig')),strict=True))
    if len(fields)!=285 or len(set(fields))!=285 or not set(c.config['required_fields']).issubset(fields):raise Blocked('285/91 header contract')
    with z.open(m['companion']) as companion:
     ch=hashlib.sha256();nc=0;cap=expected[m['companion']]['bytes']
     while True:
      control.guard(stage);block=companion.read(min(65536,cap-nc+1))
      if not block:break
      nc+=len(block);ch.update(block)
      if nc>cap:raise Blocked('companion expansion')
    if nc!=cap or ch.hexdigest()!=expected[m['companion']]['sha256']:raise Blocked('companion hash')
   if before!=_identity(os.fstat(f.fileno())):raise Blocked('source changed during metadata')
  current,cd,cc=_open_no_follow(path)
  try:
   with current:
    if cc!=chain or _identity(os.fstat(current.fileno()))!=before:raise Blocked('source lexical replacement')
  finally:os.close(cd)
 finally:os.close(dfd)
 control.guard(stage)
 return {'identity':before,'chain':chain,'archive_sha256':m['archive_sha256'],'metadata_expanded_bytes':len(head)+nc,'person_rows':0}


@owned_source
def parse_state(c,control,stage,*,primary_person_sha256=None):
 a.require(c)
 if stage not in ('DC_PRIMARY','DC_REPLAY') or stage=='DC_PRIMARY' and primary_person_sha256 is not None or stage=='DC_REPLAY' and (type(primary_person_sha256) is not str or len(primary_person_sha256)!=64):raise Blocked('exact primary/replay digest role')
 control.access(stage,'person')
 m=c.source;pre=inspect_source(c,control,stage);spec=c.binding['spec'];s=spec['universe']['state_fips'].index(m['state']);matrix=AdultMatrix()
 accounting={k:parts.empty() for k in ('all','adult','under18')};domains={str(d):{k:parts.empty() for k in ('all','adult','under18')} for d in range(6)};n=nb=0;h=hashlib.sha256()
 stream,dfd,chain=_open_no_follow(c.root/m['relative_path'])
 try:
  with stream:
   if chain!=m['chain'] or _identity(os.fstat(stream.fileno()))!=m['identity']:raise Blocked('person stream current identity')
   with zipfile.ZipFile(stream) as z:
    with z.open(m['person']) as person:
     def lines():
      nonlocal nb
      last=a.tick();bucket=0
      while True:
       now=a.tick()
       if nb//65536!=bucket or a.elapsed(last,now)>=0.1:
        control.guard(stage);last=now;bucket=nb//65536
       line=person.readline(65537)
       if not line:break
       nb+=len(line);h.update(line)
       if len(line)>65536 or nb>next(x['bytes'] for x in m['members'] if x['name']==m['person']):raise Blocked('person expansion/line bound')
       yield line.decode('utf-8-sig' if nb==len(line) else 'utf-8')
     reader=csv.DictReader(lines(),strict=True)
     for row in reader:
      n+=1
      if n>m['expected_rows'] or None in row or len(row)!=285 or any(type(v) is not str for v in row.values()):raise Blocked('all-age row width/count')
      local,w,reps,flags=parse_person(row,m['state'],c.config['required_fields'])
      d=(0 if int(row['CIT'])<=4 else 1)*3+(0 if int(row['RELSHIPP'])<=36 else int(row['RELSHIPP'])-36)
      kind='under18' if local is None else 'adult'
      for target in (accounting['all'],accounting[kind],domains[str(d)]['all'],domains[str(d)][kind]):parts.count_add(target,w,reps)
      if local is not None:matrix.add(s*72+local,w,reps,flags)
   if _identity(os.fstat(stream.fileno()))!=m['identity']:raise Blocked('person post descriptor identity')
 finally:os.close(dfd)
 person=next(x for x in m['members'] if x['name']==m['person']);digest=h.hexdigest()
 if n!=m['expected_rows'] or nb!=person['bytes'] or primary_person_sha256 is not None and digest!=primary_person_sha256:raise Blocked('person EOF/count/hash replay')
 post=inspect_source(c,control,stage)
 if pre!=post:raise Blocked('postparse source closure')
 matrix.mark_state(s)
 part={'schema':parts.SCHEMA,'realm':c.realm.kind,'state':m['state'],'spec_sha256':c.config['specification']['sha256'],'source_manifest_sha256':canonical_hash(m),'source_identity':pre['identity'],'person_sha256':digest,'rows':n,'csv_bytes':nb,'expanded_bytes':nb+2*pre['metadata_expanded_bytes'],'accounting':accounting,'domains':domains,'primitive_bundle':{k:v.hex() for k,v in matrix.blobs().items()},'lineage':{'kind':'GENERIC_STREAMED_'+stage,'design':c.binding['design_sha256']}}
 parts.validate(part,spec,expected_state=m['state'],expected_source=canonical_hash(m),expected_spec=c.config['specification']['sha256']);control.guard(stage);return part
