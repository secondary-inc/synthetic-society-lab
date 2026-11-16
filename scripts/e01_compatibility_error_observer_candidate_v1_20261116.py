"""PURE MOCK / UNWIRED bounded error observation; no runtime probing or IO.

No exception arguments, attributes, names, messages, frames, locals, traceback,
cause, context or module paths are inspected. Codes come only from an explicit
allowlisted call-site token, never by recovering text from an exception. A real
integration would require separate exact source review and finite authority.
"""
import json

KIND = 'E01_COMPATIBILITY_ERROR_OBSERVER_PURE_MOCK_V1'
MAX_PHASES = 16
MAX_COUNTER = 65535
MAX_JSON_BYTES = 4096
UNAVAILABLE = 'UNAVAILABLE_OR_UNALLOWLISTED'
PHASES = frozenset({
    'GUEST_ENTRY', 'GUARD_READY', 'MIME_PREPARE', 'MIME_READY',
    'PIP_ROOT_LOAD', 'PIP_ROOT_READY', 'ADAPTER_SOCKET_CHECK',
    'ADAPTER_OWNER_CHECK', 'ADAPTER_FRESHNESS_CHECK', 'ADAPTER_PARENT_CHECK',
    'ADAPTER_SOURCE_CHECK', 'ADAPTER_SCOPE_ENTER', 'ADAPTER_IMPORT_START',
    'ADAPTER_IMPORT_RETURN', 'ADAPTER_RESULT_CHECK', 'ADAPTER_SCOPE_RESTORE',
    'ADAPTER_RECEIPT_WRITE', 'PIP_DRY_RUN_START', 'PIP_DRY_RUN_RETURN',
    'GUEST_REFUSALS_WRITE', 'GUEST_RESULT_WRITE', 'GUEST_FINAL_COUNTER',
    'NOT_STARTED', 'UNKNOWN_PHASE'})
CODES = frozenset({
    'COMPATIBILITY_IMPORT_LOADER', 'COMPATIBILITY_IMPORT_STATE_DRIFT',
    'COMPATIBILITY_UNBOUND_IMPORT_ORIGIN', 'COMPATIBILITY_VENDOR_RESULT',
    'COMPATIBILITY_IMPORT_IN_PROGRESS', 'COMPATIBILITY_VENDOR_PRELOADED',
    'COMPATIBILITY_CLOSURE_MODULE_CAP', 'COMPATIBILITY_CLOSURE_READ_CAP',
    'COMPATIBILITY_SOURCE_CHANGED', 'COMPATIBILITY_SOURCE_FILE_CAP',
    'COMPATIBILITY_SOCKET_ORIGIN', 'COMPATIBILITY_EXACT_SOCKET_MODULE',
    'COMPATIBILITY_PROCESS_THREAD_OWNER', 'COMPATIBILITY_ORIGINAL_NOT_TRUE',
    'COMPATIBILITY_REENTRY', 'COMPATIBILITY_STICKY_FAILURE',
    'COMPATIBILITY_PRIOR_FAILURE_NO_RETRY', 'COMPATIBILITY_SCOPE_DRIFT',
    'COMPATIBILITY_RESTORE_FAILED', 'COMPATIBILITY_UNFINISHED_MODULE',
    'COMPATIBILITY_IMPORT_SPEC', 'COMPATIBILITY_RELOAD_DENIED',
    'COMPATIBILITY_PARENT_MODULE', 'COMPATIBILITY_INITIAL_MODULE_CAP',
    'COMPATIBILITY_PREEXISTING_MODULE_DRIFT', 'COMPATIBILITY_ORIGIN_ALIAS',
    'COMPATIBILITY_ORIGIN_NOT_FILE', 'COMPATIBILITY_IMPORT_ORIGIN_DRIFT',
    'GUEST_NETWORK_HELPER_OR_CTYPES_DENIED', 'GUEST_CAUGHT_VIOLATION',
    'PIP_NONZERO_EXIT', 'DOWNLOADED_PACKAGE_IMPORT_DENIED',
    'DIAGNOSTIC_GUEST_ERROR', 'DIAGNOSTIC_GUEST_DEADLINE',
    'DIAGNOSTIC_EXACT_ARGUMENTS', 'BASE_OR_OLD_SITE_ON_PATH',
    'PIP_LOADED_VERSION', 'DIAGNOSTIC_PIP_PRELOADED',
    'DIAGNOSTIC_OLD_SITE_EXPOSED', 'INPUT_HASH', 'INPUT_REF',
    'INPUT_TYPE_SIZE', 'INPUT_CHANGED', 'READ_CAP'})
