"""Metadata-only effect spies. No prior studies or model/client execution."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import wrapper_crossmodel_v1_fixture_20261115 as m

class MetadataTests(unittest.TestCase):
    def test_regular_bounded_read_and_exact_limit(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'index.json';p.write_bytes(b'{}')
            self.assertEqual(m._bounded_regular_bytes(p,2),b'{}')
            with patch.object(m.os,'fdopen',side_effect=AssertionError('contents opened before size guard')) as opened:
                with self.assertRaises(ValueError):m._bounded_regular_bytes(p,1)
                opened.assert_not_called()
    def test_symlink_directory_and_fifo_refuse_before_content_read(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);target=root/'authored';target.write_bytes(b'AUTHORED_ONLY')
            alias=root/'index.json';alias.symlink_to(target);fifo=root/'pipe';os.mkfifo(fifo)
            for p in (alias,root,fifo):
                with self.subTest(kind=p.name),patch.object(m.os,'fdopen',side_effect=AssertionError('contents opened')) as opened:
                    with self.assertRaises((OSError,ValueError)):m._bounded_regular_bytes(p,1048576)
                    opened.assert_not_called()
    def test_manifest_checks_all_file_sizes_before_any_content_read(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);a=root/'a';b=root/'b';a.write_bytes(b'a');b.write_bytes(b'b')
            original=Path.lstat
            def metadata(path,*args,**kw):
                result=original(path,*args,**kw)
                if path==b:
                    values=list(result);values[6]=16000001;return os.stat_result(values)
                return result
            with patch.object(Path,'lstat',metadata),patch.object(m,'_bounded_regular_bytes',side_effect=AssertionError('content read')) as read:
                with self.assertRaises(ValueError):m._manifest(root)
                read.assert_not_called()
    def test_manifest_count_and_total_caps_precede_hashing(self):
        for count,size in ((4097,0),(9,16000000)):
            with self.subTest(count=count),tempfile.TemporaryDirectory() as t:
                root=Path(t);paths=[root/str(i) for i in range(count)]
                metadata=os.stat_result((stat.S_IFREG|0o600,0,0,1,0,0,size,0,0,0))
                with patch.object(Path,'rglob',return_value=iter(paths)),patch.object(Path,'lstat',return_value=metadata), \
                     patch.object(m,'_bounded_regular_bytes',side_effect=AssertionError('content read')) as read:
                    with self.assertRaises(ValueError):m._manifest(root)
                    read.assert_not_called()
    def test_valid_small_manifest_hashes_and_create_once_are_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'a').write_bytes(b'abc');(root/'run.lock').write_bytes(b'')
            pin=m._manifest(root);raw=(root/'index.json').read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),pin)
            index=json.loads(raw);self.assertEqual(index['files']['a']['sha256'],hashlib.sha256(b'abc').hexdigest())
            self.assertEqual(index['files']['run.lock']['bytes'],0)
            with self.assertRaises(FileExistsError):m._manifest(root)
            self.assertEqual((root/'index.json').read_bytes(),raw)

if __name__=='__main__':unittest.main()
