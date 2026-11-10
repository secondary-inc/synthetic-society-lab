"""Fresh, explicitly reviewed crypto-closure qualification; no acquired PDFs.

Both consumed ancestors remain intact. No arbitrary site-packages allowance,
dependency installation, hidden module pruning, provider fallback or source grant.
"""
import base64
import os
from pathlib import Path
import re
import subprocess
import sys
import time

if __name__ == '__main__' and len(sys.argv) == 3 and sys.argv[1] == '--crypto-qualification-worker':
    sys.path.insert(0, str(Path(sys.argv[2]).absolute() / 'src'))

from civiclab.e01 import clerk2020_native_qualification_v1 as frozen
from civiclab.e01.clerk2020_m2_v1_1_contracts import Refused, canonical, decode, digest, exact, hex64, require, sha

ENTRY = 'src/civiclab/e01/clerk2020_crypto_qualification_v1.py'
CODE_PATHS = frozen.CODE_PATHS + (ENTRY,)
SCOPE = 'data/processed/e01_clerk2020_native_qualification_v1/qualification-crypto-v1'
KIND = 'CLERK2020_CRYPTO_QUALIFICATION_RELEASE_V1'
PROFILE = {'admission': 'Only named pypdf/cryptography/cffi/pycparser/PIL roots and exact CFFI backend; eagerly loaded '
              'existing Pillow supported explicitly; no ANY-venv, hidden modules, crypto fallback or '
              'image-processing claim.',
 'declared_versions': {'cffi': '2.1.1',
                       'cryptography': '50.0.2',
                       'pillow': '13.0.0',
                       'pycparser': '3.12',
                       'pypdf': '6.10.0'},
 'native_backend': {'bytes': 229552,
                    'path': '.venv/lib/python3.12/site-packages/_cffi_backend.cpython-312-darwin.so',
                    'sha256': '90177c34e639a067ee1f5a2028320b3af2940d47dfaf9583727b59abf0b3263f'},
 'static_files': {'.venv/lib/python3.12/site-packages/PIL/__init__.py': {'bytes': 2035,
                                                                         'sha256': '7361b6ad3878589affe5956e4a4da24d71398b0891fd3a8c15e9362217b4ca01'},
                  '.venv/lib/python3.12/site-packages/cffi-2.1.1.dist-info/METADATA': {'bytes': 2527,
                                                                                       'sha256': '558bafb9093a8e790175d9ecff9688382981d744877dad86fd6770db0f4dc918'},
                  '.venv/lib/python3.12/site-packages/cffi-2.1.1.dist-info/RECORD': {'bytes': 3590,
                                                                                     'sha256': '244456e894b5ea7812f60d8c0272e694e40999028412323b3aedee4987b07e19'},
                  '.venv/lib/python3.12/site-packages/cryptography-50.0.2.dist-info/METADATA': {'bytes': 4394,
                                                                                                'sha256': '047cfc71226409de4318b360aef15c63a2adf609731e3dcf7fe932f14ea042ee'},
                  '.venv/lib/python3.12/site-packages/cryptography/__about__.py': {'bytes': 445,
                                                                                   'sha256': '95184137751279e4ccc0ababa44ed8bc380fbcdd5ba584f0407c5d14e31c109d'},
                  '.venv/lib/python3.12/site-packages/pillow-13.0.0.dist-info/METADATA': {'bytes': 9118,
                                                                                          'sha256': 'dba7fdfe24e302f46bae562f55d66cc367c0618abae9894a1ebec93dc8f0e511'},
                  '.venv/lib/python3.12/site-packages/pycparser-3.12.dist-info/METADATA': {'bytes': 9709,
                                                                                           'sha256': 'ad8db5fe2b0e0a3b0e8419fe5041b80be92470a40b06bd9c1462a0a8bb637c92'},
                  '.venv/lib/python3.12/site-packages/pypdf-6.10.0.dist-info/METADATA': {'bytes': 7112,
                                                                                         'sha256': '74db615a83dee1980ab4c4a73609d53cebf557e80ee822e9ac363cd575f7a61a'},
                  '.venv/lib/python3.12/site-packages/pypdf/__init__.py': {'bytes': 1283,
                                                                           'sha256': '612ff566b4378c13c7b1180cb2da89ac0b6cde5500a63fe530e30ae6a88b1b9c'},
                  '.venv/lib/python3.12/site-packages/pypdf/_crypt_providers/__init__.py': {'bytes': 3054,
                                                                                            'sha256': '2b767a02e5e15d579780b7adf93ba4ab682df47eba3a076ea6cbf1212d429a42'},
                  '.venv/lib/python3.12/site-packages/pypdf/_crypt_providers/_cryptography.py': {'bytes': 4460,
                                                                                                 'sha256': 'f733a4933312b17e1a974454934a8cd1d29f7dc1e47b8c1f9845caf64c28450f'}}}
