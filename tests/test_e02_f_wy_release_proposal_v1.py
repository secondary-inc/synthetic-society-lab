"""Static proposal checks only; never access raw sources or run admission factories."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = 'configs/e02_F_WY_ACTUAL_RELEASE_PROPOSAL_v1.json'

def read(name):
    return json.loads((ROOT / name).read_text())

def digest(name):
    assert Path(name).parts[0] in ('configs', 'docs', 'reports', 'src', 'tests')
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()

class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.p = read(PROPOSAL)
        self.b = read(self.p['baseline']['path'])

    def test_frozen_references(self):
        self.assertEqual(digest(self.p['baseline']['path']), self.p['baseline']['sha256'])
        for name, expected in self.p['required_files'].items():
            self.assertEqual(digest(name), expected, name)
        ref = self.p['capability_remediation']
        self.assertEqual(digest(ref['path']), ref['sha256'])

    def test_design_and_no_authority(self):
        design = {k:v for k,v in self.b.items() if k not in ('actual_authority','actual_approvals','scope')}
        d = hashlib.sha256(json.dumps(design, sort_keys=True, separators=(',',':'), allow_nan=False).encode()).hexdigest()
        self.assertEqual(d, self.p['reviewed_design_sha256'])
        for cfg in (self.p, self.b):
            self.assertEqual(cfg['actual_authority'], 0)
            self.assertTrue(all(v is None for v in cfg['actual_approvals'].values()))

    def test_draft_receipts_cannot_be_approvals(self):
        for key, ref in self.p['draft_receipts_not_runtime_approvals'].items():
            self.assertEqual(digest(ref['path']), ref['sha256'])
            t = read(ref['path'])
            self.assertEqual(t['status'], 'DRAFT_NOT_AN_APPROVAL')
            self.assertIsNone(t['auditor_role'])
            self.assertEqual(t['reviewed_required_files'], self.b['required_files'])
            self.assertEqual(t['reviewed_design_sha256'], self.p['reviewed_design_sha256'])
            self.assertNotEqual(t['status'], t['expected_future_status'])
            if key == 'adapter_code': self.assertIsNone(t['fixture_tests_passed'])
            if key == 'execution':
                for field in ('adapter_code_approval_sha256','exact_source_approval_sha256','inspection_carry_forward_evidence_sha256'):
                    self.assertIsNone(t[field])
                self.assertNotIn('runtime_config_sha256', t)

    def test_unknown_identity_and_results(self):
        self.assertEqual(set(self.p['fresh_source_stat_identity']), {'device','inode','bytes','mtime_ns','ctime_ns'})
        self.assertTrue(all(v is None for v in self.p['fresh_source_stat_identity'].values()))
        self.assertEqual(self.p['source_filesystem_operations_performed'], 0)
        self.assertFalse(self.p['fresh_source_verification_performed'])
        for key in ('adult_count','adult_weight','six_domain_values'): self.assertIsNone(self.p[key])

    def test_exact_source_and_manifest(self):
        s = read(self.b['proposal'])['source']
        self.assertEqual(s, self.p['known_historical_source_metadata'])
        m = self.p['provisional_runtime_manifest_not_admissible']
        self.assertEqual(m['archive_sha256'], s['archive']['sha256'])
        self.assertEqual(m['expected_identity'], self.p['fresh_source_stat_identity'])
        self.assertEqual(m['expected_rows'], 29297)
        for actual, known in zip(m['members'], s['literal_members'], strict=True):
            self.assertEqual(actual['name'], known['name'])
            self.assertEqual(actual['bytes'], known['declared_uncompressed_bytes'])
            self.assertEqual(actual['compressed_bytes'], known['compressed_bytes'])
            self.assertEqual(actual['crc32'], known['crc32'])
        self.assertEqual(len(m['members']), 2)
        self.assertEqual(self.p['known_metadata_origins'], self.b['metadata_sources'])

    def test_caps_and_accounting(self):
        self.assertEqual(self.p['native_limits_unchanged'], self.b['limits'])
        self.assertEqual(self.p['native_storage_unchanged'], self.b['storage'])
        r = self.p['resource_accounting']; a = r['source_admission_inspection']; e = r['runtime_ENROLL']; q = r['runtime_PRIMARY_and_REPLAY_each']
        self.assertEqual(a['expected_expanded_bytes'], 1876+99489)
        self.assertEqual(a['reserved_expanded_bytes'], 65536+3*2097152)
        self.assertEqual(q['reserved_expanded_bytes'], 18928161+2*(1876+99489))
        for field in ('expected_expanded_bytes','reserved_expanded_bytes','person_rows','logical_operations','maximum_seconds'):
            self.assertEqual(r['runtime_totals'][field], e[field]+2*q[field])
            self.assertEqual(r['inspection_plus_runtime_totals'][field], a[field]+e[field]+2*q[field])
        self.assertEqual(r['inspection_plus_runtime_totals']['reserved_expanded_bytes'], 50975766)
        self.assertLessEqual(r['inspection_plus_runtime_totals']['maximum_seconds'], self.b['limits']['processing_seconds'])
        self.assertEqual(r['unique_source_bytes_once'], 4202266)
        self.assertEqual(r['retained_archive_bytes_once'], 4202266)
        for k in ('GETs','network_body_bytes','model_calls','api_cost_usd','automatic_retries'): self.assertEqual(r[k], 0)

    def test_output_is_lexical_and_new_proposal_only(self):
        relative = Path(self.p['proposed_output_directory'])
        self.assertFalse(relative.is_absolute())
        self.assertNotIn('..', relative.parts)
        self.assertEqual(relative.parts[:3], ('data','processed','e02_F_wy_private'))
        # This frozen proposal records its author's historical lexical path.
        # A restored checkout must not relabel that string as a fresh location
        # observation or rewrite it to match the current machine.
        self.assertEqual(digest(PROPOSAL), 'f39e262dd8b706569092def719711cdbefdafd7efaf20aa2d97a3206605e8aa5')
        historical = Path(self.p['proposed_canonical_output_directory'])
        self.assertTrue(historical.is_absolute())
        self.assertNotIn('..', historical.parts)
        self.assertEqual(historical.parts[-len(relative.parts):], relative.parts)
        self.assertEqual(self.p['status'], 'PROPOSAL_ONLY_NOT_A_RELEASE')
        original = 'tests/fixtures/historical/e02_f_wy_release_proposal_v1_test_original.py.txt'
        self.assertEqual(digest(original), '24d795a3753d215ecacab0d05e4fefa4c68d34ecdbd07913b4128a2b80a4c180')
        self.assertFalse(self.p['output_existence_and_canonicalization_verified'])

    def test_bootstrap_and_enforcement_remain_blocked(self):
        self.assertIn('NOT_IMPLEMENTED', self.p['resource_accounting']['combined_deadline_enforcement'])
        self.assertGreaterEqual(len(self.p['blocks']), 5)
        self.assertIn('actual_source_continuation', self.p['forbidden_actions'])
        self.assertEqual(self.p['status'], 'PROPOSAL_ONLY_NOT_A_RELEASE')
