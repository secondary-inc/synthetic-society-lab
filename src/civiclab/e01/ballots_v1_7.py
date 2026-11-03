"""Versioned DE/NE extension; v1.6.1 remains unchanged and independently callable.

Offline cached-source validation only. Local candidate objects do not establish
legal final ballots, latest amendments, geography or a selected race sample.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
from pathlib import Path
import re

from civiclab.common import RunStore, canonical_hash, sha256_file
from civiclab.e01 import ballots as base
from civiclab.e01 import delaware_v1_7 as de
from civiclab.e01 import nebraska_v1_7 as ne

BASE_PATH='configs/e01_ballot_readiness_v1_6_1.json'
BASE_SHA='71816d8ffb72c24adebaa5df6642ee9ed90040656a45562b10c20db5bffa988b'
CONTRACT_PATH='configs/e01_de_ne_source_contract_v1_7.json'
CONTRACT_SHA='f698aa051299e0c9787a5376d455a941fa0374bf5524941988ff49ad27f3321a'
SCOPE='OFFICIAL_BALLOT_READINESS_V1_7_ONLY'
PIN_PATHS=(BASE_PATH,CONTRACT_PATH,'src/civiclab/common.py','src/civiclab/e01/ballots.py',
 'src/civiclab/e01/ballot_formats_v1_3.py','src/civiclab/e01/ballot_capture_formats_v1_4.py',
 'src/civiclab/e01/maine_v1_5.py','src/civiclab/e01/ballot_formats_v1_6.py',
 'src/civiclab/e01/delaware_v1_7.py','src/civiclab/e01/nebraska_v1_7.py')
SOURCE_IDS=('de_index','de_general','de_writeins','de_general_xlsx','ne_index','ne_general')


def admit_metadata(config):
    expected={'schema_version','scope','source_adoption','frozen_input_hashes','geometry_runtime'}
    if not isinstance(config,dict) or set(config)!=expected:raise ValueError('v1.7 metadata schema differs')
    if type(config['schema_version']) is not int or config['schema_version']!=1 or config['scope']!=SCOPE or config['source_adoption'] is not False:
        raise ValueError('v1.7 metadata scope differs')
    pins=config['frozen_input_hashes']
    if not isinstance(pins,dict) or set(pins)!=set(PIN_PATHS) or any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in pins.values()):
        raise ValueError('v1.7 frozen input schema differs')
    if pins[BASE_PATH]!=BASE_SHA or pins[CONTRACT_PATH]!=CONTRACT_SHA:raise ValueError('v1.7 original input identity differs')
    if config['geometry_runtime']!={'engine':'pdfplumber','version':'0.11.9'}:raise ValueError('v1.7 declared geometry runtime differs')
    return {'role':SCOPE,'config_sha256':canonical_hash(config)}


def local_path(root,relative):
    """Refuse traversal and symlinks, including symlinked ancestor directories."""
    root=Path(root).resolve();p=root/relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:raise ValueError('v1.7 local path differs')
    if any(a.is_symlink() for a in (p,*p.parents) if a!=root and a.is_relative_to(root)):
        raise ValueError('v1.7 source/input symlink refused')
    if not p.resolve().is_relative_to(root) or not p.is_file():raise ValueError('v1.7 local input missing/outside root')
    return p


def verify_inputs(root,config):
    admit_metadata(config)
    for relative,digest in config['frozen_input_hashes'].items():
        if sha256_file(local_path(root,relative))!=digest:raise ValueError('v1.7 implementation or frozen input changed')
    # Check that imported helpers are the exact pinned local source, not another
    # installed package with matching files merely staged under root.
    for module in (base,de,ne):
        expected=local_path(root,'src/'+module.__name__.replace('.','/')+'.py')
        if Path(module.__file__).resolve()!=expected.resolve():raise ValueError('v1.7 imported helper origin differs')
    contract=json.loads(local_path(root,CONTRACT_PATH).read_text())
    sources=contract['sources']
    if [s['source_id'] for s in sources]!=list(SOURCE_IDS):raise ValueError('v1.7 exact six sources differ')
    paths={}
    for s in sources:
        p=local_path(root,s['path'])
        if not p.is_relative_to((Path(root)/'data/raw').resolve()):raise ValueError('v1.7 source outside raw')
        if p.stat().st_size!=s['bytes'] or sha256_file(p)!=s['sha256']:raise ValueError('v1.7 cached source identity changed')
        paths[s['source_id']]=p
    return json.loads(local_path(root,BASE_PATH).read_text()),contract,paths


def geometry_runtime(config):
    try:module=importlib.import_module('pdfplumber')
    except ImportError:raise RuntimeError('v1.7 optional geometry runtime absent') from None
    if getattr(module,'__version__',None)!=config['geometry_runtime']['version']:
        raise RuntimeError('v1.7 geometry runtime version differs')
    return module


def validate_readiness(root,config):
    baseline,contract,paths=verify_inputs(root,config)
    geometry_runtime(config)  # Must precede any geometry extraction.
    report=base.validate_readiness(root,baseline)
    old_rosters=copy.deepcopy(report['local_only_rosters'])
    if set(old_rosters)!=set('AK CO IA KS ME NC NH NJ VA WY'.split()):raise ValueError('v1.7 expected ten-state baseline differs')
    if any(x['state'] in {'DE','NE'} and x['candidate_source_ids'] for x in baseline['class_II_frame']):
        raise ValueError('v1.7 extension already present in base')
    d=de.reconcile(paths['de_general'].read_text(),paths['de_writeins'].read_text(),paths['de_general_xlsx'],paths['de_index'].read_text())
    n=ne.read_pdf(paths['ne_general'],paths['ne_index'].read_text())
    if (n.get('geometry_engine'),n.get('geometry_engine_version'))!=('pdfplumber','0.11.9'):
        raise RuntimeError('v1.7 actual serving geometry differs')
    common={'office':'SENATE','seat_class':2,'election_date':'2026-11-03',
        'completeness_claim':'OBTAINED_SOURCE_CONSISTENCY_NOT_LATEST_AMENDMENT_OR_FINAL_BALLOT_ACCEPTANCE'}
    d_roster={**common,'state':'DE','printed_stage':'GENERAL_FILED_STATUS_WITH_SEPARATE_DECLARED_WRITEINS',
        'candidates':d['printed_candidates']+d['declared_write_ins'],'printed_candidates':d['printed_candidate_count'],
        'declared_write_ins':d['declared_write_in_count'],'delaware_reconciliation':d}
    n_roster={**common,**n,'printed_stage':'GENERAL_FINAL_TITLED_SOURCE_NOT_FINAL_ACCEPTANCE'}
    for state,roster,refs in [('DE',d_roster,SOURCE_IDS[:4]),('NE',n_roster,SOURCE_IDS[4:])]:
        roster['source_hashes']=[s['sha256'] for s in contract['sources'] if s['source_id'] in refs]
        roster['source_ids']=list(refs)
        roster['observations']=base.roster_observations(roster)
        if state=='DE':roster['observations'].update(printed_candidate_count=2,declared_write_in_count=3)
        report['local_only_rosters'][state]=roster
        finding={'state':state,'status':'OFFICIAL_DOCUMENT_EXTRACTED_PENDING_FINAL_AMENDMENT_AND_INDEPENDENT_REVIEW',**roster['observations']}
        report['candidate_observations']=[finding if x['state']==state else x for x in report['candidate_observations']]
    if any(report['local_only_rosters'][s]!=v for s,v in old_rosters.items()):raise RuntimeError('v1.7 earlier roster changed')
    # Recheck all pinned bytes after parsing before any successful artifact write.
    verify_inputs(root,config)
    report.update(config_sha256=canonical_hash(config),baseline_config_sha256=canonical_hash(baseline),
        extension_version='1.7',source_hash_checks=report['source_hash_checks']+6,official_rosters_extracted=len(report['local_only_rosters']),
        preserved_prior_roster_count=10,geometry_runtime=config['geometry_runtime'],
        extension_source_contract_sha256=CONTRACT_SHA,frozen_input_hashes=config['frozen_input_hashes'])
    return report


def run_readiness(root,config):
    run_config=admit_metadata(config)  # No arbitrary text/secret metadata persisted.
    failure=None
    with RunStore(Path(root),'E01',run_config,kind='EXPLORATORY') as run:
        try:result=validate_readiness(root,config)
        except BaseException as exc:
            failure=exc
            run.event('failed',error_type=type(exc).__name__)
            run.write('failure.json',{'status':'FAILED','error_type':type(exc).__name__})
            run.finish({'status':'FAILED','error_type':type(exc).__name__,'final_ballots_accepted':0,'actual_selection':False,'cost_usd':0})
        else:
            run.write('ballot_readiness.json',{k:v for k,v in result.items() if k!='local_only_rosters'})
            run.write('candidate_rosters.local.json',result['local_only_rosters'])
            run.finish({'status':result['status'],'source_hash_checks':result['source_hash_checks'],'regular_frame_slots':33,
                'official_rosters_extracted':result['official_rosters_extracted'],'final_ballots_accepted':0,'actual_selection':False,'cost_usd':0})
    if failure is not None:raise failure
    return run.path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('config',type=Path);p.add_argument('--root',type=Path,default=Path.cwd());a=p.parse_args()
    print(run_readiness(a.root,json.loads(a.config.read_text())))


if __name__=='__main__':main()