BUILTIN_TYPES = (
    (ModuleNotFoundError, 'MODULE_NOT_FOUND_ERROR'), (ImportError, 'IMPORT_ERROR'),
    (AttributeError, 'ATTRIBUTE_ERROR'), (TypeError, 'TYPE_ERROR'),
    (ValueError, 'VALUE_ERROR'), (KeyError, 'KEY_ERROR'),
    (PermissionError, 'PERMISSION_ERROR'), (FileNotFoundError, 'FILE_NOT_FOUND_ERROR'),
    (TimeoutError, 'TIMEOUT_ERROR'), (OSError, 'OS_ERROR'),
    (RuntimeError, 'RUNTIME_ERROR'), (AssertionError, 'ASSERTION_ERROR'),
    (MemoryError, 'MEMORY_ERROR'), (RecursionError, 'RECURSION_ERROR'),
    (OverflowError, 'OVERFLOW_ERROR'), (NotImplementedError, 'NOT_IMPLEMENTED_ERROR'),
    (SystemExit, 'SYSTEM_EXIT'), (KeyboardInterrupt, 'KEYBOARD_INTERRUPT'))
TRUSTED_LABELS = frozenset({'COMPATIBILITY_REFUSED', 'FROZEN_GUARD_REFUSED'})
TYPE_LABELS = frozenset(label for _, label in BUILTIN_TYPES) | TRUSTED_LABELS | {
    'UNKNOWN_TYPE'}


class ObserverPayloadRefused(ValueError):
    pass


def require(value):
    if not value: raise ObserverPayloadRefused('OBSERVER_PAYLOAD_REFUSED')


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


class ErrorObserver:
    """Closed primitive state only; never retain the exception instance.

    trusted_types is an explicit reviewed binding of at most two exact custom
    exception classes to fixed labels. Class names and inheritance do not infer
    trust. Unknown subclasses are UNKNOWN_TYPE. This model does not attest that
    caller-supplied labels correspond to any actual runtime.
    """
    def __init__(self, trusted_types=()):
        require(type(trusted_types) is tuple and len(trusted_types) <= 2)
        classes, labels = [], []
        for entry in trusted_types:
            require(type(entry) is tuple and len(entry) == 2)
            cls, label = entry
            require(type(cls) is type and issubclass(cls, BaseException)
                    and type(label) is str and label in TRUSTED_LABELS
                    and cls not in classes and label not in labels
                    and all(cls is not builtin for builtin, _ in BUILTIN_TYPES))
            classes.append(cls); labels.append(label)
        self._trusted_types = tuple(trusted_types)
        self.phases = []
        self.phase_total = self.phase_dropped = self.failure_total = 0
        self.phase_saturated = self.failure_saturated = False
        self.last_phase = 'NOT_STARTED'
        self.first_error = self.latest_error = None
        self.unknown_phase_seen = self.unallowlisted_code_seen = False
        self.observer_failed = False

    def mark_phase(self, phase):
        if type(phase) is not str or len(phase) > 64 or phase not in PHASES:
            phase = 'UNKNOWN_PHASE'
            self.unknown_phase_seen = True
        if phase == 'UNKNOWN_PHASE': self.unknown_phase_seen = True
        self.last_phase = phase
        if self.phase_total < MAX_COUNTER: self.phase_total += 1
        else: self.phase_saturated = True
        if len(self.phases) < MAX_PHASES:
            self.phases.append({'sequence': self.phase_total, 'phase': phase})
        elif self.phase_dropped < MAX_COUNTER:
            self.phase_dropped += 1
        else: self.phase_saturated = True

    def record_exception(self, error, code=None):
        # No getattr, str, repr, args, __dict__ or metadata access on error.
        cls = type(error)
        label = 'UNKNOWN_TYPE'
        for approved, safe_label in self._trusted_types + BUILTIN_TYPES:
            if cls is approved:
                label = safe_label
                break
        available = type(code) is str and len(code) <= 80 and code in CODES
        if not available:
            code = UNAVAILABLE
            self.unallowlisted_code_seen = True
        record = {'exception_type': label, 'code': code,
                  'code_available': available, 'phase': self.last_phase}
        if self.first_error is None: self.first_error = record
        self.latest_error = record
        if self.failure_total < MAX_COUNTER: self.failure_total += 1
        else: self.failure_saturated = True

    def observe_call(self, phase, callback, *, code=None):
        """Mock boundary: return unchanged or rethrow the same primary error.

        code is a fixed call-site token, not a dynamic exception-derived value.
        Observer recording failure is sticky and never replaces a callback's
        primary exception. Original callbacks/guards run exactly once.
        """
        self.mark_phase(phase)
        try:
            return callback()
        except BaseException as error:
            try: self.record_exception(error, code)
            except BaseException: self.observer_failed = True
            raise

    def snapshot(self):
        result = {'kind': KIND, 'phase_total': self.phase_total,
            'phase_dropped': self.phase_dropped, 'phase_saturated': self.phase_saturated,
            'failure_total': self.failure_total, 'failure_saturated': self.failure_saturated,
            'last_phase': self.last_phase, 'phases': [dict(row) for row in self.phases],
            'first_error': dict(self.first_error) if self.first_error is not None else None,
            'latest_error': dict(self.latest_error) if self.latest_error is not None else None,
            'unknown_phase_seen': self.unknown_phase_seen,
            'unallowlisted_code_seen': self.unallowlisted_code_seen,
            'observer_failed': self.observer_failed}
        validate(result)
        return result

    def encode(self):
        raw = packed(self.snapshot())
        require(len(raw) <= MAX_JSON_BYTES)
        return raw


