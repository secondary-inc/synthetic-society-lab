"""Authored tokens/byte arrays and subprocesses only; no actual PDFs/covers/raw inputs."""
import ast
import copy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from civiclab.e01 import clerk2020_contracts_v1 as c
from civiclab.e01 import clerk2020_inspection_m1_v1 as h

ROOT=Path(__file__).resolve().parents[1]
CONTEXT_FIELDS={'office_literal','state_literal','contest_label_literal','event_date_literal','stage_literal','special_term_literal','unit_literal','mode_literal'}


def row_fixture(occurrence='DEMO_A',name='DEMO_ALPHA',party='DEMO_D_A',votes='500',**changes):
    values={'office_literal':'SENATE','state_literal':'GA','contest_label_literal':'2020|C2|2021-2027','event_date_literal':'2020-11-03',
            'stage_literal':'GEN','special_term_literal':'REGULAR','candidate_name_literal':name,'party_line_literal':party,'votes_literal':votes,
            'unit_literal':'STATEWIDE','mode_literal':'TOTAL','footnote_literals':['COMPONENT','COMPLETE']}
    values.update(changes);pieces=[]
    for field,value in values.items():
        if field=='footnote_literals':pieces.extend((field,v) for v in value)
        elif type(value) is str:pieces.append((field,value))
    text='\n'.join(v for field,v in pieces)+'\n';context=c.authored_context('DEMO_SOURCE_'+occurrence.removeprefix('DEMO_'),[text])
    spans=[];start=0
    for field,value in pieces:
        raw=value.encode();spans.append({'source_id':context['source_id'],'source_sha256':context['source_sha256'],'physical_pdf_page_1_based':1,
          'printed_page_label':c.unknown(),'extraction_backend':'AUTHORED_UTF8_PAGE_ARRAY_V1','backend_version':'1.0.0',
          'text_coordinate_system':'UTF8_BYTE_OFFSETS_V1','text_start':start,'text_end':start+len(raw),'text_span_utf8_sha256':c.digest(raw),
          'render_bbox_points':c.unknown(),'field_roles':[field]});start+=len(raw)+1
    row={'schema_version':1,'kind':'HISTORICAL_2020_VOTE_LINE','occurrence_id':occurrence,'source_id':context['source_id'],
      'source_sha256':context['source_sha256'],'source_spans':spans,**values,
      'source_context_span_refs':[i for i,s in enumerate(spans) if s['field_roles'][0] in CONTEXT_FIELDS]}
    return row,context


def record(**kw):return c.normalize_authored(*row_fixture(**kw))
def target(**kw):return {'label':'MOCK','year':2026,'state':'GA','office':'SENATE','seat_class':2,'term_context':'2027-2033',
    'prior_constituency_sha256':'a'*64,'target_constituency_sha256':'a'*64,'feature_as_of':'2026-11-01','cutoff':'2026-11-02',**kw}
def pair():return [record(),record(occurrence='DEMO_R',name='DEMO_BETA',party='DEMO_R',votes='400')]

def document(identifier='DEMO_DOC',pages=None,**kw):
    data={'schema_version':1,'label':'MOCK','backend_id':'AUTHORED_UTF8_PAGE_ARRAY_V1','backend_version':'1.0.0','source_id':identifier,
          'source_role':'AUTHORED_HISTORICAL_COUNTS','pages':['DEMO text'] if pages is None else pages,**kw}
    return h.MAGIC+c.canonical(data)


