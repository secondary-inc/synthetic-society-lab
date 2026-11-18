"""CI process isolation, not research or runtime qualification authority.

The supervisor never imports tests. Frozen groups retain their original guards
inside disposable children; ordinary discovery cannot execute those modules.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import contextmanager
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import selectors
import signal
import stat
import subprocess
import sys
import time
import traceback
from types import ModuleType
import unittest

ROOT = Path(__file__).resolve().parents[1]
MARKER = "OFFLINE_CI_RECEIPT_V1="
FROZEN = {
    "observer-v1": ("test_e01_compatibility_error_observer_candidate_v1_20261116.py", 19017, "83969d6ad8086d140bbeaf44880f79a68774fdca3b7e9c76965c8857114ed760", 34, "GuardAndStaticModelTests.test_stdlib_socket_origin_record_without_operation_or_mutation", "t.g.old"),
    "observer-v2": ("test_e01_compatibility_error_observer_candidate_v2_20261116.py", 20835, "0060994e89ed4e8c62a4a9b734aba4389f9d81878f882e5b88b1a0134f2e002a", 37, "GuardAndStaticModelTests.test_stdlib_socket_origin_record_without_operation_or_mutation", "t.g.old"),
    "import-methods-v1": ("test_e01_offline_import_protocol_methods_v1_20261116.py", 16128, "44589c9f6076d8589eb3a4da2d43c3a3fa18b296a3193c0f98aa4cabfb93324a", 20, None, None),
    "compatibility-v1": ("test_e01_offline_ipv6_compatibility_v1_20261116.py", 28254, "61358fc6b1f2285dac745bf207908372fd2525cf4a3cb169008b5feb4a6affb8", 47, "FrozenStructureTests.test_stdlib_socket_origin_record_only_no_mutation", "g.f.old.g.old"),
    "compatibility-v1_1": ("test_e01_offline_ipv6_compatibility_v1_1_20261116.py", 34253, "439a2d46ebcfc57c295a95e4fa353691246ab1e2ea0db1feebff41f4a3ba96a2", 53, "FrozenStructureTests.test_stdlib_socket_origin_record_only_no_mutation", "g.f.old.g.old"),
    "probe-v2": ("test_e01_offline_ipv6_probe_mock_candidate_v2_20261116.py", 17601, "dabe56af0d88df61d2dae07d6230018b0a2b18915bd5e2a11ae2faafcf4458ad", 29, None, "t.g.old"),
}
HOST_CASE_RULES = {'test_e01_p2_builtin_mime_candidate_v1_20261116.py': {'test_ref': {'path': 'tests/test_e01_p2_builtin_mime_candidate_v1_20261116.py', 'bytes': 4504, 'sha256': '899eaa7a82a54a7db8c62ca487cd2b1bf6d5d22afaa701c04c6c42bdb1917b91'}, 'contract_ref': {'path': 'scripts/e01_p2_builtin_mime_candidate_v1_20261116.py', 'bytes': 1113, 'sha256': '99ab72562c3376ee3c0e95f0025c809cdcedaf06a9fa6c13803b34d55bc2c3ff'}, 'gate': 'DARWIN_MIME_ONLY', 'local_cases': ['BuiltinMimeCandidateTests.test_public_knownfiles_clear_and_empty_init_need_no_file_open', 'BuiltinMimeCandidateTests.test_all_five_wheel_names_remain_non_html_without_io', 'BuiltinMimeCandidateTests.test_already_initialized_module_refuses_without_state_reset', 'BuiltinMimeCandidateTests.test_initialization_exception_propagates_without_retry_or_fallback', 'BuiltinMimeCandidateTests.test_unexpected_knownfiles_schema_refuses']}, 'test_e01_p2_builtin_mime_candidate_v2_20261116.py': {'test_ref': {'path': 'tests/test_e01_p2_builtin_mime_candidate_v2_20261116.py', 'bytes': 6054, 'sha256': '629cecddb82718ec71c3b1b634ff02c6a10f8ed4b872dabaca8f5412b583c373'}, 'contract_ref': {'path': 'scripts/e01_p2_builtin_mime_candidate_v2_20261116.py', 'bytes': 1077, 'sha256': '864d337ad575918a395beb21b3cbd7ceed3bc6c4c59e0801df3a0cdc2326c768'}, 'gate': 'DARWIN_MIME_ONLY', 'local_cases': ['BuiltinMimeRebuildTests.test_fresh_rebuild_and_classification_need_zero_file_opens', 'BuiltinMimeRebuildTests.test_prepopulated_rebuild_removes_machine_specific_mappings_without_io', 'BuiltinMimeRebuildTests.test_rebuild_is_repeatable_and_resets_public_add_type_changes', 'BuiltinMimeRebuildTests.test_init_failure_propagates_once_without_fallback', 'BuiltinMimeRebuildTests.test_unexpected_state_refuses_before_init']}, 'test_e01_pypa_fixture_harness_candidate_v1_1_20261116.py': {'test_ref': {'path': 'tests/test_e01_pypa_fixture_harness_candidate_v1_1_20261116.py', 'bytes': 33431, 'sha256': '8236f2fcaaf325af67bf1c134fb98a4f18445e18af18330ce7f34fdb96e1bedc'}, 'contract_ref': {'path': 'scripts/e01_pypa_fixture_harness_candidate_v1_1_20261116.py', 'bytes': 52778, 'sha256': '1c55c942b061452f741d1242640fd1b85a8f11b398a30fea6c391525006b20b8'}, 'gate': 'EXACT_GENERATED_RUNTIME', 'local_cases': ['GeneratedCompilationTests.test_runtime_stdlib_binding_is_exact_and_not_an_import_time_hook', 'GeneratedCompilationTests.test_exact_fifteen_sources_match_inert_stdlib_dataclass_generation_without_exec', 'GeneratedCompilationTests.test_finite_ordered_plan_accepts_only_exact_mock_frame_context', 'GeneratedCompilationTests.test_source_filename_phase_and_sequence_drift_refuse_and_latch', 'GeneratedCompilationTests.test_stdlib_code_identity_globals_and_tool_origins_cannot_drift', 'GeneratedCompilationTests.test_missing_generated_event_refuses_finish_permanently', 'GeneratedCompilationTests.test_real_policy_callback_rejects_forged_caller_and_arbitrary_source', 'GeneratedCompilationTests.test_other_runtime_plan_is_distinct_and_unknown_runtime_refuses']}}
COMPILE_PROFILE_PINS = {'3.11.17': {'executable': (17344128, '595d73e8b246e5276a3ae0409de4d01dd59fd6ec5f3190cfe28e05bf2de4986f'), 'dataclasses': (58472, '77a41ea9eb35d959781087b72ef5b452218b57b9d8f2d28688d45a40ca7f8a09')}, '3.12.14': {'executable': (18058560, '9d1335796350848c36dc2711a3298e096deebee18c85f1ab36edd8747fdf85eb'), 'dataclasses': (62085, 'd242aea5fcf6408b1c1f622442f88f68b9526ce1f8bd2890d74a144677c427d9')}}

SOCKET_PINS = {
    "3.11.17": (37557, "64360e73e3db69396d45d5ee256e8306b3653212ab96ae4a130070488cddbb30"),
    "3.12.14": (37815, "7d4d4c66e6f4bcc961ab462c4f08002ca97def8713a4be1c7373bdbd970a5274"),
}
ORDINARY_WALL = 10800
COORDINATOR_WALL = ORDINARY_WALL + 10 * 120 + 120
MODULE_WALL = 3600
EVENT_MARKER = "OFFLINE_CI_TEST_EVENT_V1="


class IsolationError(Exception):
    pass


def require(ok, code):
    if not ok:
        raise IsolationError(code)


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def verified_source(root, group):
    name, size, digest, _, _, _ = FROZEN[group]
    path = Path(root) / "tests" / name
    require(not any(p.is_symlink() for p in (path, *path.parents)), "FROZEN_SOURCE_ALIAS")
    require(path.stat().st_size == size, "FROZEN_SOURCE_SIZE")
    raw = path.read_bytes()
    require(len(raw) == size and sha(raw) == digest, "FROZEN_SOURCE_HASH")
    return raw


def case_inventory(raw):
    """Frozen files use direct unittest.TestCase classes, without inherited cases."""
    tree = ast.parse(raw)
    return sorted(f"{node.name}.{method.name}" for node in tree.body
                  if isinstance(node, ast.ClassDef)
                  and any(ast.unparse(base) == "unittest.TestCase" for base in node.bases)
                  for method in node.body
                  if isinstance(method, ast.FunctionDef) and method.name.startswith("test_"))


def plan(root=ROOT):
    root = Path(root)
    jobs = [{"id": "ordinary", "group": "ordinary", "phase": "ordinary",
             "wall_seconds": ORDINARY_WALL, "output_bytes": 16 * 1024 * 1024}]
    inventory = {}
    for group, (name, size, digest, count, qualification, _) in FROZEN.items():
        cases = case_inventory(verified_source(root, group))
        require(len(cases) == count and len(set(cases)) == count, "FROZEN_CASE_INVENTORY")
        require(qualification is None or qualification in cases, "QUALIFICATION_CASE_MISSING")
        portable = [case for case in cases if case != qualification]
        inventory[group] = {"path": "tests/" + name, "bytes": size, "sha256": digest,
                            "all_cases": cases, "portable_cases": portable,
                            "historical_cases": [qualification] if qualification else []}
        jobs.append({"id": group + "-portable", "group": group, "phase": "portable",
                     "wall_seconds": 120, "output_bytes": 262144})
    for group, row in inventory.items():
        if row["historical_cases"]:
            jobs.append({"id": group + "-historical", "group": group, "phase": "historical",
                         "wall_seconds": 120, "output_bytes": 262144})
    return {"jobs": jobs, "inventory": inventory, "portable_cases": sum(len(r["portable_cases"]) for r in inventory.values()),
            "historical_cases": sum(len(r["historical_cases"]) for r in inventory.values())}


def ordinary_modules(root):
    """Hash every ordinary discovery file, including zero-case helper modules."""
    tests = ordinary_origin(Path(root) / "tests")
    # Per-file isolation currently supports a flat tests namespace. unittest
    # also discovers package directories (and their load_tests hooks): refuse
    # those explicitly instead of quietly dropping them from the manifest.
    for child in tests.iterdir():
        if child.is_dir():
            ordinary_origin(child)
            require(not (child / "__init__.py").exists(), "ORDINARY_NESTED_PACKAGES_UNSUPPORTED")
    excluded = {row[0] for row in FROZEN.values()}
    rows = []
    for path in sorted(tests.glob("test*.py")):
        if path.name in excluded:
            continue
        ordinary_origin(path)
        require(path.is_file() and path.stat().st_size <= 1048576, "ORDINARY_SOURCE_BOUND")
        raw = path.read_bytes()
        rows.append({"path": "tests/" + path.name, "bytes": len(raw), "sha256": sha(raw),
                     "declared_local_cases": case_inventory(raw)})
    require(0 < len(rows) <= 4096, "ORDINARY_MODULE_COUNT")
    return rows


def module_plan(root=ROOT, *, shard_index=0, shard_count=1, module_wall=MODULE_WALL, only_modules=None):
    require(type(shard_count) is int and 1 <= shard_count <= 16
            and type(shard_index) is int and 0 <= shard_index < shard_count, "SHARD_PARAMETERS")
    require(type(module_wall) is int and 1 <= module_wall <= ORDINARY_WALL, "MODULE_WALL")
    specification = plan(root)
    rows = ordinary_modules(root)
    available = {Path(row["path"]).name for row in rows}
    if only_modules is not None:
        require(type(only_modules) in {list, tuple} and only_modules
                and len(set(only_modules)) == len(only_modules)
                and set(only_modules) <= available, "FOCUSED_MODULE_SET")
    jobs = []
    for index, row in enumerate(rows):
        filename = Path(row["path"]).name
        if index % shard_count != shard_index or (only_modules is not None and filename not in only_modules):
            continue
        jobs.append({"id": "ordinary-" + filename[:-3], "group": "ordinary", "phase": "ordinary",
                     "test_module": filename, "source_ref": {k: row[k] for k in ("path", "bytes", "sha256")},
                     "declared_local_cases": row["declared_local_cases"], "wall_seconds": module_wall,
                     "output_bytes": 16 * 1024 * 1024})
    if shard_index == 0 and only_modules is None:
        jobs.extend(specification["jobs"][1:])
    specification.update(jobs=jobs, ordinary_module_manifest=rows,
                         ordinary_manifest_sha256=sha(packed(rows)),
                         suite_scope="FOCUSED_MODULES_ONLY" if only_modules is not None else "ALL_DISCOVERY_MODULES",
                         root=str(Path(root).resolve()),
                         shard={"index": shard_index, "count": shard_count,
                                "aggregate_budget_seconds_all_shards": COORDINATOR_WALL,
                                "budget_seconds": COORDINATOR_WALL // shard_count + int(shard_index < COORDINATOR_WALL % shard_count)})
    return specification


class OrdinaryLoader(unittest.TestLoader):
    def __init__(self, root):
        super().__init__()
        self.excluded = {str((Path(root) / "tests" / row[0]).resolve()) for row in FROZEN.values()}

    def _match_path(self, path, full_path, pattern):
        return str(Path(full_path).resolve()) not in self.excluded and super()._match_path(path, full_path, pattern)


def ordinary_origin(path):
    path = Path(path).absolute()
    require(path == path.resolve() and not any(p.is_symlink() for p in (path, *path.parents)),
            "ORDINARY_IMPORT_PATH_ALIAS")
    return path


class OrdinaryNamespaceFinder:
    """Own only the verified tests namespace and its bare fixture names.

    This is an import-context boundary for trusted CI, not a Python sandbox.
    Frozen names fail before either import spelling can execute their source;
    CollectionBarrier still covers direct/transitive filename execution.
    """
    offline_ci_owned_tests_namespace_v1_2 = True

    def __init__(self, root):
        self.root = ordinary_origin(root)
        self.tests = ordinary_origin(self.root / "tests")
        require(self.tests.is_dir() and not (self.tests / "__init__.py").exists(),
                "ORDINARY_EXPECTED_TESTS_NAMESPACE")
        self.bare_names = {p.stem for p in self.tests.glob("*.py")}
        for name in self.bare_names:
            ordinary_origin(self.tests / (name + ".py"))
        self.frozen_names = {Path(row[0]).stem for row in FROZEN.values()}

    def owned(self, name):
        return name == "tests" or name.startswith("tests.") or name in self.bare_names

    def validate_spec(self, name, spec):
        parts = name.split(".")[1:] if name.startswith("tests.") else [name]
        if name == "tests":
            expected = self.tests
        else:
            expected = self.tests.joinpath(*parts)
        if spec.origin is None:
            locations = list(spec.submodule_search_locations or [])
            require(locations == [str(expected)] and ordinary_origin(expected).is_dir(),
                    "FOREIGN_TESTS_NAMESPACE")
        else:
            allowed = {expected.with_suffix(".py"), expected / "__init__.py"}
            require(name != "tests" and ordinary_origin(spec.origin) in allowed,
                    "FOREIGN_TEST_MODULE_ORIGIN")
        return spec

    def validate_cached(self):
        for name, module in list(sys.modules.items()):
            if not self.owned(name):
                continue
            require(name.rsplit(".", 1)[-1] not in self.frozen_names,
                    "PRELOADED_FROZEN_TEST_MODULE")
            require(module is not None and getattr(module, "__spec__", None) is not None,
                    "UNBOUND_CACHED_TEST_MODULE")
            self.validate_spec(name, module.__spec__)
            if module.__spec__.origin is None:
                require(list(getattr(module, "__path__", [])) == list(module.__spec__.submodule_search_locations),
                        "FOREIGN_CACHED_TEST_NAMESPACE_PATH")
            else:
                require(ordinary_origin(module.__file__) == ordinary_origin(module.__spec__.origin),
                        "CACHED_TEST_MODULE_ORIGIN_CHANGED")

    def preflight_path(self):
        # PathFinder checks metadata only; no candidate module is executed.
        for entry in sys.path:
            for name in ("tests", *sorted(self.bare_names)):
                spec = importlib.machinery.PathFinder.find_spec(name, [entry])
                if spec is not None:
                    self.validate_spec(name, spec)

    def find_spec(self, fullname, path=None, target=None):
        if not self.owned(fullname):
            return None
        leaf = fullname.rsplit(".", 1)[-1]
        require(leaf not in self.frozen_names, "TRANSITIVE_FROZEN_MODULE_IMPORT")
        if fullname == "tests":
            spec = importlib.machinery.ModuleSpec(fullname, loader=None, is_package=True)
            spec.submodule_search_locations = [str(self.tests)]
            return spec
        parent = self.tests.joinpath(*fullname.split(".")[1:-1]) if fullname.startswith("tests.") else self.tests
        if fullname.startswith("tests."):
            require(list(path or []) == [str(parent)], "FOREIGN_TEST_NAMESPACE_SEARCH_PATH")
        else:
            require(path is None, "FOREIGN_BARE_TEST_SEARCH_PATH")
        spec = importlib.machinery.PathFinder.find_spec(fullname, [str(ordinary_origin(parent))])
        require(spec is not None, "OWNED_TEST_MODULE_MISSING")
        return self.validate_spec(fullname, spec)


@contextmanager
def ordinary_import_context(root):
    """Child-local admission; restore namespace, paths and importer cache on exit."""
    finder = OrdinaryNamespaceFinder(root)
    finder.validate_cached()
    old_path_object, old_meta_object = sys.path, sys.meta_path
    old_path, old_meta = sys.path[:], sys.meta_path[:]
    old_cache = sys.path_importer_cache.copy()
    old_modules = {name: module for name, module in sys.modules.items() if finder.owned(name)}
    old_attributes = {name: module.__dict__.copy() for name, module in old_modules.items()}
    try:
        finder.preflight_path()
        sys.path[:0] = [str(finder.root), str(finder.tests)]
        sys.meta_path.insert(0, finder)
        if "tests" not in sys.modules:
            spec = finder.find_spec("tests")
            sys.modules["tests"] = importlib.util.module_from_spec(spec)
        yield finder
    finally:
        sys.path, sys.meta_path = old_path_object, old_meta_object
        sys.path[:], sys.meta_path[:] = old_path, old_meta
        for name in list(sys.modules):
            if finder.owned(name) and name not in old_modules:
                del sys.modules[name]
        sys.modules.update(old_modules)
        for name, attributes in old_attributes.items():
            old_modules[name].__dict__.clear()
            old_modules[name].__dict__.update(attributes)
        sys.path_importer_cache.clear()
        sys.path_importer_cache.update(old_cache)


class CollectionBarrier:
    """Child-only fail-closed barrier; not an adversarial Python sandbox."""
    def __init__(self, root):
        self.excluded = OrdinaryLoader(root).excluded
        self.collecting = False

    def __call__(self, event, args):
        if event == "exec" and args and hasattr(args[0], "co_filename"):
            require(str(Path(args[0].co_filename).resolve()) not in self.excluded,
                    "TRANSITIVE_FROZEN_MODULE_EXECUTION")
        if event == "sys.addaudithook" and self.collecting:
            # Exception, not RuntimeError: do not silently suppress registration.
            raise IsolationError("GLOBAL_HOOK_DURING_ORDINARY_COLLECTION")


def _collect_ordinary(root, *, loader=None, install_hook=sys.addaudithook, pattern=None):
    barrier = CollectionBarrier(root)
    install_hook(barrier)  # This function is called only in the ordinary child.
    barrier.collecting = True
    try:
        selected = loader or OrdinaryLoader(root)
        suite = (selected.discover(str(Path(root) / "tests")) if pattern is None else
                 selected.discover(str(Path(root) / "tests"), pattern=pattern))
        return suite, barrier
    finally:
        barrier.collecting = False


def collect_ordinary(root, *, loader=None, install_hook=sys.addaudithook):
    with ordinary_import_context(root):
        return _collect_ordinary(root, loader=loader, install_hook=install_hook)


def socket_observation():
    """Read-only origin observation, never a new historical source pin."""
    module = sys.modules.get("socket")
    if module is None:
        import socket as module
    expected = Path(sys.base_prefix) / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/socket.py"
    path = Path(module.__file__).absolute()
    require(path == expected and module.__spec__.origin == str(expected), "SOCKET_ORIGIN")
    require(not any(p.is_symlink() for p in (path, *path.parents)), "SOCKET_ALIAS")
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_size <= 131072, "SOCKET_SOURCE_BOUND")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        identity = lambda item: (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns)
        require(identity(info) == identity(opened), "SOCKET_SOURCE_CHANGED")
        body = stream.read(info.st_size + 1)
        require(identity(opened) == identity(os.fstat(stream.fileno())), "SOCKET_SOURCE_CHANGED")
    require(len(body) == info.st_size, "SOCKET_SOURCE_CHANGED")
    return {"scope": "OBSERVATION_ONLY_NOT_HISTORICAL_QUALIFICATION", "path": str(path),
            "bytes": len(body), "sha256": sha(body)}


def historical_admission(host, observation):
    pin = SOCKET_PINS.get(host.get("version"))
    reasons = []
    for key, expected in (("implementation", "cpython"), ("platform", "darwin"),
                          ("machine", "arm64"), ("macos", "26.6")):
        if host.get(key) != expected:
            reasons.append("UNSUPPORTED_" + key.upper())
    if pin is None:
        reasons.append("UNSUPPORTED_EXACT_PYTHON_VERSION")
    elif observation is None or (observation.get("bytes"), observation.get("sha256")) != pin:
        reasons.append("HISTORICAL_SOCKET_SOURCE_NOT_MATCHED")
    return {"status": "SUPPORTED" if not reasons else "NOT_RUN", "reasons": reasons,
            "scope": "FOUR_FROZEN_SOCKET_CHECKS_ONLY_NOT_FULL_RUNTIME_QUALIFICATION"}


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def case_id(test):
    method = getattr(test, "_testMethodName", None)
    return type(test).__name__ + "." + method if method is not None else test.id()[:512]


def full_case_id(test):
    value = test.id()
    require(type(value) is str and 0 < len(value) <= 2048, "CASE_ID_BOUND")
    return value


def module_source(root, filename, expected_sha=None):
    require(type(filename) is str and Path(filename).name == filename
            and filename.startswith("test") and filename.endswith(".py")
            and filename not in {row[0] for row in FROZEN.values()}, "ORDINARY_MODULE_NAME")
    path = ordinary_origin(Path(root) / "tests" / filename)
    require(path.is_file() and path.stat().st_size <= 1048576, "ORDINARY_SOURCE_BOUND")
    raw = path.read_bytes()
    reference = {"path": "tests/" + filename, "bytes": len(raw), "sha256": sha(raw)}
    require(expected_sha is None or reference["sha256"] == expected_sha, "ORDINARY_SOURCE_CHANGED")
    return reference


def host_case_decision(root, filename, *, version=None, platform_name=None, observe=None):
    """Only the frozen ten Darwin MIME and eight exact-runtime cases qualify."""
    rule = HOST_CASE_RULES.get(filename)
    if rule is None:
        return None
    for reference in (rule["test_ref"], rule["contract_ref"]):
        path = ordinary_origin(Path(root) / reference["path"])
        raw = path.read_bytes()
        require((len(raw), sha(raw)) == (reference["bytes"], reference["sha256"]), "HOST_CASE_SOURCE_CHANGED")
    version = sys.version.split()[0] if version is None else version
    platform_name = sys.platform if platform_name is None else platform_name
    evidence = {"gate": rule["gate"], "python": version, "platform": platform_name,
                "test_ref": rule["test_ref"], "contract_ref": rule["contract_ref"]}
    if rule["gate"] == "DARWIN_MIME_ONLY":
        supported = platform_name == "darwin"
        reasons = [] if supported else ["FROZEN_CANDIDATE_REQUIRES_DARWIN"]
    else:
        pins = COMPILE_PROFILE_PINS.get(version)
        reasons = []
        if pins is None:
            reasons.append("FROZEN_GENERATED_RUNTIME_VERSION_UNSUPPORTED")
        else:
            if observe is None:
                paths = {"executable": Path(sys.executable).resolve(),
                         "dataclasses": Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "dataclasses.py"}
                observations = {}
                for kind, path in paths.items():
                    raw = ordinary_origin(path).read_bytes()
                    require(len(raw) <= 33554432, "HOST_RUNTIME_SOURCE_BOUND")
                    observations[kind] = (len(raw), sha(raw))
            else:
                observations = observe()
            evidence["observations"] = observations
            if observations != pins:
                reasons.append("FROZEN_EXECUTABLE_OR_DATACLASSES_NOT_MATCHED")
        supported = not reasons
    return {**evidence, "status": "SUPPORTED" if supported else "NOT_RUN", "reasons": reasons,
            "local_cases": rule["local_cases"], "scope": "NAMED_ORIGINAL_HOST_CASES_ONLY_NOT_FULL_RUNTIME_QUALIFICATION"}


class OrdinaryRecordingResult(unittest.TextTestResult):
    """Immediate bounded failure details survive a later test timeout."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_cases = []
        self.started_case_ids, self.completed_case_ids, self.outcomes = [], [], []
        self._times = {}
        self._status = {}

    def event(self, event, test, **extra):
        record = {"event": event, "case_id": full_case_id(test), **extra}
        self.stream.writeln("\n" + EVENT_MARKER + packed(record).decode())
        self.stream.flush()

    def startTest(self, test):
        self.started_cases.append(case_id(test))
        self.started_case_ids.append(full_case_id(test))
        self._times[id(test)] = time.monotonic()
        self._status[id(test)] = "PASS"
        super().startTest(test)
        self.event("START", test)

    def stopTest(self, test):
        self.completed_case_ids.append(full_case_id(test))
        status = self._status.pop(id(test), "ERROR")
        self.outcomes.append({"case_id": full_case_id(test), "status": status})
        self.event("STOP", test, status=status,
                   elapsed_seconds=time.monotonic() - self._times.pop(id(test), time.monotonic()))
        super().stopTest(test)

    def detail(self, test, text, status):
        self._status[id(test)] = status
        raw = text.encode("utf-8", "replace")
        self.event(status, test, traceback_bytes=len(raw), traceback_sha256=sha(raw),
                   traceback_truncated=len(raw) > 65536)
        self.stream.writeln("CI_FAILURE_DETAIL_BEGIN " + full_case_id(test))
        self.stream.writeln(raw[:65536].decode("utf-8", "replace"))
        self.stream.writeln("CI_FAILURE_DETAIL_END")
        self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.detail(test, self.failures[-1][1], "FAIL")

    def addError(self, test, err):
        super().addError(test, err)
        self.detail(test, self.errors[-1][1], "ERROR")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            failures = self.failures if issubclass(err[0], test.failureException) else self.errors
            self.detail(subtest, failures[-1][1], "FAIL" if failures is self.failures else "ERROR")
            self._status[id(test)] = "FAIL" if failures is self.failures else "ERROR"

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        parent = getattr(test, "test_case", test)
        if self._status.get(id(parent), "PASS") in {"PASS", "SKIP"}:
            self._status[id(parent)] = "SKIP"
        self.event("SKIP", test, reason=reason[:512])

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._status[id(test)] = "EXPECTED_FAILURE"


