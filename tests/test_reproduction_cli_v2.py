"""The public command must enforce current receipt and original-seal guards."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from civiclab.cli import main
import test_reproduction_v2 as fixtures


class ReproductionCommandTests(unittest.TestCase):
    def invoke(self, root, run_id):
        with patch.object(sys,'argv',['civiclab','--root',str(root),'repro-pack',
                                     '--run',run_id,'--out','result.zip']), redirect_stdout(io.StringIO()):
            main()

    def test_command_emits_reviewed_v2_evidence_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); run=fixtures.PublicEvidencePackageTests().populate(root)
            self.invoke(root,run.run_id)
            with zipfile.ZipFile(root/'result.zip') as archive:
                manifest=json.loads(archive.read('REPRODUCIBILITY_MANIFEST.json'))
                self.assertEqual(manifest['schema_version'],2)
                self.assertEqual(len(manifest['public_evidence_receipts']),6)

    def test_command_refuses_missing_required_receipt(self):
        from civiclab.reproduction_v2 import PUBLIC_RECEIPTS
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); run=fixtures.PublicEvidencePackageTests().populate(root)
            (root/next(iter(PUBLIC_RECEIPTS))).unlink()
            with self.assertRaisesRegex(ValueError,'required public receipt missing'):
                self.invoke(root,run.run_id)
            self.assertFalse((root/'result.zip').exists())

    def test_command_refuses_post_verification_run_mutation(self):
        from civiclab.dashboard import verified_run
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); run=fixtures.PublicEvidencePackageTests().populate(root)
            def mutation(path):
                original=verified_run(path)
                (path/'mock.json').write_text('{"label":"MOCK","value":5}')
                return original
            with patch('civiclab.reproduction_v2.verified_run',side_effect=mutation):
                with self.assertRaisesRegex(ValueError,'payload changed'):
                    self.invoke(root,run.run_id)
            self.assertFalse((root/'result.zip').exists())


if __name__=='__main__':unittest.main()
