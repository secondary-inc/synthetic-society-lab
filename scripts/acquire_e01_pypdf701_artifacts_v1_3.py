"""Fixed-artifact cache freshness successor. No metadata refresh or installation.

All failed attempts remain charged. Root explicitly raised the cumulative
technical GET allowance from historical13 to14; monetary limits are unchanged.
Raw response headers are never rewritten to bypass the frozen policy.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import resource
import signal
import stat

PREVIOUS_CODE_SHA = '961ef657dd6860c83d32acf5f2b4673976c33b996b2907ec4cc86f3eb5574634'
PREVIOUS_CODE_BYTES = 20351
OUTPUT = 'data/processed/e01_pypdf701_build_v1/acquisition-v1_3-20261115'
METHODS = 'configs/e01_pypdf701_acquisition_v1_3_20261115.json'


def load_previous():
    import hashlib
    path = Path(__file__).absolute().with_name('acquire_e01_pypdf701_artifacts_v1_2.py')
    if any(p.is_symlink() for p in (path, *path.parents)): raise RuntimeError('PREVIOUS_CODE_ALIAS')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream: raw = stream.read(PREVIOUS_CODE_BYTES+1)
    if len(raw) != PREVIOUS_CODE_BYTES or hashlib.sha256(raw).hexdigest() != PREVIOUS_CODE_SHA:
        raise RuntimeError('PREVIOUS_CODE_HASH')
    spec = importlib.util.spec_from_file_location('p1_frozen_v1_2', path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


v = load_previous()
n, c = v.n, v.c
CAPS = {**c.CAPS, 'GET': 14, 'wheel_GET': 6}
MEDIA = ['application/octet-stream', 'application/zip', 'binary/octet-stream']


def cache_directives(raw):
    if raw is None: return {}
    c.need(type(raw) is str and 0 < len(raw) <= 2048 and raw.isascii(), 'CACHE_CONTROL_SCHEMA')
    parts = raw.split(','); c.need(len(parts) <= 32, 'CACHE_CONTROL_SCHEMA')
    result = {}
    for part in parts:
        match = re.fullmatch(r'\s*([A-Za-z][A-Za-z0-9_-]*)(?:\s*=\s*([^\s,]+))?\s*', part)
        c.need(match is not None, 'CACHE_CONTROL_SCHEMA')
        key, value = match.groups(); key = key.lower()
        c.need(key not in result, 'CACHE_CONTROL_DUPLICATE')
        result[key] = value
    c.need('s-maxage' not in result, 'CACHE_CONTROL_SHARED_MAXAGE_REFUSED')
    c.need(not {'no-cache', 'no-store', 'private'}.intersection(result), 'CACHE_CONTROL_CONFLICT')
    if 'immutable' in result: c.need(result['immutable'] is None, 'CACHE_CONTROL_IMMUTABLE_VALUE')
    if 'max-age' in result:
        value = result['max-age']
        c.need(type(value) is str and re.fullmatch('[0-9]{1,10}', value)
               and int(value) <= 2147483647, 'CACHE_CONTROL_MAXAGE')
        result['max-age'] = int(value)
    return result


def freshness_decision(headers, kind, now):
    c.need(kind in {'wheel', 'metadata'}, 'HTTP_KIND')
    try: served = c.parsedate_to_datetime(headers.get('date', ''))
    except (ValueError, TypeError): raise c.Refused('HTTP_DATE') from None
    c.need(served is not None and served.tzinfo is not None, 'HTTP_DATE')
    difference = (now-served).total_seconds()
    c.need(abs(difference) <= 300, 'HTTP_DATE_FRESHNESS')
    age_raw = headers.get('age')
    age = '0' if age_raw is None else age_raw
    c.need(type(age) is str and re.fullmatch('[0-9]{1,10}', age)
           and int(age) <= 2147483647, 'HTTP_AGE')
    age = int(age)
    if kind == 'metadata':
        c.need(age <= 3600, 'HTTP_FRESHNESS')
        return {'policy': 'ORIGINAL_METADATA_AGE_3600', 'Age_seconds': age, 'Date_difference_seconds': difference}
    directives = cache_directives(headers.get('cache-control'))
    if 'immutable' in directives and 'max-age' in directives and age_raw is not None:
        maximum = directives['max-age']
        c.need(age < maximum, 'HTTP_IMMUTABLE_AGE_EXPIRED')
        return {'policy': 'FIXED_IMMUTABLE_ARTIFACT_UNIQUE_MAX_AGE', 'Age_seconds': age,
                'max_age_seconds': maximum, 'Date_difference_seconds': difference}
    c.need(age <= 3600, 'HTTP_FRESHNESS')
    return {'policy': 'ORIGINAL_WHEEL_AGE_3600', 'Age_seconds': age,
            'Age_absent_default_zero': age_raw is None, 'Date_difference_seconds': difference}


class HTTPTransport(c.HTTPTransport):
    def open(self, url, timeout):
        response = super().open(url, timeout)
        # The old response dict preserves only the last Cache-Control field.
        # Retain the complete raw occurrences so duplicates cannot disappear.
        response.raw_cache_control_values = [value for key, value in response.response.getheaders()
                                             if key.lower() == 'cache-control']
        return response


class Budget(n.ContinuationBudget):
    def begin(self, kind):
        self.check(); c.need(kind in {'wheel', 'metadata'}, 'HTTP_KIND'); key = kind+'_GET'
        c.need(self.attempts['GET'] < CAPS['GET'] and self.attempts[key] < CAPS[key] and self.held == 0, 'REQUEST_CAP')
        cap = min(CAPS[kind+'_each'], CAPS[kind+'_total']-self.bytes[kind], CAPS['network_total']-sum(self.bytes.values()))
        c.need(cap > 1, 'BODY_CAP')
        self.attempts['GET'] += 1; self.attempts[key] += 1; self.held = cap
        return cap


class Collector(v.Collector):
    def __init__(self, root, methods, transport, **kwargs):
        super().__init__(root, methods, transport, **kwargs)
        self.scope, self.transport = self.root/OUTPUT, transport
        self.budget = Budget(self.budget.clock, self.budget.cpu)

    def fetch(self, url, kind, name, filename=None):
        c.need(kind == 'wheel' and url in self.companion_urls, 'FOUR_FIXED_COMPANIONS_ONLY')
        c.validate_url(url, kind, filename)
        cap = self.budget.begin(kind); started = self.budget.clock()
        self.current_request = {'url': url, 'kind': kind, 'cap': cap}
        self.event('REQUEST_RESERVED', {**self.current_request, 'budget': self.budget.record()})
        response, body = None, bytearray()
        def remaining():
            self.budget.check()
            left = min(20-(self.budget.clock()-started), 120-(self.budget.clock()-self.budget.started))
            c.need(left > 0, 'REQUEST_TIMEOUT')
            return left
        try:
            if self.stage_signals: signal.setitimer(signal.ITIMER_REAL, remaining())
            response = self.transport.open(url, remaining()); headers = response.headers
            c.need(type(headers) is dict and all(type(key) is str and type(value) is str for key, value in headers.items()), 'HTTP_HEADER_SCHEMA')
            self.current_request['HTTP_status'] = response.status
            raw_headers = {key: headers.get(key) for key in ('date', 'age', 'cache-control', 'content-type', 'content-length', 'content-encoding')}
            cc_values = getattr(response, 'raw_cache_control_values',
                                [] if headers.get('cache-control') is None else [headers['cache-control']])
            try:
                c.need(type(response.status) is int and response.status == 200, 'HTTP_STATUS')
                c.need(headers.get('content-encoding', 'identity') == 'identity', 'CONTENT_ENCODING')
                c.need(type(cc_values) in {list, tuple} and len(cc_values) <= 1, 'CACHE_CONTROL_DUPLICATE_FIELD')
                c.need(not cc_values or cc_values[0] == headers.get('cache-control'), 'CACHE_CONTROL_FIELD_BINDING')
                media = headers.get('content-type', '').split(';')[0].strip().lower()
                c.need(media in MEDIA, 'CONTENT_TYPE')
                decision = freshness_decision(headers, kind, self.utc())
                length = headers.get('content-length')
                if length is not None:
                    c.need(re.fullmatch('[0-9]{1,10}', length) and int(length) < cap, 'CONTENT_LENGTH')
            except c.Refused as exc:
                self.event('RAW_HTTP_HEADER_DECISION', {'url': url, 'HTTP_status': response.status,
                    'raw_headers': raw_headers, 'raw_cache_control_field_values': cc_values,
                    'decision': {'status': 'REFUSED', 'reason': str(exc)}})
                raise
            self.event('RAW_HTTP_HEADER_DECISION', {'url': url, 'HTTP_status': response.status,
                'raw_headers': raw_headers, 'raw_cache_control_field_values': cc_values,
                'decision': {'status': 'ACCEPTED', **decision}})
            while True:
                requested = min(65536, cap-len(body)); chunk = response.read(requested, remaining())
                c.need(type(chunk) is bytes and len(chunk) <= requested, 'TRANSPORT_SCHEMA')
                if not chunk: break
                body.extend(chunk); c.need(len(body) < cap, 'BODY_CAP')
            remaining()
            if length is not None: c.need(len(body) == int(length), 'CONTENT_LENGTH')
            body = bytes(body); ref = self.write(name, body, False)
            self.budget.settle(kind, len(body)); self.current_request = None
            self.event('RESPONSE_RECORDED', {'url': url, 'ref': ref, 'budget': self.budget.record()})
            return body, headers, ref
        except BaseException:
            if self.current_request is not None:
                self.current_request.update(observed_partial_body_bytes=len(body), partial_body_sha256=c.sha(bytes(body)))
            if self.budget.held: self.budget.settle(kind)
            raise
        finally:
            if response is not None: response.close()
            if self.stage_signals:
                signal.setitimer(signal.ITIMER_REAL, max(.001, 120-(self.budget.clock()-self.budget.started)))

    def predecessor(self):
        m = self.methods
        c.need(m.get('kind') == 'E01_PYPDF701_ACQUISITION_METHODS_V1_3' and m.get('schema_version') == 1
               and m.get('output') == OUTPUT and m.get('root_sha256') == c.sha(str(self.root).encode())
               and m.get('caps') == CAPS and m.get('historical_original_caps') == c.CAPS
               and m.get('additional_technical_GET') == 1 and m.get('previous_scope') == v.OUTPUT
               and m.get('previous_code_ref') == {'path': 'scripts/acquire_e01_pypdf701_artifacts_v1_2.py',
                    'bytes': PREVIOUS_CODE_BYTES, 'sha256': PREVIOUS_CODE_SHA}, 'METHODS_IDENTITY')
        c.need(m.get('continuation_limits') == {'wall_seconds': 120, 'CPU_seconds': 30,
               'preflight_read_bytes': 4194304, 'fresh_capture_max_age_seconds': 3600,
               'original_version_metadata_max_age_seconds': 14400, 'stdout_bytes': 262144}
               and m.get('remaining_GET_split') == {'metadata': 0, 'pypdf': 0, 'companions': 4, 'total': 4}
               and m.get('allowed_wheel_media') == MEDIA, 'CONTINUATION_LIMITS')
        reads = [0]
        def read(path, ref):
            reads[0] += ref['bytes']+1; c.need(reads[0] <= 4194304, 'PREFLIGHT_READ_CAP')
            return n.read_ref(self.root, path, ref, [0])
        previous_ref = m['previous_methods_ref']
        previous_raw = read(previous_ref['path'], {k: previous_ref[k] for k in ('bytes', 'sha256')})
        previous_methods = c.json_body(previous_raw)
        c.need(c.packed(previous_methods) == previous_raw, 'PREVIOUS_METHODS_CANONICAL')
        previous = v.Collector(self.root, previous_methods, None,
                               clock=self.budget.clock, cpu=self.budget.cpu, utc=self.utc)
        _, selected, assessment, proof, _, prior_reads = previous.predecessor()
        reads[0] += prior_reads; c.need(reads[0] <= 4194304, 'PREFLIGHT_READ_CAP')
        refs = m['previous_refs']
        bodies = {name: read(v.OUTPUT+'/'+name, ref) for name, ref in refs.items()}
        terminal = c.json_body(bodies['TERMINAL.json'])
        indexed = {ref['path']: {'bytes': ref['bytes'], 'sha256': ref['sha256']} for ref in terminal['artifacts']}
        c.need(len(indexed) == len(terminal['artifacts']) and indexed ==
               {name: ref for name, ref in refs.items() if name != 'TERMINAL.json'}, 'PREVIOUS_REFSET')
        c.need(terminal.get('kind') == 'P1_TERMINAL_V1_2' and terminal.get('status') == 'FAILED_OR_UNKNOWN_NO_RETRY'
               and terminal.get('phase') == 'CACHE_THEN_FOUR_COMPANIONS' and terminal.get('reason') == 'HTTP_FRESHNESS'
               and terminal.get('installation') is False and terminal.get('package_imports') is False
               and terminal.get('extraction') is False and terminal.get('model_calls') == 0
               and terminal.get('no_retry') is True and terminal.get('prior_cumulative') == previous_methods['prior_cumulative']
               and terminal.get('previous_scope') == previous_methods['previous_scope']
               and terminal.get('previous_terminal_ref') == previous_methods['previous_refs']['TERMINAL.json'], 'PREVIOUS_FAILURE_IDENTITY')
        started = c.json_body(bodies['STARTED.json'])
        c.need(started.get('kind') == 'P1_SECOND_SUCCESSOR_STARTED_NO_RETRY'
               and started.get('methods_sha256') == previous_ref['sha256']
               and started.get('code_sha256') == PREVIOUS_CODE_SHA, 'PREVIOUS_START_BINDING')
        budget, cumulative = terminal['budget'], m['prior_cumulative']
        c.need(budget == cumulative['budget'] and budget['attempts'] == {'GET': 10, 'metadata_GET': 8, 'wheel_GET': 2}
               and budget['body_bytes_charged']['wheel'] == 2*c.CAPS['wheel_each']
               and budget['body_bytes_charged']['metadata'] == previous_methods['prior_cumulative']['budget']['body_bytes_charged']['metadata']
               and budget['outstanding_body_hold'] == 0, 'PREVIOUS_BUDGET')
        request = terminal['current_request']
        c.need(type(request) is dict and request.get('url') == selected[1]['url'] and request.get('kind') == 'wheel'
               and request.get('HTTP_status') == 200 and request.get('cap') == c.CAPS['wheel_each']
               and request.get('observed_partial_body_bytes') == 0 and request.get('partial_body_sha256') == c.sha(b''), 'PREVIOUS_FAILED_CFFI')
        physical = sum(map(len, bodies.values()))
        raw_output = sum(len(raw) for name, raw in bodies.items() if name.startswith(('metadata/', 'wheels/')))
        old = previous_methods['prior_cumulative']
        c.need(cumulative['owned_bytes'] == old['owned_bytes']+physical
               and cumulative['control_bytes'] == old['control_bytes']+physical-raw_output
               and cumulative['events'] == 20
               and terminal['cumulative_owned_write_bytes_charged_before_terminal']+len(bodies['TERMINAL.json']) == cumulative['owned_bytes'],
               'CUMULATIVE_WRITE_ACCOUNTING')
        prepared = c.json_body(bodies['selected.prepared.json'])
        c.need(prepared.get('wheels') == selected and prepared.get('provenance_scope') == proof
               and bodies['advisory-assessment.json'] == c.packed(assessment), 'PREVIOUS_REUSED_METADATA')
        cached_ref = m['cached_pypdf_ref']; cached_name = 'wheels/'+c.PYPDF['filename']
        c.need(cached_ref == {'path': v.OUTPUT+'/'+cached_name, **refs[cached_name]}
               and cached_ref['bytes'] == c.PYPDF['size'] and cached_ref['sha256'] == c.PYPDF['sha256'], 'CACHE_BINDING')
        e18 = c.json_body(bodies['events/18.json']); e19 = c.json_body(bodies['events/19.json']); e20 = c.json_body(bodies['events/20.json'])
        c.need(e18.get('kind') == 'EXACT_CACHED_PYPDF_REUSED_NO_GET' and e18.get('sequence') == 18
               and e18.get('ref') == {'path': cached_name, **refs[cached_name]}
               and e18.get('budget') == old['budget'], 'PREVIOUS_CACHE_EVENT')
        c.need(e19.get('kind') == 'REQUEST_RESERVED' and e19.get('request_kind') == 'wheel'
               and e19.get('sequence') == 19 and e19.get('url') == selected[1]['url']
               and e19.get('budget') == {'attempts': budget['attempts'],
                   'body_bytes_charged': old['budget']['body_bytes_charged'], 'outstanding_body_hold': c.CAPS['wheel_each']}
               and e20.get('kind') == 'WHEEL_RESPONSE_MEDIA' and e20.get('sequence') == 20
               and e20.get('url') == selected[1]['url'] and e20.get('HTTP_status') == 200, 'PREVIOUS_FAILED_EVENTS')
        diagnostic_ref = m['freshness_diagnostic_ref']
        diagnostic = c.json_body(read(diagnostic_ref['path'], {k: diagnostic_ref[k] for k in ('bytes', 'sha256')}))
        c.need(diagnostic.get('status') == 'HEAD_METADATA_ONLY_COMPLETE' and diagnostic.get('HEAD_attempts') == 1
               and diagnostic.get('GET_attempts') == 0 and diagnostic.get('application_body_bytes_read') == 0
               and diagnostic.get('HTTP_status') == 200 and diagnostic.get('url') == selected[1]['url']
               and diagnostic['headers'].get('Content-Length') == str(selected[1]['size']), 'FRESHNESS_DIAGNOSTIC')
        head_headers = {key.lower(): value for key, value in diagnostic['headers'].items() if value is not None}
        head_decision = freshness_decision(head_headers, 'wheel', c.utc_parse(diagnostic.get('observed_at_utc')))
        c.need(head_decision['policy'] == 'FIXED_IMMUTABLE_ARTIFACT_UNIQUE_MAX_AGE', 'FRESHNESS_PRIMARY_EVIDENCE')
        self.budget.attempts, self.budget.bytes = dict(budget['attempts']), dict(budget['body_bytes_charged'])
        self.written, self.control, self.events = cumulative['owned_bytes'], cumulative['control_bytes'], 20
        self.companion_urls = {item['url'] for item in selected[1:]}
        return bodies, selected, assessment, proof, bodies[cached_name], reads[0]

    def run(self):
        c.need(not any(path.is_symlink() for path in (self.scope, *self.scope.parents)), 'OUTPUT_ALIAS')
        c.need(not self.scope.exists(), 'SUCCESSOR_ALREADY_CONSUMED')
        bodies, selected, assessment, proof, cache, read_bytes = self.predecessor()
        self.budget.check(); self.scope.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.scope.mkdir(mode=0o700, exist_ok=False)
        fd = os.open(self.scope.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        self.write('STARTED.json', c.packed({'kind': 'P1_THIRD_SUCCESSOR_STARTED_NO_RETRY',
            'methods_sha256': c.sha(c.packed(self.methods)), 'code_sha256': c.sha(Path(__file__).read_bytes()),
            'previous_terminal_ref': self.methods['previous_refs']['TERMINAL.json'],
            'prior_cumulative': self.methods['prior_cumulative'], 'preflight_read_bytes_charged': read_bytes,
            'historical_original_caps': c.CAPS, 'cumulative_caps': CAPS,
            'additional_root_authorized_technical_GET': 1, 'time_utc': self.utc().isoformat(), 'no_retry': True}))
        status, reason, lock_ref = 'FAILED_OR_UNKNOWN_NO_RETRY', None, None
        try:
            self.phase = 'REUSE_CAPTURED_METADATA'
            for name, raw in bodies.items():
                if name.startswith('metadata/'): self.write(name, raw, False)
            self.write('ancestry.json', c.packed({'previous_scope': v.OUTPUT, 'previous_refs': self.methods['previous_refs'],
                'previous_methods_ref': self.methods['previous_methods_ref'], 'freshness_diagnostic_ref': self.methods['freshness_diagnostic_ref'],
                'all_failed_wheel_body_charges_retained': 2*c.CAPS['wheel_each'],
                'old_GET_Date_Age_unknown_not_reconstructed': True,
                'captured_advisory_provenance_reused_no_deadline_extension': True}))
            self.write('advisory-assessment.json', c.packed(assessment))
            self.write('selected.prepared.json', c.packed({'candidate': '7.0.1', 'wheels': selected,
                'provenance_scope': proof, 'ready_for_install': False}))
            self.phase = 'CACHE_THEN_FOUR_COMPANIONS'
            entries = inflated = 0
            for index, item in enumerate(selected):
                if index == 0:
                    raw = cache
                    inspection = c.inspect_wheel(raw, item['name'], item['filename'], self.budget,
                        c.CAPS['ZIP_entries']-entries, c.CAPS['ZIP_uncompressed_bytes']-inflated)
                    ref = self.write('wheels/'+item['filename'], raw, False)
                    self.event('EXACT_CACHED_PYPDF_REUSED_NO_GET', {'cache_ref': self.methods['cached_pypdf_ref'],
                        'ref': ref, 'budget': self.budget.record()})
                    origin = 'EXACT_HASHED_CACHE_REUSE_V1_2'
                else:
                    raw, _, ref = self.fetch(item['url'], 'wheel', 'wheels/'+item['filename'], item['filename'])
                    c.need(len(raw) == item['size'] and c.sha(raw) == item['sha256'], 'WHEEL_IDENTITY')
                    inspection = c.inspect_wheel(raw, item['name'], item['filename'], self.budget,
                        c.CAPS['ZIP_entries']-entries, c.CAPS['ZIP_uncompressed_bytes']-inflated)
                    origin = 'NEW_FIXED_COMPANION_GET'
                self.budget.check(); entries += inspection['entries']; inflated += inspection['uncompressed_bytes']
                c.need(entries <= c.CAPS['ZIP_entries'] and inflated <= c.CAPS['ZIP_uncompressed_bytes'], 'ZIP_AGGREGATE_CAP')
                item.update(artifact_ref=ref, inspection=inspection, acquisition_origin=origin)
            lock_ref = self.write('hashlock.json', c.packed({'kind': 'P1_FIVE_WHEEL_HASHLOCK_V1', 'schema_version': 1,
                'methods_sha256': c.sha(c.packed(self.methods)), 'target': c.TARGET, 'wheels': selected,
                'advisory_assessment_sha256': c.sha(c.packed(assessment)), 'provenance_scope': proof,
                'not_latest': True, 'ready_for_install': False, 'qualification_or_source_authority': False,
                'previous_terminal_sha256': self.methods['previous_refs']['TERMINAL.json']['sha256'],
                'cached_pypdf_ref': self.methods['cached_pypdf_ref'], 'failed_wheel_GET_charges_retained': 2*c.CAPS['wheel_each'],
                'historical_original_GET_cap': 13, 'cumulative_root_authorized_GET_cap': 14}))
            status = 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION'
        except BaseException as exc:
            reason = str(exc) if type(exc) is c.Refused else type(exc).__name__
        finally:
            self.write('TERMINAL.json', c.packed({'kind': 'P1_TERMINAL_V1_3', 'status': status,
                'phase': self.phase, 'reason': reason, 'budget': self.budget.record(), 'current_request': self.current_request,
                'artifacts': self.refs, 'previous_scope': v.OUTPUT,
                'previous_terminal_ref': self.methods['previous_refs']['TERMINAL.json'], 'prior_cumulative': self.methods['prior_cumulative'],
                'cumulative_owned_write_bytes_charged_before_terminal': self.written,
                'historical_original_GET_cap': 13, 'cumulative_root_authorized_GET_cap': 14,
                'no_retry': True, 'model_calls': 0, 'cost_usd': 0, 'installation': False,
                'package_imports': False, 'extraction': False, 'source_or_campaign_authority': False}))
        return {'status': status, 'scope': str(self.scope), 'reason': reason, 'budget': self.budget.record(),
                'hashlock_ref': lock_ref, 'model_calls': 0, 'cost_usd': 0}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--methods-sha256', required=True)
    args = parser.parse_args(); root = Path.cwd().absolute(); path = root/METHODS
    c.need(not any(p.is_symlink() for p in (path, *path.parents)), 'METHODS_ALIAS')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        c.need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'METHODS_TYPE'); raw = stream.read(65537)
    c.need(len(raw) <= 65536 and c.sha(raw) == args.methods_sha256, 'METHODS_HASH')
    methods = c.json_body(raw); c.need(c.packed(methods) == raw, 'METHODS_CANONICAL')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0)); resource.setrlimit(resource.RLIMIT_CPU, (29, 30))
    def deadline(*_): raise c.Refused('CONTINUATION_DEADLINE_SIGNAL')
    signal.signal(signal.SIGALRM, deadline); signal.signal(signal.SIGXCPU, deadline); signal.setitimer(signal.ITIMER_REAL, 120)
    result = Collector(root, methods, HTTPTransport(), signals=True).run(); signal.setitimer(signal.ITIMER_REAL, 0)
    print(c.packed(result).decode()); return 0 if result['status'].startswith('ACQUISITION_COMPLETE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
