"""Authored Idaho fixture suite; never parses cached real source captures."""
import copy
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from civiclab.e01 import idaho_v1_8_1 as m

REPO=Path(__file__).resolve().parents[1]
CONTRACT_PATH='configs/e01_id_standalone_runtime_contract_v1_8_1_candidate.json'


def rows(variant):
    out=[['DEMO NAME '+str(i),'Federal','United States Senator','',party,date,'',status,'View Details'] for i,(party,status,date) in enumerate(m.INVENTORY)]
    for i in range((50,15,5)[variant]-5):out.append(['DEMO OTHER '+str(i),'Federal' if i<10 else 'Statewide','United States Representative' if i<10 else 'Governor','1' if i<10 else '', 'Republican','02/23/2026','','Approved','View Details'])
    return out


def table(data):
    header_cells=[]
    for number,(column,header) in enumerate(zip(m.COLUMNS,m.HEADERS)):
        if number<8:
            label=m.SEMANTIC_HEADERS[number]
            content='<div class="mat-sort-header-container mat-focus-indicator" role="button" tabindex="-1" aria-describedby="cdk-describedby-message-ng-1-2" cdk-describedby-host="ng-1"><div class="mat-sort-header-content"><span tabindex="-1">'+label+'</span><span class="emptyHidden">Header</span></div><div class="mat-sort-header-arrow"><svg viewBox="0 -960 960 960" focusable="false" aria-hidden="true"><path d="'+m.SORT_PATH+'"></path></svg></div></div>'
        else:content='ACTIONS'
        header_cells.append('<th role="columnheader" class="cdk-column-'+column+'">'+content+'</th>')
    h=''.join(header_cells)
    body=''.join('<tr>'+''.join('<td role="cell" class="cdk-column-'+column+'"><div><div>'+value+'</div></div></td>' for column,value in zip(m.COLUMNS,row))+'</tr>' for row in data)
    return '<table role="table" aria-describedby="SmartTableGrid"><caption>Smart Table</caption><thead><tr>'+h+'</tr></thead><tbody>'+body+'</tbody></table>'


def payload(variant):
    count=(592,15,5)[variant];num=(50,15,5)[variant];total=(592,15,5)[variant]
    body='Search Filed Candidates\nFINAL CANDIDATES LIST\n'+m.ELECTION+'\nFiling Status\nSelect All\nApproved\nWithdrawn\nReset All Filters\n'+f'{count} Candidate(s) Found of 592 total\n'+ '\n'.join(' '.join(row) for row in rows(variant))+f'\n1 – {num} of {total}'
    controls=[{'id':'mat-select-0','text':m.ELECTION},{'id':'mat-select-1','text':'Select District Type' if variant==0 else 'Federal'}]
    if variant:controls.append({'id':'mat-select-4','text':'Select Office' if variant==1 else 'United States Senator'})
    controls.extend([{'id':'partyAffiliation','text':'Select Party'},{'id':'mat-select-3','text':'50'}])
    if variant==0:
        for c in controls:c['disabled']='false'
        data={'body':body,'selects':controls,'tables':[table(rows(variant))]}
    else:data={'body':body,'selected':controls,'table':table(rows(variant)),'checkboxes':[{'id':f'mat-mdc-checkbox-{i}-input','checked':True} for i in range(3)]}
    return {'url':m.URL,'capture_kind':m.KIND,'captured_at_utc':f'2026-11-03T15:2{variant}:01.000Z','data':data}


INDEX='<title>2026 Idaho General Election</title><a href="https://run.voteidaho.gov/search">See The Full Candidate List</a>'
SHELL='<title>Idaho Candidate Filing Portal - ReFrame</title><script src="DEMO.js"></script>'


