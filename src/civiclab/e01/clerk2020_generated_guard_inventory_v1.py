"""Generated-only guarded inventory successor with bounded in-memory breadcrumbs.

No import/reader/source execution or audit-hook registration occurs on import.
Not a launcher, authority grant, runtime qualification or generic debugger.
The parser contract is copied from the frozen adapter; only stage/exception
observations are added. Acquired-source mode is explicitly unavailable here.
"""
import sys
from io import BytesIO

from civiclab.e01 import clerk2020_native_inventory_v1 as inventory
from civiclab.e01 import clerk2020_native_qualification_v1 as qualification
from civiclab.e01.clerk2020_m2_v1_1_contracts import (
    Refused, canonical, identifier, require, sha,
)
from civiclab.e01.clerk2020_m2_v1_1_backend import page_projection

InventoryRefused = inventory.InventoryRefused
_strict_diagnostics = inventory._strict_diagnostics
_check_structure = inventory._check_structure
SOURCES = inventory.SOURCES
DENIED = frozenset({'open', 'os.listdir', 'os.scandir', 'os.chdir', 'import',
                   'ctypes.dlopen', 'subprocess.Popen', 'os.system', 'os.fork',
                   'os.forkpty', 'os.posix_spawn'})
SAFE_TYPES = (Refused, InventoryRefused, qualification.QualificationStopped,
              ValueError, TypeError, RuntimeError, OSError, TimeoutError,
              MemoryError, ImportError, ModuleNotFoundError, FileNotFoundError,
              PermissionError, KeyError, IndexError, AttributeError, AssertionError)


class GeneratedTelemetry:
    """Single-worker state. No paths, error messages, arguments or locals retained."""
    def __init__(self):
        self.stage = 'NOT_STARTED'
        self.page = 0
        self.first_guard = None
        self.first_exception = None

    def guard(self, event, args):
        # Use the exact frozen event policy; event-name categories have fixed size.
        blocked = event in DENIED or event.startswith(('socket.', 'os.exec'))
        if not blocked:
            return
        if self.first_guard is None:
            kind = event if event in DENIED else ('socket.*' if event.startswith('socket.') else 'os.exec*')
            self.first_guard = {'event': kind}
        raise qualification.QualificationStopped()

    def observe(self, exc):
        if self.first_exception is not None:
            return
        known = next((c for c in SAFE_TYPES if type(exc) is c), None)
        record = {'type': known.__name__ if known is not None else 'UNKNOWN_EXACT_TYPE',
                  'stage': self.stage, 'page': self.page, 'frames': [],
                  'traceback_truncated': False}
        if known is not None:
            tb = BaseException.__getattribute__(exc, '__traceback__')
            steps = 0
            while tb is not None and steps < 32:
                code = tb.tb_frame.f_code
                for trusted, label in TRUSTED_CODES:
                    if code is trusted:
                        record['frames'].append({'function': label, 'line': tb.tb_lineno})
                        break
                tb = tb.tb_next
                steps += 1
            record['traceback_truncated'] = tb is not None
        self.first_exception = record


