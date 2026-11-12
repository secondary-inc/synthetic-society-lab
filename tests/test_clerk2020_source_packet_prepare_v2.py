"""MOCK bounded technical preparation; no campaign issuance or native access."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import test_clerk2020_source_job_v1 as fixtures

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bounded_packet_helper',REPO/'scripts/prepare_e01_source_phase_v2.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
j=fixtures.j

class BoundedPreparationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.SourceJobTests();self.f.setUp();self.root=self.f.root
        self.review=self.root/self.f.review['path']
        self.out=self.root/'data/processed/AUTHORED_CANDIDATE/boot.local.json'
    def tearDown(self):self.f.tearDown()
    def receipt(self,phase='BOOT'):
        return j.decode((self.root/helper.TECH_BASE/phase/'RECEIPT.local.json').read_bytes())
    def prepare_boot(self):return helper.prepare(self.root,'BOOT',self.review,self.out)

    def test_boot_only_two_metadata_reads_started_first_no_code_reread(self):
        original=j.read_file;reads=[]
        def reading(path,maximum):
            self.assertTrue((self.root/helper.TECH_BASE/'BOOT/STARTED.local.json').exists())
            self.assertIn(path,{self.review,self.root/j.METHODS});reads.append(path)
            return original(path,maximum)
        # Preparation transports reviewed identities. Actual BOOT verifies code.
        (self.root/j.CODE_PATHS[0]).write_bytes(b'AUTHORED_DRIFT_NOT_READ_BY_HELPER')
        with patch.object(j,'read_file',side_effect=reading),patch.object(j,'source_snapshot') as source,patch.object(j,'dispatch') as dispatch:
            result=self.prepare_boot()
        source.assert_not_called();dispatch.assert_not_called()
        receipt=self.receipt();self.assertEqual(receipt['read_count'],2)
        self.assertEqual(len(reads),2);self.assertLessEqual(receipt['reserved_read_bytes'],1048576)
        self.assertEqual(j.decode(self.out.read_bytes())['static_spec']['code_refs'],self.f.refs)
        self.assertFalse(result['registrar_issued']);self.assertEqual(self.out.stat().st_mode&0o777,0o600)
        self.assertFalse(fixtures.n.FixedStore(self.root).exists('boot_issued'))
        packet=self.out.read_bytes()
        with patch.object(j,'source_snapshot') as source:
            stopped=j.run_boot(self.root,packet,j.sha(packet))
        self.assertEqual(stopped['status'],'FAILED_OR_UNKNOWN_NO_RETRY');source.assert_not_called()

    def test_exec_six_metadata_reads_no_new_issue(self):
        self.prepare_boot();boot=self.f.boot()
        raw,_=self.f.packet('EXEC',boot['prepared_ref'],boot['completed_anchor_sha256'])
        review=self.root/j.decode(raw)['decision']['prepared_review_ref']['path']
        out=self.out.with_name('exec.local.json')
        result=helper.prepare(self.root,'EXEC',review,out,self.out)
        receipt=self.receipt('EXEC');self.assertEqual(receipt['read_count'],6)
        self.assertLessEqual(receipt['reserved_read_bytes'],1048576)
        self.assertFalse(result['registrar_issued']);self.assertFalse(receipt['campaign_issue_or_execution'])
        store=fixtures.n.FixedStore(self.root);decision=j.decode(out.read_bytes())['decision']
        store.bind_run(j.run_id(fixtures.n.CAMPAIGN,j.JOB,decision));self.assertFalse(store.exists('exec_issued'))

    def test_duplicate_scope_refused_before_any_read_even_different_output(self):
        self.prepare_boot();before=(self.root/helper.TECH_BASE/'BOOT/RECEIPT.local.json').read_bytes()
        with patch.object(j,'read_file') as read:
            with self.assertRaises(FileExistsError):helper.prepare(self.root,'BOOT',self.review,self.out.with_name('other.local.json'))
        read.assert_not_called();self.assertEqual(before,(self.root/helper.TECH_BASE/'BOOT/RECEIPT.local.json').read_bytes())

    def test_oversize_input_refused_before_open_receipt_consumed(self):
        self.review.write_bytes(b'x'*131073)
        with patch.object(j,'read_file') as read:
            with self.assertRaises(fixtures.n.Refused):self.prepare_boot()
        read.assert_not_called();r=self.receipt();self.assertEqual(r['read_count'],0)
        self.assertEqual(r['status'],'FAILED_UNKNOWN_NO_RETRY');self.assertFalse(self.out.exists())
        with self.assertRaises(FileExistsError):self.prepare_boot()

    def test_read_failure_retains_reservation_and_failure_receipt(self):
        with patch.object(j,'read_file',side_effect=OSError('AUTHORED_READ_FAILURE')):
            with self.assertRaises(OSError):self.prepare_boot()
        r=self.receipt();self.assertEqual(r['read_count'],1)
        self.assertGreater(r['reserved_read_bytes'],0);self.assertEqual(r['observed_read_bytes'],0)
        self.assertIsNone(r['reads'][0]['observed_bytes']);self.assertEqual(r['credit_restored'],0)

    def test_byte_count_and_fixed_count_caps_refuse_before_body_read(self):
        meter=helper.TechnicalReads(self.root,'BOOT',{self.review})
        meter.reserved=helper.READ_CAP
        with patch.object(j,'read_file') as read:
            with self.assertRaises(fixtures.n.Refused):meter.read(self.review,131073)
        read.assert_not_called()
        meter=helper.TechnicalReads(self.root,'BOOT',{self.review});meter.records=[{},{}]
        with patch.object(j,'read_file') as read:
            with self.assertRaises(fixtures.n.Refused):meter.read(self.review,131073)
        read.assert_not_called()

    def test_unlisted_path_and_raw_path_refused_without_body_read(self):
        for path in (self.root/j.CODE_PATHS[0],self.root/(j.DATA_ROOT+'clerk2020_statistics.pdf')):
            meter=helper.TechnicalReads(self.root,'BOOT',{self.review})
            with patch.object(j,'read_file') as read:
                with self.assertRaises(fixtures.n.Refused):meter.read(path,131073)
            read.assert_not_called()

    def test_output_collision_preserves_failure_receipt(self):
        self.out.parent.mkdir(parents=True);self.out.write_bytes(b'AUTHORED_EXISTING')
        with self.assertRaises(FileExistsError):self.prepare_boot()
        self.assertEqual(self.out.read_bytes(),b'AUTHORED_EXISTING')
        self.assertEqual(self.receipt()['status'],'FAILED_UNKNOWN_NO_RETRY')

if __name__=='__main__':unittest.main()
