"""Bounded real historical Senate diagnostic, not the complete E01 study.

Public statewide candidate facts are cross-checked against government PDFs.
The only enabled REAL path is the frozen 2018->2024 Class-I protocol. Generic
REAL execution in pipeline.freeze_predictions remains denied. No model calls.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request

from civiclab.common import RunStore, atomic_json, canonical_hash, sha256_file, utc_now
from .pipeline import validate_race, validate_pair, predict, evaluate, compare
from .isolation import worker_environment

STATE_NAMES = {
    'AZ':'ARIZONA','CA':'CALIFORNIA','CT':'CONNECTICUT','DE':'DELAWARE','FL':'FLORIDA',
    'HI':'HAWAII','IN':'INDIANA','ME':'MAINE','MD':'MARYLAND','MA':'MASSACHUSETTS',
    'MI':'MICHIGAN','MN':'MINNESOTA','MS':'MISSISSIPPI','MO':'MISSOURI','MT':'MONTANA',
    'NE':'NEBRASKA','NV':'NEVADA','NJ':'NEW JERSEY','NM':'NEW MEXICO','NY':'NEW YORK',
    'ND':'NORTH DAKOTA','OH':'OHIO','PA':'PENNSYLVANIA','RI':'RHODE ISLAND','TN':'TENNESSEE',
    'TX':'TEXAS','UT':'UTAH','VT':'VERMONT','VA':'VIRGINIA','WA':'WASHINGTON','WV':'WEST VIRGINIA',
    'WI':'WISCONSIN','WY':'WYOMING'}


def normalize(text):
    text=unicodedata.normalize('NFKD',text)
    return ' '.join(re.findall(r'[A-Z]+',text.upper()))


def surname(name):
    words=normalize(name).split()
    while words and words[-1] in {'JR','SR','II','III','IV'}:
        words.pop()
    if not words:
        raise ValueError('candidate name missing')
    return words[-1]


def _source_config(root):
    return json.loads((Path(root)/'configs/e01_official_sources.json').read_text())


def download_sources(root):
    """Pinned public retrieval. No tokens, authentication workarounds or retries."""
    root=Path(root);config=_source_config(root);records=[]
    for source in config['sources']:
        path=root/config['local_directory']/source['filename']
        if path.exists():
            if sha256_file(path)!=source['sha256']:
                raise ValueError('existing raw input changed: '+source['id'])
            records.append({**source,'status':'VERIFIED_LOCAL','path':str(path.relative_to(root))})
            continue
        if not source['url'].startswith(('https://raw.githubusercontent.com/MEDSL/','https://www.fec.gov/','https://clerk.house.gov/','https://www.senate.gov/','https://www.msa.maryland.gov/')):
            raise ValueError('source outside approved public endpoints')
        request=urllib.request.Request(source['url'],headers={'User-Agent':'SyntheticSocietyLab research source importer'})
        with urllib.request.urlopen(request,timeout=30) as response:
            data=response.read(20_000_001)
        if len(data)>20_000_000:
            raise ValueError('source exceeds download ceiling')
        path.parent.mkdir(parents=True,exist_ok=True)
        import hashlib
        actual=hashlib.sha256(data).hexdigest()
        if actual!=source['sha256']:
            rejected=path.with_name(path.name+'.REJECTED.'+actual[:12])
            rejected.write_bytes(data)
            raise ValueError('source drift; rejected bytes retained: '+source['id'])
        path.write_bytes(data)
        records.append({**source,'status':'DOWNLOADED_VERIFIED','path':str(path.relative_to(root)),
                        'retrieved_at_utc':utc_now()})
    atomic_json(root/'data/processed/e01/source_receipt.json',{'sources':records,'scope':'Historical real-data diagnostic'})
    return records


def verify_sources(root):
    root=Path(root);config=_source_config(root);result={}
    for source in config['sources']:
        path=root/config['local_directory']/source['filename']
        if not path.is_file() or sha256_file(path)!=source['sha256']:
            raise ValueError('missing or changed pinned source '+source['id'])
        result[source['id']]={**source,'path':str(path.relative_to(root))}
    return result


def extract_pdf(path):
    # Data acquisition extra only; core fixture tests do not require pypdf.
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError('Official PDF verification needs optional pypdf==6.10.0 in the executing Python environment') from None
    reader=PdfReader(path)
    return [{'pdf_page':i+1,'text':page.extract_text(extraction_mode='layout') if '/Contents' in page else ''}
            for i,page in enumerate(reader.pages)]


def official_sections(pages,year):
    """Keep only Senate state sections; never search House tables for a match."""
    sections=defaultdict(list);state=None;senate=False;general_start=None
    for page in pages:
        text=page['text']
        if year==2018:
            if '2018 U.S. SENATE RESULTS' in text:
                senate=True
            if 'SENATE RACES:' in text or '2018 U.S. HOUSE OF REPRESENTATIVES RESULTS' in text:
                senate=False
        for line in text.splitlines():
            for code,name in STATE_NAMES.items():
                if re.match(r'^\s*'+re.escape(name)+r'(?:\s{2,}|\s*$|\s*\()',line):
                    state=code
                    if year==2024:
                        senate=False
                    break
            if year==2024:
                if 'FOR UNITED STATES SENATOR' in line:
                    senate=True
                if ('FOR UNITED STATES REPRESENTATIVE' in line or 'Recapitulation of Votes Cast' in line):
                    senate=False
            elif 'ELECTION TYPE:' in line and 'GENERAL' in line:
                general_start=line.index('GENERAL')-10
            if senate and state:
                sections[state].append({'line':line,'pdf_page':page['pdf_page'],'general_start':general_start})
    return dict(sections)


def official_candidate_votes(section,name,year,*,expected_party=None,official_family=None):
    family=official_family or surname(name);matches=[]
    parties=set()
    if year==2018:
        for row in section:
            line=row['line'];start=row['general_start']
            if start is None or family not in normalize(line[:75]).split():
                continue
            fields=re.split(r'\s{2,}',re.sub(r'^\s*\(I\)\s*','',line).strip())
            if len(fields)>1:
                token=fields[1].split()[0]
                if token in {'D','DFL','DNL'}:parties.add('DEMOCRAT')
                elif token=='R':parties.add('REPUBLICAN')
            field=line[start:]
            # FEC brackets are sub-party votes under an already combined total.
            if '[' in field:
                continue
            number=re.search(r'(?<!\w)([\d,]+)\s+\d+\.\d+%',field)
            if number:
                matches.append({'votes':int(number.group(1).replace(',','')),'pdf_page':row['pdf_page'],
                                'official_name_line':line[:75].strip()})
    else:
        active=None;entries=[]
        for row in section:
            line=row['line'];number=re.search(r'([\d,]+)\s*$',line)
            if not number or '..' not in line:
                continue
            label=re.split(r'\.{2,}',line)[0].strip()
            if ',' in label:
                active={'label':label,'votes':int(number.group(1).replace(',','')),'pages':[row['pdf_page']]}
                entries.append(active)
            elif normalize(label).startswith('WRITE IN'):
                active=None
            elif active and normalize(label) in {'WORKING FAMILIES','CONSERVATIVE','INDEPENDENT'}:
                # Fusion party continuation immediately below the named candidate.
                active['votes']+=int(number.group(1).replace(',',''));active['pages'].append(row['pdf_page'])
            else:
                # Blanks, undervotes and "All Others" are not fusion lines.
                active=None
        for entry in entries:
            name_part=entry['label'].rsplit(',',1)[0]
            if family in normalize(name_part).split():
                token=normalize(entry['label'].rsplit(',',1)[1])
                if token in {'DEMOCRAT','DEMOCRATIC','DEMOCRATIC FARMER LABOR','DEMOCRATIC NPL','DEMOCRATIC NONPARTISAN LEAGUE'}:parties.add('DEMOCRAT')
                elif token=='REPUBLICAN':parties.add('REPUBLICAN')
                matches.append({'votes':entry['votes'],'pdf_page':entry['pages'][0],
                                'official_name_line':entry['label']})
    if len(matches)!=1:
        raise ValueError(f'official candidate match not unique: {name}, {year}, {len(matches)}')
    if expected_party is not None and parties!={expected_party}:
        raise ValueError(f'official party mismatch: {name}, {year}, {sorted(parties)}')
    matches[0]['official_parties']=sorted(parties)
    return matches[0]


def read_statewide(path,year):
    groups=defaultdict(list);seen=set()
    with Path(path).open(newline='',encoding='latin1' if year==2018 else 'utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            if int(row['year'])!=year or row['stage'].upper()!='GEN' or row['special'].upper()!='FALSE':
                continue
            if row['office'].upper()!='US SENATE' or row['mode'].upper()!='TOTAL':
                raise ValueError('unexpected office/mode in statewide source')
            key=(row['state_po'],normalize(row['candidate']),row.get('party',row.get('party_detailed')))
            if key in seen:
                raise ValueError('duplicate candidate/party line')
            seen.add(key)
            raw=row.get('candidatevotes',row.get('votes'))
            if not re.fullmatch(r'\d+',raw):
                raise ValueError('invalid statewide candidate votes')
            groups[row['state_po']].append({**row,'count':int(raw)})
    return dict(groups)


def major_candidates(rows):
    anchors={'DEMOCRAT':set(),'REPUBLICAN':set()}
    for row in rows:
        party=row.get('party_simplified',row.get('party','')).upper()
        if party in {'DEMOCRAT','DEMOCRATIC-FARMER-LABOR','DEMOCRATIC-NPL'}:
            anchors['DEMOCRAT'].add(normalize(row['candidate']))
        elif party=='REPUBLICAN':
            anchors['REPUBLICAN'].add(normalize(row['candidate']))
    if any(len(v)!=1 for v in anchors.values()):
        raise ValueError('requires one named Democrat and Republican; no margin/winner-based exclusions')
    result=[]
    for party,names in anchors.items():
        normalized=next(iter(names));lines=[r for r in rows if normalize(r['candidate'])==normalized]
        result.append({'name':lines[0]['candidate'],'party':party,'votes':sum(r['count'] for r in lines),
                       'party_lines':[r.get('party_detailed',r.get('party')) for r in lines]})
    return result


def prepare(root):
    root=Path(root);sources=verify_sources(root)
    protocol=json.loads((root/'configs/e01_senate2018_2024.json').read_text())
    if protocol['prior_year']!=2018 or protocol['target_year']!=2024 or protocol['seat_class']!=1 or set(protocol['class1_states'])!=set(STATE_NAMES):
        raise ValueError('only frozen 2018→2024 Class-I diagnostic is enabled')
    if protocol['national_shift_pp']!=0 or protocol['incumbency_adjustment_pp']!=0:
        raise ValueError('historical diagnostic forbids tuning shifts on target outcomes')
    raw=lambda key:root/sources[key]['path']
    year_rows={2018:read_statewide(raw('medsl2018'),2018),2024:read_statewide(raw('medsl2024'),2024)}
    sections={2018:official_sections(extract_pdf(raw('fec2018')),2018),
              2024:official_sections(extract_pdf(raw('clerk2024')),2024)}
    geo={'vintage':'STATEWIDE_CLASS_I_2018_2024_CONSTITUENCY','official_source':sources['fec2018']['url']+' (printed p.34 six-year cycle); '+sources['senateclass1']['url'],
         'sha256':sources['fec2018']['sha256'],'verified':True}
    races=[];features=[];outcomes=[];exclusions=[];crosschecks=[]
    for state in sorted(protocol['class1_states']):
        try:
            candidates={year:major_candidates(year_rows[year].get(state,[])) for year in (2018,2024)}
        except ValueError as error:
            exclusions.append({'state':state,'reason':str(error),'basis':'party/participant structure, not performance'});continue
        manifests={}
        for year in (2018,2024):
            official_key='fec2018' if year==2018 else 'clerk2024'
            for candidate in candidates[year]:
                alias=protocol.get('official_name_aliases',{}).get(f'{year}:{state}:'+normalize(candidate['name']))
                if alias and alias['corroboration_source'] not in sources:
                    raise ValueError('name alias lacks verified corroborating source')
                match=official_candidate_votes(sections[year].get(state,[]),candidate['name'],year,
                    expected_party=candidate['party'],official_family=alias['official_family'] if alias else None)
                if alias:match['name_reconciliation']=alias
                if candidate['votes']!=match['votes']:
                    adjudications=[a for a in protocol.get('official_count_adjudications',[])
                        if (a['state'],a['year'],a['party'],a['csv_votes'],a['official_votes'])==
                           (state,year,candidate['party'],candidate['votes'],match['votes'])]
                    if len(adjudications)!=1:
                        raise ValueError(f'official count disagreement blocks evaluation: {state} {year} {candidate["name"]}: CSV={candidate["votes"]}, official={match["votes"]}')
                    match['count_adjudication']=adjudications[0]
                    candidate['votes']=match['votes']
                crosschecks.append({'state':state,'year':year,'party':candidate['party'],'candidate':candidate['name'],
                                    'votes':candidate['votes'],'source_sha256':sources[official_key]['sha256'],**match})
            manifest={'race_id':f'{year}-{state}-SENATE-STATEWIDE-C1','year':year,'state':state,'office':'SENATE',
                      'district':'STATEWIDE','seat_class':1,'stage':'GEN','special':False,
                      'election_date':protocol['prior_election_date'] if year==2018 else protocol['target_election_date'],
                      'cutoff':f'{year}-11-01','status':'RETROSPECTIVE','geography':dict(geo),
                      'candidates':[{'candidate_id':f'{year}-{state}-'+c['party'], 'name':c['name'],'party':c['party'],
                                     'official_ballot_source':sources[official_key]['url'],
                                     'sha256':sources[official_key]['sha256'],'verified':True} for c in candidates[year]]}
            validate_race(manifest);manifests[year]=manifest
        validate_pair(manifests[2018],manifests[2024]);races.append({'prior':manifests[2018],'target':manifests[2024]})
        def margin(year):
            d=next(c['votes'] for c in candidates[year] if c['party']=='DEMOCRAT')
            r=next(c['votes'] for c in candidates[year] if c['party']=='REPUBLICAN')
            if d<=0 or r<=0:raise ValueError('uncontested/zero major-party count')
            return 100*(d-r)/(d+r)
        race_id=manifests[2024]['race_id']
        features.append({'race_id':race_id,'office':'SENATE','prior_margin_pp':margin(2018),
                         'national_shift_pp':0,'incumbency_adjustment_pp':0,'feature_as_of':protocol['feature_as_of'],
                         'cutoff':protocol['feature_cutoff'],'source_hashes':[sources['fec2018']['sha256']]})
        outcomes.append({'race_id':race_id,'office':'SENATE','observed_margin_pp':margin(2024)})
    if not races:
        raise ValueError('no eligible verified races')
    return {'protocol':protocol,'sources':sources,'manifest':races,'features':features,'outcomes':outcomes,
            'exclusions':exclusions,'official_crosschecks':crosschecks,
            'selection_sha256':canonical_hash([r['target']['race_id'] for r in races]),
            'claim_limit':'Real historical diagnostic; not prospective, not full 2026 E01, no agents, no historically untouched sample.'}


def _frozen_real(features,prepared,method):
    if method not in {'S0','S_ZERO'}:
        raise ValueError('unapproved retrospective baseline method')
    manifest=prepared['manifest']
    if (len(features)!=len(manifest) or len({f['race_id'] for f in features})!=len(features)
            or {f['race_id'] for f in features}!={r['target']['race_id'] for r in manifest}):
        raise ValueError('feature/manifest coverage mismatch')
    if canonical_hash(features)!=canonical_hash(prepared['features']):
        raise ValueError('features differ from official prepared inputs')
    for pair in manifest:validate_pair(pair['prior'],pair['target'])
    for feature in features:predict(feature)
    with tempfile.TemporaryDirectory(prefix='civiclab-real-predictor-') as cwd:
        result=subprocess.run([sys.executable,'-m','civiclab.e01.worker','--method',method],
                              input=json.dumps(features,allow_nan=False),text=True,capture_output=True,check=True,
                              cwd=cwd,env=worker_environment(),timeout=30)
    predictions=sorted(json.loads(result.stdout),key=lambda r:r['race_id'])
    payload={'status':'RETROSPECTIVE','dataset_kind':'REAL_HISTORICAL_DIAGNOSTIC','method':method,
             'config':prepared['protocol'],'manifest_sha256':canonical_hash(manifest),
             'features_sha256':canonical_hash(features),'selection_sha256':prepared['selection_sha256'],
             'predictions':predictions,'claim_limit':prepared['claim_limit']}
    return {**payload,'freeze_sha256':canonical_hash(payload)}


def run_historical(root):
    root=Path(root);prepared=prepare(root)
    config={'protocol':prepared['protocol'],'sources':{k:s['sha256'] for k,s in prepared['sources'].items()},
            'selection_sha256':prepared['selection_sha256'],'role':'historical diagnostic; original E01 2026 remains incomplete'}
    with RunStore(root,'E01',config,kind='RETROSPECTIVE') as run:
        run.write('race_manifest.json',prepared['manifest']);run.write('source_receipt.json',prepared['sources'])
        run.write('eligibility.json',{'selection_sha256':prepared['selection_sha256'],'excluded':prepared['exclusions']})
        run.write('official_crosschecks.json',prepared['official_crosschecks'])
        run.write('features.json',prepared['features'])
        # Both predictor children receive only features, never target outcome values.
        frozen={method:_frozen_real(prepared['features'],prepared,method) for method in ('S_ZERO','S0')}
        for method,value in frozen.items():run.write(f'{method}.predictions.frozen.json',value)
        run.event('predictions_sealed',hashes={k:v['freeze_sha256'] for k,v in frozen.items()})
        # The parent has reconstructed outcomes; this is retrospective computational separation,
        # not a claim that the researcher or sample-selection code never saw target data.
        run.write('outcomes.json',prepared['outcomes'])
        official_hash=prepared['sources']['clerk2024']['sha256']
        evaluations={k:evaluate(v,prepared['outcomes'],outcome_source_sha256=official_hash) for k,v in frozen.items()}
        for method,value in evaluations.items():run.write(method+'.evaluation.json',value)
        conditions={'race_ids':sorted(f['race_id'] for f in prepared['features']),
                    'historical_cutoff':prepared['protocol']['feature_cutoff'],
                    'selection_rule':prepared['protocol']['selection_rule'],
                    'feature_access':'same historical features available; S_ZERO ignores prior margin by definition',
                    'compute_policy':'deterministic arithmetic; no inference; zero paid spend'}
        paired=compare(evaluations['S_ZERO'],evaluations['S0'],simple_conditions=conditions,advanced_conditions=conditions)
        run.write('paired_comparison.json',paired)
        differences=[r['advanced_minus_simple_absolute_error_pp'] for r in paired['paired_differences']]
        leave_one=[statistics.mean(differences[:i]+differences[i+1:]) for i in range(len(differences))] if len(differences)>1 else []
        summary={'status':'REAL_RETROSPECTIVE_DIAGNOSTIC_COMPLETE','dataset_kind':'REAL_HISTORICAL_DIAGNOSTIC',
                 'study_scope':'2018→2024 Class-I Senate; original 2026/agent E01 contract remains incomplete',
                 'races':len(prepared['features']),'excluded':prepared['exclusions'],
                 'methods':{k:v['by_office'] for k,v in evaluations.items()},
                 'paired_S0_minus_S_ZERO_mae_pp':statistics.mean(differences),
                 'leave_one_state_out_paired_mean_range_pp':[min(leave_one),max(leave_one)] if leave_one else None,
                 'uncertainty':'Finite retrospectively eligible cohort; no sampling CI. Leave-one-state-out range is descriptive sensitivity, not forecast uncertainty.',
                 'prediction_hashes':{k:v['freeze_sha256'] for k,v in frozen.items()},
                 'reproducibility_hash':canonical_hash({'frozen':frozen,'evaluations':evaluations,'paired':paired}),
                 'source_validation':'Each modeled major candidate and combined vote count matched official government PDF',
                 'paid_calls':0,'spent_usd':0,'cost_usd':0,'original_E01_completion':'BLOCKED: 2026 outcomes, verified 2026 sample and agent comparisons remain missing',
                 'limitations':prepared['protocol']['limitations']}
        run.finish(summary)
    return run.path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['download','verify','prepare','run'])
    parser.add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args()
    if args.action=='download':print(json.dumps(download_sources(args.root),indent=2))
    elif args.action=='verify':print(json.dumps(verify_sources(args.root),indent=2))
    elif args.action=='prepare':
        prepared=prepare(args.root);atomic_json(args.root/'data/processed/e01/prepared_historical.json',prepared)
        print(json.dumps({'eligible':len(prepared['features']),'excluded':prepared['exclusions'],'crosschecks':len(prepared['official_crosschecks'])}))
    else:print(run_historical(args.root))


if __name__=='__main__':main()
