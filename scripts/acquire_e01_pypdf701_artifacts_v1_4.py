"""Fresh-metadata acquisition successor. No installation or package imports.

All failed attempts remain charged. Root explicitly raised the cumulative
technical GET allowance to21, including seven fresh metadata responses.
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

PREVIOUS_CODE_SHA = '412bed35d55837a36288221ce80f3e81e156480e7b1f6d059e33d850041437b6'
PREVIOUS_CODE_BYTES = 24250
OUTPUT = 'data/processed/e01_pypdf701_build_v1/acquisition-v1_4-20261116'
METHODS = 'configs/e01_pypdf701_acquisition_v1_4_20261116.json'


def load_previous():
    import hashlib
    path = Path(__file__).absolute().with_name('acquire_e01_pypdf701_artifacts_v1_3.py')
    if any(p.is_symlink() for p in (path, *path.parents)): raise RuntimeError('PREVIOUS_CODE_ALIAS')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream: raw = stream.read(PREVIOUS_CODE_BYTES+1)
    if len(raw) != PREVIOUS_CODE_BYTES or hashlib.sha256(raw).hexdigest() != PREVIOUS_CODE_SHA:
        raise RuntimeError('PREVIOUS_CODE_HASH')
    spec = importlib.util.spec_from_file_location('p1_frozen_v1_3', path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


v = load_previous()
n, c = v.n, v.c
CAPS = {**c.CAPS, 'GET': 21, 'metadata_GET': 15, 'wheel_GET': 6}
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
    def __init__(self, clock, cpu, utc, deadline):
        super().__init__(clock, cpu)
        self.utc, self.deadline = utc, deadline
        now = utc()
        c.need(isinstance(now, c.datetime) and now.utcoffset() is not None
               and isinstance(deadline, c.datetime) and deadline.utcoffset() is not None
               and deadline.utcoffset().total_seconds() == 0
               and 0 < (deadline-now).total_seconds() <= 120, 'ABSOLUTE_UTC_DEADLINE_BINDING')
        self.prior_utc = now

    def check(self):
        super().check()
        now = self.utc()
        c.need(isinstance(now, c.datetime) and now.utcoffset() is not None, 'UTC_CLOCK_UNAVAILABLE')
        c.need(now >= self.prior_utc, 'UTC_CLOCK_REGRESSION')
        self.prior_utc = now
        c.need(now < self.deadline, 'ABSOLUTE_UTC_DEADLINE_EXPIRED')

    def begin(self, kind):
        self.check(); c.need(kind in {'wheel', 'metadata'}, 'HTTP_KIND'); key = kind+'_GET'
        c.need(self.attempts['GET'] < CAPS['GET'] and self.attempts[key] < CAPS[key] and self.held == 0, 'REQUEST_CAP')
        cap = min(CAPS[kind+'_each'], CAPS[kind+'_total']-self.bytes[kind], CAPS['network_total']-sum(self.bytes.values()))
        c.need(cap > 1, 'BODY_CAP')
        self.attempts['GET'] += 1; self.attempts[key] += 1; self.held = cap
        return cap


class Collector(v.Collector):
    def __init__(self, root, methods, transport, *, operation_deadline_utc, **kwargs):
        super().__init__(root, methods, transport, **kwargs)
        self.scope, self.transport = self.root/OUTPUT, transport
        self.budget = Budget(self.budget.clock, self.budget.cpu, self.utc, operation_deadline_utc)
        self.metadata_urls = {f'https://pypi.org/pypi/{name}/{version}/json' for name, version in c.VERSIONS.items()} | {c.API, c.PROVENANCE}

    def fetch(self, url, kind, name, filename=None):
        c.need((kind == 'wheel' and url in self.companion_urls) or
               (kind == 'metadata' and url in self.metadata_urls), 'FIXED_METADATA_OR_COMPANIONS_ONLY')
        c.validate_url(url, kind, filename)
        cap = self.budget.begin(kind); started = self.budget.clock()
        self.current_request = {'url': url, 'kind': kind, 'cap': cap}
        self.event('REQUEST_RESERVED', {**self.current_request, 'budget': self.budget.record()})
        response, body = None, bytearray()
        def remaining():
            self.budget.check()
            left = min(20-(self.budget.clock()-started), 120-(self.budget.clock()-self.budget.started),
                       (self.budget.deadline-self.budget.prior_utc).total_seconds())
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
                if kind == 'wheel':
                    c.need(type(cc_values) in {list, tuple} and len(cc_values) <= 1, 'CACHE_CONTROL_DUPLICATE_FIELD')
                    c.need(not cc_values or cc_values[0] == headers.get('cache-control'), 'CACHE_CONTROL_FIELD_BINDING')
                media = headers.get('content-type', '').split(';')[0].strip().lower()
                c.need(media in (MEDIA if kind == 'wheel' else ['application/json', 'application/vnd.pypi.integrity.v1+json']), 'CONTENT_TYPE')
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
        c.need(m.get('kind') == 'E01_PYPDF701_ACQUISITION_METHODS_V1_4' and m.get('schema_version') == 1
               and m.get('output') == OUTPUT and m.get('root_sha256') == c.sha(str(self.root).encode())
               and m.get('caps') == CAPS and m.get('historical_original_caps') == c.CAPS
               and m.get('versions') == c.VERSIONS and m.get('target') == c.TARGET
               and m.get('latest_scope') == v.v.OUTPUT and m.get('allowed_wheel_media') == MEDIA
               and m.get('policy_helper_ref') == {'path': 'scripts/acquire_e01_pypdf701_artifacts_v1_3.py',
                   'bytes': PREVIOUS_CODE_BYTES, 'sha256': PREVIOUS_CODE_SHA}, 'METHODS_IDENTITY')
        c.need(m.get('continuation_limits') == {'wall_seconds': 120, 'CPU_seconds': 30,
               'historical_read_bytes': 8388608, 'stdout_bytes': 262144,
               'maximum_initial_absolute_UTC_deadline_seconds': 120}
               and m.get('fresh_GET_split') == {'version_metadata': 5, 'advisory': 1,
                   'provenance': 1, 'companions': 4, 'pypdf_wheel': 0, 'total': 11}, 'CONTINUATION_LIMITS')
        unused = self.root/v.OUTPUT
        c.need(not unused.exists() and not unused.is_symlink(), 'UNMODELED_V1_3_STATE')
        reads = [0]
        def read(path, ref):
            self.budget.check()
            reads[0] += ref['bytes']+1; c.need(reads[0] <= 8388608, 'HISTORICAL_READ_CAP')
            raw = n.read_ref(self.root, path, ref, [0])
            self.budget.check()
            return raw
        def method(ref):
            raw = read(ref['path'], {key: ref[key] for key in ('bytes', 'sha256')})
            value = c.json_body(raw)
            c.need(c.packed(value) == raw and value.get('root_sha256') == m['root_sha256']
                   and value.get('caps') == c.CAPS, 'HISTORICAL_METHODS')
            return value
        latest_methods = method(m['latest_methods_ref'])
        middle_ref = latest_methods['previous_methods_ref']
        middle_methods = method(middle_ref)
        original_ref = m['original_methods_ref']
        original_methods = method(original_ref)
        first = middle_methods['predecessor']
        c.need(latest_methods.get('kind') == 'E01_PYPDF701_ACQUISITION_METHODS_V1_2'
               and latest_methods.get('output') == v.v.OUTPUT
               and latest_methods.get('previous_scope') == n.OUTPUT
               and middle_methods.get('kind') == 'E01_PYPDF701_ACQUISITION_METHODS_V1_1'
               and middle_methods.get('output') == n.OUTPUT
               and original_methods.get('kind') == 'E01_PYPDF701_ACQUISITION_METHODS_V1'
               and original_methods.get('output') == c.OUTPUT
               and first['scope'] == c.OUTPUT and first['methods_sha256'] == original_ref['sha256'],
               'HISTORICAL_METHOD_CHAIN')
        specifications = [
            (c.OUTPUT, first['refs'], first, original_ref, 'P1_TERMINAL_V1', 'P1_STARTED_NO_RETRY',
             'ADVISORY_PACKAGE_MISSING', n.BASE_SHA, {'GET': 6, 'metadata_GET': 6, 'wheel_GET': 0}, 0, range(1,13)),
            (n.OUTPUT, latest_methods['previous_refs'], latest_methods['prior_cumulative'], middle_ref,
             'P1_TERMINAL_V1_1', 'P1_SUCCESSOR_STARTED_NO_RETRY', 'CONTENT_TYPE', v.v.PREVIOUS_CODE_SHA,
             {'GET': 9, 'metadata_GET': 8, 'wheel_GET': 1}, 16777216, range(13,18)),
            (v.v.OUTPUT, m['latest_refs'], m['prior_cumulative'], m['latest_methods_ref'],
             'P1_TERMINAL_V1_2', 'P1_SECOND_SUCCESSOR_STARTED_NO_RETRY', 'HTTP_FRESHNESS', v.PREVIOUS_CODE_SHA,
             {'GET': 10, 'metadata_GET': 8, 'wheel_GET': 2}, 33554432, range(18,21))]
        owned = control = 0
        retained = []
        for scope, refs, cumulative, methods_ref, terminal_kind, started_kind, reason, code_sha, attempts, wheel_charge, sequences in specifications:
            bodies = {name: read(scope+'/'+name, ref) for name, ref in refs.items()}
            terminal, started = c.json_body(bodies['TERMINAL.json']), c.json_body(bodies['STARTED.json'])
            indexed = {ref['path']: {'bytes': ref['bytes'], 'sha256': ref['sha256']} for ref in terminal['artifacts']}
            c.need(len(indexed) == len(terminal['artifacts']) and indexed ==
                   {name: ref for name, ref in refs.items() if name != 'TERMINAL.json'}, 'HISTORICAL_REFSET')
            c.need(terminal.get('kind') == terminal_kind and terminal.get('status') == 'FAILED_OR_UNKNOWN_NO_RETRY'
                   and terminal.get('reason') == reason and terminal.get('no_retry') is True
                   and terminal.get('model_calls') == 0 and terminal.get('cost_usd') == 0
                   and terminal.get('package_imports') is False and terminal.get('installation') is False
                   and terminal.get('extraction') is False, 'HISTORICAL_FAILURE')
            c.need(started.get('kind') == started_kind and started.get('methods_sha256') == methods_ref['sha256']
                   and started.get('code_sha256') == code_sha, 'HISTORICAL_START_BINDING')
            c.utc_parse(started.get('time_utc'))  # Syntax only: no currentness authorization.
            budget = terminal['budget']
            metadata_bytes = sum(len(raw) for name,raw in bodies.items() if name.startswith('metadata/'))
            c.need(budget == cumulative['budget'] and budget['attempts'] == attempts
                   and budget['body_bytes_charged']['wheel'] == wheel_charge
                   and budget['body_bytes_charged']['metadata'] == metadata_bytes
                   and budget['outstanding_body_hold'] == 0, 'HISTORICAL_BUDGET')
            physical = sum(map(len, bodies.values()))
            raw_bytes = sum(len(raw) for name, raw in bodies.items() if name.startswith(('metadata/', 'wheels/')))
            owned += physical; control += physical-raw_bytes
            c.need(cumulative['owned_bytes'] == owned and cumulative['control_bytes'] == control
                   and cumulative['events'] == sequences.stop-1, 'HISTORICAL_WRITE_ACCOUNTING')
            event_names = {'events/'+str(i).zfill(2)+'.json' for i in sequences}
            c.need({name for name in refs if name.startswith('events/')} == event_names, 'HISTORICAL_EVENT_SET')
            for i in sequences:
                event = c.json_body(bodies['events/'+str(i).zfill(2)+'.json'])
                c.need(event.get('sequence') == i, 'HISTORICAL_EVENT_SEQUENCE')
            retained.append((terminal, bodies))
        first_terminal, middle_terminal, latest_terminal = [item[0] for item in retained]
        c.need(first_terminal.get('current_request') is None
               and middle_terminal.get('predecessor') == first
               and latest_terminal.get('previous_scope') == n.OUTPUT
               and latest_terminal.get('previous_terminal_ref') == latest_methods['previous_refs']['TERMINAL.json']
               and latest_terminal.get('prior_cumulative') == latest_methods['prior_cumulative'], 'HISTORICAL_TERMINAL_CHAIN')
        for terminal, expected_url in ((middle_terminal, c.PYPDF['url']),
                (latest_terminal, c.json_body(retained[-1][1]['selected.prepared.json'])['wheels'][1]['url'])):
            request = terminal.get('current_request')
            c.need(type(request) is dict and request.get('url') == expected_url and request.get('kind') == 'wheel'
                   and request.get('HTTP_status') == 200 and request.get('cap') == c.CAPS['wheel_each']
                   and request.get('observed_partial_body_bytes') == 0 and request.get('partial_body_sha256') == c.sha(b''),
                   'HISTORICAL_FAILED_BODY_HOLD')
        bodies = retained[-1][1]
        prepared = c.json_body(bodies['selected.prepared.json'])
        selected = []
        for name in c.VERSIONS:
            item = c.select_wheel(name, c.json_body(bodies['metadata/'+name+'.json']))
            item['metadata_ref'] = {'path': 'metadata/'+name+'.json', **m['latest_refs']['metadata/'+name+'.json']}
            selected.append(item)
        c.need(prepared.get('wheels') == selected and prepared.get('ready_for_install') is False, 'HISTORICAL_SELECTION')
        cached_name = 'wheels/'+c.PYPDF['filename']; cached_ref = m['cached_pypdf_ref']
        c.need(cached_ref == {'path': v.v.OUTPUT+'/'+cached_name, **m['latest_refs'][cached_name]}
               and cached_ref['bytes'] == c.PYPDF['size'] and cached_ref['sha256'] == c.PYPDF['sha256'], 'CACHE_BINDING')
        prior = m['prior_cumulative']
        self.budget.attempts = dict(prior['budget']['attempts'])
        self.budget.bytes = dict(prior['budget']['body_bytes_charged'])
        self.written, self.control, self.events = owned, control, 20
        return selected, bodies[cached_name], reads[0]

    def run(self):
        c.need(not any(path.is_symlink() for path in (self.scope, *self.scope.parents)), 'OUTPUT_ALIAS')
        c.need(not self.scope.exists(), 'SUCCESSOR_ALREADY_CONSUMED')
        old_selected, cache, read_bytes = self.predecessor()
        self.budget.check(); self.scope.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.scope.mkdir(mode=0o700, exist_ok=False)
        fd = os.open(self.scope.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        capture_started = self.utc().isoformat()
        self.write('STARTED.json', c.packed({'kind': 'P1_FRESH_METADATA_SUCCESSOR_STARTED_NO_RETRY',
            'methods_sha256': c.sha(c.packed(self.methods)), 'code_sha256': c.sha(Path(__file__).read_bytes()),
            'latest_terminal_ref': self.methods['latest_refs']['TERMINAL.json'],
            'prior_cumulative': self.methods['prior_cumulative'], 'historical_read_bytes_charged': read_bytes,
            'historical_original_caps': c.CAPS, 'cumulative_caps': CAPS,
            'unused_expired_v1_3_not_executed_or_reallocated': True, 'time_utc': capture_started,
            'absolute_operation_deadline_utc': self.budget.deadline.isoformat(), 'no_retry': True}))
        status, reason, lock_ref = 'FAILED_OR_UNKNOWN_NO_RETRY', None, None
        try:
            self.write('ancestry.json', c.packed({'latest_scope': self.methods['latest_scope'],
                'latest_methods_ref': self.methods['latest_methods_ref'], 'latest_refs': self.methods['latest_refs'],
                'all_failed_wheel_body_charges_retained': 33554432,
                'historical_currentness_used': False, 'expired_v1_3_unexecuted': True}))
            self.phase = 'FRESH_VERSION_METADATA'; selected = []; metadata_refs = []
            for old_item, (name, version) in zip(old_selected, c.VERSIONS.items()):
                raw, _, ref = self.fetch(f'https://pypi.org/pypi/{name}/{version}/json', 'metadata', 'metadata/'+name+'.json')
                item = c.select_wheel(name, c.json_body(raw))
                c.need(all(item[key] == old_item[key] for key in ('name','version','filename','url','size','sha256')), 'CHANGED_FIXED_ARTIFACT_IDENTITY')
                item['metadata_ref'] = ref; selected.append(item); metadata_refs.append(ref)
            self.phase = 'FRESH_ADVISORIES'
            raw, headers, ref = self.fetch(c.API, 'metadata', 'metadata/advisories-current.json')
            current = c.json_body(raw); next_url = c.next_advisory(headers, current, 1)
            c.need(len(current) < 100 and next_url is None, 'FRESH_ADVISORY_SINGLE_PAGE_CAP')
            assessment = n.assess_advisories([current]); assessment['fresh_current_response'] = True
            self.write('advisory-assessment.json', c.packed(assessment))
            c.need(assessment['status'] == 'NO_APPLICABLE_ISSUE_IN_CAPTURED_MAINTAINER_PAGES', 'APPLICABLE_ADVISORY')
            metadata_refs.append(ref)
            self.phase = 'FRESH_PROVENANCE'
            raw, _, ref = self.fetch(c.PROVENANCE, 'metadata', 'metadata/pypdf-provenance.json')
            proof = c.provenance_binding(c.json_body(raw)); metadata_refs.append(ref)
            receipt = {'kind': 'FRESH_SEVEN_METADATA_GETS_V1_4', 'capture_started_utc': capture_started,
                'fresh_metadata_refs': metadata_refs, 'fresh_metadata_GETs': 7,
                'prior_metadata_GETs': 8, 'metadata_GETs_cumulative': self.budget.attempts['metadata_GET'],
                'no_old_response_relabeling': True}
            c.need(receipt['metadata_GETs_cumulative'] == 15 and len(metadata_refs) == 7, 'FRESH_METADATA_COUNT')
            receipt_ref = self.write('fresh-metadata-receipt.json', c.packed(receipt))
            self.write('selected.prepared.json', c.packed({'candidate': '7.0.1', 'wheels': selected,
                'provenance_scope': proof, 'ready_for_install': False, 'fresh_metadata_receipt_ref': receipt_ref}))
            self.companion_urls = {item['url'] for item in selected[1:]}
            self.phase = 'CACHE_THEN_FOUR_COMPANIONS'; entries = inflated = 0
            for index, item in enumerate(selected):
                if index == 0:
                    raw = cache
                    inspection = c.inspect_wheel(raw, item['name'], item['filename'], self.budget,
                        c.CAPS['ZIP_entries']-entries, c.CAPS['ZIP_uncompressed_bytes']-inflated)
                    ref = self.write('wheels/'+item['filename'], raw, False)
                    self.event('EXACT_CACHED_PYPDF_REUSED_NO_GET', {'cache_ref': self.methods['cached_pypdf_ref'],
                        'ref': ref, 'budget': self.budget.record()})
                    origin = 'EXACT_HASHED_CACHE_REUSE_V1_2_FRESH_SUBJECT_RECHECK'
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
                'latest_terminal_sha256': self.methods['latest_refs']['TERMINAL.json']['sha256'],
                'cached_pypdf_ref': self.methods['cached_pypdf_ref'], 'failed_wheel_GET_charges_retained': 33554432,
                'fresh_metadata_receipt_ref': receipt_ref, 'historical_original_GET_cap': 13,
                'unused_expired_v1_3_GET_cap': 14, 'cumulative_root_authorized_GET_cap': 21}))
            self.budget.check()
            status = 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION'
        except BaseException as exc:
            reason = str(exc) if type(exc) is c.Refused else type(exc).__name__
        finally:
            self.write('TERMINAL.json', c.packed({'kind': 'P1_TERMINAL_V1_4', 'status': status,
                'phase': self.phase, 'reason': reason, 'budget': self.budget.record(), 'current_request': self.current_request,
                'artifacts': self.refs, 'latest_scope': self.methods['latest_scope'],
                'latest_terminal_ref': self.methods['latest_refs']['TERMINAL.json'], 'prior_cumulative': self.methods['prior_cumulative'],
                'cumulative_owned_write_bytes_charged_before_terminal': self.written,
                'historical_original_GET_cap': 13, 'cumulative_root_authorized_GET_cap': 21,
                'unused_expired_v1_3_not_actual_consumption': True,
                'absolute_operation_deadline_utc': self.budget.deadline.isoformat(),
                'last_observed_utc': self.budget.prior_utc.isoformat(),
                'no_retry': True, 'model_calls': 0, 'cost_usd': 0, 'installation': False,
                'package_imports': False, 'extraction': False, 'source_or_campaign_authority': False}))
        return {'status': status, 'scope': str(self.scope), 'reason': reason, 'budget': self.budget.record(),
                'hashlock_ref': lock_ref, 'model_calls': 0, 'cost_usd': 0}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--methods-sha256', required=True)
    parser.add_argument('--operation-deadline-utc', required=True)
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
    result = Collector(root, methods, HTTPTransport(), signals=True,
        operation_deadline_utc=c.utc_parse(args.operation_deadline_utc)).run()
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(c.packed(result).decode()); return 0 if result['status'].startswith('ACQUISITION_COMPLETE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
