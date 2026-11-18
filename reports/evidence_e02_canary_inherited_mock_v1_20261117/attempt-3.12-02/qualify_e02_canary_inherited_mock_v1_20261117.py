"""Authored L03 temporary full-history fixture; never live owner authority.

No factory is called on import. Constructor, _empty/_verify/_registration/_apply
remain inherited. Only production path routing and clock/transport seams are
explicitly mocked by tests. No original state is adopted as reducer state.
"""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.e02.wrapper_crossmodel_canary_v1_owner import CanaryOwnerV1,ANCHOR
from civiclab.e02 import wrapper_crossmodel_canary_v1 as pure

ROOT=Path(__file__).resolve().parents[1]
EXPORT=ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/post-run-owner-export.local.json'
REGISTRATION=ROOT/'data/processed/e02_canary_closed_registration_20261117_01/openrouter-v4-bootstrap.local.json'
EXPORT_PIN=(3893676,'ba726232dbc1375f5e7c48d5f96f3bdec70a9812a25cacfe3c00640197aa6f66')
REGISTRATION_PIN=(546,'920278f3258c856f60959cf7bd380a944cc09d797084552698dd7ae7024a54e9')


def read_pinned(path,pin):
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file() or path.stat().st_size!=pin[0]:raise RuntimeError('CLOSED_FIXTURE_PIN')
    raw=path.read_bytes()
    if len(raw)!=pin[0] or hashlib.sha256(raw).hexdigest()!=pin[1]:raise RuntimeError('CLOSED_FIXTURE_HASH')
    return raw


def write_private(path,raw):
    with path.open('xb') as stream:os.chmod(path,0o600);stream.write(raw)


def reconstruct(directory,export,registration,meter):
    directory.mkdir(mode=0o700);owner_path=directory/'owner';owner_path.mkdir(mode=0o700)
    write_private(directory/'openrouter-v4-bootstrap.local.json',registration)
    write_private(owner_path/'owner-v4-guard.local.json',canonical_bytes(export['header']))
    write_private(owner_path/'owner-v4-head.local.json',canonical_bytes(export['head']))
    meter['writes'][0]+=48*1024*1024;meter['reads'][0]+=24*1024*1024
    database=owner_path/'owner-v4.local.sqlite'
    with sqlite3.connect(database) as db:
        db.execute('PRAGMA page_size=4096');db.execute('PRAGMA max_page_count=6144');db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA temp_store=MEMORY')
        db.execute('CREATE TABLE header(data TEXT)');db.execute('CREATE TABLE events(sequence INTEGER PRIMARY KEY,data TEXT,digest TEXT)');db.execute('CREATE TABLE charges(id TEXT PRIMARY KEY,data TEXT)')
        db.execute('INSERT INTO header VALUES (?)',(canonical_bytes(export['header']).decode(),))
        db.executemany('INSERT INTO events VALUES (?,?,?)',[(e['sequence'],canonical_bytes(e).decode(),canonical_hash(e)) for e in export['history']])
        db.executemany('INSERT INTO charges VALUES (?,?)',[(key,canonical_bytes(row).decode()) for key,row in export['rows'].items()])
    db.close();os.chmod(database,0o600)
    for p in (directory/'openrouter-v4-bootstrap.local.json',owner_path/'owner-v4-guard.local.json'):os.chmod(p,0o400)
    return owner_path


def clone_completed(source,destination,meter):
    # Exact owned private physical copy; state is still recomputed by verifier.
    size=sum(p.stat().st_size for p in source.rglob('*') if p.is_file())
    meter['reads'][0]+=size;meter['writes'][0]+=size
    shutil.copytree(source,destination,copy_function=shutil.copyfile)
    for p in destination.rglob('*'):
        if p.is_file():os.chmod(p,0o600)
    return destination/'owner'


def packet(export,now):
    old=export['wrapper_crossmodel']['packet'];releases=deepcopy(old['price_release']);end=now+timedelta(seconds=600)
    for release in releases.values():
        for key in ('terms','interpretation'):release[key].update(valid_from_utc=now.isoformat(),valid_until_utc=end.isoformat())
        release['terms']['interpretation_hash']=canonical_hash(release['interpretation'])
    q={'kind':'WRAPPER_CANARY_PACKET_V1','owner_id':export['header']['owner_id'],'parent_key':pure.identity(export['header']['owner_id']),'expected_head':deepcopy(export['head']),'parent_binding':deepcopy(ANCHOR),'run_id':'AUTHORED_L03_INHERITED_CANARY','valid_from_utc':now.isoformat(),'valid_until_utc':end.isoformat(),'bounds':deepcopy(pure.BOUNDS),'code_hash':canonical_hash(pure.contract()),'price_release':releases}
    q['authority']={'kind':pure.AUTHORITY,'scope_hash':canonical_hash(q)}
    q['review']={'kind':'INDEPENDENT_WRAPPER_CANARY_REVIEW_V1','reviewer_role':'independent_auditor','review_id':'a'*32,'inputs_hash':canonical_hash(q)}
    release={'kind':'LEAD_WRAPPER_CANARY_RELEASE_V1','packet_sha256':canonical_hash(q),'code_hash':canonical_hash(pure.contract()),'review_sha256':canonical_hash(q['review']),'maximum_POSTs':1,'scope':'ORIGINAL45_ONLY_NOT_FULL80'}
    return q,release


def protected_methods():
    names=('__init__','_location','_registration','_empty','_verify','_apply','_binding')
    return {(cls,name):getattr(cls,name) for cls in CanaryOwnerV1.__mro__ for name in names if hasattr(cls,name)}


def assert_methods_same(prior):
    return all(getattr(cls,name) is value for (cls,name),value in prior.items())


if __name__=='__main__':raise SystemExit('No standalone/live execution mode; use bounded authored test only.')
