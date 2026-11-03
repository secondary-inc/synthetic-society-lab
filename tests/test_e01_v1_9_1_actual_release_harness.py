"""Authored harness plumbing/guard checks. All actual component calls mocked."""
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('authored_v191_release_harness', Path(__file__).resolve().parents[1] / 'scripts/e01_typed_readiness_v1_9_1_actual_release.py')
h = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)


class ActualReleaseHarnessGuards(unittest.TestCase):
    def setup(self, root):
        (root/'data/processed/runs').mkdir(parents=True)
        control = root/'data/processed/e01_typed_v1_9_1_actual_control/AUTHORED_ONLY'
        c = {'sources':[{'source_id':'DEMO'+str(i),'bytes':1} for i in range(40)],
             'references':{k:{} for k in ['legacy_public','legacy_rosters','id_records','id_diagnostics']}}
        stack = ExitStack()
        stack.enter_context(patch.object(h, 'pins_and_runtime', return_value=(c, {}, {'python':'AUTHORED'})))
        stack.enter_context(patch.object(h.m, 'root_guard', return_value=root))
        stack.enter_context(patch.object(h.m, 'verify_bound_inputs', return_value={k:None for k in c['references']}))
        return control, stack

    def phase(self, root, control, phase, authorization=None):
        argv = ['harness', phase, '--root', str(root), '--control', str(control),
                '--execute-lead-release', authorization or h.AUTHORIZATION]
        with patch('sys.argv', argv), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            h.main()

    def test_static_version_and_exact_pins_are_the_distinct_new_release(self):
        self.assertEqual(h.AUTHORIZATION, 'E01_TYPED_V1_9_1_CACHED_PRIMARY_REPLAY_20261103_77f74649')
        self.assertEqual(h.CONFIG, 'configs/e01_typed_readiness_v1_9_1_candidate.json')
        self.assertEqual(h.EXPECTED[h.CONFIG], 'f017d3b4ceb1647add88eeb66a8d4d386f156f98169ac3807f7d800083fb2997')
        self.assertEqual(h.EXPECTED['src/civiclab/e01/ballots_v1_9_1.py'], '30e02bfa068f400846c8feff612695c3ba2c12497d6bc1567ad4c75858788f8b')
        self.assertEqual(h.EXPECTED[h.AUDIT], '77f746498aa9d25e3737dbc7f73c0e2950009b890e83a11a7e906458c4cb7b89')

    def test_wrong_release_refused_before_control_creation_or_any_component(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();control=root/'data/processed/e01_typed_v1_9_1_actual_control/AUTHORED_ONLY'
            with patch.object(h,'pins_and_runtime') as pins,patch.object(h.m,'run_readiness') as run,self.assertRaises(SystemExit):
                self.phase(root,control,'preflight','OLD_UNAPPROVED_RELEASE')
            self.assertFalse(control.exists());pins.assert_not_called();run.assert_not_called()

    def test_authored_primary_replay_exactly_once_and_repeated_phase_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();control,stack=self.setup(root);count=[0]
            def run(*args):
                count[0]+=1;p=root/'data/processed/runs'/('e01-AUTHORED-'+str(count[0]));p.mkdir()
                (p/'fixture.local.json').write_text('{"scope":"AUTHORED_ONLY"}');return p
            with stack,patch.object(h.m,'run_readiness',side_effect=run),patch.object(h.m,'read_verified_public',return_value={'metrics':{}}):
                self.phase(root,control,'preflight');self.phase(root,control,'primary');self.phase(root,control,'replay')
                for phase in ['preflight','primary','replay']:
                    with self.assertRaises(FileExistsError):self.phase(root,control,phase)
            self.assertEqual(count[0],2)
            self.assertTrue((control/'primary_complete.local.json').exists());self.assertTrue((control/'replay_complete.local.json').exists())

    def test_primary_failure_or_uncertain_ack_stops_no_auto_retry_or_reader_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();control,stack=self.setup(root);count=[0]
            def run(*args):
                count[0]+=1;p=root/'data/processed/runs/e01-AUTHORED-FAILED';p.mkdir()
                (p/'typed_release.json').write_text('{"scope":"AUTHORED_FAKE_SEAL"}')
                raise RuntimeError('DEMO_PRIVATE_ERROR_NOT_EXPORTED')
            with stack,patch.object(h.m,'run_readiness',side_effect=run),patch.object(h.m,'read_verified_public') as reader:
                self.phase(root,control,'preflight')
                with self.assertRaises(SystemExit):self.phase(root,control,'primary')
                with self.assertRaises(FileExistsError):self.phase(root,control,'primary')
                with self.assertRaises(AssertionError):self.phase(root,control,'replay')
                reader.assert_not_called()
            self.assertEqual(count[0],1)
            self.assertFalse((control/'primary_complete.local.json').exists());self.assertFalse((control/'replay_complete.local.json').exists())
            receipt=json.loads((control/'primary_uncertain_or_failed.local.json').read_text())
            self.assertEqual(receipt['caller_error_type'],'RuntimeError');self.assertFalse(receipt['automatic_retry'])
            self.assertNotIn('DEMO_PRIVATE_ERROR',json.dumps(receipt))

    def test_preflight_pin_error_retained_and_cannot_advance_to_primary(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();control,stack=self.setup(root)
            with stack,patch.object(h,'pins_and_runtime',side_effect=AssertionError('PIN_DRIFT_ABORT')),patch.object(h.m,'run_readiness') as run:
                with self.assertRaises(AssertionError):self.phase(root,control,'preflight')
                with self.assertRaises(FileExistsError):self.phase(root,control,'preflight')
                run.assert_not_called()
            self.assertTrue((control/'preflight_started.local.json').exists());self.assertTrue((control/'preflight_control_error.local.json').exists())
            self.assertFalse((control/'preflight_complete.local.json').exists())


if __name__=='__main__':unittest.main()
