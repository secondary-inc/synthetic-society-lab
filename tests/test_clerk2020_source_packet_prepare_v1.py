"""Private authority preparation on authored trees, not issuance/execution."""
import importlib.util
from pathlib import Path
import unittest

import test_clerk2020_source_job_v1 as fixtures

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('authored_packet_helper',REPO/'scripts/prepare_e01_source_phase.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)


class PacketPreparationTests(unittest.TestCase):
    def setUp(self):self.f=fixtures.SourceJobTests();self.f.setUp()
    def tearDown(self):self.f.tearDown()

    def test_boot_packet_preparation_is_private_and_does_not_issue(self):
        root=self.f.root;out=root/'data/processed/AUTHORED_CANDIDATE/boot.local.json'
        result=helper.prepare(root,'BOOT',root/self.f.review['path'],out)
        self.assertFalse(result['registrar_issued']);self.assertEqual(result['source_reads'],0)
        self.assertEqual(out.stat().st_mode&0o777,0o600)
        self.assertEqual(fixtures.j.sha(out.read_bytes()),result['sha256'])
        self.assertFalse(fixtures.n.FixedStore(root).exists('boot_issued'))
        with self.assertRaises(FileExistsError):helper.prepare(root,'BOOT',root/self.f.review['path'],out)

    def test_exec_preparation_requires_exact_prepared_review_and_no_new_issue(self):
        root=self.f.root;boot_packet=root/'data/processed/AUTHORED_CANDIDATE/boot.local.json'
        helper.prepare(root,'BOOT',root/self.f.review['path'],boot_packet)
        boot=self.f.boot();self.assertEqual(boot['status'],'BOOT_PREPARED_NO_SOURCE')
        raw,h=self.f.packet('EXEC',boot['prepared_ref'],boot['completed_anchor_sha256'])
        decision=fixtures.j.decode(raw)['decision'];review=root/decision['prepared_review_ref']['path']
        result=helper.prepare(root,'EXEC',review,root/'data/processed/AUTHORED_CANDIDATE/exec.local.json',boot_packet)
        self.assertFalse(result['registrar_issued'])
        self.assertFalse(fixtures.n.FixedStore(root).exists('exec_issued'))


if __name__=='__main__':unittest.main()
