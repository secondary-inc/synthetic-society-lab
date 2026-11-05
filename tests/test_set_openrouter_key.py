"""Fake credential strings in isolated folders; no real secrets or network."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('key_setup',Path(__file__).resolve().parents[1]/'scripts/set_openrouter_key.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
FAKE = 'sk-or-v1-AUTHORED_FAKE_NOT_A_REAL_CREDENTIAL'


class SetupTests(unittest.TestCase):
    def test_atomic_private_replacement_preserves_other_settings_and_removes_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'.env'
            path.write_text('MAX_SPEND_USD=5\nOPENROUTER_API_KEY=old\n# comment\nexport OPENROUTER_API_KEY=duplicate\nOTHER_SETTING=keep')
            MODULE.save_key(root,FAKE)
            self.assertEqual(path.read_text(),'MAX_SPEND_USD=5\nOPENROUTER_API_KEY='+FAKE+'\n# comment\nOTHER_SETTING=keep')
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(list(root.glob('.env.key-*')),[])

    def test_invalid_or_symlink_source_refuses_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'target';target.write_text('unchanged')
            (root/'.env').symlink_to(target)
            with self.assertRaises(ValueError):MODULE.save_key(root,FAKE)
            self.assertEqual(target.read_text(),'unchanged')
            (root/'.env').unlink()
            for key in ('bad',FAKE+'\n',FAKE+' secret',FAKE+'$(command)',FAKE+'#comment',FAKE+'"'):
                with self.assertRaises(ValueError):MODULE.save_key(root,key)
            self.assertFalse((root/'.env').exists())

    def test_failed_replace_preserves_previous_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'.env';path.write_text('unchanged')
            with patch.object(MODULE.os,'replace',side_effect=OSError('authored failure')):
                with self.assertRaises(OSError):MODULE.save_key(root,FAKE)
            self.assertEqual(path.read_text(),'unchanged')
            self.assertEqual(list(root.glob('.env.key-*')),[])


if __name__=='__main__':unittest.main()