def validate(value):
    require(type(value) is dict and set(value) == {'kind', 'phase_total',
        'phase_dropped', 'phase_saturated', 'failure_total', 'failure_saturated',
        'last_phase', 'phases', 'first_error', 'latest_error', 'unknown_phase_seen',
        'unallowlisted_code_seen', 'observer_failed'} and value['kind'] == KIND)
    for key in ('phase_total', 'phase_dropped', 'failure_total'):
        require(type(value[key]) is int and 0 <= value[key] <= MAX_COUNTER)
    for key in ('phase_saturated', 'failure_saturated', 'unknown_phase_seen',
                'unallowlisted_code_seen', 'observer_failed'):
        require(type(value[key]) is bool)
    require(type(value['last_phase']) is str and value['last_phase'] in PHASES)
    require(type(value['phases']) is list and len(value['phases']) <= MAX_PHASES)
    require(len(value['phases']) == min(value['phase_total'], MAX_PHASES)
            and (not value['phase_saturated'] or value['phase_total'] == MAX_COUNTER)
            and (not value['failure_saturated'] or value['failure_total'] == MAX_COUNTER))
    previous = 0
    for row in value['phases']:
        require(type(row) is dict and set(row) == {'sequence', 'phase'}
                and type(row['sequence']) is int and previous < row['sequence'] <= value['phase_total']
                and row['sequence'] == previous+1
                and type(row['phase']) is str and row['phase'] in PHASES)
        require(row['phase'] != 'UNKNOWN_PHASE' or value['unknown_phase_seen'])
        previous = row['sequence']
    require(value['phase_total'] >= len(value['phases'])
            and (value['phase_saturated'] or
                 value['phase_dropped'] == value['phase_total']-len(value['phases'])))
    if value['phase_total'] == 0:
        require(value['last_phase'] == 'NOT_STARTED')
    elif value['phase_dropped'] == 0 and not value['phase_saturated']:
        require(value['last_phase'] == value['phases'][-1]['phase'])
    require(value['last_phase'] != 'UNKNOWN_PHASE' or value['unknown_phase_seen'])
    for key in ('first_error', 'latest_error'):
        row = value[key]
        if row is None:
            require(value['failure_total'] == 0)
        else:
            require(value['failure_total'] > 0 and type(row) is dict
                    and set(row) == {'exception_type', 'code', 'code_available', 'phase'}
                    and type(row['exception_type']) is str and row['exception_type'] in TYPE_LABELS
                    and type(row['code']) is str and row['code'] in CODES | {UNAVAILABLE}
                    and type(row['code_available']) is bool
                    and row['code_available'] is (row['code'] != UNAVAILABLE)
                    and type(row['phase']) is str and row['phase'] in PHASES)
            require(row['code'] != UNAVAILABLE or value['unallowlisted_code_seen'])
            require(row['phase'] != 'UNKNOWN_PHASE' or value['unknown_phase_seen'])
    if value['failure_total'] == 1:
        require(value['first_error'] == value['latest_error'])
    require(len(packed(value)) <= MAX_JSON_BYTES)
    return value


def decode(raw):
    require(type(raw) is bytes and len(raw) <= MAX_JSON_BYTES)
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out)
            out[key] = value
        return out
    def bad_constant(_): raise ObserverPayloadRefused('OBSERVER_PAYLOAD_REFUSED')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ObserverPayloadRefused('OBSERVER_PAYLOAD_REFUSED') from None
    return validate(value)
