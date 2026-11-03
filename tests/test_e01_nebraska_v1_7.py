"""Authored physical text-box fixtures derived from observed source geometry."""
import copy
import math
import unittest
from civiclab.e01 import nebraska_v1_7 as n


def add(words,text,x,top):
    for token in text.split():
        width=len(token)*2;words.append({'text':token,'x0':x,'x1':x+width,'top':top,'bottom':top+7.2});x+=width+2


def boxes():
    w=[];add(w,'Final Statewide General Candidate List',323,23.43);add(w,'November 3, 2026 General Election',327,35.43);add(w,'9/11/2026',733.61,23.91)
    for label,x in n.HEADERS.items():add(w,label,x,55.8)
    labels=[['Republican'],['Legal Marijuana','NOW'],['Nebraska Working','People'],['America First'],['By Petition']]
    for i,parts in enumerate(labels):
        top=74.4+i*21.48;add(w,'For United States Senator',19.32,top);add(w,'6',212.03,top);add(w,'1',238.55,top)
        for j,part in enumerate(parts):add(w,part,255.12,top+j*9.24)
        add(w,'DEMO NAME '+chr(65+i),317.66,top);add(w,'DEMO CITY',431.19,top);add(w,'Incumbent' if i==0 else 'Nonincumbent',485.56,top)
        add(w,'DEMO PRIVATE CONTACT',650,top)
    add(w,'For Representative in Congress',19.32,181.8)
    return w


class NebraskaTests(unittest.TestCase):
    def test_physical_row_band_wrapped_labels_minor_petition_not_democratic(self):
        r=n.extract_geometry(boxes(),metadata={'CreationDate':"D:20260916164704-05'00'"})
        self.assertEqual(r['candidate_count'],5)
        self.assertEqual([x['source_party_label'] for x in r['candidates']],['Republican','Legal Marijuana NOW','Nebraska Working People','America First','By Petition'])
        self.assertEqual([x['party_class'] for x in r['candidates']],['R']+['UNSPECIFIED']*4)
        self.assertNotIn('DEMO CITY',str(r));self.assertNotIn('DEMO PRIVATE CONTACT',str(r))
        self.assertEqual(r['source_printed_edition'],'2026-09-11');self.assertEqual(r['final_ballots_accepted'],0)
        self.assertEqual(r['pdf_creation_metadata'],"D:20260916164704-05'00'")

    def test_wrong_document_rotation_dimensions_title_header_refused(self):
        for kwargs in [{'page_count':23},{'rotation':0},{'width':612},{'height':792}]:
            with self.assertRaises(ValueError):n.extract_geometry(boxes(),**kwargs)
        for text in ['9/11/2026','Office']:
            w=boxes();next(x for x in w if x['text']==text)['text']='ALTERED'
            with self.assertRaises(ValueError):n.extract_geometry(w)

    def test_nonfinite_overlapping_columns_term_vote_scope_and_status_refused(self):
        changes=[('6','text','5'),('1','text','2'),('Incumbent','text','UNKNOWN'),
                 ('Republican','x1',318),('Republican','x0',float('nan'))]
        for text,key,value in changes:
            w=boxes();next(x for x in w if x['text']==text)[key]=value
            with self.assertRaises(ValueError):n.extract_geometry(w)
        w=boxes();add(w,'DISTRICT',160,74.4)
        with self.assertRaises(ValueError):n.extract_geometry(w)

    def test_missing_boundary_duplicate_name_and_name_continuation_refused(self):
        w=boxes();w=[x for x in w if x['top']!=181.8]
        with self.assertRaises(ValueError):n.extract_geometry(w)
        w=boxes();next(x for x in w if x['text']=='B')['text']='A'
        with self.assertRaises(ValueError):n.extract_geometry(w)
        w=boxes();add(w,'EXTRA NAME',317.66,74.4+9.24)
        with self.assertRaises(ValueError):n.extract_geometry(w)


if __name__=='__main__':unittest.main()
