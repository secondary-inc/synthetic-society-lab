"""Once-only metadata verification; never calls execute, guest_main, or pip."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.abc
import importlib.util
import json
import os
import resource
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / 'data/processed/e01_pypdf701_p2_metadata_preflight_v3_20261116'
REPORT = ROOT / 'reports/E01_PYPDF701_P2_REAL_METADATA_PREFLIGHT_V3_20261116.json'
PINS = {
    'scripts/install_e01_pypdf701_runtime_v1_4.py': '5d118a009805890854dcad6e17c89d297376cb685b22c0374a2fd5fb33d4b6f3',
    'configs/e01_pypdf701_install_v1_4_20261116.json': '4a3b12a980652c26c48bdffd8308bc7d4f7252c7c5189ae6174600ea5334d9c6',
    'data/processed/e01_pypdf701_build_v1/install-v1_4-packet-20261116.json': '7b248077701e8d6bc7552eb765a44cc48f5da43ef7f3f232a5d8d5721f787e4c',
}

class NoDownloadedImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'pip', 'pypdf', 'PIL', 'cryptography', 'cffi', '_cffi_backend', 'pycparser'}:
            raise RuntimeError('PREFLIGHT_PACKAGE_IMPORT_DENIED')

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())

def audit(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec', 'ctypes.dlopen'}:
        raise RuntimeError('PREFLIGHT_EXECUTION_DENIED')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).absolute()
        flags = args[2]
        if path.is_relative_to(ROOT / 'data/raw') or path.name == '.env':
            raise RuntimeError('PREFLIGHT_SOURCE_OR_CREDENTIAL_READ_DENIED')
        if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            if not path.is_relative_to(SCOPE) and path != REPORT:
                raise RuntimeError('PREFLIGHT_WRITE_DENIED')

def main():
    utc_start, mono_start = time.time(), time.monotonic()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (7, 8))
    def stop(*_): raise TimeoutError('PREFLIGHT_DEADLINE')
    signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, 120)
    SCOPE.mkdir(mode=0o700, exist_ok=False)
    sys.addaudithook(audit)
    sys.meta_path.insert(0, NoDownloadedImports())
    save(SCOPE / 'STARTED.json', {'kind': 'ONCE_READONLY_P2_METADATA_PREFLIGHT_V3', 'pins': PINS,
         'UTC_started': datetime.fromtimestamp(utc_start, timezone.utc).isoformat(),
         'wall_seconds': 120, 'CPU_soft_hard': [7, 8], 'reader_bytes': 536870912})
    reader = None
    result = {'kind': 'E01_P2_READONLY_REAL_METADATA_PREFLIGHT_V3', 'status': 'FAILED_NO_INSTALL',
              'source_pins': PINS, 'installer_commands': 0, 'pip_imports': 0,
              'downloaded_package_imports': 0, 'actual_research_source_reads': 0,
              'network_requests': 0, 'model_calls': 0, 'cost_USD': 0}
    try:
        bodies = {}
        for name, digest in PINS.items():
            path = ROOT / name
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
                raise RuntimeError('PREFLIGHT_PIN_PATH_OR_SIZE')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise RuntimeError('PREFLIGHT_PIN_HASH')
            bodies[name] = raw
        spec = importlib.util.spec_from_file_location('p2_readonly_v14', ROOT / next(iter(PINS)))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        methods = module.json_body(bodies[module.METHODS])
        packet = module.json_body(bodies[methods['packet']])
        module.validate_methods(ROOT, methods)
        reader = module.Reader(ROOT)
        binding = module.verify_bootstrap(ROOT, methods, reader)
        result['validated_pip_base_paths'] = module.narrowed_paths(list(sys.path), binding['base_prefix'])
        evidence = module.verify_acquisition(ROOT, methods, packet, reader)
        prior = module.verify_prior_install(ROOT, methods, packet, reader)
        snapshot = module.prior_metadata_snapshot(ROOT)
        occupied = module.owned_size(ROOT)
        upper = occupied + 2*evidence['inflated_bytes'] + binding['executable_ref']['bytes'] + 33554432
        module.need(upper <= module.CAPS['owned_logical_bytes'], 'OWNED_PREFLIGHT_UPPER_BOUND')
        for name in (module.OUTPUT, module.TARGET):
            module.no_alias(ROOT / name)
            module.need(not (ROOT / name).exists(), 'P2_ALREADY_CONSUMED')
        result.update(prior_installation=prior, prior_metadata_snapshot=snapshot,
                      prior_owned_logical_bytes=occupied, combined_preflight_upper_bound=upper)
        result.update(status='PASS_METADATA_ONLY_NO_INSTALL', verified_wheels=len(evidence['identities']),
                      dependency_closure=evidence['closure'], inflated_bytes=evidence['inflated_bytes'])
    except Exception as error:
        result['reason'] = str(error) if type(error).__name__ == 'Refused' else type(error).__name__
    result.update(reader_bytes_charged=reader.charged if reader else 0,
                  UTC_elapsed_seconds=time.time() - utc_start,
                  monotonic_elapsed_seconds=time.monotonic() - mono_start,
                  target_env_created=(ROOT / '.venv-e01-pypdf-7.0.1-v2').exists())
    save(SCOPE / 'RECEIPT.json', result)
    save(REPORT, result)
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps({k: v for k, v in result.items() if k not in {'dependency_closure', 'source_pins'}}))
    return 0 if result['status'].startswith('PASS') else 1

if __name__ == '__main__':
    raise SystemExit(main())
