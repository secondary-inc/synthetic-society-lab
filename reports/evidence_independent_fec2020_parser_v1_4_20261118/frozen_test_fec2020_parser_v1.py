"""Fictional cells and inert workbook objects only; no FEC source is opened."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import signal
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

from civiclab.e01 import fec2020_parser_v1 as p

ROOT = Path(__file__).resolve().parents[1]


def cell(value):
    return p.Cell(value, "s" if type(value) is str else "b" if type(value) is bool else "n")


def archive(members=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, value in (members or {"[Content_Types].xml": "<Types/>"}).items():
            z.writestr(name, value)
    return stream.getvalue()


def source(raw=b"AUTHORED_FEC_FIXTURE"):
    return {"source_id": "AUTHORED_FEC_FIXTURE", "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "provenance": "MOCK"}


def candidate(number, state="AL", party="D", name="Fictional Delta", votes=12, *, contest="S", fec="S0ZZ00001", runoff=None, footnote=None):
    values = [None]*26
    for column, value in {0:number, 1:state, 2:"Fictional state label", 3:contest, 4:fec, 8:name, 10:party, 15:votes, 17:runoff, 23:footnote}.items():
        values[column] = value
    return [cell(value) for value in values]


def total(number, votes=20, *, state="AL", contest="S", runoff=None, label="Total State Votes:"):
    row = candidate(number, state, None, None, votes, contest=contest, fec="n/a", runoff=runoff)
    row[9] = cell(label)
    return row


def tables(contract):
    result = {title: [[cell(None) for _ in range(columns)] for _ in range(rows)] for title, (rows, columns) in p.RANGES.items()}
    result[p.SENATE][0] = [cell(v) for v in contract["input_contract"]["header_literal"]]
    for number in range(2,543):
        result[p.SENATE][number-1][0] = cell(number)
    summary = result[p.SUMMARY]
    summary[2][1:] = [cell(v) for v in ["PRIMARY ELECTION (D)", "PRIMARY ELECTION (R)", "PRIMARY ELECTION (O)", "GENERAL ELECTION (D)", "GENERAL ELECTION (R)", "GENERAL ELECTION (O)"]]
    summary[3] = [cell(v) for v in ["State", "Democratic", "Republican", "Other", "Democratic", "Republican", "Other"]]
    states = "AL AK AS AZ AR CA CO CT DE DC FL GA GU HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND MP OH OK OR PA PR RI SC SD TN TX UT VT VI VA WA WV WI WY".split()
    for index, state in enumerate(states, 4):
        summary[index][0] = cell(state)
    result[p.SENATE][2] = candidate(3)
    result[p.SENATE][3] = candidate(4,party="R",name="Fictional Rho",votes=8,fec="S0ZZ00002")
    result[p.SENATE][4] = total(5)
    summary[4][4:] = [cell(12),cell(8),cell(0)]
    return result


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = p.load_contract(ROOT/"configs/e01_fec2020_senate_mapping_v1.json")
    def setUp(self):
        self.tables = tables(self.contract)
    def parsed(self):
        return p.result_from_tables(self.tables,self.contract,source())

    def test_candidate_audit_is_deterministic_nonadopted_and_preserves_witness(self):
        before = deepcopy(self.tables)
        first, second = self.parsed(), self.parsed()
        self.assertEqual(p.packed(first),p.packed(second));self.assertEqual(self.tables,before)
        record=first['records'][1]
        self.assertEqual(record['raw_row']['row'],3);self.assertEqual(record['stages'][2]['cell'],'P3')
        self.assertEqual(record['raw_row_sha256'],p.digest(record['raw_row']))
        self.assertEqual(record['source'],source());self.assertEqual(record['stages'][2]['votes'],12)
        self.assertEqual(first['features'],[])
        self.assertTrue(all(first[k] is False for k in p.FALSE_FLAGS))

    def test_total_and_party_subtotal_not_added_to_candidates(self):
        subtotal=total(6,votes=None,label='Party Votes:');subtotal[10]=cell('D');subtotal[11]=cell(100)
        self.tables[p.SENATE][5]=subtotal
        controls=self.parsed()['stage_controls'];general=next(r for r in controls if r['state']=='AL' and r['stage']=='GENERAL')
        self.assertEqual(general['candidate_sum'],20);self.assertEqual(general['candidate_count'],2)
        self.assertEqual(general['status'],'PASS_INTERNAL_COUNT')

    def test_mismatch_is_visible_and_does_not_become_an_adopted_feature(self):
        self.tables[p.SENATE][4][15]=cell(21)
        result=self.parsed();self.assertIn('MISMATCH',[r['status'] for r in result['stage_controls']]);self.assertEqual(result['features'],[])

    def test_missing_zero_and_one_are_distinct(self):
        for value, expected in [(None,None),(' ',None),('*',None),('n/a',None),('-',None),(0,0),(1,1),(1.0,1)]:
            with self.subTest(value=value):self.assertEqual(p.count(value)['votes'],expected)
        self.assertEqual(p.count(0)['status'],'OBSERVED_INTEGER')

    def test_invalid_counts_are_refused_without_rounding_or_string_conversion(self):
        for value in [True,False,-1,1.2,float('nan'),float('inf'),'1','1,000','−1','1*',10**13]:
            with self.subTest(value=value),self.assertRaises(p.ParserRefused):p.count(value)

    def test_removed_MT_marker_requires_exact_row_and_footnote(self):
        good=candidate(304,state='MT',party='GRE',votes='#',footnote=p.REMOVAL_FOOTNOTE)
        self.tables[p.SENATE][303]=good
        result=self.parsed();removed=result['records'][302]
        self.assertEqual(removed['role'],'FOOTNOTE_REMOVAL');self.assertIsNone(removed['stages'][2]['votes'])
        self.tables[p.SENATE][303][23]=cell('Not the source-bound footnote')
        self.assertEqual(self.parsed()['records'][302]['stages'][2]['status'],'UNKNOWN_BLOCKED')
        self.assertEqual(p.count('#')['status'],'UNKNOWN_BLOCKED')

    def test_primary_convention_marker_does_not_erase_general_count(self):
        self.tables[p.SENATE][2][11]=cell('*')
        record=self.parsed()['records'][1]
        self.assertEqual(record['stages'][0]['status'],'NONNUMERIC_MARKER');self.assertEqual(record['stages'][2]['votes'],12)

    def test_primary_votes_never_supply_missing_general_count(self):
        row=self.tables[p.SENATE][2];row[11]=cell(777);row[15]=cell(None)
        record=self.parsed()['records'][1]
        self.assertEqual(record['role'],'PRIMARY_ONLY');self.assertIsNone(record['stages'][2]['votes'])
        self.assertEqual(record['stages'][0]['votes'],777)

    def test_GA_events_and_terms_are_separate_with_2021_runoff_year(self):
        self.tables[p.SENATE][83]=candidate(84,state='GA',contest='S-FULL TERM',runoff=10,footnote='General Runoff Election on January 5, 2021.')
        self.tables[p.SENATE][96]=candidate(97,state='GA',contest='S-UNEXPIRED TERM',runoff=7,footnote='Special General Runoff Election on January 5, 2021.')
        result=self.parsed();record=result['records'][82]
        self.assertEqual(record['stages'][3]['event_date'],'2021-01-05');self.assertEqual(record['stages'][3]['event_year'],2021)
        self.assertEqual(record['stages'][3]['cycle_year'],2020);self.assertIsNone(record['stages'][2]['event_date'])
        groups=[r for r in result['stage_controls'] if r['state']=='GA' and r['candidate_count']]
        self.assertEqual(len(groups),4)
        slot=next(r for r in result['cohort'] if r['state']=='GA');self.assertEqual(slot['general_candidate_observations'],1)
        self.assertIn('CONDITIONAL_GENERAL_PROTOCOL_UNREVIEWED',slot['blockers'])

    def test_runoff_without_date_witness_is_unknown(self):
        row=candidate(84,state='GA',contest='S-FULL TERM',runoff=10)
        record=p.row_record(row,84,source());self.assertIsNone(record['stages'][3]['event_date'])

    def test_party_ambiguities_stay_unreviewed_and_coalition_count_is_once(self):
        for index,state,party in [(16,'AK','N(D)/D'),(261,'MN','DFL'),(402,'OR','DEM/IP/WF')]:
            self.tables[p.SENATE][index]=candidate(index+1,state=state,party=party)
        result=self.parsed()
        for state in ('AK','MN','OR'):
            row=next(r for r in result['records'] if r['state']==state)
            self.assertEqual(row['party_bucket'],'UNKNOWN');self.assertIn('PARTY_IDENTITY_UNREVIEWED',row['blockers'])
        group=next(r for r in result['stage_controls'] if r['state']=='OR' and r['stage']=='GENERAL')
        self.assertEqual(group['candidate_sum'],12);self.assertEqual(group['candidate_count'],1)

    def test_unknown_party_never_defaults_to_other(self):
        self.tables[p.SENATE][2][10]=cell('NOT_A_KNOWN_PARTY')
        record=self.parsed()['records'][1];self.assertEqual(record['party_bucket'],'UNKNOWN')

    def test_LA_multiple_candidates_block_instead_of_summing_nominees(self):
        self.tables[p.SENATE][2]=candidate(3,state='LA')
        self.tables[p.SENATE][3]=candidate(4,state='LA',name='Fictional Second D',fec='S0ZZ00002',votes=8)
        self.tables[p.SENATE][4]=total(5,state='LA')
        slot=next(r for r in self.parsed()['cohort'] if r['state']=='LA')
        self.assertIn('REQUIRES_EXACTLY_ONE_D',slot['blockers']);self.assertIsNone(slot['prior_margin_pp'])

    def test_full_33_slot_frame_retained_and_context_state_not_replacement(self):
        self.tables[p.SENATE][7]=candidate(8,state='AZ')
        result=self.parsed();self.assertEqual(len(result['cohort']),33)
        self.assertNotIn('AZ',[r['state'] for r in result['cohort']]);self.assertTrue(any(r['state']=='AZ' for r in result['records']))
        for state in ('AR','ME'):
            self.assertEqual(next(r for r in result['cohort'] if r['state']==state)['status'],'BLOCKED_NOT_ADOPTED')

    def test_duplicate_FEC_or_same_name_different_FEC_refused(self):
        for fec,name in [('S0ZZ00001','Different name'),('S0ZZ99999','Fictional Delta')]:
            self.tables[p.SENATE][5]=candidate(6,fec=fec,name=name)
            with self.assertRaisesRegex(p.ParserRefused,'DUPLICATE'):self.parsed()

    def test_same_FEC_in_distinct_term_not_joined(self):
        self.tables[p.SENATE][5]=candidate(6,contest='S-UNEXPIRED TERM')
        result=self.parsed();self.assertEqual(len([r for r in result['records'] if r['candidate_name']=='Fictional Delta']),2)

    def test_no_forward_fill_unknown_role_and_wrong_total_label_refused(self):
        for column,value in [(1,None),(9,'Unexpected total'),(3,'HOUSE')]:
            original=self.tables[p.SENATE][2][column];self.tables[p.SENATE][2][column]=cell(value)
            with self.assertRaises(p.ParserRefused):self.parsed()
            self.tables[p.SENATE][2][column]=original
        self.tables[p.SENATE][4][9]=cell('Total Full Term State Votes:')
        with self.assertRaises(p.ParserRefused):self.parsed()

    def test_NC_whitespace_control_is_not_a_candidate(self):
        row=total(386,state='NC');row[8]=cell(' ');row[10]=cell(' ')
        self.assertEqual(p.row_record(row,386,source())['role'],'CONTEST_TOTAL')

    def test_combined_total_and_extra_columns_refused(self):
        for column in (19,20,24,25):
            row=candidate(3);row[column]=cell(12)
            with self.assertRaises(p.ParserRefused):p.row_record(row,3,source())

    def test_formula_error_and_nonprimitive_cells_refused(self):
        for value in [p.Cell('=1+1','f'),p.Cell('#N/A','e'),p.Cell(object(),'s'),p.Cell(float('nan'),'n')]:
            self.tables[p.SENATE][2][15]=value
            with self.assertRaises(p.ParserRefused):self.parsed()

    def test_header_ordinal_missing_extra_and_width_refused(self):
        rows=self.tables[p.SENATE]
        for changed in [rows[:-1],rows+[rows[-1]],[[cell(True),*rows[0][1:]],*rows[1:]],[[cell('changed'),*rows[0][1:]],*rows[1:]]]:
            with self.assertRaises(p.ParserRefused):p.audit_rows(changed,self.contract,source())
        wrong=deepcopy(rows);wrong[2]=wrong[2][:-1]
        with self.assertRaises(p.ParserRefused):p.audit_rows(wrong,self.contract,source())

    def test_summary_partial_controls_and_mismatches_visible(self):
        self.tables[p.SUMMARY][4][6]=cell(None)
        result=self.parsed();summary=[r for r in result['party_summary_controls'] if r['state']=='AL']
        self.assertEqual([r['status'] for r in summary],['PASS_INTERNAL_COUNT','PASS_INTERNAL_COUNT','UNAVAILABLE_CONTROL'])
        self.tables[p.SUMMARY][4][4]=cell(13)
        self.assertEqual(next(r for r in self.parsed()['party_summary_controls'] if r['state']=='AL' and r['bucket']=='D')['status'],'MISMATCH')

    def test_GA_summary_composition_not_guessed_even_when_values_match(self):
        self.tables[p.SENATE][83]=candidate(84,state='GA',contest='S-FULL TERM')
        self.tables[p.SUMMARY][15][4]=cell(12)
        row=next(r for r in self.parsed()['party_summary_controls'] if r['state']=='GA' and r['bucket']=='D')
        self.assertEqual(row['status'],'BLOCKED_EVENT_OR_PARTY_COMPOSITION');self.assertIsNone(row['candidate_sum'])

    def test_percentage_diagnostic_never_reconstructs_votes(self):
        self.tables[p.SENATE][2][16]=cell(.6)
        result=self.parsed();self.assertEqual(result['percentage_diagnostics'][0]['status'],'PASS_DIAGNOSTIC')
        self.tables[p.SENATE][2][16]=cell(.7)
        self.assertEqual(self.parsed()['percentage_diagnostics'][0]['status'],'MISMATCH')
        self.tables[p.SENATE][2][15]=cell(None)
        self.assertIsNone(self.parsed()['records'][1]['stages'][2]['votes'])

    def test_duplicate_summary_state_and_unknown_state_are_refused(self):
        for state in ('AL','ZZ'):
            self.tables[p.SUMMARY][5][0]=cell(state)
            with self.assertRaises(p.ParserRefused):self.parsed()

    def test_contract_coedit_or_authority_flags_are_refused(self):
        for field,value in [('adoption',True),('input_contract',dict(self.contract['input_contract'],header_literal=[]))]:
            altered=deepcopy(self.contract);altered[field]=value
            with self.assertRaises(p.ParserRefused):p.audit_rows(self.tables[p.SENATE],altered,source())

    def test_output_limit_refuses_without_publishing_partial_result(self):
        for number in range(3,542):
            row=candidate(number,name='Z'*4090+str(number),fec='n/a');row[23]=cell('X'*4096)
            self.tables[p.SENATE][number-1]=row
        with self.assertRaisesRegex(p.ParserRefused,'OUTPUT_BOUND'):self.parsed()


class InertSheet:
    def __init__(self,rows):
        self.rows=rows;self.max_row=len(rows);self.max_column=len(rows[0]);self.calls=[]
    def iter_rows(self,**kwargs):
        self.calls.append(kwargs)
        for row in self.rows:yield [SimpleNamespace(value=c.value,data_type=c.kind) for c in row]


class InertBook:
    def __init__(self,tables):self.sheets={k:InertSheet(v) for k,v in tables.items()};self.closed=False;self.close_error=False
    def __getitem__(self,name):return self.sheets[name]
    def close(self):
        self.closed=True
        if self.close_error:raise OSError('AUTHORED_CLOSE_FAILURE')


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.contract=p.load_contract(ROOT/'configs/e01_fec2020_senate_mapping_v1.json')
        self.tables=tables(self.contract);self.raw=archive();self.book=InertBook(self.tables);self.calls=[]
        def load(stream,**kwargs):self.calls.append(kwargs);self.assertEqual(stream.read(),self.raw);return self.book
        self.reader=SimpleNamespace(__version__='3.1.5',load_workbook=load)
    def run_adapter(self):return p.read_candidate_bytes(self.raw,self.contract,source(self.raw),reader=self.reader)

    def test_inert_adapter_bounds_options_version_closed_output_and_no_side_effects(self):
        result=self.run_adapter();self.assertEqual(result['reader']['version'],'3.1.5');self.assertTrue(self.book.closed)
        self.assertEqual(self.calls,[dict(read_only=True,data_only=False,keep_links=False)])
        for title,(rows,cols) in p.RANGES.items():self.assertEqual(self.book.sheets[title].calls,[dict(min_row=1,max_row=rows,min_col=1,max_col=cols)])
        self.assertEqual(result['features'],[]);self.assertEqual(len(result['cohort']),33)

    def test_hash_mismatch_and_wrong_reader_version_refuse_before_loading(self):
        with self.assertRaisesRegex(p.ParserRefused,'WORKBOOK_PIN'):p.read_candidate_bytes(self.raw+b'X',self.contract,source(self.raw),reader=self.reader)
        self.reader.__version__='3.1.4'
        with self.assertRaisesRegex(p.ParserRefused,'READER_VERSION'):self.run_adapter()
        self.assertEqual(self.calls,[])

    def test_source_schema_flags_and_fake_real_identity_refuse(self):
        for change in [{'provenance':'CANDIDATE_NOT_ADOPTED'},{'source_id':'real_FEC_but_MOCK'},{'source_adoption':True}]:
            with self.assertRaises(p.ParserRefused):p.source_reference(dict(source(self.raw),**change))

    def test_formula_any_selected_sheet_or_dimension_drift_closes_reader(self):
        self.book.sheets['14. 2020 Party Labels'].rows[0][0]=p.Cell('=1','f')
        with self.assertRaises(p.ParserRefused):self.run_adapter()
        self.assertTrue(self.book.closed)
        self.book=InertBook(self.tables);self.book.sheets[p.SENATE].max_row=543
        with self.assertRaisesRegex(p.ParserRefused,'DECLARED_SHEET_RANGE'):self.run_adapter()

    def test_no_partial_return_on_reader_failure_and_close_error_preserves_original(self):
        class Sentinel(Exception):pass
        original=Sentinel('AUTHORED_ORIGINAL_NOT_REPLACED')
        def broken(**kwargs):raise original
        self.book.sheets[p.SENATE].iter_rows=broken;self.book.close_error=True
        with self.assertRaises(Sentinel) as seen:self.run_adapter()
        self.assertIs(seen.exception,original);self.assertTrue(self.book.closed)

    def test_close_failure_after_success_does_not_publish_result(self):
        self.book.close_error=True
        with self.assertRaisesRegex(p.ParserRefused,'WORKBOOK_CLOSE_FAILED'):self.run_adapter()

    def test_archive_external_macros_DTD_duplicates_and_limits_refuse(self):
        bad=[archive({'xl/externalLinks/externalLink1.xml':'<x/>'}),archive({'xl/vbaProject.bin':'x'}),
             archive({'xl/_rels/book.rels':'<Relationships><Relationship TargetMode="External" Target="https://example.test"/></Relationships>'}),
             archive({'xl/worksheets/a.xml':'<!DOCTYPE x [<!ENTITY e "x">]><x/>'}),
             archive({str(i):'x' for i in range(81)}),b'not a zip']
        for raw in bad:
            with self.subTest(length=len(raw)),self.assertRaises(p.ParserRefused):p.archive_preflight(raw)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            z.writestr('a','x')
            with self.assertWarns(UserWarning):z.writestr('a','y')
        with self.assertRaisesRegex(p.ParserRefused,'DUPLICATE_ARCHIVE_MEMBER'):p.archive_preflight(stream.getvalue())

    def test_XML_parser_rejects_DTD_and_external_relationships_in_UTF16(self):
        for text in ['<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY y "private">]><x>&y;</x>',
                     '<?xml version="1.0" encoding="UTF-16"?><Relationships><Relationship TargetMode="External" Target="https://example.test"/></Relationships>']:
            with self.assertRaises(p.ParserRefused):p.archive_preflight(archive({'xl/_rels/book.rels':text.encode('utf-16')}))
        # Valid UTF16 XML is decoded by the same parser, not silently redecoded
        # as UTF8 or rejected solely by an incidental NUL-byte blacklist.
        p.archive_preflight(archive({'xl/worksheets/a.xml':'<?xml version="1.0" encoding="UTF-16"?><x>MOCK</x>'.encode('utf-16')}))

    def test_deadline_is_finite_restores_handler_and_does_not_extend_existing_timer(self):
        original=signal.getsignal(signal.SIGALRM)
        with mock.patch.object(p.signal,'getitimer',return_value=(.5,0)),mock.patch.object(p.signal,'setitimer') as timer:
            with p.operation_deadline():pass
        self.assertEqual(timer.call_args_list[0].args,(signal.ITIMER_REAL,.5));self.assertIs(signal.getsignal(signal.SIGALRM),original)
        with self.assertRaisesRegex(p.ParserRefused,'OPERATION_DEADLINE'):
            with p.operation_deadline(.001):
                import time
                time.sleep(.01)


class ArchiveSuffixRegressionTests(unittest.TestCase):
    def test_XML_payload_without_XML_suffix_is_still_screened(self):
        for name in ('sheet1.payload', 'sheet1', 'arbitrary.bin'):
            for encoding in ('utf-8', 'utf-16'):
                body=('<?xml version="1.0" encoding="'+encoding+'"?>'
                      '<!DOCTYPE x [<!ENTITY e "MOCK_ONLY">]><x>&e;</x>').encode(encoding)
                with self.subTest(name=name, encoding=encoding), self.assertRaisesRegex(p.ParserRefused, 'XML_DTD_OR_ENTITY'):
                    p.archive_preflight(archive({'xl/worksheets/'+name:body}))
        p.archive_preflight(archive({'xl/worksheets/sheet1.payload':b'<x>MOCK</x>'}))

    def test_external_relationship_without_relationship_suffix_refuses(self):
        body=b'<Relationships><Relationship TargetMode="External" Target="https://invalid.example/"/></Relationships>'
        with self.assertRaisesRegex(p.ParserRefused, 'EXTERNAL_RELATIONSHIP'):
            p.archive_preflight(archive({'xl/relationship.payload':body}))

    def test_opaque_exceptions_require_exact_name_length_and_digest(self):
        name='xl/printerSettings/AUTHORED.bin';raw=b'\x00\x01MOCK_OPAQUE'
        with mock.patch.object(p, 'OPAQUE_PARTS', {name:(len(raw),hashlib.sha256(raw).hexdigest())}):
            p.archive_preflight(archive({name:raw}))
            for changed in (raw+b'X',raw[:-1]+b'X',b'<!DOCTYPE x><x/>'):
                with self.subTest(changed=changed),self.assertRaisesRegex(p.ParserRefused,'OPAQUE_PART_PIN'):
                    p.archive_preflight(archive({name:changed}))
            with self.assertRaises(p.ParserRefused):
                p.archive_preflight(archive({'xl/printerSettings/OTHER.bin':raw}))

    def test_uppercase_mixedcase_and_Unicode_XML_DTD_refused(self):
        for filename in ('worksheet.XML','worksheet.Xml','worksheet.xMl','Ω.XML','Straße.XmL','İ.XML'):
            for encoding in ('utf-8','utf-16'):
                declaration='UTF-16' if encoding=='utf-16' else 'UTF-8'
                body=('<?xml version="1.0" encoding="'+declaration+'"?><!DOCTYPE x [<!ENTITY e "AUTHORED_ONLY">]><x>&e;</x>').encode(encoding)
                with self.subTest(filename=filename,encoding=encoding),self.assertRaisesRegex(p.ParserRefused,'XML_DTD_OR_ENTITY'):
                    p.archive_preflight(archive({'xl/worksheets/'+filename:body}))

    def test_uppercase_mixedcase_and_Unicode_RELS_external_refused(self):
        for filename in ('workbook.RELS','workbook.Rels','workbook.reLS','Ω.RELS','Straße.ReLs','İ.RELS'):
            for encoding in ('utf-8','utf-16'):
                declaration='UTF-16' if encoding=='utf-16' else 'UTF-8'
                body=('<?xml version="1.0" encoding="'+declaration+'"?><Relationships><Relationship TargetMode="External" Target="https://example.test/INERT"/></Relationships>').encode(encoding)
                with self.subTest(filename=filename,encoding=encoding),self.assertRaisesRegex(p.ParserRefused,'EXTERNAL_RELATIONSHIP'):
                    p.archive_preflight(archive({'xl/_rels/'+filename:body}))

    def test_valid_Unicode_XML_and_RELS_stay_readable_without_case_path_rewriting(self):
        members={'xl/worksheets/Ω.XML':'<worksheet>AUTHORED</worksheet>',
                 'xl/_rels/İ.ReLs':'<?xml version="1.0" encoding="UTF-16"?><Relationships/>'.encode('utf-16')}
        result=p.archive_preflight(archive(members))
        self.assertEqual(result['members'],2)
        self.assertEqual(result['declared_expanded_bytes'],sum(len(v.encode() if isinstance(v,str) else v) for v in members.values()))


class UnopposedMarkerTests(unittest.TestCase):
    def test_unopposed_preserves_marker_and_unknown_count(self):
        self.assertEqual(p.count('Unopposed'),{'votes':None,'status':'NONNUMERIC_MARKER','literal':'Unopposed'})

    def test_unopposed_primary_does_not_erase_numeric_general(self):
        row=candidate(2)
        row[11]=cell('Unopposed')
        result=p.row_record(row,2,source())
        self.assertIsNone(result['stages'][0]['votes'])
        self.assertEqual(result['stages'][2]['votes'],12)
        self.assertFalse(result['candidate_identity_accepted'])

    def test_unopposed_general_blocks_count_acceptance(self):
        row=candidate(2,votes='Unopposed')
        result=p.row_record(row,2,source())
        self.assertIsNone(result['stages'][2]['votes'])
        self.assertIn('GENERAL_COUNT_UNAVAILABLE',result['blockers'])


class ArchiveExpansionBounds(unittest.TestCase):
    def check_members(self, sizes):
        members=[]
        for index,size in enumerate(sizes):
            info=zipfile.ZipInfo('xl/worksheets/mock'+str(index)+'.xml')
            info.file_size=size;info.compress_type=zipfile.ZIP_DEFLATED
            members.append(info)
        fake=mock.MagicMock()
        fake.__enter__.return_value=fake
        fake.infolist.return_value=members
        fake.read.return_value=b'<worksheet>AUTHORED_BOUNDARY</worksheet>'
        with mock.patch.object(p.zipfile,'ZipFile',return_value=fake):
            result=p.archive_preflight(b'AUTHORED_CENTRAL_DIRECTORY')
        return result,fake

    def test_known_source_size_and_member_ceiling_are_admissible(self):
        for size in (41139508,50331648):
            with self.subTest(size=size):
                result,fake=self.check_members([size])
                self.assertEqual(result['declared_expanded_bytes'],size)
                fake.read.assert_called_once()

    def test_member_ceiling_plus_one_refuses_before_read(self):
        with self.assertRaisesRegex(p.ParserRefused,'ARCHIVE_MEMBER'):
            self.check_members([50331649])

    def test_aggregate_ceiling_is_unchanged(self):
        with self.assertRaisesRegex(p.ParserRefused,'ARCHIVE_BOUND'):
            self.check_members([50331648,16777217])
        result,_=self.check_members([50331648,16777216])
        self.assertEqual(result['declared_expanded_bytes'],67108864)


if __name__=='__main__':
    import resource
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    signal.alarm(120)
    unittest.main(verbosity=2)
