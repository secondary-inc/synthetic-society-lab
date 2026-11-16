"""Versioned consumer tests. Reuse reviewed core tests with MOCK v1_3 inputs.

Only test-module references are adapted. No production guard is monkeypatched;
the new helper is an explicit copy whose unchanged functions are AST-checked.
"""
import ast
import copy
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


t = load('accepted_p2_authored_tests', ROOT/'tests/test_e01_pypdf701_install_v1.py')
g = load('p2_v1_1_p1_v1_3_fixtures', ROOT/'tests/test_e01_pypdf701_acquisition_v1_3.py')
p = load('p2_v1_1_consumer', ROOT/'scripts/install_e01_pypdf701_runtime_v1_1.py')
# Reuse every accepted core invariant against the new production module and
# visibly authored acquisition fixture. Original files remain byte-identical.
t.p = p
t.f = SimpleNamespace(SecondSuccessorTests=g.FourthAttemptFixtureTests, c=g.c, v=g.w.v)


class ConsumerFixtureTests(t.InstallerFixtureTests):
    def save(self, name, raw):
        # The reused old fixture's literal output name must not overwrite the
        # separately preserved v1_2 ancestor methods in this temporary tree.
        if name == 'configs/e01_pypdf701_acquisition_v1_2_20261115.json' and hasattr(self, 'prefix'):
            if raw == p.packed(self.prefix.methods):
                name = 'configs/e01_pypdf701_acquisition_v1_3_20261115.json'
        return super().save(name, raw)

    def setUp(self):
        super().setUp()
        self.methods['acquisition_code_sha256'] = p.sha((ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1_3.py').read_bytes())
        self.packet['methods_sha256'] = p.sha(p.packed(self.methods))

    def test_freshness_failure_ancestor_is_required_separately(self):
        path = self.root/g.w.v.OUTPUT/'TERMINAL.json'
        raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(p.Refused, 'INPUT_HASH'): self.execute()
        self.assertEqual(self.calls, [])

    def test_v1_2_failed_terminal_cannot_be_adopted_as_v1_3_complete(self):
        self.packet['acquisition_terminal_ref'] = self.ref(g.w.v.OUTPUT+'/TERMINAL.json')
        with self.assertRaisesRegex(p.Refused, 'ACQUISITION_PATHS'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_consumer_preserves_14_gets_and_both_failed_wheel_charges(self):
        result = p.verify_acquisition(self.root, self.methods, self.packet, p.Reader(self.root))
        terminal = p.json_body((self.root/p.P1_SCOPE/'TERMINAL.json').read_bytes())
        self.assertEqual(terminal['budget']['attempts'], {'GET': 14, 'metadata_GET': 8, 'wheel_GET': 6})
        self.assertEqual(result['lock']['failed_wheel_GET_charges_retained'], 33554432)
        self.assertEqual(result['lock']['historical_original_GET_cap'], 13)
        self.assertEqual(result['lock']['cumulative_root_authorized_GET_cap'], 14)
        self.assertEqual(len(self.calls), 0)


class ConsumerPureTests(t.PureInstallerTests):
    def test_python312_S_base_prefix_does_not_change_explicit_target(self):
        target = Path('/MOCK/newenv')
        result = p.target_scheme(target, lambda **kw: t.scheme(Path(kw['vars']['base'])))
        args = p.pip_arguments('install', target, Path('/MOCK/build/install-v1_1-20261115/requirements.txt'))
        self.assertEqual(result['purelib'], '/MOCK/newenv/lib/python3.12/site-packages')
        self.assertEqual(args[args.index('--prefix')+1], str(target))
        self.assertIn('--ignore-installed', args)
        for flag in ('--no-index', '--no-deps', '--no-compile', '--no-cache-dir', '--only-binary=:all:', '--require-hashes'):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index('--find-links')+1], '/MOCK/build/acquisition-v1_3-20261115/wheels')
        self.assertNotIn('--python', args)


class ConsumerCaptureTests(t.CaptureAndQuotaTests):
    pass


class NarrowDeltaTests(unittest.TestCase):
    def test_accepted_core_and_original_tests_are_unchanged(self):
        expected = {'scripts/install_e01_pypdf701_runtime_v1.py': 'f9b8430824e6f6b382d22ce721e197c30bdebd852433119ed26938ba67315847',
            'configs/e01_pypdf701_install_v1_20261115.json': '805718985a8384869eac1ebbde9bc9345ea2045e2702e23e1b862be48ef76c3a',
            'tests/test_e01_pypdf701_install_v1.py': 'fa4484c500056e2842d5b765143b52b2f89e513ec755f7bb916b0b9a7d476a7a'}
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest)

    def test_only_consumer_body_and_explicit_identity_literals_change(self):
        original = ast.parse((ROOT/'scripts/install_e01_pypdf701_runtime_v1.py').read_bytes())
        updated = ast.parse((ROOT/'scripts/install_e01_pypdf701_runtime_v1_1.py').read_bytes())
        replacements = {
            'configs/e01_pypdf701_install_v1_1_20261115.json': 'configs/e01_pypdf701_install_v1_20261115.json',
            'data/processed/e01_pypdf701_build_v1/install-v1_1-20261115': 'data/processed/e01_pypdf701_build_v1/install-v1-20261115',
            'data/processed/e01_pypdf701_build_v1/acquisition-v1_3-20261115': 'data/processed/e01_pypdf701_build_v1/acquisition-v1_2-20261115',
            'scripts/install_e01_pypdf701_runtime_v1_1.py': 'scripts/install_e01_pypdf701_runtime_v1.py',
            'E01_PYPDF701_OFFLINE_INSTALL_METHODS_V1_1': 'E01_PYPDF701_OFFLINE_INSTALL_METHODS_V1'}
        class Normalize(ast.NodeTransformer):
            def visit_Constant(self, node):
                if type(node.value) is str and node.value in replacements:
                    node.value = replacements[node.value]
                return node
        updated = Normalize().visit(updated)
        old_nodes = [node for node in original.body if not isinstance(node, ast.FunctionDef) or node.name != 'verify_acquisition']
        new_nodes = [node for node in updated.body if not isinstance(node, ast.FunctionDef) or node.name != 'verify_acquisition']
        self.assertEqual(ast.dump(ast.Module(body=old_nodes, type_ignores=[]), include_attributes=False),
                         ast.dump(ast.Module(body=new_nodes, type_ignores=[]), include_attributes=False))


if __name__ == '__main__':
    g.old.guarded_test_main()