class PureContracts(unittest.TestCase):
    def test_F01_oracle_exact_raw_detachment_and_schema_field_contracts(self):
        records=[record(votes='550'),record(occurrence='DEMO_R',name='DEMO_BETA',party='DEMO_R',votes='450')]
        before=records[0]._raw;out=c.derive_authored_feature(records,target());self.assertEqual(out.feature()['prior_margin_pp'],10)
        self.assertEqual(out.lineage()['denominator'],1000);self.assertEqual(records[0]._raw,before)
        detached=records[0].raw();detached['candidate_name_literal']='ALTERED';self.assertEqual(records[0]._raw,before)
        self.assertNotIn('ALPHA',repr(records[0]));self.assertNotIn('ALPHA',repr(out))
        methods=json.loads((ROOT/'configs/e01_clerk_2020_senate_input_methods_v1.json').read_text())
        for fields,key in [(c.RAW_FIELDS,'historical_raw_occurrence'),(c.ANNOTATION_FIELDS,'historical_normalized_annotation'),(c.SPAN_FIELDS,'source_span'),(c.NOMINEE_FIELDS,'nominee_observation'),(c.FEATURE_FIELDS,'predictor_feature')]:
            self.assertEqual(set(fields),set(methods['proposed_schema_contracts_not_record_instances'][key]['closed_fields']))
        tree=ast.parse((ROOT/'src/civiclab/e01/pipeline.py').read_text())
        value=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FEATURE_FIELDS' for t in n.targets))
        self.assertEqual(ast.literal_eval(value),set(c.FEATURE_FIELDS))

    def test_F02_regular_special_same_state_year_refuse_merge(self):
        for change in [{'special_term_literal':'SPECIAL'},{'contest_label_literal':'2020|C3|2021-2027'}]:
            with self.subTest(change=change),self.assertRaises(c.ContractRejected):c.derive_authored_feature([pair()[0],record(occurrence='DEMO_S',name='DEMO_BETA',party='DEMO_R',**change)],target())

    def test_F03_later_year_runoff_preserved_never_relabeled_GEN(self):
        runoff=record(event_date_literal='2021-01-05',stage_literal='RUNOFF')
        self.assertEqual(runoff.annotation()['event_year'],2021);self.assertEqual(runoff.annotation()['cycle_year'],2020)
        with self.assertRaises(c.ContractRejected):c.derive_authored_feature([runoff,pair()[1]],target())

    def test_F04_GA_context_unknown_or_missing_evidence_cannot_promote(self):
        for mode in ['missing_header','bad_class','unknown_term','wrong_source','unknown_vote']:
            row,context=row_fixture()
            if mode=='missing_header':row['source_context_span_refs']=[]
            elif mode=='bad_class':row['contest_label_literal']='2020|C0|2021-2027'
            elif mode=='unknown_term':row['contest_label_literal']=c.unknown()
            elif mode=='wrong_source':row['source_sha256']='b'*64
            else:row['votes_literal']=c.unknown()
            with self.subTest(mode=mode),self.assertRaises(c.ContractRejected):
                normalized=c.normalize_authored(row,context);c.derive_authored_feature([normalized,pair()[1]],target())

    def test_F05_LA_multiple_named_party_participants_not_party_pool_or_winner(self):
        records=[record(state_literal='LA'),record(occurrence='DEMO_D2',name='DEMO_GAMMA',party='DEMO_D_A',votes='600',state_literal='LA'),
                 record(occurrence='DEMO_R',name='DEMO_BETA',party='DEMO_R',state_literal='LA')]
        with self.assertRaises(c.ContractRejected):c.derive_authored_feature(records,target(state='LA'))
        self.assertEqual(len(records),3)

    def test_F06_disjoint_fusion_components_combined_once_independent_fraction_oracle(self):
        records=[record(votes='300'),record(occurrence='DEMO_DB',party='DEMO_D_B',votes='200'),
                 record(occurrence='DEMO_DT',party='DEMO_TOTAL_D',votes='500',footnote_literals=['COMBINED_TOTAL','COMPLETE']),
                 pair()[1],record(occurrence='DEMO_RT',name='DEMO_BETA',party='DEMO_TOTAL_R',votes='400',footnote_literals=['COMBINED_TOTAL','COMPLETE'])]
        for representation in ['COMPONENTS','COMBINED_TOTAL']:
            result=c.derive_authored_feature(records,target(),representation);self.assertAlmostEqual(result.feature()['prior_margin_pp'],float(Fraction(100,9)),places=12)
            self.assertEqual(result.lineage()['D'],500);self.assertEqual(result.lineage()['denominator'],900)
        records[-1]=record(occurrence='DEMO_RT',name='DEMO_BETA',party='DEMO_TOTAL_R',votes='401',footnote_literals=['COMBINED_TOTAL','COMPLETE'])
        with self.assertRaises(c.ContractRejected):c.derive_authored_feature(records,target())

    def test_F07_uncontested_unknown_and_zero_refuse_one_is_not_automatic_sentinel(self):
        for value in ['0','-','UNOPPOSED','REDACTED']:
            with self.subTest(value=value),self.assertRaises(c.ContractRejected):c.derive_authored_feature([record(votes=value),pair()[1]],target())
        one=c.derive_authored_feature([record(votes='1'),record(occurrence='DEMO_R',name='DEMO_BETA',party='DEMO_R',votes='1')],target())
        self.assertEqual(one.feature()['prior_margin_pp'],0)
        with self.assertRaises(c.ContractRejected):c.derive_authored_feature([pair()[0]],target())

    def test_F08_ascii_count_grammar_unicode_bool_nonfinite_fraction_negative(self):
        self.assertEqual(record(votes='1,234').annotation()['votes'],1234)
        for value in ['1.5','-1','−1','1e3','1,23','01','１２','NaN','Infinity',True,4.2]:
            with self.subTest(value=value),self.assertRaises(c.ContractRejected):record(votes=value)

    def test_F09_utf8_offsets_header_page_role_and_aliases(self):
        row,context=row_fixture(name='DEMO_ÉLISE')
        rec=c.normalize_authored(row,context);self.assertEqual(rec.raw()['candidate_name_literal'],'DEMO_ÉLISE')
        for mode in ['middle_utf8','header_role','page','text_hash','bbox','context_mutation']:
            modified=copy.deepcopy(row);ctx=copy.deepcopy(context);span=next(s for s in modified['source_spans'] if s['field_roles']==['candidate_name_literal'])
            if mode=='middle_utf8':span['text_start']+=len('DEMO_')+1
            elif mode=='header_role':modified['source_spans'][0]['field_roles']=['state_literal']
            elif mode=='page':span['physical_pdf_page_1_based']=2
            elif mode=='text_hash':span['text_span_utf8_sha256']='b'*64
            elif mode=='bbox':span['render_bbox_points']=[0,0,1,1]
            else:ctx['pages'][0]+='ALTERED'
            with self.subTest(mode=mode),self.assertRaises(c.ContractRejected):c.normalize_authored(modified,ctx)

    def test_F10_duplicates_summary_unit_mode_incomplete_and_other_votes(self):
        extra=record(occurrence='DEMO_O',name='DEMO_OTHER_PERSON',party='DEMO_OTHER',votes='700')
        out=c.derive_authored_feature(pair()+[extra],target());self.assertEqual(out.lineage()['excluded_other_votes'],700)
        self.assertEqual(out.lineage()['denominator'],900)
        for records in [pair()+[pair()[0]],pair()+[record(occurrence='DEMO_SUM',footnote_literals=['SUMMARY','COMPLETE'])],
                        [record(footnote_literals=['COMPONENT']),pair()[1]]]:
            with self.assertRaises(c.ContractRejected):c.derive_authored_feature(records,target())
        for change in [{'unit_literal':'COUNTY'},{'mode_literal':'ABSENTEE'}]:
            with self.assertRaises(c.ContractRejected):record(**change)

    def test_F11_nominee_votes_and_wrong_office_cannot_become_historical_feature(self):
        row,context=row_fixture();row['kind']='DATED_2026_NOMINEE_LINE'
        with self.assertRaises(c.ContractRejected):c.normalize_authored(row,context)
        for office in ['HOUSE','PRESIDENT']:
            with self.assertRaises(c.ContractRejected):c.derive_authored_feature([record(office_literal=office),pair()[1]],target())
        # A separate nominee schema explicitly has no numeric election fields.
        nominee={k:c.unknown() for k in c.NOMINEE_FIELDS};nominee.update(schema_version=1,kind='DATED_2026_NOMINEE_LINE',votes=100)
        with self.assertRaises(c.ContractRejected):c.validate_nominee_authored(nominee,context)

    def test_F12_wrong_seat_year_term_geography_House_lag_and_postcutoff(self):
        for change in [{'seat_class':3},{'office':'HOUSE'},{'year':2024},{'term_context':'2028-2034'},
                       {'target_constituency_sha256':'b'*64},{'feature_as_of':'2026-11-04'}]:
            with self.subTest(change=change),self.assertRaises(c.ContractRejected):c.derive_authored_feature(pair(),target(**change))
        with self.assertRaises(c.ContractRejected):c.derive_authored_feature([record(contest_label_literal='2024|C2|2025-2031'),pair()[1]],target())

    def test_F13_roworder_detachment_coedited_annotations_and_closed_schemas(self):
        first=c.derive_authored_feature(pair(),target()).feature();second=c.derive_authored_feature(list(reversed(pair())),target()).feature()
        self.assertEqual(first,second)
        rec=pair()[0];annotation=rec.annotation();annotation['votes']=10000
        forged=c.AuthoredRecord(rec._raw,c.canonical(annotation),rec._context)
        with self.assertRaises(c.ContractRejected):c.derive_authored_feature([forged,pair()[1]],target())
        row,ctx=row_fixture();row['secret_extra']='PRIVATE_LITERAL'
        with self.assertRaises(c.ContractRejected) as cm:c.normalize_authored(row,ctx)
        self.assertNotIn('PRIVATE_LITERAL',str(cm.exception));self.assertIsNone(cm.exception.__context__)
        with self.assertRaises(c.ContractRejected):c.authored_context('real-source',['x'])

    def test_F14_pure_cancel_systemexit_and_sanitized_errors(self):
        for error in [ValueError,KeyboardInterrupt,SystemExit]:
            expected=error if error in [KeyboardInterrupt,SystemExit] else c.ContractRejected
            with patch.object(c,'_raw',side_effect=error('PRIVATE_LITERAL')),self.assertRaises(expected) as cm:c.normalize_authored({}, {})
            self.assertNotIn('PRIVATE_LITERAL',str(cm.exception));self.assertIsNone(cm.exception.__context__)

    def test_F15_allowlist_outcome_path_and_key_infiltration(self):
        for field in ['observed_margin_pp','outcomes','OPENROUTER_API_KEY','winner']:
            t=target();t[field]='PRIVATE_LITERAL'
            with self.assertRaises(c.ContractRejected):c.derive_authored_feature(pair(),t)
        f=c.derive_authored_feature(pair(),target()).feature();f['source_hashes']=['outcomes/2026.json']
        with self.assertRaises(c.ContractRejected):c.matched_authored_status([f['race_id']],[f])

    def test_F16_missing_prior_preserves_selected_ids_no_replacement_or_full_claim(self):
        f=c.derive_authored_feature(pair(),target()).feature();ids=[f['race_id'],'2026-LA-SENATE-STATEWIDE-C2']
        status=c.matched_authored_status(ids,[f]);self.assertEqual(status['selected_ids'],ids);self.assertEqual(status['blocked_ids'],ids[1:])
        self.assertFalse(status['replacement_permitted']);self.assertEqual(status['status'],'BLOCKED_NO_PRIOR_FEATURE')
        wrong=copy.deepcopy(f);wrong['race_id']='2026-XX-SENATE-STATEWIDE-C2'
        with self.assertRaises(c.ContractRejected):c.matched_authored_status(ids,[wrong])