PROFILE_SHA = digest(PROFILE)
ANCESTOR_RECORDS = {'data/processed/e01_clerk2020_native_qualification_v1/qualification-v1/OUTCOME.json': {'bytes': 775,
                                                                                        'sha256': '691206c41eac017175b3adab3392435815cbfd07efc4fa376bb6797a65ff52ca'},
 'data/processed/e01_clerk2020_native_qualification_v1/qualification-v1/STARTED.json': {'bytes': 660,
                                                                                        'sha256': '9f3b9aa63691818a550b582783b2fd5049f9db6ae79e406b3485bae8539fd378'},
 'data/processed/e01_clerk2020_native_qualification_v1/qualification-v1/partial_stdout.local.bin': {'bytes': 114,
                                                                                                    'sha256': 'd155497b8919144990a65cc3e9d9001a93be8d89298caa8ef287ebd08a21bf2d'},
 'data/processed/e01_clerk2020_native_qualification_v1/runtime-diagnostic-v1/OUTCOME.json': {'bytes': 700,
                                                                                             'sha256': 'f3cb2f09411d57c39e5df72da5f81e86303dfe3ed15a57ff085c7fbf7187fe65'},
 'data/processed/e01_clerk2020_native_qualification_v1/runtime-diagnostic-v1/STARTED.json': {'bytes': 861,
                                                                                             'sha256': 'c76b9daa10f3d98ec41803dfc6a90f5e75a48a16bfd595a681956f30c5451bc6'},
 'data/processed/e01_clerk2020_native_qualification_v1/runtime-diagnostic-v1/worker.json': {'bytes': 1232,
                                                                                            'sha256': '6be52b1238c9899c4bf6672ef40e3ba84cf7eb5026483dd741cc23e6ef96bfd8'}}
PAST_LIMITS = {'qualification-v1': {'child_cpu_hard_seconds': 11,
                      'child_cpu_soft_seconds': 10,
                      'child_wall_seconds': 30,
                      'code_read_bytes': 1048576,
                      'model_calls': 0,
                      'native_import_attempts': 1,
                      'network_requests': 0,
                      'owned_write_bytes': 131072,
                      'packet_bytes': 32768,
                      'page_extractions': 119,
                      'reader_attempts': 4,
                      'rss_peak_bytes': 268435456,
                      'runtime_files': 1024,
                      'runtime_hash_bytes': 536870912,
                      'runtime_manifest_bytes': 98304,
                      'source_reads': 0,
                      'stderr_bytes': 4096,
                      'stdout_bytes': 114688,
                      'wall_ms': 45000},
 'runtime-diagnostic-v1': {'ancestor_read_bytes_reserved': 3104,
                           'ancestor_record_reads': 6,
                           'child_cpu_hard_seconds': 11,
                           'child_cpu_soft_seconds': 10,
                           'child_wall_seconds': 30,
                           'code_read_bytes': 1048576,
                           'collector_passes': 1,
                           'model_calls': 0,
                           'native_import_attempts': 1,
                           'network_requests': 0,
                           'owned_write_bytes': 131072,
                           'packet_bytes': 32768,
                           'page_extractions': 0,
                           'reader_attempts': 0,
                           'rss_peak_bytes': 268435456,
                           'runtime_files': 1024,
                           'runtime_hash_bytes': 536870912,
                           'runtime_manifest_bytes': 98304,
                           'source_reads': 0,
                           'stderr_bytes': 4096,
                           'stdout_bytes': 114688,
                           'wall_ms': 45000}}
