"""Authored code-only reproduction of JSON-list versus native-tuple equality.

No actual source/reference/helper invocation; frozen implementation unchanged.
"""
import copy
from pathlib import Path
import tempfile
import unittest

from civiclab.e01 import ballots_v1_9 as m
from tests.test_e01_typed_readiness_v1_9 import fixture, runtime, new_runs


class TypedTupleDiagnosis(unittest.TestCase):
    def test_native_NE_bounds_tuple_equals_saved_JSON_bytes_but_strict_object_check_rejects(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            c, base, bundle = fixture(root)
            # This field shape comes from static nebraska_v1_7.extract_geometry
            # source, not actual cached parsing or a private reference body.
            bounds = copy.deepcopy(m.legacy.ne.BOUNDS)
            self.assertTrue(all(type(v) is tuple for v in bounds.values()))
            base['local_only_rosters']['NE']['physical_column_bounds'] = bounds
            ref = c['references']['legacy_rosters']
            raw = m.encoded(base['local_only_rosters'])
            (root / ref['path']).write_bytes(raw)
            ref['sha256'] = m.idaho.digest(raw)
            decoded = m.idaho.strict_json(raw)
            self.assertNotEqual(base['local_only_rosters'], decoded)
            self.assertEqual(m.encoded(base['local_only_rosters']), m.encoded(decoded))
            self.assertEqual(m.canonical_hash(base['local_only_rosters']), m.canonical_hash(decoded))
            self.assertTrue(all(type(v) is list for v in decoded['NE']['physical_column_bounds'].values()))
            before = set((root / 'data/processed/runs').iterdir())
            with runtime(root, c, base, bundle), self.assertRaises(m.idaho.CaptureRejected):
                m.run_readiness(root, c)
            parents = new_runs(root, before)
            self.assertEqual(len(parents), 1)
            failure = m.idaho.strict_json((parents[0] / 'failure.json').read_bytes())
            self.assertEqual(failure['error_type'], 'ValueError')
            self.assertFalse((parents[0] / 'typed_document_readiness.json').exists())
            self.assertFalse((parents[0] / 'typed_release.json').exists())


if __name__ == '__main__':
    unittest.main()