def unstarted_skip_cases(planned, started, skipped):
    remaining = Counter(planned) - Counter(started)
    covered = []
    for test, reason in skipped:
        description = full_case_id(test)
        if description.startswith("setUpClass (") and description.endswith(")"):
            prefix = description[len("setUpClass ("):-1] + "."
        elif description.startswith("setUpModule (") and description.endswith(")"):
            prefix = description[len("setUpModule ("):-1] + "."
        else:
            continue
        cases = [case for case, count in list(remaining.items()) if case.startswith(prefix) for _ in range(count)]
        covered.append({"holder": description, "reason": reason[:512], "case_ids": cases})
        remaining.subtract(Counter(cases))
    return covered


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_cases = []

    def startTest(self, test):
        self.started_cases.append(case_id(test))
        super().startTest(test)


def result_record(result):
    return {"tests_run": result.testsRun, "started_cases": result.started_cases,
            "failures": [case_id(t) for t, _ in result.failures],
            "errors": [case_id(t) for t, _ in result.errors],
            "skips": [{"case": case_id(t), "reason": reason[:512]} for t, reason in result.skipped],
            "unexpected_successes": [case_id(t) for t in result.unexpectedSuccesses]}


def run_frozen(root, group, phase, *, admission=None):
    raw = verified_source(root, group)
    cases = case_inventory(raw)
    qualification = FROZEN[group][4]
    observation, host, decision = None, None, None
    if phase == "historical":
        require(qualification is not None, "NO_HISTORICAL_CASE")
        host = {"version": sys.version.split()[0], "implementation": sys.implementation.name,
                "platform": sys.platform, "machine": platform.machine(), "macos": platform.mac_ver()[0]}
        try:
            observation = socket_observation()
        except (OSError, IsolationError):
            observation = None
        decision = (admission or historical_admission)(host, observation)
        if decision["status"] != "SUPPORTED":
            return {"status": "NOT_RUN", "qualification": decision, "host": host,
                    "socket_observation": observation, "planned_cases": [qualification], "tests_run": 0}
    selected = [c for c in cases if (c == qualification) == (phase == "historical")]
    module = ModuleType("ci_frozen_" + group.replace("-", "_"))
    path = Path(root) / "tests" / FROZEN[group][0]
    module.__file__ = str(path)
    module.__spec__ = importlib.util.spec_from_file_location(module.__name__, path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    if qualification and phase == "portable":
        observation = socket_observation()

    class SelectedLoader(unittest.TestLoader):
        def loadTestsFromModule(self, target, *args, **kwargs):
            all_tests = list(flatten(super().loadTestsFromModule(target, *args, **kwargs)))
            require(sorted(case_id(t) for t in all_tests) == cases, "DYNAMIC_CASE_INVENTORY_CHANGED")
            return unittest.TestSuite(t for t in all_tests if case_id(t) in selected)

    original_main = unittest.main
    captured = []

    def selected_main(*args, **kwargs):
        kwargs.update(module=module, argv=[str(path)], testLoader=SelectedLoader(), exit=False,
                      testRunner=unittest.TextTestRunner(verbosity=2, failfast=True, resultclass=RecordingResult))
        program = original_main(*args, **kwargs)
        captured.append(program.result)
        return program

    unittest.main = selected_main
    try:
        chain = FROZEN[group][5]
        target = module
        if chain is None:
            target.guarded_main()
        else:
            for name in chain.split("."):
                target = getattr(target, name)
            target.guarded_test_main()
    finally:
        unittest.main = original_main
    require(len(captured) == 1, "ORIGINAL_GUARDED_MAIN_NOT_RUN")
    verified_source(root, group)
    result = captured[0]
    complete = sorted(result.started_cases) == selected and result.testsRun == len(selected) and not result.skipped
    return {"status": "PASS" if result.wasSuccessful() and complete else "FAIL", "planned_cases": selected,
            "socket_observation": observation,
            "host": host, "qualification": decision,
            "historical_case_separate": qualification if phase == "portable" else None,
            **result_record(result)}


def child_entry(root, group, phase, *, test_module=None, module_sha=None, module_wall=MODULE_WALL):
    seconds = (module_wall if test_module is not None else ORDINARY_WALL) if phase == "ordinary" else 120
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (seconds - 1, seconds))
    def deadline(*_):
        raise IsolationError("CI_CHILD_DEADLINE")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    if phase == "ordinary":
        with ordinary_import_context(root):
            reference = module_source(root, test_module, module_sha) if test_module is not None else None
            suite, _ = (_collect_ordinary(root) if test_module is None else
                        _collect_ordinary(root, pattern=test_module))
            discovered = list(flatten(suite))
            planned = [full_case_id(test) for test in discovered]
            require(len(planned) <= 65536, "ORDINARY_CASE_COUNT")
            decision = host_case_decision(root, test_module) if test_module is not None else None
            active, not_run = [], []
            matched_host_cases = []
            for test in discovered:
                if decision is not None and case_id(test) in decision["local_cases"]:
                    matched_host_cases.append(case_id(test))
                    if decision["status"] == "NOT_RUN":
                        not_run.append({"case_id": full_case_id(test), "qualification": decision})
                        continue
                active.append(test)
            if decision is not None:
                require(sorted(matched_host_cases) == sorted(decision["local_cases"]), "HOST_CASE_INVENTORY_CHANGED")
            print("OFFLINE_CI_MODULE_PLAN_V1=" + packed({"source_ref": reference,
                  "planned_case_ids": planned, "not_run_cases": not_run}).decode(), flush=True)
            result = unittest.TextTestRunner(verbosity=2, resultclass=OrdinaryRecordingResult).run(unittest.TestSuite(active))
            if reference is not None:
                require(module_source(root, test_module, module_sha) == reference, "ORDINARY_SOURCE_CHANGED")
            started = getattr(result, "started_case_ids", [])
            return {"status": "PASS" if result.wasSuccessful() else "FAIL", **result_record(result),
                    "skips": [{"case": full_case_id(test), "reason": reason[:512]} for test, reason in result.skipped],
                    "suite_scope": "ONE_ORDINARY_MODULE" if reference is not None else "LEGACY_AGGREGATE",
                    "source_ref": reference, "test_module": test_module,
                    "planned_case_ids": planned, "discovered_case_ids": planned[:],
                    "started_case_ids": started,
                    "completed_case_ids": getattr(result, "completed_case_ids", []),
                    "outcomes": getattr(result, "outcomes", []), "not_run_cases": not_run,
                    "expected_failures": [full_case_id(test) for test, _ in result.expectedFailures],
                    "unstarted_skips": unstarted_skip_cases([full_case_id(t) for t in active], started, result.skipped),
                    "host_case_decision": decision}
    return run_frozen(root, group, phase)


