"""Exact six-source derived office context; immutable original occurrence data.

A pure transform, not an authority factory. No source I/O or broad alias map.
The rule requires a separately admitted bound transcript and independent audit.
"""
from collections import Counter
from civiclab.e01 import alabama_documents_v1 as old

RULE_SHA = '48a9cbeefbaccb3b51c1d916990e962a816cfa73767afe3f7513190122b9f974'
SCOPE = 'AL_SOURCE_BOUND_SENATE_OFFICE_LABEL_RECONCILIATION_ONLY'
FAMILY = 'US_SENATE_DOCUMENT_CONTEXT'
DYNAMIC = {'scope','actual_execution_release','release_documents','transcription','independent_transcription_audit'}


def admit_rule(value):
    rule=old.closed_snapshot(value)
    old.require(old.digest(old.canonical(rule))==RULE_SHA)
    old.require(type(rule['schema_version']) is int and rule['schema_version']==1)
    old.require(rule['literal_review_required'] is True and rule['source_objects_may_be_rewritten'] is False)
    old.require(rule['party_context_preserved_separate'] is True and rule['legal_term_seat_class_geography_latest_or_asof_adjudication'] is False)
    old.require(rule['unsupported_label_or_source_scope']=='REFUSE_NO_FALLBACK')
    old.require(len(rule['permitted_rows'])==6)
    old.require(all(type(x['source_occurrence_index']) is int and x['source_occurrence_index']==i for i,x in enumerate(rule['permitted_rows'])))
    old.require([x['cross_literal_exception'] for x in rule['permitted_rows']]==[False,True,False,False,False,False])
    old.require(all(type(x['cross_literal_exception']) is bool and x['derived_office_family_key']==FAMILY for x in rule['permitted_rows']))
    return rule