def inspect_snapshot(raw, source_id, reader_factory, *, authored_fixture=False,
                     fixture_pages=None, telemetry=None):
    """One memory-only parse; caller handles finite I/O/runtime/process authority.

    Actual source mode requires the exact acquired bytes and fixed page count.
    Authored mode requires a DEMO source ID and cannot yield a REAL label. Tests
    inject a finite reader double; real-library fixtures need separate review.
    Errors expose only a fixed type, never source text or library diagnostics.
    """
    require(type(telemetry) is GeneratedTelemetry and authored_fixture is True)
    telemetry.stage = 'INPUT_CONTRACT'
    result = None
    failed = False
    interrupted = None
    try:
        require(type(raw) is bytes and 0 < len(raw) <= 1048576 and raw.startswith(b'%PDF-'))
        require(type(authored_fixture) is bool and callable(reader_factory))
        if authored_fixture:
            require(identifier(source_id) and source_id.startswith('DEMO_'))
            require(type(fixture_pages) is int and 1 <= fixture_pages <= 100)
            expected = {'pages': fixture_pages, 'role': 'AUTHORED_GENERATED_PDF_ONLY',
                        'worker_output_bytes': min(247808, fixture_pages * 2048 + 2048)}
        else:
            require(source_id in SOURCES and fixture_pages is None)
            expected = SOURCES[source_id]
            require(len(raw) == expected['bytes'] and sha(raw) == expected['sha256'])
        require(identifier(source_id) and len(source_id) <= 59)
        label = 'MOCK' if authored_fixture else 'REAL_SOURCE_FORMAT_INSPECTION_ONLY'
        stream = BytesIO(raw)
        with _strict_diagnostics():
            telemetry.stage = 'READER_CONSTRUCTION'
            reader = reader_factory(stream, strict=True)
            telemetry.stage = 'READER_CONTRACT'
            require(type(reader.is_encrypted) is bool and reader.is_encrypted is False)
            pages = reader.pages
            require(len(pages) == expected['pages'])
            telemetry.stage = 'STRUCTURE'
            visited = _check_structure(reader.root_object)
            projected = []
            chars = utf8_bytes = 0
            for index in range(expected['pages']):
                telemetry.stage = 'PAGE_EXTRACTION'
                telemetry.page = index + 1
                text = pages[index].extract_text(extraction_mode='plain')
                telemetry.stage = 'PAGE_PROJECTION'
                require(type(text) is str and len(text) <= 40000)
                row = page_projection('DEMO_' + source_id, sha(raw), index + 1, text)
                row['source_id'] = source_id  # Shrinks the validated serialized row.
                require(len(canonical(row)) <= 2048)
                chars += row['full_extracted_text_characters']
                utf8_bytes += row['full_extracted_text_utf8_bytes']
                require(chars <= 4760000 and utf8_bytes <= 19040000)
                projected.append(row)
                del text
            telemetry.stage = 'FINAL_READER_CONTRACT'
            require(len(pages) == expected['pages'] and stream.getvalue() == raw)
        telemetry.stage = 'OUTPUT_CONTRACT'
        private = {
            'label': label, 'kind': 'CLERK_NATIVE_FORMAT_INVENTORY_V1',
            'source_id': source_id, 'source_sha256': sha(raw), 'source_bytes': len(raw),
            'source_role': expected['role'], 'page_count': expected['pages'],
            'pages': projected, 'candidate_or_vote_records_parsed': 0,
            'printed_dates_or_roles_adopted': False,
            'retained_full_document': all(p['retained_whole_page'] for p in projected),
        }
        diagnostic = {
            'label': label, 'kind': 'CLERK_NATIVE_FORMAT_DIAGNOSTICS_V1',
            'source_id': source_id, 'source_sha256': sha(raw), 'source_bytes': len(raw),
            'source_role': expected['role'], 'page_count': expected['pages'],
            'text_characters': chars, 'text_utf8_bytes': utf8_bytes,
            'omitted_text_utf8_bytes': sum(p['omitted_text_utf8_bytes'] for p in projected),
            'unknown_role_layout_pages': expected['pages'], 'structure_nodes_checked': visited,
            'candidate_or_vote_records_parsed': 0, 'source_or_feature_adoption': False,
            'model_calls': 0, 'cost_usd': 0,
        }
        private_raw, public_raw = canonical(private), canonical(diagnostic)
        require(len(private_raw) <= expected['worker_output_bytes'] and len(public_raw) <= 8192)
        result = {'private_projection': private_raw, 'public_diagnostics': public_raw}
    except KeyboardInterrupt:
        interrupted = 'KEYBOARD'
    except SystemExit:
        interrupted = 'EXIT'
    except BaseException as exc:
        telemetry.observe(exc)
        failed = True
    # Raise outside the exception handler to avoid a raw parser traceback chain.
    if interrupted == 'KEYBOARD':
        raise KeyboardInterrupt()
    if interrupted == 'EXIT':
        raise SystemExit(2)
    if failed:
        raise InventoryRefused()
    telemetry.stage = 'COMPLETE'
    return result



# Immutable code identities are captured before any untrusted reader callback.
TRUSTED_CODES = (
    (inspect_snapshot.__code__, 'inspect_snapshot'),
    (_check_structure.__code__, '_check_structure'),
    (require.__code__, 'require'),
    (page_projection.__code__, 'page_projection'),
    (GeneratedTelemetry.guard.__code__, 'parse_guard'),
)
