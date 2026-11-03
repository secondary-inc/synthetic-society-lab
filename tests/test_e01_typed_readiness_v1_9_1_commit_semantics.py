"""Separate commit/acknowledgment clarification fixtures; frozen candidate unchanged.

Read-only storage is modeled by EROFS at both RunStore persistence boundaries.
This does not mount an OS filesystem or claim a hostile-host guarantee.
"""
import errno
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab.common import sha256_file
from civiclab.e01 import ballots_v1_9_1 as m
from tests.test_e01_typed_readiness_v1_9_1 import fixture, runtime, new_runs


class TypedCommitSemanticsTests(unittest.TestCase):
    def scenario(self, commit_file, read_only):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            c, base, bundle = fixture(root)
            before = set((root / 'data/processed/runs').iterdir())
            original_write = m.RunStore.write
            original_event = m.RunStore.event
            injected = {'persisted': False, 'denials': 0}
            committed_bytes = {}

            def unavailable():
                injected['denials'] += 1
                raise OSError(errno.EROFS, 'AUTHORED_READ_ONLY_STORAGE')

            def write(run, name, value):
                if injected['persisted'] and read_only:
                    unavailable()
                result = original_write(run, name, value)
                if name == commit_file and not injected['persisted']:
                    # Persist exact bytes first. Then fail delivery of the ACK.
                    committed_bytes.update({
                        p.name: p.read_bytes() for p in run.path.iterdir()
                        if p.is_file() and p.name != '.lock'
                    })
                    injected['persisted'] = True
                    raise OSError(errno.EIO, 'AUTHORED_ACK_UNCERTAIN')
                return result

            def event(run, kind, **fields):
                if injected['persisted'] and read_only:
                    unavailable()
                return original_event(run, kind, **fields)

            with runtime(root, c, base, bundle), \
                    patch.object(m.RunStore, 'write', new=write), \
                    patch.object(m.RunStore, 'event', new=event):
                with self.assertRaises(m.idaho.CaptureRejected) as outcome:
                    m.run_readiness(root, c)
                self.assertNotIn('AUTHORED_', str(outcome.exception))
                self.assertTrue(injected['persisted'])
                parents = new_runs(root, before)
                self.assertEqual(len(parents), 1)  # No implicit retry or new parent.
                parent = parents[0]
                if read_only:
                    self.assertGreater(injected['denials'], 0)
                    self.assertEqual(committed_bytes, {
                        p.name: p.read_bytes() for p in parent.iterdir()
                        if p.is_file() and p.name != '.lock'
                    })
                    self.assertFalse((parent / 'failure.json').exists())
                    self.assertFalse((parent / 'terminal_failure.local.json').exists())
                if commit_file == 'typed_release.json' and read_only:
                    # Valid final seal survives caller exception. Read-only
                    # resolution validates evidence without rewriting it.
                    public = m.read_verified_public(parent)
                    self.assertFalse(public['accepted_coverage_promoted'])
                    self.assertFalse(public['source_adoption'])
                    self.assertFalse(public['forecast_consumption'])
                    self.assertEqual(public['metrics']['final_ballots_accepted'], 0)
                    before_read = {p.name: sha256_file(p) for p in parent.iterdir() if p.is_file()}
                    m.read_verified_public(parent)
                    self.assertEqual(before_read, {p.name: sha256_file(p) for p in parent.iterdir() if p.is_file()})
                else:
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        m.read_verified_public(parent)
                if not read_only:
                    self.assertTrue((parent / 'failure.json').exists())
                    self.assertTrue((parent / 'terminal_failure.local.json').exists())
                    # Original successful summary and seal remain evidence;
                    # failure records invalidate ordinary consumer admission.
                    self.assertEqual((parent / 'summary.json').read_bytes(), committed_bytes['summary.json'])
                    self.assertEqual((parent / 'typed_release.json').read_bytes(), committed_bytes['typed_release.json'])

    def test_after_final_seal_persist_then_error_read_only_retains_valid_commit(self):
        self.scenario('typed_release.json', read_only=True)

    def test_before_final_seal_read_only_failure_remains_uncommitted(self):
        self.scenario('checksums.json', read_only=True)

    def test_after_final_seal_error_writable_failure_evidence_still_denies(self):
        self.scenario('typed_release.json', read_only=False)


if __name__ == '__main__':
    unittest.main()
