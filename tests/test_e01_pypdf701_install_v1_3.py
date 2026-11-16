"""Versioned consumer tests. Reuse reviewed core tests with MOCK v1_4 inputs.

Only test-module references are adapted. No production guard is monkeypatched;
the new helper is an explicit copy whose unchanged functions are AST-checked.
"""
import ast
import copy
from email import policy
from email.parser import BytesParser
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
g = load('p2_v1_1_p1_v1_3_fixtures', ROOT/'tests/test_e01_pypdf701_acquisition_v1_4.py')
p = load('p2_v1_1_consumer', ROOT/'scripts/install_e01_pypdf701_runtime_v1_3.py')
# Reuse every accepted core invariant against the new production module and
# visibly authored acquisition fixture. Original files remain byte-identical.
t.p = p
t.f = SimpleNamespace(SecondSuccessorTests=g.FreshMetadataTests, c=g.c, v=g.w.v.v)


class ConsumerFixtureTests(t.InstallerFixtureTests):
    def save(self, name, raw):
        # The reused old fixture's literal output name must not overwrite the
        # separately preserved v1_2 ancestor methods in this temporary tree.
        if name == 'configs/e01_pypdf701_acquisition_v1_2_20261115.json' and hasattr(self, 'prefix'):
            if raw == p.packed(self.prefix.methods):
                name = 'configs/e01_pypdf701_acquisition_v1_4_20261116.json'
        return super().save(name, raw)

    def setUp(self):
        super().setUp()
        self.methods['acquisition_code_sha256'] = p.sha((ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1_4.py').read_bytes())
        self.packet['methods_sha256'] = p.sha(p.packed(self.methods))

    def test_freshness_failure_ancestor_is_required_separately(self):
        path = self.root/g.w.v.v.OUTPUT/'TERMINAL.json'
        raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(p.Refused, 'INPUT_HASH'): self.execute()
        self.assertEqual(self.calls, [])

    def test_v1_2_failed_terminal_cannot_be_adopted_as_v1_4_complete(self):
        self.packet['acquisition_terminal_ref'] = self.ref(g.w.v.v.OUTPUT+'/TERMINAL.json')
        with self.assertRaisesRegex(p.Refused, 'ACQUISITION_PATHS'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_consumer_preserves_21_gets_and_both_failed_wheel_charges(self):
        result = p.verify_acquisition(self.root, self.methods, self.packet, p.Reader(self.root))
        terminal = p.json_body((self.root/p.P1_SCOPE/'TERMINAL.json').read_bytes())
        self.assertEqual(terminal['budget']['attempts'], {'GET': 21, 'metadata_GET': 15, 'wheel_GET': 6})
        self.assertEqual(result['lock']['failed_wheel_GET_charges_retained'], 33554432)
        self.assertEqual(result['lock']['historical_original_GET_cap'], 13)
        self.assertEqual(result['lock']['cumulative_root_authorized_GET_cap'], 21)
        self.assertEqual(len(self.calls), 0)

    def rebind_receipt(self, value):
        receipt = self.save(p.P1_SCOPE+'/fresh-metadata-receipt.json', p.packed(value))
        local_receipt = {**receipt, 'path': 'fresh-metadata-receipt.json'}
        lock = p.json_body((self.root/p.P1_SCOPE/'hashlock.json').read_bytes())
        lock['fresh_metadata_receipt_ref'] = local_receipt
        self.packet['hashlock_ref'] = self.save(p.P1_SCOPE+'/hashlock.json', p.packed(lock))
        local_lock = {**self.packet['hashlock_ref'], 'path': 'hashlock.json'}
        terminal = p.json_body((self.root/p.P1_SCOPE/'TERMINAL.json').read_bytes())
        for ref in terminal['artifacts']:
            if ref['path'] == 'fresh-metadata-receipt.json': ref.update(local_receipt)
            if ref['path'] == 'hashlock.json': ref.update(local_lock)
        self.packet['acquisition_terminal_ref'] = self.save(p.P1_SCOPE+'/TERMINAL.json', p.packed(terminal))

    def test_coherently_hashed_relabeling_flag_still_refuses(self):
        receipt = p.json_body((self.root/p.P1_SCOPE/'fresh-metadata-receipt.json').read_bytes())
        receipt['no_old_response_relabeling'] = False
        self.rebind_receipt(receipt)
        with self.assertRaisesRegex(p.Refused, 'FRESH_METADATA_RECEIPT'): self.execute()
        self.assertEqual(self.calls, [])

    def test_duplicate_fresh_metadata_refs_cannot_satisfy_seven_gets(self):
        receipt = p.json_body((self.root/p.P1_SCOPE/'fresh-metadata-receipt.json').read_bytes())
        receipt['fresh_metadata_refs'][-1] = dict(receipt['fresh_metadata_refs'][0])
        self.rebind_receipt(receipt)
        with self.assertRaisesRegex(p.Refused, 'FRESH_METADATA_REFSET'): self.execute()
        self.assertEqual(self.calls, [])

    def test_old_capture_timestamp_cannot_replace_new_metadata_epoch(self):
        receipt = p.json_body((self.root/p.P1_SCOPE/'fresh-metadata-receipt.json').read_bytes())
        receipt['capture_started_utc'] = g.old.NOW.isoformat()
        self.rebind_receipt(receipt)
        with self.assertRaisesRegex(p.Refused, 'FRESH_METADATA_RECEIPT'): self.execute()
        self.assertEqual(self.calls, [])

    def test_final_metadata_charge_includes_all_seven_new_bodies(self):
        terminal = p.json_body((self.root/p.P1_SCOPE/'TERMINAL.json').read_bytes())
        terminal['budget']['body_bytes_charged']['metadata'] = self.prefix.methods['prior_cumulative']['budget']['body_bytes_charged']['metadata']
        self.packet['acquisition_terminal_ref'] = self.save(p.P1_SCOPE+'/TERMINAL.json', p.packed(terminal))
        with self.assertRaisesRegex(p.Refused, 'P1_FINAL_BODY_ACCOUNTING'): self.execute()
        self.assertEqual(self.calls, [])


class ConsumerPureTests(t.PureInstallerTests):
    def test_real_email_parser_header_boundary_is_lossless_and_satisfies_closure(self):
        raw = b'Metadata-Version: 2.3\nName: cryptography\nVersion: 50.0.2\nRequires-Dist: cffi>=2.0; platform_python_implementation != "PyPy"\n\n'
        values = BytesParser(policy=policy.default).parsebytes(raw).get_all('Requires-Dist')
        self.assertIsNot(type(values[0]), str)
        self.assertIsInstance(values[0], str)
        normalized = p.requires_dist_strings(values)
        self.assertIs(type(normalized[0]), str)
        self.assertEqual(normalized, values)
        requirements = {name: [] for name in p.VERSIONS}; requirements['cryptography'] = normalized
        self.assertTrue(p.dependency_closure(requirements)[0]['active'])

    def test_frozen_wheel_inspector_real_email_headers_cross_the_same_boundary(self):
        filename = 'cffi-2.1.1-cp312-cp312-macosx_11_0_arm64.whl'
        body = g.old.make_wheel('cffi', filename, extra={'cffi-2.1.1.dist-info/METADATA':
            b'Metadata-Version: 2.3\nName: cffi\nVersion: 2.1.1\nRequires-Python: >=3.10\nRequires-Dist: pycparser>=2.18\n\n'})
        inspection = g.c.inspect_wheel(body, 'cffi', filename)
        self.assertIsNot(type(inspection['requires_dist'][0]), str)
        normalized = p.requires_dist_strings(inspection['requires_dist'])
        requirements = {name: [] for name in p.VERSIONS}; requirements['cffi'] = normalized
        self.assertEqual(p.dependency_closure(requirements)[0]['dependency'], 'pycparser')

    def test_folded_email_requirement_matches_json_lock_without_losing_text(self):
        raw = b'Requires-Dist: pycparser>=2.18;\n python_version >= "3.10"\n\n'
        values = BytesParser(policy=policy.default).parsebytes(raw).get_all('Requires-Dist')
        normalized = p.requires_dist_strings(values)
        self.assertEqual(normalized, p.json_body(p.packed(values)))
        self.assertTrue(all(type(value) is str for value in normalized))
        requirements = {name: [] for name in p.VERSIONS}; requirements['cffi'] = normalized
        self.assertTrue(p.dependency_closure(requirements)[0]['active'])

    def test_header_boundary_refuses_arbitrary_objects_subclasses_and_other_headers(self):
        class ArbitraryStr(str):
            def __str__(self): raise AssertionError('MUST_NOT_CALL_USER_COERCION')
        subject = BytesParser(policy=policy.default).parsebytes(b'Subject: cffi>=2.0\n\n')['Subject']
        for value in (ArbitraryStr('cffi>=2.0'), object(), 3, subject):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(p.Refused):
                p.requires_dist_strings([value])

    def test_legacy_certificate_option_is_explicit_and_not_a_network_or_native_fallback(self):
        for stage in ('install', 'check'):
            args = p.pip_arguments(stage, Path('/MOCK/newenv'), Path('/MOCK/build/install-v1_3-20261116/requirements.txt'))
            self.assertEqual(args.count('--use-deprecated=legacy-certs'), 1)
            self.assertNotIn('--python', args)
            self.assertIn('--isolated', args)
            self.assertIn('--no-cache-dir', args)
        install = p.pip_arguments('install', Path('/MOCK/newenv'), Path('/MOCK/build/install-v1_3-20261116/requirements.txt'))
        for flag in ('--no-index', '--no-deps', '--no-compile', '--only-binary=:all:', '--require-hashes'):
            self.assertIn(flag, install)

    def test_python312_S_base_prefix_does_not_change_explicit_target(self):
        target = Path('/MOCK/newenv')
        result = p.target_scheme(target, lambda **kw: t.scheme(Path(kw['vars']['base'])))
        args = p.pip_arguments('install', target, Path('/MOCK/build/install-v1_3-20261116/requirements.txt'))
        self.assertEqual(result['purelib'], '/MOCK/newenv/lib/python3.12/site-packages')
        self.assertEqual(args[args.index('--prefix')+1], str(target))
        self.assertIn('--ignore-installed', args)
        for flag in ('--no-index', '--no-deps', '--no-compile', '--no-cache-dir', '--only-binary=:all:', '--require-hashes'):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index('--find-links')+1], '/MOCK/build/acquisition-v1_4-20261116/wheels')
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
        updated = ast.parse((ROOT/'scripts/install_e01_pypdf701_runtime_v1_3.py').read_bytes())
        replacements = {
            'configs/e01_pypdf701_install_v1_3_20261116.json': 'configs/e01_pypdf701_install_v1_20261115.json',
            'data/processed/e01_pypdf701_build_v1/install-v1_3-20261116': 'data/processed/e01_pypdf701_build_v1/install-v1-20261115',
            'data/processed/e01_pypdf701_build_v1/acquisition-v1_4-20261116': 'data/processed/e01_pypdf701_build_v1/acquisition-v1_2-20261115',
            'scripts/install_e01_pypdf701_runtime_v1_3.py': 'scripts/install_e01_pypdf701_runtime_v1.py',
            'E01_PYPDF701_OFFLINE_INSTALL_METHODS_V1_3': 'E01_PYPDF701_OFFLINE_INSTALL_METHODS_V1'}
        class Normalize(ast.NodeTransformer):
            def visit_Constant(self, node):
                if type(node.value) is str and node.value in replacements:
                    node.value = replacements[node.value]
                return node
        updated = Normalize().visit(updated)
        # The only command compatibility change is one supported argv option;
        # removing exactly that literal restores the complete accepted core.
        arguments = next(node for node in updated.body if isinstance(node, ast.FunctionDef) and node.name == 'pip_arguments')
        base = next(node for node in arguments.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'base' for target in node.targets))
        added = [node for node in base.value.elts if isinstance(node, ast.Constant) and node.value == '--use-deprecated=legacy-certs']
        self.assertEqual(len(added), 1)
        base.value.elts.remove(added[0])
        old_nodes = [node for node in original.body if not isinstance(node, ast.FunctionDef) or node.name != 'verify_acquisition']
        # New normalizer is separately covered by real stdlib parser and
        # negative coercion tests; all accepted guard/closure code stays exact.
        new_nodes = [node for node in updated.body if not isinstance(node, ast.FunctionDef)
                     or node.name not in {'verify_acquisition', 'requires_dist_strings'}]
        self.assertEqual(ast.dump(ast.Module(body=old_nodes, type_ignores=[]), include_attributes=False),
                         ast.dump(ast.Module(body=new_nodes, type_ignores=[]), include_attributes=False))


if __name__ == '__main__':
    g.old.guarded_test_main()
