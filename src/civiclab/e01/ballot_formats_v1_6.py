"""Narrow obtained Iowa/New Hampshire general roster editions, no final acceptance."""
from datetime import datetime
import re
from civiclab.e01.ballot_formats_v1_3 import candidate,norm,roster


def extract_ia_senate(pages,index_text):
    if len(pages)!=14:raise ValueError('Iowa expects obtained14page edition')
    text=pages[0]
    if not all(x in text for x in ['Candidate List','November 3, 2026 General Election','Ballot Name(s)',
                                  'Filing Date','8/19/2026 1:36 PM']):raise ValueError('Iowa general edition/header differs')
    if not all(x in norm(index_text) for x in ['November 3, 2026','Candidate List','Candidates are only added after review and acceptance']):
        raise ValueError('Iowa official index context differs')
    if text.count('United States Senator')!=1 or text.count('United States Representative District 1')!=1:
        raise ValueError('Iowa Senate boundary missing/ambiguous')
    block=text.split('United States Senator',1)[1].split('United States Representative District 1',1)[0]
    out=[]
    for line in block.splitlines():
        if not line.strip():continue
        fields=re.split(r'\s{2,}',line.strip())
        # First office label was removed by exact section boundary; all three
        # obtained rows now have party/name/address/phone/email/date columns.
        if len(fields)!=6 or not fields[0] or not fields[1]:raise ValueError('Iowa candidate row layout differs')
        filed=datetime.strptime(fields[-1],'%m/%d/%Y').date().isoformat()
        if not '2026-01-01'<=filed<='2026-08-19':raise ValueError('Iowa filing date after obtained edition')
        out.append(candidate(fields[1],fields[0],filing_date_printed=filed,pdf_page=1))
    if len(out)!=3:raise ValueError('Iowa obtained-edition Senate row count differs')
    return roster('IA',out,publication_date_printed='2026-08-19',
                  withdrawal_scope='ACCEPTED_FILINGS_IN_OBTAINED_LIST_NOT_LATEST_AMENDMENT_OR_FINAL_BALLOT')


def extract_nh_senate(pages,index_text,vacancy_pages,withdrawal_pages):
    if len(pages)!=46:raise ValueError('New Hampshire expects obtained46page edition')
    text=pages[0]
    if not all(x in text for x in ['CANDIDATE LIST W/ ADDRESS - 09/17/2026','Candidate Name','Candidate Address','City/State/Zip','Party']):
        raise ValueError('New Hampshire body edition/header differs')
    header=next((line for line in text.splitlines() if line.startswith('Candidate Name') and 'Candidate Address' in line),None)
    if header is None or [header.index(x) for x in ['Candidate Name','Domicile','Candidate Address','City/State/Zip','Party']]!=[0,31,54,93,130]:
        raise ValueError('New Hampshire obtained column positions differ')
    if not all(x in norm(index_text) for x in ['2026 General Election Candidates','Vacancies Created Following the State Primary 2026','Withdrawals']):
        raise ValueError('New Hampshire general stage/index context differs')
    if text.count('United States Senator')!=1 or text.count('Representative in Congress')!=1:
        raise ValueError('New Hampshire Senate boundary missing/ambiguous')
    if len(vacancy_pages)!=1 or len(withdrawal_pages)!=1:raise ValueError('New Hampshire context edition page count differs')
    if not norm(vacancy_pages[0]).startswith('Vacancies Created Following the State Primary - 2026') or not norm(withdrawal_pages[0]).startswith('Withdrawals - 2026'):
        raise ValueError('New Hampshire context document titles differ')
    if any(re.search(r'United States Senator|U\.?S\.? Senator|UNITED STATES SENATOR',p) for p in vacancy_pages+withdrawal_pages):
        raise ValueError('New Hampshire possible Senate change requires separate context review')
    out=[];continuations=0;last_kind=None;block=text.split('United States Senator',1)[1].split('Representative in Congress',1)[0]
    for line in block.splitlines():
        if not line.strip():continue
        fields=re.split(r'\s{2,}',line.strip())
        if len(fields)==1:
            start=len(line)-len(line.lstrip());end=len(line.rstrip())
            # Obtained edition has one postal-box continuation after candidate2,
            # wholly inside CandidateAddress. Never discard arbitrary one-field text.
            if (len(out)!=2 or last_kind!='candidate' or start!=55 or end>93 or
                line[:54].strip() or line[93:].strip() or
                not re.fullmatch(r'PO BOX [0-9]+',line.strip(),re.I)):
                raise ValueError('ambiguous New Hampshire continuation layout')
            continuations+=1;last_kind='continuation';continue
        if len(fields)!=5 or not fields[0] or not fields[-1]:raise ValueError('New Hampshire candidate row layout differs')
        starts=[];cursor=0
        for value in fields:
            cursor=line.index(value,cursor);starts.append(cursor);cursor+=len(value)
        if starts!=[0,32,55,93,130]:raise ValueError('New Hampshire candidate field positions differ')
        row=candidate(fields[0],fields[-1],pdf_page=1)
        row['party_class']={'DEM':'D','REP':'R'}.get(fields[-1],'UNSPECIFIED')
        out.append(row);last_kind='candidate'
    if continuations!=1:raise ValueError('New Hampshire obtained continuation count differs')
    if len(out)!=3:raise ValueError('New Hampshire obtained-edition Senate row count differs')
    return roster('NH',out,publication_date_printed='2026-09-17',
                  omitted_address_continuation_count=continuations,
                  general_stage_evidence='OFFICIAL_INDEX_LINK_NOT_PDF_BODY_STAMP',
                  context_scope='FILING_WITHDRAWALS_AND_POST_PRIMARY_VACANCIES_NOT_AUTOMATIC_GENERAL_EXCLUSIONS',
                  context_observation='NO_EXACT_SENATOR_PHRASE_IN_OBTAINED_CONTEXTS_NOT_ABSENCE_OF_AMENDMENTS',
                  withdrawal_scope='LATER_GENERAL_AMENDMENTS_AND_FINAL_BALLOT_UNVERIFIED')
