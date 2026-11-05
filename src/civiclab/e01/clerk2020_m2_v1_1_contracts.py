"""Finite M2 v1.1 primitives. Pure bytes only; never grants actual authority."""
from dataclasses import dataclass, replace
import hashlib
import json
import re
import math


class Refused(ValueError):
    def __init__(self):
        super().__init__('CLERK_M2_V1_1_REFUSED')


def require(condition):
    if not condition:
        raise Refused()


def uint(value, maximum=2**63 - 1):
    return type(value) is int and 0 <= value <= maximum


def identifier(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value) is not None


def hex64(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def relative_path(value):
    return (type(value) is str and 0 < len(value.encode('utf8')) <= 256
            and all(part and part not in {'.', '..'} for part in value.split('/'))
            and not any(ord(c) < 32 or c in '\\:' for c in value))


def canonical(value):
    """No custom serialization hooks, coercion, floats or unlimited recursion."""
    left = [16384]
    def walk(x, depth):
        left[0] -= 1
        require(left[0] >= 0 and depth <= 12)
        if x is None or type(x) is bool:
            return
        if type(x) is int:
            require(abs(x) <= 2**63 - 1)
        elif type(x) is str:
            require(len(x) <= 160000)
            try:
                x.encode('utf8')
            except UnicodeError:
                raise Refused() from None
        elif type(x) is list:
            for item in x:
                walk(item, depth + 1)
        elif type(x) is dict:
            require(all(type(k) is str for k in x))
            for k, item in x.items():
                walk(k, depth + 1)
                walk(item, depth + 1)
        else:
            raise Refused()
    walk(value, 0)
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf8')


def sha(raw):
    require(type(raw) is bytes)
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value))


def decode(raw, ceiling=262144):
    require(type(raw) is bytes and len(raw) <= ceiling)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result
    def invalid(_):
        raise Refused()
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid,
                           parse_float=invalid)
        require(canonical(value) == raw)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise Refused() from None


def exact(value, fields):
    require(type(value) is dict and set(value) == set(fields))


CEILINGS = {
    'bootstrap_attempts': 1, 'execution_admission_attempts': 1, 'source_jobs': 1,
    'source_read_attempts': 2, 'source_read_bytes': 859913,
    'backend_attempts': 2, 'page_extractions': 119,
    'code_integrity_read_bytes': 536870912, 'metadata_read_bytes': 8388608,
    'record_verification_read_bytes': 2097152, 'inspection_data_write_bytes': 262144,
    'recorder_control_write_bytes': 131072, 'owned_write_bytes': 524288,
    'active_time_ms': 120000, 'cpu_ms': 60000,
}


@dataclass(frozen=True)
class Axis:
    ceiling: int
    held: int = 0
    reserved: int = 0
    charged: int = 0
    observed_known_sum: int = 0
    uncertain_charged: int = 0

    def __post_init__(self):
        require(all(uint(v) for v in vars(self).values()))
        require(self.held + self.reserved + self.charged <= self.ceiling)
        require(self.observed_known_sum + self.uncertain_charged <= self.charged)

    @property
    def observed(self):
        return None if self.uncertain_charged else self.observed_known_sum

    def allocate(self, n):
        require(uint(n))
        return replace(self, held=self.held + n)

    def reserve(self, n):
        require(uint(n) and n <= self.held)
        return replace(self, held=self.held - n, reserved=self.reserved + n)

    def settle(self, reservation, actual=None):
        require(uint(reservation) and reservation <= self.reserved)
        require(actual is None or uint(actual, reservation))
        if actual is None:
            return replace(self, reserved=self.reserved - reservation,
                           charged=self.charged + reservation,
                           uncertain_charged=self.uncertain_charged + reservation)
        return replace(self, reserved=self.reserved - reservation,
                       charged=self.charged + actual,
                       held=self.held + reservation - actual,
                       observed_known_sum=self.observed_known_sum + actual)

    def precharge(self, n):
        return self.reserve(n).settle(n)

    def stop_unknown(self):
        return replace(self, held=0, reserved=0,
                       charged=self.charged + self.held + self.reserved,
                       uncertain_charged=self.uncertain_charged + self.held + self.reserved)

    def record(self):
        return {**vars(self), 'observed': self.observed}


class Counters:
    """All-axis transaction: a refused update cannot partly mutate the set."""
    def __init__(self):
        self._axes = {name: Axis(n) for name, n in CEILINGS.items()}

    def transition(self, operation, amounts):
        require(type(amounts) is dict and set(amounts) <= set(self._axes))
        require(operation in {'allocate', 'reserve', 'precharge'})
        replacement = dict(self._axes)
        for name, n in amounts.items():
            replacement[name] = getattr(replacement[name], operation)(n)
        self._axes = replacement

    def settle(self, name, reservation, actual=None):
        require(name in self._axes)
        self._axes[name] = self._axes[name].settle(reservation, actual)

    def stop_unknown(self):
        self._axes = {k: v.stop_unknown() for k, v in self._axes.items()}

    def snapshot(self):
        return {k: v.record() for k, v in self._axes.items()}


def run_id(campaign_id, job_id, execution_decision):
    require(identifier(campaign_id) and identifier(job_id))
    return 'e01-' + digest({'kind': 'M2_RUN_ID_V1_1', 'campaign_id': campaign_id,
                           'job_id': job_id,
                           'execution_decision_sha256': digest(execution_decision)})[:32]


def check_declared_graph(nodes, edges):
    require(type(nodes) is list and all(identifier(n) for n in nodes)
            and len(nodes) == len(set(nodes)))
    require(type(edges) is list and all(type(e) is list and len(e) == 2
            and all(n in nodes for n in e) for e in edges))
    pending, seen = set(nodes), set()
    while pending:
        ready = {n for n in pending if all(a in seen for a, b in edges if b == n)}
        require(bool(ready))
        pending -= ready
        seen |= ready
    return True


class SampledResourceWindow:
    """Finite authored sample validator; no clocks, ps calls or native guards.

    Sampling can only establish observations supplied to this interface, never
    hard containment or the absence of peaks between samples.
    """
    def __init__(self, wall_ms, cpu_ms, rss_bytes=268435456):
        require(all(uint(x) and x > 0 for x in [wall_ms, cpu_ms, rss_bytes]))
        self.wall_ms, self.cpu_ms, self.rss_bytes = wall_ms, cpu_ms, rss_bytes
        self.last = None
        self.stopped = False

    def sample(self, active_ms, cpu_ms, rss_bytes):
        require(not self.stopped)
        try:
            values = (active_ms, cpu_ms, rss_bytes)
            require(all(type(x) in {int, float} and math.isfinite(x) and x >= 0 for x in values))
            require(active_ms <= self.wall_ms and cpu_ms <= self.cpu_ms and 0 < rss_bytes <= self.rss_bytes)
            require(self.last is None or active_ms >= self.last[0] and cpu_ms >= self.last[1])
            self.last = values
        except BaseException:
            self.stopped = True
            raise


def actual_factory(*args, **kwargs):
    """No flag, passed credential or fabricated approval can enable actual M2."""
    raise Refused()
