"""Pathless strict-reader adapter for the acquired Clerk format inventory.

This module performs no source/runtime I/O and imports no PDF library. A reviewed
caller must supply immutable source bytes and a reviewed reader implementation.
Neither this interface nor fixture success constitutes actual source authority.
"""
from contextlib import contextmanager
from io import BytesIO
import logging
import math
import warnings

from civiclab.e01.clerk2020_m2_v1_1_contracts import (
    canonical, identifier, require, sha,
)
from civiclab.e01.clerk2020_m2_v1_1_backend import page_projection

SOURCES = {
    'clerk2020_statistics': {
        'bytes': 602172, 'sha256': '666b2a1f673f263087c141c4d44b0dce47cbddc8f4df27fbc8b415cf05842b76',
        'pages': 81, 'role': 'HISTORICAL_2020_COUNTS_NOT_2026_OUTCOMES',
        'worker_output_bytes': 167936,
    },
    'clerk2026_nominees': {
        'bytes': 257739, 'sha256': 'cb2e4194c88042cf22f8589fb6b8c352d29b501f96abc62a962b6cc52e2c28a8',
        'pages': 38, 'role': 'DATED_2026_NOMINEES_NOT_OUTCOMES_OR_FINAL_BALLOTS',
        'worker_output_bytes': 79872,
    },
}
FORBIDDEN_KEYS = frozenset({
    '/OpenAction', '/AA', '/A', '/JavaScript', '/JS', '/EmbeddedFiles', '/EF',
    '/Launch', '/URI', '/GoToR', '/SubmitForm', '/ImportData', '/Rendition',
    '/RichMedia', '/XFA', '/AcroForm',
})
FORBIDDEN_TYPES = frozenset({'/Filespec', '/EmbeddedFile', '/Action'})


class InventoryRefused(ValueError):
    def __init__(self):
        super().__init__('CLERK_NATIVE_INVENTORY_REFUSED')


@contextmanager
def _strict_diagnostics():
    """Single worker only: warnings/logs stop without retaining their text."""
    class StopWarning(logging.Handler):
        def emit(self, record):
            raise InventoryRefused()
    logger = logging.getLogger('pypdf')
    prior = logger.handlers[:], logger.propagate, logger.level, logger.disabled
    logger.handlers = [StopWarning()]
    logger.propagate = False
    logger.setLevel(logging.WARNING)
    logger.disabled = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            yield
    finally:
        logger.handlers, logger.propagate, logger.level, logger.disabled = prior


def _check_structure(root):
    """Bounded catalogue object traversal, without decoding stream bodies.

    It deliberately refuses unknown object kinds and active/external features.
    Unique objects are capped; repeated shared fonts/parent links are not cycles
    to follow forever. Parser allocation precedes these checks; no preallocation
    or hard decompression-containment claim is made.
    """
    stack = [(root, 0)]
    seen = set()
    visited = 0
    while stack:
        obj, depth = stack.pop()
        require(depth <= 32)
        identity = id(obj)
        if identity in seen:
            continue
        seen.add(identity)
        visited += 1
        require(visited <= 16384)
        if hasattr(obj, 'get_object'):
            resolved = obj.get_object()
            if resolved is not obj:
                stack.append((resolved, depth + 1))
                continue
        if isinstance(obj, dict):
            require(len(obj) <= 4096)
            require(all(str(k) not in FORBIDDEN_KEYS for k in obj))
            require(str(obj.get('/Type', '')) not in FORBIDDEN_TYPES)
            stack.extend((value, depth + 1) for value in obj.values())
        elif isinstance(obj, (list, tuple)):
            require(len(obj) <= 4096)
            stack.extend((value, depth + 1) for value in obj)
        else:
            # pypdf PDF scalar classes are subclasses or explicitly named null/
            # boolean wrappers; arbitrary callbacks or lazy plugin objects fail.
            scalar = isinstance(obj, (str, bytes, int, float, bool)) or obj is None
            wrapper = (type(obj).__module__.startswith('pypdf.generic')
                       and type(obj).__name__ in {'NullObject', 'BooleanObject'})
            require(scalar or wrapper)
            if isinstance(obj, float):
                require(math.isfinite(obj))
    return visited


def inspect_snapshot(raw, source_id, reader_factory, *, authored_fixture=False,
                     fixture_pages=None):
    """One memory-only parse; caller handles finite I/O/runtime/process authority.

    Actual source mode requires the exact acquired bytes and fixed page count.
    Authored mode requires a DEMO source ID and cannot yield a REAL label. Tests
    inject a finite reader double; real-library fixtures need separate review.
    Errors expose only a fixed type, never source text or library diagnostics.
    """
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
            reader = reader_factory(stream, strict=True)
            require(type(reader.is_encrypted) is bool and reader.is_encrypted is False)
            pages = reader.pages
            require(len(pages) == expected['pages'])
            visited = _check_structure(reader.root_object)
            projected = []
            chars = utf8_bytes = 0
            for index in range(expected['pages']):
                text = pages[index].extract_text(extraction_mode='plain')
                require(type(text) is str and len(text) <= 40000)
                row = page_projection('DEMO_' + source_id, sha(raw), index + 1, text)
                row['source_id'] = source_id  # Shrinks the validated serialized row.
                require(len(canonical(row)) <= 2048)
                chars += row['full_extracted_text_characters']
                utf8_bytes += row['full_extracted_text_utf8_bytes']
                require(chars <= 4760000 and utf8_bytes <= 19040000)
                projected.append(row)
                del text
            require(len(pages) == expected['pages'] and stream.getvalue() == raw)
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
    except BaseException:
        failed = True
    # Raise outside the exception handler to avoid a raw parser traceback chain.
    if interrupted == 'KEYBOARD':
        raise KeyboardInterrupt()
    if interrupted == 'EXIT':
        raise SystemExit(2)
    if failed:
        raise InventoryRefused()
    return result


def actual_source_factory(*args, **kwargs):
    """No source path, implicit import or actual execution entry is enabled."""
    raise InventoryRefused()
