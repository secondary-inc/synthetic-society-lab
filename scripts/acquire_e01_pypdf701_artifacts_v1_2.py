"""Finite P1 successor: reuse accepted pypdf wheel, acquire four companions.

Preserves both failed scopes and all charges. Actual CLI is lead-only after
independent review. No installation, package import or source qualification.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import resource
import signal
import stat

PREVIOUS_CODE_SHA = '10d476ebea780a0f2726b559e35e1eb65e350dbacf867544f992560ce8e2b686'
PREVIOUS_CODE_BYTES = 22091
OUTPUT = 'data/processed/e01_pypdf701_build_v1/acquisition-v1_2-20261115'
METHODS = 'configs/e01_pypdf701_acquisition_v1_2_20261115.json'


def load_previous():
    import hashlib
    path = Path(__file__).absolute().with_name('acquire_e01_pypdf701_artifacts_v1_1.py')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RuntimeError('PREVIOUS_CODE_ALIAS')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(PREVIOUS_CODE_BYTES+1)
    if len(raw) != PREVIOUS_CODE_BYTES or hashlib.sha256(raw).hexdigest() != PREVIOUS_CODE_SHA:
        raise RuntimeError('PREVIOUS_CODE_HASH')
    spec = importlib.util.spec_from_file_location('p1_frozen_v1_1', path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


n = load_previous()
c = n.c


class MediaResponse:
    def __init__(self, response, headers):
        self.actual, self.headers, self.status = response, headers, response.status
    def read(self, size, timeout): return self.actual.read(size, timeout)
    def close(self): self.actual.close()


class WheelMediaTransport:
    def __init__(self, transport, collector): self.actual, self.collector = transport, collector
    def open(self, url, timeout):
        owner = self.collector
        c.need(url in owner.companion_urls, 'COMPANION_ONLY_NO_PYPDF_REPLAY')
        response = self.actual.open(url, timeout)
        try:
            headers = dict(response.headers)
            raw = headers.get('content-type')
            c.need(type(raw) is str and len(raw) <= 256, 'WHEEL_MEDIA_SCHEMA')
            media = raw.split(';')[0].strip().lower()
            owner.event('WHEEL_RESPONSE_MEDIA', {'url': url, 'HTTP_status': response.status,
                'raw_content_type': raw, 'normalized_media': media,
                'mapping': 'binary/octet-stream_TO_application/octet-stream' if media == 'binary/octet-stream' else 'UNCHANGED',
                'diagnostic_ref': owner.methods['mime_diagnostic_ref']})
            c.need(media in owner.methods['allowed_wheel_media'], 'UNKNOWN_WHEEL_MEDIA')
            if media == 'binary/octet-stream': headers['content-type'] = 'application/octet-stream'
            return MediaResponse(response, headers)
        except BaseException:
            response.close()
            raise


class Collector(n.Collector):
    def __init__(self, root, methods, transport, **kwargs):
        super().__init__(root, methods, transport, **kwargs)
        self.scope = self.root/OUTPUT
        self.companion_urls = set()
        self.transport = WheelMediaTransport(transport, self)

    def predecessor(self):
        m = self.methods
        c.need(m.get('kind') == 'E01_PYPDF701_ACQUISITION_METHODS_V1_2' and m.get('schema_version') == 1
               and m.get('output') == OUTPUT and m.get('root_sha256') == c.sha(str(self.root).encode())
               and m.get('caps') == c.CAPS and m.get('previous_scope') == n.OUTPUT
               and m.get('previous_code_ref') == {'path': 'scripts/acquire_e01_pypdf701_artifacts_v1_1.py',
                   'bytes': PREVIOUS_CODE_BYTES, 'sha256': PREVIOUS_CODE_SHA}, 'METHODS_IDENTITY')
        c.need(m.get('continuation_limits') == {'wall_seconds': 120, 'CPU_seconds': 30,
               'preflight_read_bytes': 4194304, 'fresh_capture_max_age_seconds': 3600,
               'original_version_metadata_max_age_seconds': 14400, 'stdout_bytes': 262144}
               and m.get('remaining_GET_split') == {'metadata': 0, 'pypdf': 0, 'companions': 4, 'total': 4}
               and m.get('allowed_wheel_media') == ['application/octet-stream', 'application/zip', 'binary/octet-stream'],
               'CONTINUATION_LIMITS')
        auxiliary_reads = [0]
        ref = m['previous_methods_ref']
        previous_raw = n.read_ref(self.root, ref['path'], {k: ref[k] for k in ('bytes', 'sha256')}, auxiliary_reads)
        previous_methods = c.json_body(previous_raw)
        c.need(c.packed(previous_methods) == previous_raw, 'PREVIOUS_METHODS_CANONICAL')
        # Frozen v1_1 independently verifies every original v1 ref and its
        # request/settlement chain; this call performs no writes or transport.
        first = n.Collector(self.root, previous_methods, None, clock=self.budget.clock,
                            cpu=self.budget.cpu, utc=self.utc)
        _, _, first_reads = first.predecessor()
        prior = m['previous_refs']
        reads = [0]
        bodies = {name: n.read_ref(self.root, n.OUTPUT+'/'+name, ref, reads) for name, ref in prior.items()}
        terminal = c.json_body(bodies['TERMINAL.json'])
        c.need(terminal.get('kind') == 'P1_TERMINAL_V1_1'
               and terminal.get('status') == 'FAILED_OR_UNKNOWN_NO_RETRY'
               and terminal.get('phase') == 'WHEELS' and terminal.get('reason') == 'CONTENT_TYPE'
               and terminal.get('installation') is False and terminal.get('package_imports') is False
               and terminal.get('extraction') is False and terminal.get('model_calls') == 0
               and terminal.get('no_retry') is True and terminal.get('predecessor') == previous_methods['predecessor'],
               'PREVIOUS_FAILURE_IDENTITY')
        indexed = {ref['path']: {'bytes': ref['bytes'], 'sha256': ref['sha256']} for ref in terminal['artifacts']}
        c.need(len(indexed) == len(terminal['artifacts']) and indexed ==
               {name: ref for name, ref in prior.items() if name != 'TERMINAL.json'}, 'PREVIOUS_REFSET')
        started = c.json_body(bodies['STARTED.json'])
        c.need(started.get('kind') == 'P1_SUCCESSOR_STARTED_NO_RETRY'
               and started.get('code_sha256') == PREVIOUS_CODE_SHA
               and started.get('methods_sha256') == ref_value(m['previous_methods_ref'], 'sha256')
               and started.get('predecessor') == previous_methods['predecessor'], 'PREVIOUS_START_BINDING')
        age = (self.utc()-c.utc_parse(started.get('time_utc'))).total_seconds()
        c.need(0 <= age <= 3600, 'SAVED_CURRENT_CAPTURE_STALE_OR_FUTURE')
        budget = terminal['budget']
        c.need(budget == m['prior_cumulative']['budget'] and budget['attempts'] == {'GET': 9, 'metadata_GET': 8, 'wheel_GET': 1}
               and budget['body_bytes_charged']['wheel'] == c.CAPS['wheel_each']
               and budget['outstanding_body_hold'] == 0, 'PREVIOUS_BUDGET')
        request = terminal['current_request']
        c.need(type(request) is dict and request.get('url') == c.PYPDF['url']
               and request.get('kind') == 'wheel' and request.get('cap') == c.CAPS['wheel_each']
               and request.get('HTTP_status') == 200 and request.get('observed_partial_body_bytes') == 0
               and request.get('partial_body_sha256') == c.sha(b''), 'PREVIOUS_FAILED_WHEEL')
        current = c.json_body(bodies['metadata/advisories-current.json'])
        c.need(type(current) is list and 0 < len(current) < 100, 'PREVIOUS_CURRENT_COVERAGE')
        assessment = n.assess_advisories([current]); assessment['fresh_current_response'] = True
        c.need(c.packed(assessment) == bodies['advisory-assessment.json']
               and assessment['status'] == 'NO_APPLICABLE_ISSUE_IN_CAPTURED_MAINTAINER_PAGES', 'PREVIOUS_ADVISORY_GATE')
        proof = c.provenance_binding(c.json_body(bodies['metadata/pypdf-provenance.json']))
        prepared = c.json_body(bodies['selected.prepared.json'])
        c.need(prepared.get('candidate') == '7.0.1' and prepared.get('provenance_scope') == proof
               and prepared.get('ready_for_install') is False, 'PREVIOUS_SELECTION')
        selected = []
        for name in c.VERSIONS:
            item = c.select_wheel(name, c.json_body(bodies['metadata/'+name+'.json']))
            item['metadata_ref'] = {'path': 'metadata/'+name+'.json', **prior['metadata/'+name+'.json']}
            selected.append(item)
        c.need(prepared.get('wheels') == selected, 'PREVIOUS_SELECTION_IDENTITY')
        # Preserve the known full failed body hold; it was settled, not refunded.
        old = previous_methods['predecessor']
        physical = sum(map(len, bodies.values()))
        metadata = sum(len(body) for name, body in bodies.items() if name.startswith('metadata/'))
        cumulative = m['prior_cumulative']
        c.need(cumulative['owned_bytes'] == old['owned_bytes']+physical
               and cumulative['control_bytes'] == old['control_bytes']+physical-metadata
               and cumulative['events'] == 17 and metadata == budget['body_bytes_charged']['metadata']
               and terminal['cumulative_owned_write_bytes_charged_before_terminal']+len(bodies['TERMINAL.json']) == cumulative['owned_bytes'],
               'CUMULATIVE_WRITE_ACCOUNTING')
        event13 = c.json_body(bodies['events/13.json']); event14 = c.json_body(bodies['events/14.json'])
        event15 = c.json_body(bodies['events/15.json']); event16 = c.json_body(bodies['events/16.json'])
        event17 = c.json_body(bodies['events/17.json'])
        previous_bytes = old['budget']['body_bytes_charged']['metadata']
        for sequence, event, url, response, record_name in ((13, event13, c.API, event14, 'metadata/advisories-current.json'),
                (15, event15, c.PROVENANCE, event16, 'metadata/pypdf-provenance.json')):
            attempt = 7 if sequence == 13 else 8
            attempts = {'GET': attempt, 'metadata_GET': attempt, 'wheel_GET': 0}
            c.need(event.get('kind') == 'REQUEST_RESERVED' and event.get('request_kind') == 'metadata'
                   and event.get('sequence') == sequence and event.get('url') == url
                   and event.get('budget') == {'attempts': attempts, 'body_bytes_charged': {'metadata': previous_bytes, 'wheel': 0},
                       'outstanding_body_hold': c.CAPS['metadata_each']}, 'PREVIOUS_REQUEST_EVENT')
            previous_bytes += prior[record_name]['bytes']
            c.need(response.get('kind') == 'RESPONSE_RECORDED' and response.get('sequence') == sequence+1
                   and response.get('url') == url and response.get('ref') == {'path': record_name, **prior[record_name]}
                   and response.get('budget') == {'attempts': attempts, 'body_bytes_charged': {'metadata': previous_bytes, 'wheel': 0},
                       'outstanding_body_hold': 0}, 'PREVIOUS_RESPONSE_EVENT')
        c.need(event17.get('kind') == 'REQUEST_RESERVED' and event17.get('request_kind') == 'wheel'
               and event17.get('sequence') == 17 and event17.get('url') == c.PYPDF['url']
               and event17.get('budget') == {'attempts': {'GET': 9, 'metadata_GET': 8, 'wheel_GET': 1},
                   'body_bytes_charged': {'metadata': previous_bytes, 'wheel': 0},
                   'outstanding_body_hold': c.CAPS['wheel_each']}, 'PREVIOUS_FAILED_RESERVATION')
        cache_ref = m['cached_pypdf_ref']
        c.need(cache_ref['bytes'] == c.PYPDF['size'] and cache_ref['sha256'] == c.PYPDF['sha256']
               and cache_ref['path'] == 'data/processed/e01_pypdf_fresh_install_20261112/'+c.PYPDF['filename'], 'CACHE_BINDING')
        cache = n.read_ref(self.root, cache_ref['path'], {k: cache_ref[k] for k in ('bytes', 'sha256')}, auxiliary_reads)
        diagnostic_ref = m['mime_diagnostic_ref']
        diagnostic_raw = n.read_ref(self.root, diagnostic_ref['path'],
                                    {k: diagnostic_ref[k] for k in ('bytes', 'sha256')}, auxiliary_reads)
        diagnostic = c.json_body(diagnostic_raw)
        c.need(diagnostic.get('status') == 'HEAD_METADATA_ONLY_COMPLETE' and diagnostic.get('HEAD_attempts') == 2
               and diagnostic.get('application_body_bytes_read') == 0 and len(diagnostic.get('observations', [])) == 2,
               'MIME_DIAGNOSTIC')
        first_head, second_head = diagnostic['observations']
        c.need(first_head.get('url') == c.PYPDF['url'] and first_head.get('HTTP_status') == 200
               and first_head.get('application_body_bytes_read') == 0
               and first_head['headers'].get('Content-Type') == 'binary/octet-stream'
               and first_head['headers'].get('Content-Length') == str(c.PYPDF['size'])
               and first_head['headers'].get('Location') is None
               and second_head.get('url') == selected[1]['url'] and second_head.get('HTTP_status') == 200
               and second_head['headers'].get('Content-Type') == 'application/octet-stream'
               and second_head['headers'].get('Content-Length') == str(selected[1]['size']), 'MIME_PRIMARY_EVIDENCE')
        total_reads = first_reads+reads[0]+auxiliary_reads[0]
        c.need(total_reads <= 4194304, 'PREFLIGHT_READ_CAP')
        self.budget.attempts, self.budget.bytes = dict(budget['attempts']), dict(budget['body_bytes_charged'])
        self.written, self.control, self.events = cumulative['owned_bytes'], cumulative['control_bytes'], 17
        self.companion_urls = {item['url'] for item in selected[1:]}
        return bodies, selected, assessment, proof, cache, total_reads

    def run(self):
        c.need(not any(path.is_symlink() for path in (self.scope, *self.scope.parents)), 'OUTPUT_ALIAS')
        c.need(not self.scope.exists(), 'SUCCESSOR_ALREADY_CONSUMED')
        bodies, selected, assessment, proof, cache, read_bytes = self.predecessor()
        self.budget.check()
        self.scope.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.scope.mkdir(mode=0o700, exist_ok=False)
        fd = os.open(self.scope.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        self.write('STARTED.json', c.packed({'kind': 'P1_SECOND_SUCCESSOR_STARTED_NO_RETRY',
            'methods_sha256': c.sha(c.packed(self.methods)), 'code_sha256': c.sha(Path(__file__).read_bytes()),
            'previous_terminal_ref': self.methods['previous_refs']['TERMINAL.json'],
            'prior_cumulative': self.methods['prior_cumulative'], 'preflight_read_bytes_charged': read_bytes,
            'time_utc': self.utc().isoformat(), 'no_retry': True}))
        status, reason, lock_ref = 'FAILED_OR_UNKNOWN_NO_RETRY', None, None
        try:
            self.phase = 'REUSE_CAPTURED_METADATA'
            for name, raw in bodies.items():
                if name.startswith('metadata/'): self.write(name, raw, False)
            self.write('ancestry.json', c.packed({'previous_scope': n.OUTPUT,
                'previous_refs': self.methods['previous_refs'], 'previous_methods_ref': self.methods['previous_methods_ref'],
                'original_predecessor': c.json_body(bodies['TERMINAL.json'])['predecessor'],
                'failed_pypdf_GET_full_body_charge_retained': c.CAPS['wheel_each'],
                'HEAD_diagnostic_ref': self.methods['mime_diagnostic_ref'],
                'old_failed_GET_Content_Type_unknown_not_reconstructed': True,
                'captured_advisory_provenance_reused_not_new_HTTP': True}))
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
                    origin = 'EXACT_HASHED_CACHE_REUSE_PREVIOUSLY_ACCEPTED_20261112'
                else:
                    raw, _, ref = self.fetch(item['url'], 'wheel', 'wheels/'+item['filename'], item['filename'])
                    c.need(len(raw) == item['size'] and c.sha(raw) == item['sha256'], 'WHEEL_IDENTITY')
                    inspection = c.inspect_wheel(raw, item['name'], item['filename'], self.budget,
                        c.CAPS['ZIP_entries']-entries, c.CAPS['ZIP_uncompressed_bytes']-inflated)
                    origin = 'NEW_FIXED_COMPANION_GET'
                self.budget.check()
                entries += inspection['entries']; inflated += inspection['uncompressed_bytes']
                c.need(entries <= c.CAPS['ZIP_entries'] and inflated <= c.CAPS['ZIP_uncompressed_bytes'], 'ZIP_AGGREGATE_CAP')
                item.update(artifact_ref=ref, inspection=inspection, acquisition_origin=origin)
            lock_ref = self.write('hashlock.json', c.packed({'kind': 'P1_FIVE_WHEEL_HASHLOCK_V1', 'schema_version': 1,
                'methods_sha256': c.sha(c.packed(self.methods)), 'target': c.TARGET, 'wheels': selected,
                'advisory_assessment_sha256': c.sha(c.packed(assessment)), 'provenance_scope': proof,
                'not_latest': True, 'ready_for_install': False, 'qualification_or_source_authority': False,
                'previous_terminal_sha256': self.methods['previous_refs']['TERMINAL.json']['sha256'],
                'cached_pypdf_ref': self.methods['cached_pypdf_ref'], 'failed_pypdf_GET_charge_retained': c.CAPS['wheel_each']}))
            status = 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION'
        except BaseException as exc:
            reason = str(exc) if type(exc) is c.Refused else type(exc).__name__
        finally:
            self.write('TERMINAL.json', c.packed({'kind': 'P1_TERMINAL_V1_2', 'status': status,
                'phase': self.phase, 'reason': reason, 'budget': self.budget.record(),
                'current_request': self.current_request, 'artifacts': self.refs,
                'previous_scope': n.OUTPUT, 'previous_terminal_ref': self.methods['previous_refs']['TERMINAL.json'],
                'prior_cumulative': self.methods['prior_cumulative'],
                'cumulative_owned_write_bytes_charged_before_terminal': self.written,
                'no_retry': True, 'model_calls': 0, 'cost_usd': 0, 'installation': False,
                'package_imports': False, 'extraction': False, 'source_or_campaign_authority': False}))
        return {'status': status, 'scope': str(self.scope), 'reason': reason,
                'budget': self.budget.record(), 'hashlock_ref': lock_ref, 'model_calls': 0, 'cost_usd': 0}


def ref_value(ref, key): return ref[key]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--methods-sha256', required=True)
    args = parser.parse_args(); root = Path.cwd().absolute(); path = root/METHODS
    c.need(not any(p.is_symlink() for p in (path, *path.parents)), 'METHODS_ALIAS')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        c.need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'METHODS_TYPE')
        raw = stream.read(65537)
    c.need(len(raw) <= 65536 and c.sha(raw) == args.methods_sha256, 'METHODS_HASH')
    methods = c.json_body(raw); c.need(c.packed(methods) == raw, 'METHODS_CANONICAL')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0)); resource.setrlimit(resource.RLIMIT_CPU, (29, 30))
    def deadline(*_): raise c.Refused('CONTINUATION_DEADLINE_SIGNAL')
    signal.signal(signal.SIGALRM, deadline); signal.signal(signal.SIGXCPU, deadline)
    signal.setitimer(signal.ITIMER_REAL, 120)
    result = Collector(root, methods, c.HTTPTransport(), signals=True).run()
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(c.packed(result).decode())
    return 0 if result['status'].startswith('ACQUISITION_COMPLETE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