LIMITS = {**frozen.LIMITS, 'static_profile_reads': 11, 'static_read_bytes_reserved': 47738,
          'ancestor_record_reads': 12, 'ancestor_read_bytes_reserved': 8696}
MODULE_PREFIXES = ('pypdf/', 'cryptography/', 'cffi/', 'pycparser/', 'PIL/')


class OriginRefused(ValueError):
    def __init__(self, predicate, module_name):
        require(type(predicate) is str and predicate in {'EXPLICIT_ORIGIN_PROFILE', 'PROFILE_PACKAGE_ROOT', 'NATIVE_BACKEND_PATH', 'NATIVE_BACKEND_HASH'})
        super().__init__('CRYPTO_QUALIFICATION_ORIGIN_REFUSED')
        self.predicate = predicate
        self.module_name = module_name if type(module_name) is str and re.fullmatch('[A-Za-z0-9_.]{1,128}', module_name) else 'UNKNOWN_MODULE'


class DurableQualification(frozen.DurableQualification):
    def __init__(self, root):
        root = Path(root).absolute()
        frozen._no_alias(root)
        self.path = root / SCOPE
        frozen._no_alias(self.path)
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.path.mkdir(mode=0o700, exist_ok=False)
        frozen._fsync_dir(self.path.parent)
        self.spent = 0


def validate_packet(root, raw, expected):
    require(type(raw) is bytes and len(raw) <= LIMITS['packet_bytes'] and hex64(expected) and sha(raw) == expected)
    p = decode(raw, LIMITS['packet_bytes'])
    exact(p, {'schema_version', 'kind', 'phase_id', 'root_sha256', 'code_refs', 'profile_sha256',
              'ancestor_records', 'past_limits', 'credit_restored', 'limits', 'review_bytes_b64', 'review_sha256'})
    require(type(p['schema_version']) is int and p['schema_version'] == 1 and p['kind'] == KIND
            and p['phase_id'] == 'qualification-crypto-v1' and p['root_sha256'] == sha(str(Path(root).absolute()).encode())
            and p['profile_sha256'] == PROFILE_SHA and canonical(p['ancestor_records']) == canonical(ANCESTOR_RECORDS)
            and canonical(p['past_limits']) == canonical(PAST_LIMITS) and type(p['credit_restored']) is int
            and p['credit_restored'] == 0 and canonical(p['limits']) == canonical(LIMITS))
    exact(p['code_refs'], CODE_PATHS)
    for r in p['code_refs'].values():
        exact(r, {'bytes', 'sha256'})
        require(type(r['bytes']) is int and 0 < r['bytes'] <= 262144 and hex64(r['sha256']))
    require(p['code_refs']['src/civiclab/e01/clerk2020_native_qualification_v1.py']['sha256'] ==
            '29ff273b6d7a97d83a01573bfee39f060927b1f41501e2f86b4ada1c3323382f')
    require(sum(r['bytes'] + 1 for r in p['code_refs'].values()) <= LIMITS['code_read_bytes'])
    try:
        rraw = base64.b64decode(p['review_bytes_b64'], validate=True)
    except (ValueError, TypeError):
        raise frozen.QualificationStopped() from None
    require(sha(rraw) == p['review_sha256'])
    review = decode(rraw, 16384)
    exact(review, {'kind', 'status', 'reviewer_role', 'code_refs', 'profile_sha256', 'ancestor_records',
                   'past_limits', 'credit_restored', 'limits', 'source_authority'})
    require(review['kind'] == 'CLERK2020_CRYPTO_QUALIFICATION_CODE_BINDING_V1'
            and review['status'] == 'PASS_EXACT_FRESH_GENERATED_QUALIFICATION_ONLY'
            and review['reviewer_role'] == 'independent_auditor' and review['source_authority'] is False)
    for key in ['code_refs', 'profile_sha256', 'ancestor_records', 'past_limits', 'credit_restored', 'limits']:
        require(canonical(review[key]) == canonical(p[key]))
    return p


def _verify_files(root, records, allowance):
    actual = reserved = 0
    for name, ref in records.items():
        h, n, charge = frozen._stable_hash(root / name, allowance - reserved)
        actual += n
        reserved += charge
        require(n == ref['bytes'] and h == ref['sha256'])
    return actual, reserved