class InspectionHarness(unittest.TestCase):
    def test_fixed_backend_real_subprocess_positive_replay_and_metrics(self):
        docs=[document(pages=['DEMO first','DEMO unicode É']),document('DEMO_OTHER',['DEMO nominee'],source_role='AUTHORED_NOMINEE_COMPILATION')]
        one=h.inspect_authored(docs);two=h.inspect_authored(docs)
        self.assertEqual(one['projection'],two['projection']);p=one['projection'];self.assertEqual(p['page_count'],3)
        self.assertEqual(p['candidate_or_vote_records_parsed'],0);self.assertFalse(p['actual_source_access']);self.assertNotIn('unicode',c.canonical(p).decode())
        self.assertGreater(one['resources']['rss_peak_bytes'],0);self.assertTrue(one['resources']['cpu_limit_applied'])

    def test_actual_source_factory_refuses_before_any_argument_or_filesystem_touch(self):
        class Bomb:
            def __fspath__(self):raise AssertionError('ACTUAL_SOURCE_PATH_TOUCHED')
        with patch.object(h,'load_policy') as load,patch.object(h.subprocess,'Popen') as popen,self.assertRaises(c.ContractRejected):h.inspect_actual(Bomb())
        load.assert_not_called();popen.assert_not_called()

    def test_input_byte_document_backend_version_label_and_magic_bounds_before_dispatch(self):
        variants=[[b'%PDF- actual'],[document(label='REAL')],[document(backend_version='latest')],[document(backend_id='pypdf')],
                  [document(identifier='clerk2020_statistics')],[b'x'*1048577],[document('DEMO_A'),document('DEMO_B'),document('DEMO_C')],
                  [document('DEMO_A'),document('DEMO_A')]]
        for docs in variants:
            with self.subTest(size=len(docs)),patch.object(h.subprocess,'Popen') as popen,self.assertRaises(c.ContractRejected):h.inspect_authored(docs)
            popen.assert_not_called()

    def test_page_text_json_duplicate_nonfinite_and_depth_bounds(self):
        variants=[[document(pages=['x']*101)],[document('DEMO_A',['x']*100),document('DEMO_B',['x']*20)],
                  [document(pages=['x'*40001])],[h.MAGIC+b'{"schema_version":1,"schema_version":1}'],[h.MAGIC+b'{"pages":NaN}'],
                  [h.MAGIC+('['*15+'0'+']'*15).encode()]]
        for docs in variants:
            with patch.object(h.subprocess,'Popen') as popen,self.assertRaises(c.ContractRejected):h.inspect_authored(docs)
            popen.assert_not_called()

    def test_policy_coedited_or_enabled_config_fails_compiled_digest(self):
        raw,cfg=h.load_policy();self.assertFalse(cfg['actual_source_enabled'])
        for mode in ['wall_seconds','output_bytes','actual_source_enabled','backend']:
            changed=copy.deepcopy(cfg)
            if mode in cfg['limits']:changed['limits'][mode]*=10
            elif mode=='backend':changed['backend']['version']='other'
            else:changed[mode]=True
            with self.assertRaises(c.ContractRejected):h.policy_from_bytes(c.canonical(changed))

    def test_response_semantic_coedit_resource_unknown_or_spoof_and_backend_refused(self):
        docs=[document()];raw,cfg=h.load_policy();expected=h.project_authored(docs,cfg);valid=h.inspect_authored(docs)
        for mode in ['rss','bool_rss','missing_rss','CPU','AS','source_hash','page_count','backend','extra']:
            bad=copy.deepcopy({k:valid[k] for k in ['projection','resources']})
            if mode=='rss':bad['resources']['rss_peak_bytes']=cfg['limits']['rss_peak_bytes']+1
            elif mode=='bool_rss':bad['resources']['rss_peak_bytes']=True
            elif mode=='missing_rss':bad['resources'].pop('rss_peak_bytes')
            elif mode=='CPU':bad['resources']['cpu_limit_applied']=False
            elif mode=='AS':bad['resources']['rss_backend']='UNKNOWN'
            elif mode=='source_hash':bad['projection']['documents'][0]['input_sha256']='0'*64
            elif mode=='page_count':bad['projection']['page_count']=2
            elif mode=='backend':bad['projection']['backend']['version']='LATEST'
            else:bad['extra']='PRIVATE_LITERAL'
            with self.subTest(mode=mode),self.assertRaises(c.ContractRejected):h.validate_response(c.canonical(bad),expected,cfg)

    def _native_replacement(self,script):
        original=subprocess.Popen;children=[]
        def launch(*args,**kwargs):
            if args and args[0][0]=='/bin/ps':return original(*args,**kwargs)
            child=original([sys.executable,'-c',script],**kwargs);children.append(child);return child
        return launch,children

    def test_native_wall_timeout_kills_reaps_once_no_retry(self):
        launch,children=self._native_replacement('import time;time.sleep(30)');start=time.monotonic()
        with patch.object(h.subprocess,'Popen',side_effect=launch),self.assertRaises(c.ContractRejected):h.inspect_authored([document()])
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll());self.assertLess(time.monotonic()-start,8)

    def test_native_stdout_stderr_nonzero_and_malformed_streams_refuse_reap(self):
        scripts=['import os;os.write(1,b"x"*300000)','import os;os.write(2,b"x"*5000)',
                 'import sys;sys.exit(2)','import sys;sys.stdin.buffer.read();print("{}")']
        for script in scripts:
            launch,children=self._native_replacement(script)
            with self.subTest(script=script),patch.object(h.subprocess,'Popen',side_effect=launch),self.assertRaises(c.ContractRejected):h.inspect_authored([document()])
            self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll())

    def test_cancel_SystemExit_exchange_failure_kills_reaps_and_hides_literals(self):
        for error in [KeyboardInterrupt,SystemExit,OSError]:
            launch,children=self._native_replacement('import time;time.sleep(30)')
            expected=error if error in [KeyboardInterrupt,SystemExit] else c.ContractRejected
            with patch.object(h.subprocess,'Popen',side_effect=launch),patch.object(h,'_exchange',side_effect=error('PRIVATE_LITERAL')),self.assertRaises(expected) as cm:h.inspect_authored([document()])
            self.assertIsNotNone(children[0].poll());self.assertNotIn('PRIVATE_LITERAL',str(cm.exception));self.assertIsNone(cm.exception.__context__)

    def test_numeric_page_and_text_boundary_projections_are_MOCK_only(self):
        raw,cfg=h.load_policy()
        exact=h.project_authored([document('DEMO_A',['x']*100),document('DEMO_B',['x']*19)],cfg)
        self.assertEqual(exact['page_count'],119)
        exact=h.project_authored([document(pages=['x'*40000])],cfg);self.assertEqual(exact['text_characters'],40000)
        with patch.object(h.subprocess,'Popen') as popen,self.assertRaises(c.ContractRejected):h.inspect_authored([document(pages=['x'*40001])])
        popen.assert_not_called()

    def test_native_sampled_RSS_threshold_stops_owned_child(self):
        launch,children=self._native_replacement('import time;x=bytearray(160*1024*1024);time.sleep(30)')
        seen=[];original_run=subprocess.run
        def probe(*args,**kw):
            result=original_run(*args,**kw)
            if args and args[0][0]=='/bin/ps' and result.stdout.strip().isdigit():seen.append(int(result.stdout.strip())*1024)
            return result
        start=time.monotonic()
        with patch.object(h.subprocess,'Popen',side_effect=launch),patch.object(h.subprocess,'run',side_effect=probe),self.assertRaises(c.ContractRejected):h.inspect_authored([document()])
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll());self.assertTrue(any(v>134217728 for v in seen));self.assertLess(time.monotonic()-start,5)

    def test_unknown_RSS_or_nonfinite_regressive_clock_kills_reaps(self):
        for mode in ['rss','nan','inf','backward']:
            launch,children=self._native_replacement('import time;time.sleep(30)')
            with patch.object(h.subprocess,'Popen',side_effect=launch):
                if mode=='rss':
                    with patch.object(h,'_sample_rss',side_effect=c.ContractRejected()),self.assertRaises(c.ContractRejected):h.inspect_authored([document()])
                else:
                    values=[float('nan')] if mode=='nan' else ([float('inf')] if mode=='inf' else [100.,99.])
                    with patch.object(h.time,'monotonic',side_effect=values),self.assertRaises(c.ContractRejected):h.inspect_authored([document()])
            self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll())


