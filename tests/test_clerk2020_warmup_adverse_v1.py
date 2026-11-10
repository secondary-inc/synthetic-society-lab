"""Additional authored swallowed-negative regressions; no installed/native/source I/O."""
from pathlib import Path
import tempfile
import unittest

from test_clerk2020_warmup_qualification_v1 import c, authored_reader, patch


class WarmupSwallowedCacheRefusalTests(unittest.TestCase):
    def test_alias_and_malformed_cache_failures_survive_expected_negative(self):
        for kind, expected in [('alias', 'CACHE_SOURCE_ALIAS_REFUSED'),
                               ('absent_source', 'READ_STAT_UNAVAILABLE'),
                               ('malformed_cache', 'READ_STAT_UNAVAILABLE')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                base = root / 'AUTHORED_BASE'
                base.mkdir()
                with patch.object(c.sys, 'base_prefix', str(base)):
                    guard = c.WarmupGuard(root)
                guard.transition('WARMUP')
                if kind == 'alias':
                    target = base / 'target.py'
                    target.write_bytes(b'# AUTHORED')
                    source = base / 'alias.py'
                    source.symlink_to(target)
                    cache = Path(c.importlib.util.cache_from_source(str(source)))
                elif kind == 'absent_source':
                    cache = Path(c.importlib.util.cache_from_source(str(base / 'ABSENT.py')))
                else:
                    cache = base / '__pycache__' / 'INVALID_CACHE_NAME.pyc'
                reader, _ = authored_reader()
                def swallowed(stream, **kwargs):
                    if b'not a PDF object graph' in stream.getvalue():
                        try:
                            guard.guard('open', (str(cache), 'r', 0))
                        except c.frozen.QualificationStopped:
                            pass  # Intentionally simulate a parser swallowing it.
                    return reader(stream, **kwargs)
                progress = {}
                self.assertEqual(c.generated_checks(swallowed, c.guarded.GeneratedTelemetry(), progress), 119)
                self.assertEqual(progress['reader_attempts_entered'], 4)
                self.assertEqual(guard.first_refusal['predicate'], expected)
                self.assertEqual(guard.first_refusal['phase'], 'WARMUP')
                with self.assertRaises(c.frozen.QualificationStopped):
                    guard.transition('HASH')
                self.assertEqual(guard.phase, 'WARMUP')


if __name__ == '__main__':
    unittest.main()
