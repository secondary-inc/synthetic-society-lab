"""CI process isolation, not research or runtime qualification authority.

The supervisor never imports tests. Frozen groups retain their original guards
inside disposable children; ordinary discovery cannot execute those modules.
"""
from __future__ import annotations

import argparse
import ast
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
SOCKET_PINS = {
    "3.11.17": (37557, "64360e73e3db69396d45d5ee256e8306b3653212ab96ae4a130070488cddbb30"),
    "3.12.14": (37815, "7d4d4c66e6f4bcc961ab462c4f08002ca97def8713a4be1c7373bdbd970a5274"),
}
ORDINARY_WALL = 10800
COORDINATOR_WALL = ORDINARY_WALL + 10 * 120 + 120


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


def _collect_ordinary(root, *, loader=None, install_hook=sys.addaudithook):
    barrier = CollectionBarrier(root)
    install_hook(barrier)  # This function is called only in the ordinary child.
    barrier.collecting = True
    try:
        return (loader or OrdinaryLoader(root)).discover(str(Path(root) / "tests")), barrier
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


def child_entry(root, group, phase):
    seconds = ORDINARY_WALL if phase == "ordinary" else 120
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (seconds - 1, seconds))
    def deadline(*_):
        raise IsolationError("CI_CHILD_DEADLINE")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    if phase == "ordinary":
        with ordinary_import_context(root):
            suite, _ = _collect_ordinary(root)
            result = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult).run(suite)
            return {"status": "PASS" if result.wasSuccessful() else "FAIL", **result_record(result)}
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
            streams.append(open(path, "xb"))
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
        require(receipt["status"] == "PASS" and type(receipt.get("tests_run")) is int
                and receipt["tests_run"] > 0, "ORDINARY_COVERAGE_EMPTY")
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
    if any(r["status"] == "NOT_RUN" for r in results):
        return "FAIL_HISTORICAL_NOT_RUN" if require_historical else "PASS_PORTABLE_HISTORICAL_NOT_RUN"
    return "PASS_ALL_REQUESTED_GROUPS"


def run_parent(directory, *, root=ROOT, run_process=supervise, require_historical=False):
    specification = plan(root)
    runner_sha = sha(Path(__file__).read_bytes())
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    save_new(directory / "PLAN.json", {"kind": "OFFLINE_CI_PLAN_V1", "runner_sha256": runner_sha, **specification})
    started, results = time.monotonic(), []
    for job in specification["jobs"]:
        if time.monotonic() - started >= COORDINATOR_WALL:
            result = {"job_id": job["id"], "status": "ERROR", "reason": "COORDINATOR_WALL_LIMIT"}
        else:
            isolation = ["-I", "-B"] + ([] if job["phase"] == "ordinary" else ["-S"])
            command = [sys.executable, *isolation, str(Path(__file__).resolve()), "--child", job["group"],
                       "--phase", job["phase"], "--runner-sha256", runner_sha]
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
    save_new(directory / "SUMMARY.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--child", choices=["ordinary", *FROZEN])
    parser.add_argument("--phase", choices=["ordinary", "portable", "historical"])
    parser.add_argument("--runner-sha256")
    parser.add_argument("--require-historical", action="store_true")
    args = parser.parse_args()
    if args.child:
        require(args.runner_sha256 == sha(Path(__file__).read_bytes()), "RUNNING_CI_SOURCE_HASH")
        require((args.child == "ordinary") == (args.phase == "ordinary"), "CHILD_PHASE")
        job_id = "ordinary" if args.child == "ordinary" else args.child + "-" + args.phase
        try:
            receipt = child_entry(ROOT, args.child, args.phase)
        except BaseException:
            receipt = {"status": "ERROR", "reason": "CHILD_SETUP_OR_HARNESS_ERROR", "tests_run": None,
                       "coverage": "UNKNOWN_AFTER_SETUP_OR_HARNESS_ERROR"}
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
    summary = run_parent(args.output_dir, require_historical=args.require_historical)
    print(packed({"status": summary["status"], "summary": str(args.output_dir / "SUMMARY.json")}).decode())
    return 0 if summary["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