class AdditionalContractCoverage(unittest.TestCase):
    def test_nominee_positive_has_distinct_role_unknowns_and_no_vote_channel(self):
        values={'office_literal':'SENATE','state_literal':'GA','district_or_seat_literal':'C2','candidate_name_literal':'DEMO_NOMINEE','party_literal':'DEMO_D_A'}
        text='\n'.join(values.values())+'\n';ctx=c.authored_context('DEMO_NOMINEES',[text],'AUTHORED_NOMINEE_COMPILATION')
        spans=[];start=0
        for field,value in values.items():
            raw=value.encode();spans.append({'source_id':ctx['source_id'],'source_sha256':ctx['source_sha256'],'physical_pdf_page_1_based':1,'printed_page_label':c.unknown(),
                'extraction_backend':'AUTHORED_UTF8_PAGE_ARRAY_V1','backend_version':'1.0.0','text_coordinate_system':'UTF8_BYTE_OFFSETS_V1',
                'text_start':start,'text_end':start+len(raw),'text_span_utf8_sha256':c.digest(raw),'render_bbox_points':c.unknown(),'field_roles':[field]});start+=len(raw)+1
        row={'schema_version':1,'kind':'DATED_2026_NOMINEE_LINE','occurrence_id':'DEMO_N','source_id':ctx['source_id'],'source_sha256':ctx['source_sha256'],
             'source_spans':spans,'publication_date_evidence':c.unknown(),**values,'footnote_literals':[],'source_role':'DATED_NOMINEE_OBSERVATION_ONLY',
             'typed_unknowns':{k:c.unknown() for k in ['printed_on_final_ballot','legal_nominee_adjudication','latest_amendment_complete','independent_cutoff_binding']}}
        out=c.validate_nominee_authored(row,ctx);self.assertEqual(out,row)
        for field in ['votes','observed_margin_pp','winner','returns']:
            changed=copy.deepcopy(row);changed[field]=10
            with self.assertRaises(c.ContractRejected):c.validate_nominee_authored(changed,ctx)
        changed=copy.deepcopy(row);changed['source_spans'][0]['field_roles']=['votes_literal']
        with self.assertRaises(c.ContractRejected):c.validate_nominee_authored(changed,ctx)
        with self.assertRaises(c.ContractRejected):c.normalize_authored(row,ctx)

    def test_authored_cross_page_continuations_keep_offsets_and_header_roles(self):
        row,ctx=row_fixture(name='DEMO_ÉLISE');old=ctx['pages'][0].encode();split=7
        first=row['source_spans'][:split];last=row['source_spans'][split:];cut=last[0]['text_start']
        new=c.authored_context(ctx['source_id'],[old[:cut].decode(),old[cut:].decode()]);row['source_sha256']=new['source_sha256']
        for i,span in enumerate(row['source_spans']):
            span['source_sha256']=new['source_sha256']
            if i>=split:span['physical_pdf_page_1_based']=2;span['text_start']-=cut;span['text_end']-=cut
        rec=c.normalize_authored(row,new);self.assertEqual(rec.raw()['candidate_name_literal'],'DEMO_ÉLISE')
        altered=copy.deepcopy(row);altered['source_spans'][0]['physical_pdf_page_1_based']=2
        with self.assertRaises(c.ContractRejected):c.normalize_authored(altered,new)

    def test_existing_private_package_guard_on_authored_temporary_run(self):
        import tempfile
        from civiclab.common import RunStore
        from civiclab.reproduction import build_package
        rec=pair()[0]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve()
            with RunStore(root,'E01',{'label':'MOCK','role':'CLERK_M1_AUTHORED_ONLY'},kind='MOCK') as run:
                run.write('clerk_rows.local.json',{'label':'MOCK','rows':[rec.raw()]});run.finish({'status':'MOCK_ONLY'})
            with self.assertRaisesRegex(ValueError,'local-only'):build_package(root,root/'must-refuse.zip',[run.path.name])
            self.assertFalse((root/'must-refuse.zip').exists())

    def test_custom_objects_nonfinite_missing_required_fields_and_source_aliases_refuse(self):
        class Evil(dict):pass
        row,ctx=row_fixture()
        with self.assertRaises(c.ContractRejected):c.normalize_authored(Evil(row),ctx)
        for field in ['candidate_name_literal','source_spans','votes_literal','occurrence_id']:
            bad=copy.deepcopy(row);bad.pop(field)
            with self.assertRaises(c.ContractRejected):c.normalize_authored(bad,ctx)
        bad=copy.deepcopy(ctx);bad['pages']=[float('nan')]
        with self.assertRaises(c.ContractRejected):c.normalize_authored(row,bad)
        source=c.authored_context('DEMO_X',['x']);source['pages'][0]='y'
        with self.assertRaises(c.ContractRejected):c.validate_span({},source)


class CleanupPermissionRace(unittest.TestCase):
    def test_group_permission_denial_direct_owned_child_kill_and_reap(self):
        launch,children=InspectionHarness()._native_replacement('import time;time.sleep(30)')
        with patch.object(h.subprocess,'Popen',side_effect=launch),patch.object(h,'_exchange',side_effect=c.ContractRejected()),patch.object(h.os,'killpg',side_effect=PermissionError()),self.assertRaises(c.ContractRejected):
            h.inspect_authored([document()])
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll())

    def test_unknown_or_nonvoting_state_cannot_be_known_Senate_feature(self):
        for state in ['XX','ZZ','DC']:
            with self.subTest(state=state),self.assertRaises(c.ContractRejected):record(state_literal=state)
        self.assertEqual(len(c.SENATE_STATES),50)
