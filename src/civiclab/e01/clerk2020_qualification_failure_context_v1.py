"""Proposed future failure telemetry only; no execution, I/O or policy changes.

This cannot reconstruct the discarded traceback of qualification-v1. It formats
an exception already in memory in a future separately reviewed diagnostic pass.
It never grants a retry, runs a collector or changes the frozen qualification.
"""
from pathlib import PosixPath, WindowsPath
import re

QUALIFICATION_FILE = 'src/civiclab/e01/clerk2020_native_qualification_v1.py'
FUNCTIONS = frozenset({'_worker', '_runtime_inventory', '_stable_hash', '_no_alias', 'allowed'})


def _origin_category(path, root):
    if type(path) in {PosixPath, WindowsPath}:
        path = str(path)
    if type(path) is not str:
        return 'UNKNOWN'
    if path.startswith(root + '/data/raw/'):
        return 'RESEARCH_DATA_PATH_REFUSED'
    if path.startswith(root + '/.venv/lib/python3.12/site-packages/pypdf/'):
        return 'VENV_PYPDF'
    if path.startswith(root + '/.venv/lib/python3.12/site-packages/'):
        return 'VENV_OTHER_PACKAGE'
    if path.startswith(root + '/src/') or path.startswith(root + '/tests/'):
        return 'PROJECT_CODE'
    return 'OTHER_OR_UNKNOWN'


def failure_context(exc, root):
    """Read existing frame metadata only, without exception messages/full paths.

    Last-iteration module context does not itself identify the failing predicate.
    The recorded frozen-file line must be matched to independently reviewed code.
    No filesystem, module inventory, stack source lookup or runtime probe occurs.
    """
    if not isinstance(exc, BaseException) or type(root) is not str or not root.startswith('/'):
        raise ValueError('FAILURE_CONTEXT_CONTRACT_REFUSED')
    expected = root.rstrip('/') + '/' + QUALIFICATION_FILE
    frames = []
    tb = exc.__traceback__
    steps = 0
    while tb is not None and steps < 32:
        frame = tb.tb_frame
        name = frame.f_code.co_name
        if frame.f_code.co_filename == expected and name in FUNCTIONS:
            record = {'function': name, 'line': tb.tb_lineno}
            if name == '_runtime_inventory':
                state = frame.f_locals
                module = state.get('module')
                try:
                    values = object.__getattribute__(module, '__dict__')
                except (AttributeError, TypeError):
                    values = {}
                module_name = values.get('__name__') if type(values) is dict else None
                if (type(module_name) is str and len(module_name) <= 128
                        and re.fullmatch('[A-Za-z0-9_.]+', module_name)):
                    record['last_iteration_module_not_proven_cause'] = module_name
                record['last_iteration_origin_category_not_proven_cause'] = _origin_category(state.get('path'), root.rstrip('/'))
            frames.append(record)
        tb = tb.tb_next
        steps += 1
    return {'kind': 'PROPOSED_FUTURE_FAILURE_CONTEXT_NOT_ORIGINAL_RUN_DIAGNOSIS',
            'frozen_source': QUALIFICATION_FILE, 'qualified_frames': frames,
            'traceback_truncated': tb is not None, 'extra_runtime_or_source_io': 0,
            'exception_message_retained': False, 'permits_retry_or_policy_change': False}
