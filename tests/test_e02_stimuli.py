from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from civiclab.e02.stimuli import acquire, extract_excerpt, metadata_dates, verify_corpus, URLS


RAW = b'<html><body><p>Outside context.</p><p>(3)(A) Exact <em>official</em> text &amp; conditions.</p><script>not text</script></body></html>'
XML = b'<mods xmlns="http://www.loc.gov/mods/v3"><originInfo><dateIssued encoding="w3cdtf">2024-12-31</dateIssued></originInfo></mods>'


class StimulusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'configs').mkdir()
        text = extract_excerpt(RAW, ['(3)(A)'])
        self.spec = {'schema_version':1, 'corpus_id':'EXPLICIT_OFFLINE_FIXTURE', 'sources':[
            {'source_key':'foia','url':URLS['foia'],'filename':'foia.html','sha256':sha256(RAW).hexdigest()},
            {'source_key':'foia-mods','url':URLS['foia-mods'],'filename':'foia-mods.xml','sha256':sha256(XML).hexdigest()}],
            'stimuli':[{'id':'FIXTURE','source_key':'foia','text':text,'text_sha256':sha256(text.encode()).hexdigest(),
                        'paragraph_prefixes':['(3)(A)'],'kind':'OFFICIAL_POLICY_TEXT','forecast_admissible':False,
                        'rights_basis':'US_FEDERAL_STATUTORY_TEXT_PUBLIC_DOMAIN','source_dates':metadata_dates(XML)}]}
        self.write_spec()

    def write_spec(self):
        (self.root/'configs/e02_official_stimuli.json').write_text(json.dumps(self.spec))

    def transport(self,url):
        return XML if url.endswith('mods.xml') else RAW

    def test_exact_excerpt_import_replay_dates_and_script_ignored(self):
        result = acquire(self.root,transport=self.transport)
        self.assertEqual(result['status'],'PASS_PROVENANCE_CHECKS')
        self.assertEqual(self.spec['stimuli'][0]['text'],'(3)(A) Exact official text & conditions.')
        replay=acquire(self.root,transport=lambda u:self.fail('idempotent cache must not refetch'))
        self.assertEqual(result['corpus_hash'],replay['corpus_hash'])
        self.assertEqual(replay['independent_rights_and_content_audit'],'PENDING')

    def test_missing_or_ambiguous_selectors_fail(self):
        for raw,prefix in [(RAW,'missing'),(b'<p>same text</p><p>same text</p>','same')]:
            with self.assertRaises(ValueError):extract_excerpt(raw,[prefix])

    def test_byte_drift_is_quarantined_not_silently_accepted(self):
        with self.assertRaisesRegex(ValueError,'source drift'):
            acquire(self.root,transport=lambda u:RAW+b'new source bytes')
        folder=self.root/'data/raw/e02_official_sources'
        self.assertFalse((folder/'foia.html').exists())
        self.assertEqual(len(list(folder.glob('foia-DRIFT-*'))),1)

    def test_source_override_and_path_traversal_fail_closed(self):
        self.spec['sources'][0]['url']='https://example.invalid/copyrighted-news'
        self.write_spec()
        with self.assertRaisesRegex(ValueError,'allowlisted'):
            acquire(self.root,transport=lambda u:self.fail('must fail before fetching'))
        self.spec['sources'][0]['url']=URLS['foia'];self.spec['sources'][0]['filename']='../../../outside'
        self.write_spec()
        with self.assertRaisesRegex(ValueError,'escapes'):
            acquire(self.root,transport=lambda u:self.fail('must fail before fetching'))

    def test_tampered_excerpt_date_and_duplicate_stimulus_rejected(self):
        acquire(self.root,transport=self.transport)
        original=deepcopy(self.spec)
        self.spec['stimuli'][0]['text']='invented quotation';self.write_spec()
        with self.assertRaisesRegex(ValueError,'differs'):verify_corpus(self.root)
        self.spec=deepcopy(original);self.spec['stimuli'][0]['source_dates']={};self.write_spec()
        with self.assertRaisesRegex(ValueError,'dates differ'):verify_corpus(self.root)
        self.spec=deepcopy(original);self.spec['stimuli'].append(deepcopy(self.spec['stimuli'][0]));self.write_spec()
        with self.assertRaisesRegex(ValueError,'duplicate'):verify_corpus(self.root)

    def test_empty_corpus_and_external_entity_metadata_not_accepted(self):
        self.spec['stimuli']=[];self.write_spec()
        with self.assertRaisesRegex(ValueError,'nonempty'):verify_corpus(self.root)
        with self.assertRaises(ValueError):metadata_dates(b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>')