def fixture(root):
    c=json.loads((REPO/CONTRACT_PATH).read_text());data=[INDEX.encode(),SHELL.encode()]+[json.dumps(payload(i)).encode() for i in range(3)]
    for source,raw in zip(c['inputs'],data):
        p=root/source['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);source['bytes']=len(raw);source['sha256']=m.digest(raw)
    module=root/'src/civiclab/e01/idaho_v1_8_1.py';module.parent.mkdir(parents=True);module.write_bytes((REPO/'src/civiclab/e01/idaho_v1_8_1.py').read_bytes())
    return c


def fixture_identity(root,c):
    s=ExitStack();s.enter_context(patch.object(m,'CONTRACT_CANONICAL_SHA',m.digest(m.canonical(c))));s.enter_context(patch.object(m,'__file__',str(root/'src/civiclab/e01/idaho_v1_8_1.py')));return s


def primitive(ps=None,**kwargs):
    return m._reconcile_payloads(ps if ps is not None else [payload(i) for i in range(3)],kwargs.get('index',INDEX),kwargs.get('shell',SHELL),{k:'0'*64 for k in m.SOURCE_IDS})


class IdahoFixtureTests(unittest.TestCase):
    def temp(self):return tempfile.TemporaryDirectory()

    def test_authored_five_source_success_no_writes_and_typed_unknown_status_history(self):
        with self.temp() as td:
            root=Path(td).resolve();c=fixture(root);before={str(p.relative_to(root)):m.digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
            with fixture_identity(root,c):r=m.read_sources(root,c)
            self.assertEqual(before,{str(p.relative_to(root)):m.digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()})
            records=r.local_records;public=r.public_diagnostics()
            self.assertEqual(len(records),5);self.assertEqual([x['source_status_literal'] for x in records],['Withdrawn']+['Approved']*4)
            self.assertEqual([x['source_party_label'] for x in records],['Democratic','Independent','Independent','Libertarian','Republican'])
            for item in records:
                for field in m.UNKNOWN_REASONS:self.assertEqual(item[field]['kind'],'UNKNOWN')
                for field in ['printed_on_ballot','declared_write_in','legal_nominee','party_class']:self.assertNotIn(field,item)
                self.assertEqual((item['source_write_in_cell_literal'],item['source_district_literal']),('',''))
                self.assertEqual(len(item['source_locations']),3)
            self.assertEqual(records[0]['date_filed_iso'],'2026-02-23')
            self.assertEqual(public['status_checkbox_evidence'][0]['kind'],'UNKNOWN')
            self.assertTrue(all(x['kind']=='UNKNOWN' for x in public['candidate_name_input_evidence']))
            self.assertEqual(public['capture_pagination'],['1 – 50 of 592','1 – 15 of 15','1 – 5 of 5'])
            self.assertNotIn('DEMO NAME',json.dumps(public));self.assertNotIn('DEMO NAME',repr(r))
            self.assertFalse((root/'data/processed').exists())

    def test_exact_real_contract_metadata_admission_only_no_source_reads(self):
        c=json.loads((REPO/CONTRACT_PATH).read_text())
        with patch.object(m,'_read_one',side_effect=AssertionError('must not read')):
            admitted=m.admit_metadata(c)
        self.assertEqual(admitted['contract_canonical_sha256'],m.CONTRACT_CANONICAL_SHA)

    def test_secret_or_coedited_metadata_refused_before_root_and_inputs(self):
        c=json.loads((REPO/CONTRACT_PATH).read_text())
        changes=[lambda q:q.update(secret='SYNTHETIC_PRIVATE'),lambda q:q['inputs'][0].update(url='https://user:SYNTHETIC_PRIVATE@fixture.gov'),lambda q:q['inputs'][0].update(sha256='0'*64),lambda q:q.update(pipeline_enabled=True)]
        for change in changes:
            altered=copy.deepcopy(c);change(altered)
            with patch.object(m,'_root') as root,patch.object(m,'_read_one') as read,self.assertRaises(m.CaptureRejected) as cm:m.read_sources('/SYNTHETIC_PRIVATE',altered)
            root.assert_not_called();read.assert_not_called();self.assertNotIn('SYNTHETIC_PRIVATE',str(cm.exception));self.assertIsNone(cm.exception.__context__);self.assertIsNone(cm.exception.__cause__)

    def test_capture_schema_duplicate_json_nonfinite_unknown_metadata(self):
        for raw in [b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}',b'{"a":-Infinity}']:
            with self.assertRaises(ValueError):m.strict_json(raw)
        for variant in range(3):
            for change in [lambda q:q.update(extra='SYNTHETIC_PRIVATE'),lambda q:q.update(url='https://fixture.gov/private'),lambda q:q.update(capture_kind='HTTP_RESPONSE_BODY_BYTES'),lambda q:q['data'].update(extra='x')]:
                ps=[payload(i) for i in range(3)];change(ps[variant])
                with self.assertRaises(ValueError):primitive(ps)

    def test_initial_checkbox_missing_is_explicit_unknown_not_backfilled(self):
        ps=[payload(i) for i in range(3)];ps[0]['data']['checkboxes']=copy.deepcopy(ps[1]['data']['checkboxes'])
        with self.assertRaises(ValueError):primitive(ps)
        for variant in [1,2]:
            for mode in ['missing','false','int','extra','reordered']:
                ps=[payload(i) for i in range(3)];d=ps[variant]['data']
                if mode=='missing':d.pop('checkboxes')
                elif mode=='false':d['checkboxes'][2]['checked']=False
                elif mode=='int':d['checkboxes'][2]['checked']=1
                elif mode=='extra':d['checkboxes'].append({'id':'extra','checked':True})
                else:d['checkboxes'].reverse()
                with self.assertRaises(ValueError):primitive(ps)

    def test_wrong_filter_context_title_controls_page_size_and_label_binding(self):
        for variant in range(3):
            key='selects' if variant==0 else 'selected'
            for slot in range(len(payload(variant)['data'][key])):
                ps=[payload(i) for i in range(3)];ps[variant]['data'][key][slot]['text']='ALTERED'
                with self.assertRaises(ValueError):primitive(ps)
        for old,new in [('FINAL CANDIDATES LIST','FILING ONLY'),(m.ELECTION,'May 19, 2026 - 2026 PRIMARY'),('Select All\nApproved\nWithdrawn','Select All\nWithdrawn\nApproved')]:
            ps=[payload(i) for i in range(3)];ps[2]['data']['body']=ps[2]['data']['body'].replace(old,new)
            with self.assertRaises(ValueError):primitive(ps)

    def test_pagination_totals_truncation_and_competing_ranges_refused(self):
        for variant in range(3):
            for change in [lambda d:d.update(body=d['body'].replace('of 592 total','of 591 total')),lambda d:d.update(body=d['body']+'\n1 – 5 of 5')]:
                ps=[payload(i) for i in range(3)];change(ps[variant]['data'])
                with self.assertRaises(ValueError):primitive(ps)
            ps=[payload(i) for i in range(3)];data=ps[variant]['data'];bad=table(rows(variant)[:-1])
            if variant==0:data['tables']=[bad]
            else:data['table']=bad
            with self.assertRaises(ValueError):primitive(ps)

    def test_table_header_class_identity_width_duplicate_and_active_markup_refused(self):
        original=payload(2)['data']['table']
        for bad in [original+original,original.replace('SmartTableGrid','OTHER'),original.replace('Smart Table','Other Table'),original.replace('>BALLOT NAME</span>','>OTHER LABEL</span>'),original.replace('cdk-column-status','cdk-column-other'),original.replace('<tbody>','<tbody><script>SYNTHETIC_PRIVATE</script>'),original.replace('</td>','</td><td role="cell">extra</td>',1),original[:-8],original.replace('DEMO NAME 0','DEMO NAME 0<div>PRIVATE CONTACT</div>')]:
            ps=[payload(i) for i in range(3)];ps[2]['data']['table']=bad
            with self.assertRaises(ValueError):primitive(ps)

    def test_full_tuple_edits_dates_status_party_blanks_actions_duplicates_boundaries(self):
        alterations=[(0,'DEMO NAME 0'),(1,'Statewide'),(2,'State Senator'),(3,'1'),(4,'Democratic'),(5,'02/30/2026'),(5,'11/04/2026'),(6,'Yes'),(7,'PENDING'),(8,'Open Details')]
        for column,value in alterations:
            ps=[payload(i) for i in range(3)];data=rows(2);data[1][column]=value
            ps[2]['data']['table']=table(data)
            with self.assertRaises(ValueError):primitive(ps)
        # Same initials, different full names must not reconcile.
        ps=[payload(i) for i in range(3)];ps[2]['data']['table']=ps[2]['data']['table'].replace('DEMO NAME 0','DEMO NAME 0 ALTERED')
        ps[2]['data']['body']=ps[2]['data']['body'].replace('DEMO NAME 0','DEMO NAME 0 ALTERED')
        with self.assertRaises(ValueError):primitive(ps)
        for variant in [0,1]:
            ps=[payload(i) for i in range(3)];data=rows(variant);data[5][2]='Governor'
            if variant==0:ps[variant]['data']['tables']=[table(data)]
            else:ps[variant]['data']['table']=table(data)
            with self.assertRaises(ValueError):primitive(ps)

    def test_name_header_substrings_preserved_and_body_DOM_disagreement_refused(self):
        ps=[payload(i) for i in range(3)]
        for p in ps:
            p['data']['body']=p['data']['body'].replace('DEMO NAME 0','DEMO Header NAME 0')
            if 'table' in p['data']:p['data']['table']=p['data']['table'].replace('DEMO NAME 0','DEMO Header NAME 0')
            else:p['data']['tables'][0]=p['data']['tables'][0].replace('DEMO NAME 0','DEMO Header NAME 0')
        self.assertEqual(primitive(ps).local_records[0]['official_name'],'DEMO Header NAME 0')
        ps[2]['data']['body']=ps[2]['data']['body'].replace('DEMO Header NAME 0','DEMO DIFFERENT 0')
        with self.assertRaises(ValueError):primitive(ps)

    def test_clock_malformed_nonUTC_date_and_reordered_refused(self):
        for value in ['2026-11-03T15:20:01.000+00:00','2026-11-03','2026-11-04T15:20:01.000Z','SYNTHETIC_PRIVATE']:
            ps=[payload(i) for i in range(3)];ps[1]['captured_at_utc']=value
            with self.assertRaises(ValueError):primitive(ps)
        ps=[payload(i) for i in range(3)];ps[1]['captured_at_utc']=ps[0]['captured_at_utc']
        with self.assertRaises(ValueError):primitive(ps)

    def test_index_offered_link_shell_roles_and_resource_guards(self):
        for kwargs in [{'index':INDEX.replace('search','other')},{'index':INDEX.replace('2026','2024')},{'shell':SHELL.replace('Filing Portal','Other Portal')}]:
            with self.assertRaises(ValueError):primitive(**kwargs)
        with self.assertRaises(ValueError):m.DOM('<div>'*65+'</div>'*65)
        with self.assertRaises(ValueError):m.DOM('x'*750001)
        with self.assertRaises(ValueError):m.DOM('<br>'*100001)

    def test_sources_each_drift_coedited_contract_or_after_read_mutation_refused(self):
        for position in range(5):
            with self.temp() as td:
                root=Path(td).resolve();c=fixture(root);p=root/c['inputs'][position]['path'];p.write_bytes(p.read_bytes()+b'ALTERED')
                with fixture_identity(root,c),self.assertRaises(m.CaptureRejected):m.read_sources(root,c)
                changed=copy.deepcopy(c);changed['inputs'][position]['sha256']=m.digest(p.read_bytes());changed['inputs'][position]['bytes']=p.stat().st_size
                with fixture_identity(root,c),patch.object(m,'_root') as root_check,self.assertRaises(m.CaptureRejected):m.read_sources(root,changed)
                root_check.assert_not_called()
        with self.temp() as td:
            root=Path(td).resolve();c=fixture(root);original=m._reconcile_payloads
            def mutate(*a):
                out=original(*a);p=root/c['inputs'][0]['path'];p.write_bytes(b'ALTERED');return out
            with fixture_identity(root,c),patch.object(m,'_reconcile_payloads',side_effect=mutate),self.assertRaises(m.CaptureRejected):m.read_sources(root,c)

    def test_root_ancestor_input_symlink_paths_import_origin_and_size(self):
        for mode in ['root','ancestor','source','parent','origin','oversize','traversal']:
            with self.temp() as td:
                base=Path(td).resolve();root=base/'original';root.mkdir();c=fixture(root);target=root
                if mode=='root':target=base/'linked';target.symlink_to(root,target_is_directory=True)
                elif mode=='ancestor':
                    link=base/'link';link.symlink_to(root.parent,target_is_directory=True);target=link/root.name
                elif mode=='source':
                    p=root/c['inputs'][0]['path'];q=p.with_name('other');p.rename(q);p.symlink_to(q.name)
                elif mode=='parent':
                    p=root/'data/raw/e01_ballots_batch06_v1';q=p.with_name('other');p.rename(q);p.symlink_to(q.name,target_is_directory=True)
                elif mode=='oversize':(root/c['inputs'][0]['path']).write_bytes(b'x'*1048577)
                elif mode=='traversal':c['inputs'][0]['path']='data/raw/../outside'
                with fixture_identity(root,c),ExitStack() as s:
                    if mode=='origin':s.enter_context(patch.object(m,'__file__','/foreign/idaho_v1_8_1.py'))
                    with self.assertRaises(m.CaptureRejected):m.read_sources(target,c)

    def test_cancel_and_late_failures_type_only_no_partial_result_or_side_effects(self):
        for kind in [RuntimeError,KeyboardInterrupt,SystemExit]:
            for position in range(11):
                with self.temp() as td:
                    root=Path(td).resolve();c=fixture(root);before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()};original=m._read_one;counter=[0]
                    def fail(*a):
                        n=counter[0];counter[0]+=1
                        if n==position:raise kind('SYNTHETIC_PRIVATE')
                        return original(*a)
                    with fixture_identity(root,c),ExitStack() as s:
                        if position==10:s.enter_context(patch.object(m,'_reconcile_payloads',side_effect=kind('SYNTHETIC_PRIVATE')))
                        else:s.enter_context(patch.object(m,'_read_one',side_effect=fail))
                        expected=kind if kind in [KeyboardInterrupt,SystemExit] else m.CaptureRejected
                        with self.assertRaises(expected) as cm:m.read_sources(root,c)
                    self.assertNotIn('SYNTHETIC_PRIVATE',str(cm.exception));self.assertIsNone(cm.exception.__cause__);self.assertIsNone(cm.exception.__context__)
                    self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_public_diagnostics_detached_and_never_project_private_record_mutations(self):
        r=primitive();r.local_records[0]['official_name']='SYNTHETIC_PRIVATE';public=r.public_diagnostics();public['scope']='ALTERED'
        self.assertNotIn('SYNTHETIC_PRIVATE',json.dumps(r.public_diagnostics()));self.assertNotEqual(r.public_diagnostics()['scope'],'ALTERED')
        self.assertNotIn('DEMO NAME',repr(r))


    def test_ambiguous_column_tokens_extra_header_cells_and_reordered_rows_refused(self):
        original=payload(2)['data']['table']
        for bad in [original.replace('cdk-column-status','cdk-column-status cdk-column-other'),
                    original.replace('</thead>','<td role="cell">EXTRA</td></thead>'),
                    original.replace('</th>','</th><td>EXTRA</td>',1),table(list(reversed(rows(2))))]:
            ps=[payload(i) for i in range(3)];ps[2]['data']['table']=bad
            with self.assertRaises(ValueError):primitive(ps)

    def test_added_senate_row_and_wrong_federal_remainder_refused(self):
        for variant in [0,1]:
            ps=[payload(i) for i in range(3)];data=rows(variant);data[7]=copy.deepcopy(data[0]);data[7][0]='DEMO EXTRA SENATE'
            if variant==0:ps[variant]['data']['tables']=[table(data)]
            else:ps[variant]['data']['table']=table(data)
            with self.assertRaises(ValueError):primitive(ps)
        ps=[payload(i) for i in range(3)];data=rows(1);data[10][1]='Statewide';ps[1]['data']['table']=table(data)
        with self.assertRaises(ValueError):primitive(ps)

    def test_all_three_tuple_edits_cannot_reseal_real_source_binding(self):
        with self.temp() as td:
            root=Path(td).resolve();c=fixture(root);changed=copy.deepcopy(c)
            for source in changed['inputs'][2:]:
                p=root/source['path'];p.write_text(p.read_text().replace('DEMO NAME 0','DEMO ALTERED FULL NAME 0'))
                source['bytes']=p.stat().st_size;source['sha256']=m.digest(p.read_bytes())
            with fixture_identity(root,c),patch.object(m,'_root') as check,self.assertRaises(m.CaptureRejected):m.read_sources(root,changed)
            check.assert_not_called()

    def test_exactly_five_bounded_source_reads_and_rechecks_no_network(self):
        with self.temp() as td:
            root=Path(td).resolve();c=fixture(root);original=m._read_one;seen=[]
            def read(root,source):seen.append(source['source_id']);return original(root,source)
            with fixture_identity(root,c),patch.object(m,'_read_one',side_effect=read),patch('socket.socket',side_effect=AssertionError('no network')):
                result=m.read_sources(root,c)
            self.assertEqual(seen,list(m.SOURCE_IDS)*2)
            self.assertEqual(result.public_diagnostics()['source_local_row_count'],5)


    def test_after_tuple_assembly_failure_is_value_free_and_never_returns_bundle(self):
        for error in [RuntimeError,KeyboardInterrupt,SystemExit]:
            with self.temp() as td:
                root=Path(td).resolve();c=fixture(root);original=m._reconcile_payloads;assembled=[]
                def fail(*args):
                    result=original(*args);assembled.append(result.public_diagnostics()['source_local_row_count'])
                    raise error('SYNTHETIC_PRIVATE')
                expected=error if error in [KeyboardInterrupt,SystemExit] else m.CaptureRejected
                with fixture_identity(root,c),patch.object(m,'_reconcile_payloads',side_effect=fail),self.assertRaises(expected) as cm:m.read_sources(root,c)
                self.assertEqual(assembled,[5]);self.assertNotIn('SYNTHETIC_PRIVATE',str(cm.exception));self.assertIsNone(cm.exception.__context__)
                self.assertFalse((root/'data/processed').exists())


    def test_observed_eight_inert_sort_icons_are_header_only_not_record_text(self):
        for variant in range(3):
            html=table(rows(variant));self.assertEqual(html.count('<svg'),8)
            self.assertEqual(html.count('viewBox="0 -960 960 960"'),8)
            result=m.table_rows(html);self.assertEqual(result,[tuple(r) for r in rows(variant)])
        result=primitive();self.assertNotIn('M440-',str(result.local_records));self.assertEqual(len(result.local_records),5)

    def test_svg_active_external_body_text_location_shape_and_extra_attributes_refused(self):
        original=table(rows(2));icon='<svg viewBox="0 -960 960 960" focusable="false" aria-hidden="true"><path d="'+m.SORT_PATH+'"></path></svg>'
        self.assertIn(icon,original)
        variants=[original.replace('focusable="false"','focusable="true"',1),
                  original.replace('aria-hidden="true"','aria-hidden="false"',1),
                  original.replace('viewBox="0 -960 960 960"','viewBox="0 0 100 100"',1),
                  original.replace('<svg ','<svg onload="SYNTHETIC_PRIVATE" ',1),
                  original.replace('<svg ','<svg href="https://external.invalid/x" ',1),
                  original.replace('<svg ','<svg style="background:url(https://external.invalid/x)" ',1),
                  original.replace('<path d=','<path onmouseover="bad" d=',1),
                  original.replace('</path>','<use href="https://external.invalid/x"></use></path>',1),
                  original.replace(icon,'<svg viewBox="0 -960 960 960" focusable="false" aria-hidden="true"><foreignObject>bad</foreignObject></svg>',1),
                  original.replace(icon,icon.replace('</svg>','bad</svg>'),1),
                  original.replace('mat-sort-header-arrow','other-arrow',1),
                  original.replace('class="mat-sort-header-arrow"','class="mat-sort-header-arrow" onclick="bad"',1),
                  original.replace(icon,'',1),original.replace(icon,icon+icon,1),
                  original.replace('DEMO NAME 0','DEMO NAME 0'+icon,1),
                  original.replace('>ACTIONS</th>','>ACTIONS'+icon+'</th>',1)]
        for bad in variants:
            with self.assertRaises(ValueError):m.table_rows(bad)
        # Moving an otherwise exact icon to a body cell preserves total8 but
        # must still fail header location/count validation.
        moved=original.replace(icon,'',1).replace('DEMO NAME 0','DEMO NAME 0'+icon,1)
        self.assertEqual(moved.count('<svg'),8)
        with self.assertRaises(ValueError):m.table_rows(moved)

    def test_first_middle_last_caller_metadata_and_three_capture_bytes_coedit_blocked(self):
        for position,expected_reads,replacement in [(p,n,text) for p,n in [(0,3),(4,5),(9,10)] for text in [b'DEMO UNRELEASED FULL NAME 0',b'DEMO EVIL 0']]:
            with self.temp() as td:
                root=Path(td).resolve();caller=fixture(root);original=m._read_one;seen=[]
                released=copy.deepcopy(caller)
                def attack():
                    for source in caller['inputs'][2:]:
                        p=root/source['path'];raw=p.read_bytes().replace(b'DEMO NAME 0',replacement)
                        p.write_bytes(raw);source.update(bytes=len(raw),sha256=m.digest(raw))
                def hooked_read(root,source):
                    n=len(seen);seen.append(source['source_id'])
                    if n==position:attack()
                    # Source dictionaries passed by the reader retain released
                    # authority even after all caller dictionaries were edited.
                    idx=m.SOURCE_IDS.index(source['source_id']);self.assertEqual(source,released['inputs'][idx])
                    return original(root,source)
                with fixture_identity(root,caller),patch.object(m,'_read_one',side_effect=hooked_read):
                    frozen_constant=m.CONTRACT_CANONICAL_SHA
                    with self.assertRaises(m.CaptureRejected):m.read_sources(root,caller)
                    self.assertEqual(m.CONTRACT_CANONICAL_SHA,frozen_constant)
                    self.assertNotEqual(m.digest(m.canonical(caller)),frozen_constant)
                self.assertEqual(len(seen),expected_reads)
                self.assertEqual(seen,list(m.SOURCE_IDS)*2 if position==9 else list(m.SOURCE_IDS)[:expected_reads])
                self.assertFalse((root/'data/processed').exists())

    def test_snapshot_precedes_admission_not_copy_after_mutable_gate(self):
        with self.temp() as td:
            root=Path(td).resolve();caller=fixture(root);gate=m._admit_metadata;seen=[];read=m._read_one
            def hooked_gate(snapshot):
                self.assertIsNot(snapshot,caller);self.assertIsNot(snapshot['inputs'],caller['inputs'])
                accepted=gate(snapshot)
                for source in caller['inputs'][2:]:
                    p=root/source['path'];raw=p.read_bytes().replace(b'DEMO NAME 0',b'DEMO NEW UNRELEASED 0');p.write_bytes(raw)
                    source.update(bytes=len(raw),sha256=m.digest(raw))
                return accepted
            def observed_read(root,source):seen.append(source['source_id']);return read(root,source)
            with fixture_identity(root,caller),patch.object(m,'_admit_metadata',side_effect=hooked_gate),patch.object(m,'_read_one',side_effect=observed_read),self.assertRaises(m.CaptureRejected):m.read_sources(root,caller)
            self.assertEqual(seen,list(m.SOURCE_IDS)[:3]);self.assertFalse((root/'data/processed').exists())

    def test_closed_builtin_snapshot_detaches_all_containers_and_refuses_protocol_hooks(self):
        original={'nested':[{'value':'DEMO'}],'finite':1.5};snap=m._closed_snapshot(original)
        original['nested'][0]['value']='ALTERED';self.assertEqual(snap['nested'][0]['value'],'DEMO')
        class CustomDict(dict):
            def items(self):raise AssertionError('MUST_NOT_INVOKE')
        class CustomList(list):
            def __iter__(self):raise AssertionError('MUST_NOT_INVOKE')
        for value in [CustomDict(),{'x':CustomList()}, {'x':float('nan')},{'x':float('inf')},{'x':object()}, {'x':1<<65}]:
            with self.assertRaises(ValueError):m._closed_snapshot(value)
        c=json.loads((REPO/CONTRACT_PATH).read_text());c['inputs']=CustomList(c['inputs'])
        with patch.object(m,'_root') as read,self.assertRaises(m.CaptureRejected):m.read_sources('/unused',c)
        read.assert_not_called()

    def test_caller_metadata_only_mutation_does_not_change_returned_source_authority(self):
        with self.temp() as td:
            root=Path(td).resolve();caller=fixture(root);expected={x['source_id']:x['sha256'] for x in caller['inputs']};original=m._read_one;counter=[0]
            def mutate(root,source):
                if counter[0]==0:
                    for item in caller['inputs']:item.update(path='data/raw/unreleased',sha256='0'*64,bytes=0)
                counter[0]+=1;return original(root,source)
            with fixture_identity(root,caller),patch.object(m,'_read_one',side_effect=mutate):result=m.read_sources(root,caller)
            self.assertEqual(result.public_diagnostics()['source_hashes'],expected)
            self.assertEqual(result.local_records[0]['official_name'],'DEMO NAME 0');self.assertEqual(counter[0],10)


if __name__=='__main__':unittest.main()