def _origin_allowed(path, root, base):
    if path.is_relative_to(root / 'data/raw') or path.name == '.env':
        return False
    if path.is_relative_to(base):
        return True
    if not path.is_relative_to(root):
        return False
    rel = str(path.relative_to(root))
    if rel in CODE_PATHS:
        return True
    site = '.venv/lib/python3.12/site-packages/'
    if rel.startswith(site) and any(rel[len(site):].startswith(prefix) for prefix in MODULE_PREFIXES):
        return True
    if rel == PROFILE['native_backend']['path']:
        return True
    if '/__pycache__/' in rel and rel.endswith('.pyc'):
        import importlib.util
        try:
            return str(Path(importlib.util.source_from_cache(str(path))).relative_to(root)) in CODE_PATHS
        except (ValueError, NotImplementedError):
            return False
    return False


def runtime_inventory(root):
    base = Path(sys.base_prefix).resolve()
    candidates = {Path(sys.executable).resolve()}
    for module_key, module in tuple(sys.modules.items()):
        for attr in ['__file__', '__cached__']:
            name = getattr(module, attr, None)
            if type(name) is str:
                path = Path(os.path.abspath(name))
                if type(module_key) is str and module_key == '_cffi_backend' and attr == '__file__':
                    if path != root / PROFILE['native_backend']['path']:
                        raise OriginRefused('NATIVE_BACKEND_PATH', module_key)
                if type(module_key) is str and any(module_key == p[:-1] or module_key.startswith(p[:-1] + '.')
                                                   for p in MODULE_PREFIXES):
                    package = module_key.split('.')[0]
                    if not path.is_relative_to(root / '.venv/lib/python3.12/site-packages' / package):
                        raise OriginRefused('PROFILE_PACKAGE_ROOT', module_key)
                if not _origin_allowed(path, root, base):
                    raise OriginRefused('EXPLICIT_ORIGIN_PROFILE', module_key)
                if path.is_file():
                    frozen._no_alias(path)
                    candidates.add(path)
    require(len(candidates) <= LIMITS['runtime_files'])
    rows, actual, reserved = [], 0, 0
    backend_loaded = False
    for path in sorted(candidates):
        h, n, charge = frozen._stable_hash(path, LIMITS['runtime_hash_bytes'] - reserved)
        actual += n
        reserved += charge
        if path == root / PROFILE['native_backend']['path']:
            if h != PROFILE['native_backend']['sha256'] or n != PROFILE['native_backend']['bytes']:
                raise OriginRefused('NATIVE_BACKEND_HASH', '_cffi_backend')
            backend_loaded = True
        name = ('PYTHON_BASE/' + str(path.relative_to(base)) if path.is_relative_to(base)
                else 'REPO/' + str(path.relative_to(root)))
        rows.append([name, n, h])
    require(len(canonical(rows)) <= LIMITS['runtime_manifest_bytes'])
    return rows, actual, reserved, backend_loaded


def generated_checks(reader_factory):
    from test_clerk2020_native_inventory_v1 import generated_pdf
    from civiclab.e01.clerk2020_native_inventory_v1 import InventoryRefused, inspect_snapshot
    marker = 'AUTHORED DEMO FORMAT FIXTURE'
    checked = 0
    for pages in [81, 38]:
        output = inspect_snapshot(generated_pdf(pages), 'DEMO_CRYPTO', reader_factory,
                                  authored_fixture=True, fixture_pages=pages)
        private = decode(output['private_projection'])
        require(private['page_count'] == pages and len(private['pages']) == pages)
        for row in private['pages']:
            text = ''.join(w['text'] for w in row['snippet_windows'])
            require(row['retained_whole_page'] is True and text in {marker, marker + '\n'}
                    and row['full_extracted_text_utf8_sha256'] == sha(text.encode()))
            checked += 1
    for raw in [generated_pdf(1, b'/OpenAction << /S /JavaScript /JS (DEMO) >>'),
                b'%PDF-1.4\nnot a PDF object graph\n%%EOF\n']:
        try:
            inspect_snapshot(raw, 'DEMO_CRYPTO', reader_factory, authored_fixture=True, fixture_pages=1)
        except InventoryRefused:
            continue
        raise Refused()
    return checked


