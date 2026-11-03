"""Public evidence closure and private-output refusal; isolated fixture packages."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from civiclab.common import RunStore
from civiclab import reproduction_v2 as module

ROOT = Path(__file__).resolve().parents[1]


class PublicEvidencePackageTests(unittest.TestCase):
    def populate(self, root):
        for name, expected in module.PUBLIC_RECEIPTS.items():
            blob = (ROOT / name).read_bytes()
            self.assertEqual(hashlib.sha256(blob).hexdigest(), expected)
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        with RunStore(root, 'E02', {}, kind='MOCK') as run:
            run.write('mock.json', {'label': 'MOCK', 'value': 0})
            run.finish({'status': 'MOCK'})
        return run

    def test_exact_evidence_included_without_following_private_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); run = self.populate(root)
            private = root / 'data/raw/DO_NOT_EXPORT.local.json'
            private.parent.mkdir(parents=True); private.write_text('PRIVATE_SENTINEL')
            before = private.read_bytes()
            output = root / 'review.zip'
            result = module.build_package(root, output, [run.run_id])
            self.assertEqual(result['status'], 'PASS_PACKAGE_INTEGRITY')
            with zipfile.ZipFile(output) as archive:
                manifest = json.loads(archive.read('REPRODUCIBILITY_MANIFEST.json'))
                self.assertEqual(manifest['schema_version'], 2)
                self.assertEqual(manifest['public_evidence_receipts'], module.PUBLIC_RECEIPTS)
                for name, expected in module.PUBLIC_RECEIPTS.items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)
                self.assertFalse(any(n.startswith('data/raw/') for n in archive.namelist()))
                self.assertFalse(any(b'PRIVATE_SENTINEL' in archive.read(n) for n in archive.namelist()))
            self.assertEqual(private.read_bytes(), before)
            other = root / 'review-again.zip'
            module.build_package(root, other, [run.run_id])
            self.assertEqual(output.read_bytes(), other.read_bytes())
            with self.assertRaises(FileExistsError): module.build_package(root, output, [run.run_id])

    def test_every_required_receipt_missing_changed_oversized_or_aliased_refuses(self):
        for name in module.PUBLIC_RECEIPTS:
            for attack in ('missing', 'changed', 'oversized', 'symlink'):
                with self.subTest(name=name, attack=attack), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp).resolve(); self.populate(root); target = root / name
                    if attack == 'missing': target.unlink()
                    elif attack == 'changed': target.write_bytes(target.read_bytes()+b' ')
                    elif attack == 'oversized': target.write_bytes(b'x'*(module.PUBLIC_RECEIPT_LIMIT+1))
                    else:
                        external = root / 'external.txt'; shutil.copyfile(target, external)
                        target.unlink(); target.symlink_to(external)
                    with self.assertRaises(ValueError): module.source_inputs(root)

    def test_receipt_mutation_during_assembly_refuses(self):
        from civiclab.dashboard import verified_run
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); run = self.populate(root)
            target = root / next(iter(module.PUBLIC_RECEIPTS))
            def change(path):
                result = verified_run(path)
                target.write_bytes(target.read_bytes()+b' ')
                return result
            with patch.object(module, 'verified_run', side_effect=change):
                with self.assertRaises(ValueError): module.build_package(root, root/'fail.zip', [run.run_id])
            self.assertFalse((root/'fail.zip').exists())

    def test_private_run_and_private_report_refuse_before_archive(self):
        for private_report in (False, True):
            with self.subTest(private_report=private_report), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve(); run = self.populate(root)
                if private_report:
                    (root/'reports/E02_secret.local.json').write_text('{"private":true}')
                else:
                    with RunStore(root, 'E02', {}, kind='MOCK') as run:
                        run.write('respondent.local.json', {'private':True}); run.finish({'status':'MOCK'})
                with self.assertRaisesRegex(ValueError, 'local-only'):
                    module.build_package(root, root/'fail.zip', [run.run_id])
                self.assertFalse((root/'fail.zip').exists())

    def test_unsafe_run_path_empty_selection_and_preexisting_temporary_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); run = self.populate(root)
            for ids in ([], ['../../outside']):
                with self.assertRaises(ValueError): module.build_package(root, root/'fail.zip', ids)
            temporary = root/'fail.zip.writing'; temporary.write_bytes(b'PRESERVE')
            with self.assertRaises(FileExistsError): module.build_package(root, root/'fail.zip', [run.run_id])
            self.assertEqual(temporary.read_bytes(), b'PRESERVE')

    def test_root_alias_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()/'real'; root.mkdir(); run = self.populate(root)
            alias = Path(tmp)/'alias'; alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'alias'):
                module.build_package(alias, Path(tmp)/'fail.zip', [run.run_id])

    def test_post_verification_run_mutation_and_coordinated_reseal_refuse(self):
        from civiclab.dashboard import verified_run
        for attack in ('payload', 'reseal', 'add_member', 'remove_member', 'seal_reformat'):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve(); run = self.populate(root)
                def mutate(path):
                    admitted = verified_run(path)
                    ledger = path/'checksums.json'
                    checks = json.loads(ledger.read_text())
                    if attack in ('payload', 'reseal'):
                        (path/'mock.json').write_text('{"value":999,"label":"MOCK"}')
                        checks['mock.json'] = hashlib.sha256((path/'mock.json').read_bytes()).hexdigest()
                    elif attack == 'add_member':
                        (path/'added.json').write_text('{}')
                        checks['added.json'] = hashlib.sha256(b'{}').hexdigest()
                    elif attack == 'remove_member':
                        (path/'mock.json').unlink(); del checks['mock.json']
                    if attack != 'payload': ledger.write_text(json.dumps(checks, indent=7)+'\n')
                    return admitted
                with patch.object(module, 'verified_run', side_effect=mutate):
                    with self.assertRaises((ValueError, OSError)):
                        module.build_package(root, root/'fail.zip', [run.run_id])
                self.assertFalse((root/'fail.zip').exists())
                self.assertFalse((root/'fail.zip.writing').exists())

    def test_source_alias_inside_root_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); run = self.populate(root)
            (root/'src').mkdir(); (root/'src/real.py').write_text('value=1\n')
            (root/'src/alias.py').symlink_to(root/'src/real.py')
            with self.assertRaisesRegex(ValueError, 'alias'):
                module.build_package(root, root/'fail.zip', [run.run_id])

    def test_output_created_at_publication_is_never_overwritten(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); run = self.populate(root); output = root/'late.zip'
            original_link = os.link
            def late_output(source, destination):
                Path(destination).write_bytes(b'PRESERVE_LATE_OUTPUT')
                return original_link(source, destination)
            with patch.object(module.os, 'link', side_effect=late_output):
                with self.assertRaises(FileExistsError): module.build_package(root, output, [run.run_id])
            self.assertEqual(output.read_bytes(), b'PRESERVE_LATE_OUTPUT')
            self.assertTrue(output.with_suffix('.zip.writing').is_file())


if __name__ == '__main__': unittest.main()