def child_environment(environ):
    keys = ("PATH", "HOME", "TMPDIR", "TEMP", "TMP", "SYSTEMROOT", "WINDIR", "LANG", "LC_ALL", "TZ", "CI")
    result = {key: environ[key] for key in keys if key in environ}
    result.update(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                  PAID_API_ENABLED="false", MAX_SPEND_USD="0")
    return result


class Capture:
    def __init__(self, limit):
        self.limit, self.used = limit, 0

    def take(self, body):
        allowed = body[:max(0, self.limit - self.used)]
        self.used += len(body)
        return allowed, self.used > self.limit


def save_new(path, value):
    raw = value if isinstance(value, bytes) else packed(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def supervise(command, env, job, directory, *, popen=subprocess.Popen,
              selector_factory=selectors.DefaultSelector, clock=time.monotonic,
              read_fd=os.read, kill_group=os.killpg):
    """Bound combined capture while running; kill/reap on limits, never retry."""
    directory = Path(directory)
    stdout_path, stderr_path = directory / (job["id"] + ".stdout"), directory / (job["id"] + ".stderr")
    streams = []
    proc = None
    capture, started, reason, reaped = Capture(job["output_bytes"]), clock(), None, False
    selector = None
    try:
        for path in (stdout_path, stderr_path):
            streams.append(open(path, "xb", buffering=0))
        selector = selector_factory()
        proc = popen(command, cwd=str(ROOT), env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        for pipe, sink in zip((proc.stdout, proc.stderr), streams):
            selector.register(pipe, selectors.EVENT_READ, sink)
        while selector.get_map() or proc.poll() is None:
            if clock() - started >= job["wall_seconds"]:
                reason = "WALL_LIMIT"
                break
            for key, _ in selector.select(timeout=0.1):
                body = read_fd(key.fileobj.fileno(), 65536)
                if not body:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                allowed, exceeded = capture.take(body)
                key.data.write(allowed)
                if exceeded:
                    reason = "OUTPUT_LIMIT"
                    break
            if reason:
                break
        if reason:
            try:
                kill_group(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            proc.wait(timeout=2)
            reaped = True
        except subprocess.TimeoutExpired:
            reason = reason or "SHUTDOWN_UNKNOWN"
    except BaseException as error:
        reason = "SUPERVISOR_ERROR"
        if proc is not None:
            try:
                kill_group(proc.pid, signal.SIGKILL)
                proc.wait(timeout=2)
                reaped = True
            except (OSError, subprocess.TimeoutExpired):
                pass
        if not isinstance(error, Exception):
            raise
    finally:
        if selector is not None:
            selector.close()
        for sink in streams:
            sink.flush()
            os.fsync(sink.fileno())
            sink.close()
        if proc is not None:
            for pipe in (proc.stdout, proc.stderr):
                if pipe is not None:
                    pipe.close()
    return {"returncode": proc.returncode if proc is not None else None,
            "reason": reason, "reaped": reaped, "captured_bytes": min(capture.used, capture.limit),
            "elapsed_seconds": clock() - started,
            "stdout": str(stdout_path), "stderr": str(stderr_path)}


def parse_receipt(stdout, job, runner_sha):
    lines = [line[len(MARKER):] for line in stdout.decode("utf-8", "replace").splitlines() if line.startswith(MARKER)]
    maximum = 4194304 if job["phase"] == "ordinary" else 131072
    require(len(lines) == 1 and len(lines[0].encode()) <= maximum, "MISSING_OR_DUPLICATE_CHILD_RECEIPT")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_RECEIPT_KEY")
            result[key] = value
        return result
    receipt = json.loads(lines[0], object_pairs_hook=pairs)
    require(receipt.get("kind") == "OFFLINE_CI_CHILD_V1" and receipt.get("job_id") == job["id"]
            and receipt.get("runner_sha256") == runner_sha, "CHILD_RECEIPT_BINDING")
    require(receipt.get("status") in {"PASS", "FAIL", "NOT_RUN", "ERROR"}, "CHILD_RECEIPT_STATUS")
    return receipt


def validate_coverage(receipt, job, specification):
    if receipt["status"] in {"ERROR", "FAIL"}:
        return
    if job["phase"] == "ordinary":
        require(receipt["status"] == "PASS" and type(receipt.get("tests_run")) is int,
                "ORDINARY_COVERAGE_EMPTY")
        if "test_module" in job:
            require(receipt.get("test_module") == job["test_module"] and receipt.get("source_ref") == job["source_ref"]
                    and receipt.get("suite_scope") == "ONE_ORDINARY_MODULE", "ORDINARY_SOURCE_BINDING")
        else:
            require(receipt["tests_run"] > 0 and receipt.get("suite_scope") == "LEGACY_AGGREGATE", "ORDINARY_COVERAGE_EMPTY")
        names = ("planned_case_ids", "discovered_case_ids", "started_case_ids", "completed_case_ids")
        require(all(type(receipt.get(key)) is list and all(type(case) is str and 0 < len(case) <= 2048 for case in receipt[key]) for key in names),
                "ORDINARY_CASE_INVENTORY_REQUIRED")
        planned, discovered, started, completed = (receipt[key] for key in names)
        require(planned == discovered and Counter(started) == Counter(completed)
                and receipt["tests_run"] == len(started), "ORDINARY_CASE_EXECUTION_MISMATCH")
        require(receipt.get("failures") == [] and receipt.get("errors") == []
                and receipt.get("unexpected_successes") == [], "ORDINARY_SUCCESS_WITH_FAILURES")
        if "test_module" in job:
            declared = [Path(job["test_module"]).stem + "." + case for case in job["declared_local_cases"]]
            require(not (Counter(declared) - Counter(planned)), "ORDINARY_DECLARED_CASE_MISSING")
        require(type(receipt.get("outcomes")) is list and all(type(row) is dict and set(row) == {"case_id", "status"}
                and type(row["case_id"]) is str and row["status"] in {"PASS", "SKIP", "EXPECTED_FAILURE"} for row in receipt["outcomes"]), "ORDINARY_OUTCOMES_REQUIRED")
        require(Counter(row["case_id"] for row in receipt["outcomes"]) == Counter(started), "ORDINARY_OUTCOME_COVERAGE")
        expected_failures = receipt.get("expected_failures", [])
        require(type(expected_failures) is list and all(type(case) is str for case in expected_failures)
                and Counter(expected_failures) == Counter(row["case_id"] for row in receipt["outcomes"]
                if row["status"] == "EXPECTED_FAILURE"), "ORDINARY_EXPECTED_FAILURE_DISPOSITION")
        skips = receipt.get("skips")
        require(type(skips) is list and all(type(row) is dict and set(row) == {"case", "reason"}
                and type(row["case"]) is str and type(row["reason"]) is str for row in skips),
                "ORDINARY_SKIP_RECORDS_REQUIRED")
        require(type(receipt.get("not_run_cases")) is list and type(receipt.get("unstarted_skips")) is list,
                "ORDINARY_DISPOSITIONS_REQUIRED")
        not_run = receipt["not_run_cases"]
        for row in not_run:
            require(type(row) is dict and set(row) == {"case_id", "qualification"}
                    and type(row["case_id"]) is str and type(row["qualification"]) is dict and row["qualification"].get("status") == "NOT_RUN"
                    and row["qualification"].get("reasons"), "ORDINARY_UNEXPLAINED_NOT_RUN")
        if not_run:
            require("test_module" in job, "ORDINARY_UNEXPLAINED_NOT_RUN")
            rule = HOST_CASE_RULES.get(job["test_module"])
            require(rule is not None and all(row["qualification"].get("test_ref") == rule["test_ref"]
                    and row["qualification"].get("contract_ref") == rule["contract_ref"]
                    and row["qualification"].get("gate") == rule["gate"]
                    and row["case_id"].split(".", 1)[-1] in rule["local_cases"] for row in not_run), "ORDINARY_HOST_DISPOSITION_BINDING")
            decision = host_case_decision(Path(specification.get("root", ROOT)), job["test_module"])
            require(decision is not None and decision["status"] == "NOT_RUN"
                    and all(packed(row["qualification"]) == packed(decision) for row in not_run)
                    and Counter(row["case_id"].split(".", 1)[-1] for row in not_run) == Counter(rule["local_cases"]),
                    "ORDINARY_HOST_DECISION_FORGED")
        covered_skips = []
        for row in receipt["unstarted_skips"]:
            require(type(row) is dict and set(row) == {"holder", "reason", "case_ids"}
                    and type(row["holder"]) is str and type(row["reason"]) is str
                    and type(row["case_ids"]) is list, "ORDINARY_SKIP_DISPOSITION")
            holder = row["holder"]
            if holder.startswith("setUpClass (") and holder.endswith(")"):
                prefix = holder[len("setUpClass ("):-1] + "."
            elif holder.startswith("setUpModule (") and holder.endswith(")"):
                prefix = holder[len("setUpModule ("):-1] + "."
            else:
                raise IsolationError("ORDINARY_SKIP_HOLDER")
            require(all(type(case) is str and case.startswith(prefix) for case in row["case_ids"]), "ORDINARY_SKIP_MEMBERSHIP")
            require({"case": holder, "reason": row["reason"]} in receipt.get("skips", []), "ORDINARY_SKIP_NOT_RECORDED")
            covered_skips.extend(row["case_ids"])
        require(Counter(started) + Counter(covered_skips) + Counter(row["case_id"] for row in not_run) == Counter(planned),
                "ORDINARY_PLANNED_COVERAGE_INCOMPLETE")
        holders = Counter((row["holder"], row["reason"]) for row in receipt["unstarted_skips"])
        direct, subtests = Counter(), Counter()
        for skip in skips:
            holder = (skip["case"], skip["reason"])
            if holders[holder] > 0:
                holders[holder] -= 1
            elif skip["case"] in started:
                direct[skip["case"]] += 1
            else:
                parents = [case for case in set(started)
                           if skip["case"].startswith(case + " (") and skip["case"].endswith(")")]
                require(len(parents) == 1, "ORDINARY_SKIP_PARENT_MISSING")
                subtests[parents[0]] += 1
        skipped_outcomes = Counter(row["case_id"] for row in receipt["outcomes"] if row["status"] == "SKIP")
        require(not +holders and not (direct - skipped_outcomes)
                and not ((skipped_outcomes - direct) - subtests)
                and set(subtests) <= set(skipped_outcomes), "ORDINARY_SKIP_OUTCOME_MISMATCH")
        return
    row = specification["inventory"][job["group"]]
    require(receipt.get("frozen_source_ref") == {key: row[key] for key in ("path", "bytes", "sha256")},
            "FROZEN_RECEIPT_SOURCE_BINDING")
    expected = row["historical_cases"] if job["phase"] == "historical" else row["portable_cases"]
    require(receipt.get("planned_cases") == expected, "CHILD_PLANNED_CASES_CHANGED")
    if receipt["status"] == "NOT_RUN":
        require(job["phase"] == "historical" and receipt.get("tests_run") == 0
                and receipt.get("qualification", {}).get("status") == "NOT_RUN"
                and bool(receipt["qualification"].get("reasons")), "UNEXPLAINED_NOT_RUN")
    else:
        require(receipt.get("tests_run") == len(expected)
                and sorted(receipt.get("started_cases", [])) == expected
                and receipt.get("skips") == [], "FROZEN_COVERAGE_INCOMPLETE")
        if job["phase"] == "historical":
            require(historical_admission(receipt.get("host", {}), receipt.get("socket_observation"))["status"] == "SUPPORTED",
                    "HISTORICAL_RECEIPT_PROFILE_NOT_BOUND")


def final_status(results, require_historical=False):
    if any(r["status"] not in {"PASS", "NOT_RUN"} for r in results):
        return "FAIL"
    if any(r["status"] == "NOT_RUN" or r.get("receipt", {}).get("not_run_cases") for r in results):
        return "FAIL_HISTORICAL_NOT_RUN" if require_historical else "PASS_PORTABLE_HISTORICAL_NOT_RUN"
    return "PASS_ALL_REQUESTED_GROUPS"


def canonical_interpreter():
    path = Path(sys.executable).resolve()
    require(path.is_file() and not path.is_symlink(), "CANONICAL_PYTHON_EXECUTABLE")
    return str(path)


def run_parent(directory, *, root=ROOT, run_process=supervise, require_historical=False,
               shard_index=0, shard_count=None, module_wall=MODULE_WALL, only_modules=None):
    # None retains the old pure-model interface; the CLI always supplies a count
    # and therefore uses isolated modules, including for its default one shard.
    specification = (plan(root) if shard_count is None else module_plan(root, shard_index=shard_index,
                     shard_count=shard_count, module_wall=module_wall, only_modules=only_modules))
    runner_sha = sha(Path(__file__).read_bytes())
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    save_new(directory / "PLAN.json", {"kind": "OFFLINE_CI_PLAN_V1", "runner_sha256": runner_sha, **specification})
    started, results = time.monotonic(), []
    coordinator_wall = specification.get("shard", {}).get("budget_seconds", COORDINATOR_WALL)
    for job in specification["jobs"]:
        remaining = coordinator_wall - (time.monotonic() - started)
        if remaining <= 3:
            result = {"job_id": job["id"], "status": "ERROR", "reason": "COORDINATOR_WALL_LIMIT"}
        else:
            job = dict(job, wall_seconds=min(job["wall_seconds"], max(1, int(remaining - 3))))
            isolation = ["-I", "-B"] + ([] if job["phase"] == "ordinary" else ["-S"])
            command = [canonical_interpreter(), *isolation, str(Path(__file__).resolve()), "--child", job["group"],
                       "--phase", job["phase"]]
            if "test_module" in job:
                command.extend(["--test-module", job["test_module"], "--module-sha256", job["source_ref"]["sha256"],
                                "--module-wall-seconds", str(job["wall_seconds"])])
            command.extend(["--runner-sha256", runner_sha])
            save_new(directory / (job["id"] + "-RESERVED.json"), {"job": job, "argv": command, "attempt": 1})
            execution = None
            try:
                execution = run_process(command, child_environment(os.environ), job, directory)
                receipt = parse_receipt(Path(execution["stdout"]).read_bytes(), job, runner_sha)
                validate_coverage(receipt, job, specification)
                good = execution["reason"] is None and execution["reaped"] and execution["returncode"] == (0 if receipt["status"] in {"PASS", "NOT_RUN"} else 1)
                result = {"job_id": job["id"], "status": receipt["status"] if good else "ERROR", "receipt": receipt, "execution": execution}
            except Exception:
                result = {"job_id": job["id"], "status": "ERROR", "reason": "CHILD_RECEIPT_OR_EXECUTION_FAILED"}
                if execution is not None:
                    result["execution"] = execution
        save_new(directory / (job["id"] + "-RESULT.json"), result)
        results.append(result)
    summary = {"kind": "OFFLINE_CI_SUMMARY_V1", "status": final_status(results, require_historical),
               "historical_required": require_historical, "results": results,
               "scope": "CI coverage only; NOT_RUN historical checks are never runtime/research acceptance."}
    if shard_count is not None:
        expected_jobs = [job["id"] for job in specification["jobs"]]
        require([row["job_id"] for row in results] == expected_jobs, "SHARD_JOB_COVERAGE_CHANGED")
        summary.update(suite_scope=specification["suite_scope"], shard=specification["shard"],
                       ordinary_manifest_sha256=specification["ordinary_manifest_sha256"],
                       planned_module_refs=[job["source_ref"] for job in specification["jobs"] if "source_ref" in job])
        if only_modules is not None and summary["status"].startswith("PASS"):
            summary["status"] = "PASS_FOCUSED_ONLY" if summary["status"] == "PASS_ALL_REQUESTED_GROUPS" else "PASS_FOCUSED_HISTORICAL_NOT_RUN"
    save_new(directory / "SUMMARY.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--child", choices=["ordinary", *FROZEN])
    parser.add_argument("--phase", choices=["ordinary", "portable", "historical"])
    parser.add_argument("--runner-sha256")
    parser.add_argument("--require-historical", action="store_true")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--module-wall-seconds", type=int, default=MODULE_WALL)
    parser.add_argument("--only-module", action="append")
    parser.add_argument("--test-module")
    parser.add_argument("--module-sha256")
    args = parser.parse_args()
    if args.child:
        require(args.runner_sha256 == sha(Path(__file__).read_bytes()), "RUNNING_CI_SOURCE_HASH")
        require((args.child == "ordinary") == (args.phase == "ordinary"), "CHILD_PHASE")
        require((args.test_module is None) == (args.module_sha256 is None), "MODULE_SOURCE_ARGUMENTS")
        require(args.test_module is None or args.child == "ordinary", "MODULE_PHASE")
        job_id = ("ordinary-" + args.test_module[:-3] if args.test_module else "ordinary") if args.child == "ordinary" else args.child + "-" + args.phase
        try:
            receipt = child_entry(ROOT, args.child, args.phase, test_module=args.test_module,
                                  module_sha=args.module_sha256, module_wall=args.module_wall_seconds)
        except BaseException:
            detail = traceback.format_exc().encode("utf-8", "replace")
            print("CI_SETUP_FAILURE_DETAIL_BEGIN", file=sys.stderr, flush=True)
            print(detail[:65536].decode("utf-8", "replace"), file=sys.stderr, flush=True)
            print("CI_SETUP_FAILURE_DETAIL_END", file=sys.stderr, flush=True)
            receipt = {"status": "ERROR", "reason": "CHILD_SETUP_OR_HARNESS_ERROR", "tests_run": None,
                       "coverage": "UNKNOWN_AFTER_SETUP_OR_HARNESS_ERROR",
                       "traceback_bytes": len(detail), "traceback_sha256": sha(detail),
                       "traceback_truncated": len(detail) > 65536}
        receipt.update(kind="OFFLINE_CI_CHILD_V1", job_id=job_id, runner_sha256=args.runner_sha256)
        receipt["runtime"] = {"python": sys.version.split()[0], "implementation": sys.implementation.name,
                              "platform": sys.platform}
        if args.child != "ordinary":
            name, size, digest, _, _, _ = FROZEN[args.child]
            receipt["frozen_source_ref"] = {"path": "tests/" + name, "bytes": size, "sha256": digest}
        require(len(packed(receipt)) <= (4194304 if args.phase == "ordinary" else 131072), "CHILD_RECEIPT_SIZE")
        print(MARKER + packed(receipt).decode(), flush=True)
        return 0 if receipt["status"] in {"PASS", "NOT_RUN"} else 1
    require(args.output_dir is not None and args.phase is None, "OUTPUT_DIRECTORY_REQUIRED")
    require(args.test_module is None and args.module_sha256 is None, "PARENT_MODULE_ARGUMENTS")
    summary = run_parent(args.output_dir, require_historical=args.require_historical,
                         shard_index=args.shard_index, shard_count=args.shard_count,
                         module_wall=args.module_wall_seconds, only_modules=args.only_module)
    print(packed({"status": summary["status"], "summary": str(args.output_dir / "SUMMARY.json")}).decode())
    return 0 if summary["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