def _reconcile(c, transcript, audit, proposed_rule):
    rule=admit_rule(proposed_rule)
    c,transcript,audit=[old.closed_snapshot(x) for x in [c,transcript,audit]]
    snapshot_sha=old.source_snapshot_sha(c)
    old.require(snapshot_sha==rule['source_snapshot_sha256'])
    old.require(old.digest(old.canonical({k:v for k,v in c.items() if k not in DYNAMIC}))==rule['fixed_source_policy_sha256'])
    old.require(c['transcription']['sha256']==rule['source_transcript_sha256'])
    old.require(set(transcript)=={'schema_version','scope','source_snapshot_sha256','occurrences'})
    old.require(type(transcript['schema_version']) is int and transcript['schema_version']==1)
    old.require(transcript['scope']=='LOCAL_LITERAL_TRANSCRIPTION_NOT_BALLOT_ACCEPTANCE' and transcript['source_snapshot_sha256']==snapshot_sha)
    old.require(set(audit)=={'schema_version','scope','status','source_snapshot_sha256','transcription_sha256','approved_occurrences'})
    old.require(type(audit['schema_version']) is int and audit['schema_version']==1)
    old.require(audit['scope']=='INDEPENDENT_LOCAL_LITERAL_TRANSCRIPTION_REVIEW' and audit['status']=='PASS_EXACT_TRANSCRIBED_OCCURRENCES_ONLY')
    old.require(audit['source_snapshot_sha256']==snapshot_sha and audit['transcription_sha256']==c['transcription']['sha256'])
    records=transcript['occurrences'];old.require(type(records) is list and len(records)==6)
    sources={s['source_id']:s for s in c['sources']};groups={};annotations=[]
    required={'source_id','source_sha256','physical_pdf_page_1_based','render_sha256','record_role',
              'official_name_literal','office_label_literal','party_context','date_evidence','historical',
              'transcription_method','name_utf8_sha256','office_utf8_sha256'}
    original_record_hashes=[old.digest(old.canonical(r)) for r in records]
    for index,(record,slot,row) in enumerate(zip(records,c['occurrence_slots'],rule['permitted_rows'])):
        old.require(type(record) is dict and set(record)==required)
        for key in ['source_id','physical_pdf_page_1_based','render_sha256','record_role','party_context','historical','date_evidence']:
            old.require(old.canonical(record[key])==old.canonical(slot[key])==old.canonical(row[key]))
        old.require(record['source_sha256']==sources[slot['source_id']]['sha256']==row['source_sha256'])
        old.require(record['transcription_method']=='SOURCE_BOUND_LOCAL_LITERAL_TRANSCRIPTION')
        for key,hash_key in [('official_name_literal','name_utf8_sha256'),('office_label_literal','office_utf8_sha256')]:
            value=record[key]
            old.require(type(value) is str and 0<len(value)<=256 and bool(old.norm(value)))
            old.require(not any(ord(ch)<32 and ch not in '\r\n\t' for ch in value))
            old.require(old.digest(value.encode('utf8'))==record[hash_key])
        old.require(original_record_hashes[index]==row['source_record_canonical_sha256'])
        old.require(record['name_utf8_sha256']==row['source_name_utf8_sha256'])
        old.require(record['office_label_literal']==row['expected_office_literal'] and record['office_utf8_sha256']==row['expected_office_utf8_sha256'])
        party=record['party_context'];key=(old.norm(record['official_name_literal']),row['derived_office_family_key'])
        if party in groups:old.require(groups[party]['identity']==key)
        else:groups[party]={'identity':key,'indexes':[]}
        groups[party]['indexes'].append(index)
        annotations.append({'source_occurrence_index':index,'office_family_key':FAMILY,
                            'source_office_utf8_sha256':record['office_utf8_sha256'],'rule_id':rule['rule_id'],
                            'rule_sha256':RULE_SHA,'independent_literal_audit_sha256':c['independent_transcription_audit']['sha256']})
    old.require(set(groups)=={'Democratic','Republican'})
    old.require({p:len(g['indexes']) for p,g in groups.items()}=={'Democratic':4,'Republican':2})
    old.require(type(audit['approved_occurrences']) is list and old.canonical(audit['approved_occurrences'])==old.canonical([old.occurrence_witness(r) for r in records]))
    old.require(old.is_hash(c['independent_transcription_audit']['sha256']))
    entries=[]
    for party,g in groups.items():
        indexes=g['indexes'];variants=[]
        for i in indexes:
            label=records[i]['office_label_literal']
            if label not in variants:variants.append(label)
        entries.append({'party_context':party,'official_name_literal':records[indexes[0]]['official_name_literal'],
                        'office_family_key':FAMILY,'source_office_literal_variants':variants,'occurrence_indexes':indexes,
                        'record_role':'DOCUMENT_SUPPORTED_CERTIFICATION_ENTRY_ONLY','typed_unknowns':c['unknowns']})
    used={(r['source_id'],r['physical_pdf_page_1_based']) for r in records}
    exclusions=[{k:p[k] for k in ['source_id','physical_pdf_page_1_based','role_office_observation']}
                for p in c['pages'] if (p['source_id'],p['physical_pdf_page_1_based']) not in used]
    private={'schema_version':2,'scope':SCOPE,'source_snapshot_sha256':snapshot_sha,
             'source_transcript_sha256':c['transcription']['sha256'],'occurrences':records,
             'source_record_canonical_sha256':original_record_hashes,'derived_office_contexts':annotations,
             'independent_literal_audit_sha256':c['independent_transcription_audit']['sha256'],
             'reconciled_document_entries':entries,'exclusions_by_page_role':exclusions,'typed_unknowns':c['unknowns']}
    old.require([old.digest(old.canonical(r)) for r in private['occurrences']]==original_record_hashes)
    public={'schema_version':2,'scope':SCOPE,'state':'AL','source_hashes':{s['source_id']:s['sha256'] for s in c['sources']},
            'source_count':5,'physical_page_count':47,'senate_occurrence_count':len(records),'document_supported_name_group_count':len(groups),
            'historical_occurrence_count':sum(r['historical'] for r in records),'typed_unknowns':c['unknowns'],
            'document_role_counts':dict(Counter(r['record_role'] for r in records)), 'office_family_rule_sha256':RULE_SHA,
            'office_literal_form_count':len({r['office_label_literal'] for r in records}),
            'cross_literal_exception_count':sum(r['cross_literal_exception'] for r in rule['permitted_rows']),
            'source_adoption':False,'accepted_coverage_promoted':False,'final_ballots_accepted':0,'cost_usd':0,'model_calls':0}
    validate_public(public)
    return old.DocumentBundle(old.canonical(private),old.canonical(public))


def reconcile(c,transcript,audit,rule):
    return old.safe(lambda:_reconcile(c,transcript,audit,rule))


def validate_public(value):
    keys={'schema_version','scope','state','source_hashes','source_count','physical_page_count','senate_occurrence_count',
          'document_supported_name_group_count','historical_occurrence_count','typed_unknowns','document_role_counts',
          'office_family_rule_sha256','office_literal_form_count','cross_literal_exception_count',
          'source_adoption','accepted_coverage_promoted','final_ballots_accepted','cost_usd','model_calls'}
    old.require(type(value) is dict and set(value)==keys and value['scope']==SCOPE and value['state']=='AL')
    counts={'schema_version':2,'source_count':5,'physical_page_count':47,'senate_occurrence_count':6,
            'document_supported_name_group_count':2,'historical_occurrence_count':2,'office_literal_form_count':3,
            'cross_literal_exception_count':1,'final_ballots_accepted':0,'cost_usd':0,'model_calls':0}
    old.require(all(type(value[k]) is int and value[k]==n for k,n in counts.items()))
    old.require(value['office_family_rule_sha256']==RULE_SHA)
    old.require(value['source_adoption'] is False and value['accepted_coverage_promoted'] is False)
    old.require(type(value['source_hashes']) is dict and set(value['source_hashes'])==old.SOURCE_IDS and all(old.is_hash(h) for h in value['source_hashes'].values()))
    old.require(old.canonical(value['typed_unknowns'])==old.canonical({k:{'kind':'UNKNOWN','reason':v} for k,v in old.UNKNOWN_REASONS.items()}))
    old.require(old.canonical(value['document_role_counts'])==old.canonical(old.ROLE_COUNTS))
    return value
