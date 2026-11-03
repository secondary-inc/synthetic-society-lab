from pathlib import Path
import json
import tempfile
import unittest
import zipfile
from civiclab.common import atomic_json,sha256_file
from civiclab.intake import restore_inputs


class IntakeTests(unittest.TestCase):
    def test_import_extract_replay_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'project';downloads=Path(tmp)/'downloads';downloads.mkdir()
            data=downloads/'source.csv';data.write_text('a,b\n1,2\n')
            archive=downloads/'bundle.zip'
            with zipfile.ZipFile(archive,'w') as z:z.write(data,'source.csv')
            atomic_json(root/'configs/SOURCE_INVENTORY.json',{'archives':[{
                'supplied_filename':'bundle.zip','local_archive':'data/raw/example/bundle.zip',
                'sha256':sha256_file(archive),'members':[{'name':'source.csv','sha256':sha256_file(data)}]}]})
            self.assertEqual(restore_inputs(root,downloads)['status'],'PLAN')
            self.assertFalse((root/'data/raw').exists())
            self.assertEqual(restore_inputs(root,downloads,True)['status'],'PASS_LOCAL_RESTORE')
            self.assertEqual(restore_inputs(root,downloads,True)['status'],'PASS_LOCAL_RESTORE')
            member=root/'data/raw/example/extracted/source.csv';member.write_text('changed')
            self.assertEqual(restore_inputs(root,downloads,True)['status'],'BLOCKED')
            self.assertEqual(member.read_text(),'changed')

    def test_manifest_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            atomic_json(root/'configs/SOURCE_INVENTORY.json',{'archives':[{'supplied_filename':'safe.zip',
                'local_archive':'../../outside','sha256':'a'*64}]})
            with self.assertRaises(ValueError):restore_inputs(root,root)
