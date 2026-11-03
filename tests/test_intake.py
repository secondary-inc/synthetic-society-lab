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

    def test_explicit_subset_is_not_full_inventory_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'project';downloads=Path(tmp)/'downloads';downloads.mkdir()
            source=downloads/'one.txt';source.write_text('registered bytes')
            atomic_json(root/'configs/SOURCE_INVENTORY.json',{'archives':[], 'documents':[
                {'supplied_filename':name,'local_path':'data/raw/'+name,'sha256':sha256_file(source)}
                for name in ('one.txt','missing.txt')]})
            with self.assertRaises(ValueError):restore_inputs(root,downloads,True,only=['unknown.txt'])
            with self.assertRaises(ValueError):restore_inputs(root,downloads,True,only=[])
            with self.assertRaises(ValueError):restore_inputs(root,downloads,True,only=['one.txt','one.txt'])
            self.assertFalse((root/'data/raw').exists())
            result=restore_inputs(root,downloads,True,only=['one.txt'])
            self.assertEqual(result['status'],'PASS_SELECTED_LOCAL_RESTORE')
            self.assertEqual(result['selected_inputs'],['one.txt'])
            self.assertFalse((root/'data/raw/missing.txt').exists())
            self.assertEqual(restore_inputs(root,downloads,True)['status'],'BLOCKED')
            (root/'data/raw/one.txt').write_text('drift')
            self.assertEqual(restore_inputs(root,downloads,True,only=['one.txt'])['status'],'BLOCKED')
            self.assertEqual((root/'data/raw/one.txt').read_text(),'drift')