def validate_child(raw):
    child = decode(raw, LIMITS['stdout_bytes'])
    additions = {'dependency_profile_sha256', 'selected_crypto_provider', 'eager_pillow_version', 'text_marker_pages_checked',
                 'native_backend_loaded_and_hash_matched'}
    require(type(child) is dict and additions <= set(child))
    require(child['dependency_profile_sha256'] == PROFILE_SHA
            and child['selected_crypto_provider'] == ['cryptography', '50.0.2']
            and child['eager_pillow_version'] == '13.0.0'
            and type(child['text_marker_pages_checked']) is int and child['text_marker_pages_checked'] == 119
            and type(child['native_backend_loaded_and_hash_matched']) is bool)
    frozen.validate_worker(canonical({k: v for k, v in child.items() if k not in additions}))
    native_rows = [r for r in child['runtime_manifest'] if r[0] == 'REPO/' + PROFILE['native_backend']['path']]
    require(child['native_backend_loaded_and_hash_matched'] == bool(native_rows))
    if native_rows:
        require(len(native_rows) == 1 and native_rows[0][1:] == [PROFILE['native_backend']['bytes'], PROFILE['native_backend']['sha256']])
    return child


def run_phase(root, raw, expected):
    root = Path(root).absolute()
    p = validate_packet(root, raw, expected)
    store = DurableQualification(root)
    started = time.monotonic()
    store.write('STARTED.json', canonical({'kind': KIND, 'plan_sha256': expected,
                'profile_sha256': PROFILE_SHA, 'ancestor_limits_not_reduced': True,
                'credit_restored': 0, 'limits': LIMITS, 'source_authority': False, 'no_retry': True}))
    proc, out, err = None, bytearray(), bytearray()
    failed = False
    try:
        prior = _verify_files(root, ANCESTOR_RECORDS, LIMITS['ancestor_read_bytes_reserved'] // 2)
        code = _verify_files(root, p['code_refs'], LIMITS['code_read_bytes'])
        static = _verify_files(root, PROFILE['static_files'], LIMITS['static_read_bytes_reserved'])
        require((time.monotonic() - started) * 1000 < LIMITS['wall_ms'])
        proc = subprocess.Popen([sys.executable, '-I', '-B', '-S', str(root / ENTRY),
                                '--crypto-qualification-worker', str(root)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=root, start_new_session=True, env={'PATH': os.defpath, 'LC_ALL': 'C'})
        peak = frozen._exchange(proc, canonical({'profile_sha256': PROFILE_SHA}), started, out, err)
        child = validate_child(bytes(out))
        require(prior == _verify_files(root, ANCESTOR_RECORDS, LIMITS['ancestor_read_bytes_reserved'] // 2))
        require((time.monotonic() - started) * 1000 < LIMITS['wall_ms'])
        store.write('worker.json', bytes(out))
        result = {'status': 'FRESH_GENERATED_QUALIFICATION_RECORDED_NOT_SOURCE_ADMISSION',
                  'plan_sha256': expected, 'profile_sha256': PROFILE_SHA, 'worker_sha256': sha(bytes(out)),
                  'ancestor_limits_not_reduced': True, 'ancestor_unchanged': True, 'credit_restored': 0,
                  'ancestor_bytes_observed': prior[0] * 2, 'ancestor_bytes_reserved': prior[1] * 2,
                  'code_bytes_observed': code[0], 'code_bytes_reserved': code[1],
                  'static_bytes_observed': static[0], 'static_bytes_reserved': static[1],
                  'text_marker_pages_checked': child['text_marker_pages_checked'],
                  'sampled_child_peak_rss_bytes': peak if peak else None, 'source_reads': 0,
                  'model_calls': 0, 'cost_usd': 0}
    except BaseException:
        failed = True
        result = {'status': 'CRYPTO_QUALIFICATION_UNKNOWN_STOP_NO_RETRY', 'plan_sha256': expected,
                  'ancestor_limits_not_reduced': True, 'credit_restored': 0, 'full_new_limits_consumed': LIMITS,
                  'reader_attempts_observed': None, 'source_reads': 0, 'model_calls': 0, 'cost_usd': 0}
    finally:
        if proc is not None:
            try:
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, 9)
                    except ProcessLookupError:
                        pass
                proc.wait(timeout=1)
            except BaseException:
                failed = True
                result = {'status': 'CRYPTO_QUALIFICATION_REAP_UNKNOWN_NO_RETRY',
                          'ancestor_limits_not_reduced': True, 'full_new_limits_consumed': LIMITS,
                          'source_reads': 0, 'model_calls': 0, 'cost_usd': 0}
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()
    if failed:
        if out and not (store.path / 'worker.json').exists():
            store.write('partial_stdout.local.bin', bytes(out[:LIMITS['stdout_bytes']]))
        if err:
            store.write('stderr.local.bin', bytes(err[:LIMITS['stderr_bytes']]))
    store.write('OUTCOME.json', canonical(result))
    if failed:
        raise frozen.QualificationStopped()
    return result


def _guard(event, args):
    if event.startswith(('socket.', 'os.exec')) or event in {
            'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn'}:
        raise Refused()


def _worker(root):
    import resource
    stage = 'RESOURCE'
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (LIMITS['child_cpu_soft_seconds'], LIMITS['child_cpu_hard_seconds']))
        require(decode(sys.stdin.buffer.read(1025), 1024) == {'profile_sha256': PROFILE_SHA})
        sys.path[:0] = [str(root / 'src'), str(root / 'tests'), str(root / '.venv/lib/python3.12/site-packages')]
        sys.addaudithook(_guard)
        stage = 'IMPORT_IDENTITY'
        import pypdf
        import PIL
        from pypdf._crypt_providers import crypt_provider
        import test_clerk2020_native_inventory_v1
        require(sys.implementation.name == 'cpython' and sys.version.split()[0] == '3.12.14'
                and sys.platform == 'darwin' and os.uname().machine == 'arm64'
                and pypdf.__version__ == '6.10.0' and type(crypt_provider) is tuple
                and crypt_provider == ('cryptography', '50.0.2') and PIL.__version__ == '13.0.0')
        stage = 'RUNTIME_MANIFEST'
        rows, actual, reserved, backend = runtime_inventory(root)
        stage = 'GUARDED_GENERATED_FIXTURES'
        frozen._install_parse_guard()
        checked = generated_checks(pypdf.PdfReader)
        result = {'label': 'MOCK_GENERATED_PDF_ONLY', 'status': 'NATIVE_GENERATED_FIXTURES_COMPLETE',
                  'reader_attempts': 4, 'expected_page_extractions': 119, 'positive_page_counts': [81, 38],
                  'negative_cases_refused': 2, 'actual_source_reads': 0, 'model_calls': 0,
                  'python': '3.12.14', 'pypdf': '6.10.0', 'interpreter_implementation': 'cpython',
                  'platform': 'darwin', 'machine': 'arm64', 'runtime_manifest': rows,
                  'runtime_manifest_sha256': digest(rows), 'runtime_hash_bytes_observed': actual,
                  'runtime_hash_bytes_reserved': reserved, 'runtime_manifest_scope': frozen.MANIFEST_SCOPE,
                  'guard': frozen.GUARD_SCOPE, 'dependency_profile_sha256': PROFILE_SHA,
                  'selected_crypto_provider': list(crypt_provider), 'text_marker_pages_checked': checked,
                  'eager_pillow_version': PIL.__version__,
                  'native_backend_loaded_and_hash_matched': backend}
    except BaseException as exc:
        origin = {'predicate': exc.predicate, 'module_name': exc.module_name} if type(exc) is OriginRefused else None
        result = {'status': 'CRYPTO_QUALIFICATION_WORKER_STOP', 'stage': stage,
                  'origin_refusal': origin, 'source_reads': 0, 'model_calls': 0}
    raw = canonical(result)
    require(len(raw) <= LIMITS['stdout_bytes'])
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--crypto-qualification-worker':
        _worker(Path(sys.argv[2]).absolute())
    else:
        raise SystemExit('Exact reviewed fresh qualification release required; no acquired-source entry.')
