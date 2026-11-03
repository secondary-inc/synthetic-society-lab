"""Authored fixtures only; no raw government candidate documents required."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from civiclab.e01 import ballots as b
from civiclab.e01 import ballot_formats_v1_3 as f
from tests.test_e01_ballots import ledger,write_source


def table(headers,rows):
    return '<table><tr>'+''.join('<td>'+v+'</td>' for v in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'


def co():
    return '2026 General Election Official Candidate List certified to the counties on September 4'+table(
        ['Candidate name','Office','District','Party','Write in?'],[
        ['DEMO A','US Senate','State','Democratic Party','N'],['DEMO B','US Senate','State','Republican Party','N'],
        ['DEMO C','US Senate','State','DEMO PETITION LABEL','N'],['DEMO D','US Senate','State','Republican Party','Y'],
        ['<span style="text-decoration: line-through">DEMO OTHER</span>','State Senate','1','Democratic Party','N']])


def va():
    return 'November 3, 2026 - Federal Offices'+table(f.VA_HEADER,[
        ['Member, United States Senate','Statewide','Democratic','DEMO A','Yes']+['DEMO CONTACT']*8,
        ['Member, United States Senate','Statewide','DEMO UNKNOWN','DEMO B','No']+['DEMO CONTACT']*8,
        ['Member, House of Representatives','1st District','Republican','DEMO HOUSE','No']+['DEMO CONTACT']*8])


def wy():
    return ['2026 General Election Candidate Roster\nParty Affiliation  Candidate Name  Mailing Address  Date Filed  Campaign Telephone\nDate Withdrawn\nUNITED STATES SENATOR\nRepublican  DEMO A  DEMO ADDRESS  05/15/2026  DEMO PHONE\nDEMO CITY  demo@example.invalid\nDemocratic  DEMO B  DEMO ADDRESS  05/19/2026  DEMO PHONE\nDEMO CITY  demo@example.invalid\nUNITED STATES REPRESENTATIVE\nDEMO HOUSE\nWednesday, September 09, 2026 - 11:20AM  Page 1 of 19']+['DEMO OTHER PAGE']*18


class NewFormatTests(unittest.TestCase):
    def test_co_writein_literal_label_and_unrelated_strike(self):
        r=f.extract_co_senate(co());self.assertEqual((r['printed_candidates'],r['qualified_write_ins']),(3,1))
        self.assertFalse(any(x['withdrawal_markup_observed'] for x in r['candidates']))
        self.assertEqual(r['candidates'][2]['source_party_label'],'DEMO PETITION LABEL')
        self.assertEqual(r['candidates'][2]['party_class'],'UNSPECIFIED')
        changed=f.extract_co_senate(co().replace('DEMO A','<del>DEMO A</del>'))
        self.assertTrue(changed['candidates'][0]['withdrawal_markup_observed'])

    def test_co_refuses_wrong_stage_district_writein_duplicate_and_missing_header(self):
        for old,new in [('2026 General','2024 General'),('State</td>','District</td>'),('Y</td>','MAYBE</td>'),
                        ('DEMO B','DEMO A'),('Write in?','Writein?')]:
            with self.assertRaises(ValueError):f.extract_co_senate(co().replace(old,new))

    def test_va_exact_office_no_contacts_literal_unknown(self):
        r=f.extract_va_senate(va());self.assertEqual(len(r['candidates']),2)
        self.assertNotIn('DEMO CONTACT',str(r));self.assertNotIn('DEMO HOUSE',str(r))
        self.assertEqual(r['candidates'][1]['source_party_label'],'DEMO UNKNOWN')
        self.assertEqual(r['candidates'][1]['party_class'],'UNSPECIFIED')
        for old,new in [('2026 - Federal','2024 - Federal'),('Statewide','District'),('Yes','MAYBE'),('Candidate Party','Party')]:
            with self.assertRaises(ValueError):f.extract_va_senate(va().replace(old,new))

    def test_wy_bounded_section_no_contacts_and_withdrawal_date(self):
        r=f.extract_wy_senate(wy());self.assertEqual(len(r['candidates']),2)
        self.assertTrue(all(x['withdrawal_date_printed'] is None for x in r['candidates']))
        self.assertNotIn('DEMO ADDRESS',str(r));self.assertNotIn('demo@example.invalid',str(r))
        self.assertNotIn('DEMO HOUSE',str(r))
        pages=wy();pages[0]=pages[0].replace('DEMO CITY  demo@example.invalid','DEMO CITY  09/10/2026  demo@example.invalid',1)
        self.assertEqual(f.extract_wy_senate(pages)['candidates'][0]['withdrawal_date_printed'],'09/10/2026')

    def test_wy_refuses_partial_duplicate_wrong_edition_and_count(self):
        for old,new in [('DEMO B','DEMO A'),('05/15/2026','BAD DATE'),('Page 1 of 19','Page 1 of 20'),
                        ('UNITED STATES REPRESENTATIVE','STATE REPRESENTATIVE'),('DEMO CITY  demo@example.invalid','PARTIAL ROW')]:
            pages=wy();pages[0]=pages[0].replace(old,new)
            with self.assertRaises(ValueError):f.extract_wy_senate(pages)
        with self.assertRaises(ValueError):f.extract_wy_senate(wy()[:1])

    def test_exact_colorado_host_only_no_broad_us_exception(self):
        with tempfile.TemporaryDirectory() as td:
            c=ledger(Path(td));c['sources'][0]['url']='https://www.sos.state.co.us/pubs/elections/vote/generalCandidates.html'
            b.admit_metadata(c);b.verify_source(Path(td),c['sources'][0])
            for host in ['sos.state.co.us','evil.us','www.sos.state.co.us.evil.us','evil-www.sos.state.co.us','www.sos.state.co.us@evil.us']:
                c['sources'][0]['url']='https://'+host+'/x'
                with self.assertRaises(ValueError):b.admit_metadata(c)
                with self.assertRaises(ValueError):b.verify_source(Path(td),c['sources'][0])

    def test_integrated_five_slot_readiness_without_acceptance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c=ledger(root)
            for state,key,data in [('CO','co_general',co().encode()),('VA','va_federal',va().encode()),('WY','wy_general',b'DEMO PDF')]:
                c['sources'].append(write_source(root,key,data))
                next(x for x in c['class_II_frame'] if x['state']==state)['candidate_source_ids']=[key]
            with patch.object(b,'pdf_pages',return_value=wy()):r=b.validate_readiness(root,c)
            self.assertEqual(r['official_rosters_extracted'],3);self.assertEqual(r['final_ballots_accepted'],0)
            self.assertEqual(len(r['candidate_observations']),33)
            self.assertFalse(r['source_adoption']);self.assertFalse(r['actual_selection'])


if __name__=='__main__':unittest.main()
