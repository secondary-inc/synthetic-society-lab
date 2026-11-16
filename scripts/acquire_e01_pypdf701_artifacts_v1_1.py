"""Narrow P1 successor, preserving the failed v1 and its cumulative charges.

Import is inert. All network and artifact inspection reuse the hash-bound v1.
No extraction, installation, inference or source qualification is performed.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import resource
import signal
import stat

BASE_PATH = Path(__file__).absolute().with_name('acquire_e01_pypdf701_artifacts_v1.py')
BASE_SHA = '6a8c9ec9826b3f16c8a9cd11b6f9d7991d0dbe65b136d2fed05b74330223a9cc'


def load_base():
    import hashlib
    if any(p.is_symlink() for p in (BASE_PATH, *BASE_PATH.parents)):
        raise RuntimeError('BASE_ALIAS')
    fd = os.open(BASE_PATH, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as source:
        raw = source.read(31925)
    if len(raw) != 31924 or hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise RuntimeError('BASE_HASH')
    spec = importlib.util.spec_from_file_location('e01_p1_frozen_v1', BASE_PATH)
    module = importlib.util.module_from_spec(spec)
    # Execute the verified bytes, rather than reopening a replaceable path.
    exec(compile(raw, str(BASE_PATH), 'exec'), module.__dict__)
    return module


c = load_base()
OUTPUT = 'data/processed/e01_pypdf701_build_v1/acquisition-v1_1-20261115'
METHODS = 'configs/e01_pypdf701_acquisition_v1_1_20261115.json'


def normalized_range(raw, declared_name):
    """Only numeric comma-AND grammar; exact declared package prefix is allowed."""
    c.need(type(raw) is str and 0 < len(raw) <= 256, 'UNKNOWN_RANGE')
    value = raw.strip()
    if re.match(r'[A-Za-z]', value):
        c.need(value.startswith(declared_name), 'RANGE_PACKAGE_MISMATCH')
        value = value[len(declared_name):].strip()
        c.need(bool(value) and value[0] in '<>=!', 'UNKNOWN_RANGE')
    # The frozen comparator validates all clauses, not a permissive prefix.
    c.matches(value, c.VERSIONS['pypdf'])
    return value


def assess_advisories(pages):
    """Conservatively assess every row; label ambiguity cannot discard a range."""
    result = []
    ids = set()
    for page in pages:
        c.need(type(page) is list and len(page) <= 100, 'ADVISORY_SCHEMA')
        for advisory in page:
            c.need(type(advisory) is dict and advisory.get('state') == 'published', 'ADVISORY_SCHEMA')
            ident = advisory.get('ghsa_id')
            c.need(type(ident) is str and re.fullmatch(r'GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}', ident), 'ADVISORY_SCHEMA')
            c.need(ident not in ids, 'DUPLICATE_ADVISORY')
            ids.add(ident)
            c.utc_parse(advisory.get('published_at'))
            c.utc_parse(advisory.get('updated_at'))
            c.need('withdrawn_at' in advisory, 'ADVISORY_SCHEMA')
            withdrawn = advisory['withdrawn_at']
            if withdrawn is not None:
                c.utc_parse(withdrawn)
            vulnerabilities = advisory.get('vulnerabilities')
            c.need(type(vulnerabilities) is list and 1 <= len(vulnerabilities) <= 32, 'ADVISORY_SCHEMA')
            rows = []
            for vuln in vulnerabilities:
                c.need(type(vuln) is dict and type(vuln.get('package')) is dict, 'ADVISORY_SCHEMA')
                package = vuln['package']
                name, ecosystem = package.get('name'), package.get('ecosystem')
                c.need(type(name) is str and name in {'pypdf', 'PyPDF2', 'pypi'}
                       and type(ecosystem) is str and ecosystem in {'pip', 'pypi'}, 'UNKNOWN_PACKAGE_LABEL')
                raw = vuln.get('vulnerable_version_range')
                parsed = normalized_range(raw, name)
                affected = c.matches(parsed, c.VERSIONS['pypdf'])
                c.need('patched_versions' in vuln and type(vuln['patched_versions']) in {str, type(None)}, 'ADVISORY_SCHEMA')
                patch = vuln['patched_versions']
                parsed_patch = None
                if patch:
                    parsed_patch = patch.strip()
                    if re.match(r'^[0-9]', parsed_patch):
                        parsed_patch = '==' + parsed_patch
                    parsed_patch = normalized_range(parsed_patch, name)
                    c.need(not (affected and c.matches(parsed_patch, c.VERSIONS['pypdf'])), 'INCONSISTENT_ADVISORY')
                rows.append({'package': dict(package), 'range': raw, 'normalized_range': parsed,
                             'patched_versions': patch, 'normalized_patched_versions': parsed_patch,
                             'candidate_affected_conservatively': affected,
                             'label_uncertain': name != 'pypdf' or ecosystem != 'pip',
                             'withdrawn': withdrawn is not None})
            # One exact primary-source distribution distinction. The saved
            # advisory itself has the pypdf fix and a separate PyPDF2 row.
            if ident == 'GHSA-4vvm-4w3v-6mr8':
                pair = [(r['package'], r['range'], r['patched_versions']) for r in rows]
                expected = [({'ecosystem': 'pip', 'name': 'pypdf'}, '<= 3.8.1', '>=3.9.0'),
                            ({'ecosystem': 'pip', 'name': 'PyPDF2'}, '>=2.2.0', '')]
                description = advisory.get('description')
                c.need(pair == expected and type(description) is str and
                       'It is recommended to upgrade to `pypdf>=3.9.0`. PyPDF2 users should migrate to pypdf.' in description,
                       'DISTRIBUTION_EVIDENCE_MISMATCH')
                rows[1]['candidate_distribution_excluded'] = True
                rows[1]['exclusion_reason'] = 'Distinct PyPDF2 distribution; exact paired pypdf row and maintainer migration instruction govern pypdf candidate.'
            for row in rows:
                row['candidate_affected'] = row['candidate_affected_conservatively'] and not row.get('candidate_distribution_excluded', False)
            result.append({'ghsa_id': ident, 'published_at': advisory['published_at'],
                           'updated_at': advisory['updated_at'], 'assessments': rows})
    c.need(bool(result), 'EMPTY_ADVISORY_COVERAGE')
    blocked = any(row['candidate_affected'] and not row['withdrawn']
                  for advisory in result for row in advisory['assessments'])
    return {'candidate': '7.0.1', 'not_latest': True,
            'policy': 'Every row assessed; exact GHSA-4vvm-4w3v-6mr8 paired primary-source distribution distinction only. No invented upper bounds.',
            'status': 'BLOCKED_APPLICABLE_ADVISORY' if blocked else 'NO_APPLICABLE_ISSUE_IN_CAPTURED_MAINTAINER_PAGES',
            'coverage': 'Captured bounded maintainer pages only; not proof of absence of vulnerabilities.',
            'advisories': result}


class ContinuationBudget(c.Budget):
    def check(self):
        now, cpu = self.clock(), self.cpu()
        c.need(now >= self.prior and cpu >= self.prior_cpu, 'CLOCK_REGRESSION')
        self.prior, self.prior_cpu = now, cpu
        c.need(now - self.started < 120 and cpu - self.initial_cpu < 30, 'CONTINUATION_RESOURCE_LIMIT')


def read_ref(root, relative, ref, counter):
    c.need(type(relative) is str and relative and not Path(relative).is_absolute()
           and '..' not in Path(relative).parts and str(Path(relative)) == relative, 'INPUT_PATH')
    c.need(type(ref) is dict and set(ref) == {'bytes', 'sha256'} and type(ref['bytes']) is int
           and 0 <= ref['bytes'] <= 1048576 and type(ref['sha256']) is str
           and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'INPUT_REF')
    path = root / relative
    c.need(not any(p.is_symlink() for p in (path, *path.parents))
           and stat.S_ISREG(path.stat().st_mode), 'INPUT_ALIAS_OR_TYPE')
    counter[0] += ref['bytes'] + 1
    c.need(counter[0] <= 1048576, 'PREDECESSOR_READ_CAP')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        c.need(stat.S_ISREG(info.st_mode) and info.st_size == ref['bytes'], 'INPUT_SIZE')
        raw = source.read(ref['bytes'] + 1)
    c.need(len(raw) == ref['bytes'] and c.sha(raw) == ref['sha256'], 'INPUT_HASH')
    return raw


class Collector(c.Collector):
    def __init__(self, root, methods, transport, **kwargs):
        super().__init__(root, methods, transport, **kwargs)
        self.scope = self.root / OUTPUT
        self.stage_signals, self.signals = self.signals, False
        self.budget = ContinuationBudget(self.budget.clock, self.budget.cpu)

    def event(self, kind, details):
        details = dict(details)
        if kind == 'REQUEST_RESERVED':
            c.need(details.get('kind') in {'metadata', 'wheel'} and 'request_kind' not in details, 'REQUEST_KIND')
            details['request_kind'] = details.pop('kind')
        c.need('kind' not in details and 'sequence' not in details, 'EVENT_KEY_COLLISION')
        c.need(self.events < c.CAPS['journal_events'], 'JOURNAL_CAP')
        self.events += 1
        self.write('events/' + str(self.events).zfill(2) + '.json',
                   c.packed({**details, 'sequence': self.events, 'kind': kind}))

    def fetch(self, *args, **kwargs):
        # Frozen transport/parser checks remain unchanged. The separate
        # successor timer bounds the whole request and the remaining stage.
        self.budget.check()
        if self.stage_signals:
            signal.setitimer(signal.ITIMER_REAL, min(20, 120 - (self.budget.clock() - self.budget.started)))
        try:
            return super().fetch(*args, **kwargs)
        finally:
            if self.stage_signals:
                signal.setitimer(signal.ITIMER_REAL, max(.001, 120 - (self.budget.clock() - self.budget.started)))

    def predecessor(self):
        m = self.methods
        c.need(m.get('kind') == 'E01_PYPDF701_ACQUISITION_METHODS_V1_1' and m.get('schema_version') == 1
               and m.get('versions') == c.VERSIONS and m.get('target') == c.TARGET
               and m.get('caps') == c.CAPS and m.get('output') == OUTPUT
               and m.get('base_code_sha256') == BASE_SHA
               and m.get('root_sha256') == c.sha(str(self.root).encode()), 'METHODS_IDENTITY')
        c.need(m.get('continuation_limits') == {'wall_seconds': 120, 'CPU_seconds': 30,
               'predecessor_read_bytes': 1048576, 'stdout_bytes': 262144,
               'cached_metadata_max_age_seconds': 14400}, 'CONTINUATION_LIMITS')
        c.need(m.get('remaining_GET_split') == {'metadata': 2, 'advisory': 1,
               'provenance': 1, 'wheel': 5, 'total': 7}, 'REMAINING_GET_SPLIT')
        p = m['predecessor']
        c.need(p['scope'] == c.OUTPUT and p['events'] == 12, 'PREDECESSOR_IDENTITY')
        expected_names = {'STARTED.json', 'TERMINAL.json', 'metadata/advisories-1.json'}
        expected_names.update('metadata/' + name + '.json' for name in c.VERSIONS)
        expected_names.update('events/' + str(i).zfill(2) + '.json' for i in range(1, 13))
        c.need(set(p['refs']) == expected_names, 'PREDECESSOR_REFSET')
        reads = [0]
        bodies = {name: read_ref(self.root, p['scope'] + '/' + name, ref, reads)
                  for name, ref in p['refs'].items()}
        terminal = c.json_body(bodies['TERMINAL.json'])
        started = c.json_body(bodies['STARTED.json'])
        c.need(terminal.get('kind') == 'P1_TERMINAL_V1' and terminal.get('status') == 'FAILED_OR_UNKNOWN_NO_RETRY'
               and terminal.get('phase') == 'ADVISORIES' and terminal.get('reason') == 'ADVISORY_PACKAGE_MISSING'
               and terminal.get('current_request') is None and terminal.get('no_retry') is True
               and terminal.get('installation') is False and terminal.get('package_imports') is False
               and terminal.get('extraction') is False and terminal.get('model_calls') == 0, 'PREDECESSOR_TERMINAL')
        c.need(started.get('kind') == 'P1_STARTED_NO_RETRY' and started.get('methods_sha256') == p['methods_sha256']
               and started.get('code_sha256') == BASE_SHA and started.get('caps') == c.CAPS
               and started.get('root_sha256') == m['root_sha256'], 'PREDECESSOR_STARTED')
        # Both clocks come from real UTC, not the document filename date.
        age = (self.utc() - c.utc_parse(started.get('time_utc'))).total_seconds()
        c.need(0 <= age <= 14400, 'CACHED_METADATA_FRESHNESS')
        indexed = {r['path']: {'bytes': r['bytes'], 'sha256': r['sha256']} for r in terminal['artifacts']}
        c.need(len(indexed) == len(terminal['artifacts']) and indexed ==
               {n: r for n, r in p['refs'].items() if n != 'TERMINAL.json'}, 'PREDECESSOR_INDEX')
        budget = terminal['budget']
        c.need(budget == p['budget'] and budget['attempts'] == {'GET': 6, 'metadata_GET': 6, 'wheel_GET': 0}
               and budget['body_bytes_charged']['wheel'] == 0 and budget['outstanding_body_hold'] == 0,
               'PREDECESSOR_BUDGET')
        metadata_bytes = sum(len(raw) for name, raw in bodies.items() if name.startswith('metadata/'))
        c.need(budget['body_bytes_charged']['metadata'] == metadata_bytes, 'PREDECESSOR_BODY_TOTAL')
        total = sum(map(len, bodies.values()))
        c.need(p['owned_bytes'] == total and p['control_bytes'] == total - metadata_bytes, 'PREDECESSOR_WRITE_TOTAL')
        previous = 0
        for i in range(1, 7):
            reserved = c.json_body(bodies['events/' + str(2*i-1).zfill(2) + '.json'])
            response = c.json_body(bodies['events/' + str(2*i).zfill(2) + '.json'])
            url = f'https://pypi.org/pypi/{list(c.VERSIONS)[i-1]}/{list(c.VERSIONS.values())[i-1]}/json' if i < 6 else c.API
            c.need(reserved.get('sequence') == 2*i-1 and reserved.get('kind') == 'metadata'
                   and reserved.get('url') == url and reserved.get('cap') == c.CAPS['metadata_each']
                   and response.get('sequence') == 2*i and response.get('kind') == 'RESPONSE_RECORDED'
                   and response.get('url') == url, 'PREDECESSOR_EVENT')
            ref = response['ref']
            c.need(indexed.get(ref['path']) == {'bytes': ref['bytes'], 'sha256': ref['sha256']}, 'PREDECESSOR_RESPONSE_REF')
            attempts = {'GET': i, 'metadata_GET': i, 'wheel_GET': 0}
            c.need(reserved['budget'] == {'attempts': attempts, 'body_bytes_charged': {'metadata': previous, 'wheel': 0},
                   'outstanding_body_hold': c.CAPS['metadata_each']}, 'PREDECESSOR_RESERVATION')
            previous += ref['bytes']
            c.need(response['budget'] == {'attempts': attempts, 'body_bytes_charged': {'metadata': previous, 'wheel': 0},
                   'outstanding_body_hold': 0}, 'PREDECESSOR_SETTLEMENT')
        # Frozen control flow assesses only after next_advisory has returned
        # None, or after fetching page2. Six total GETs exclude the latter.
        pages = [c.json_body(bodies['metadata/advisories-1.json'])]
        c.need(type(pages[0]) is list and 0 < len(pages[0]) < 100, 'PREDECESSOR_ADVISORY_COVERAGE')
        self.budget.attempts = dict(budget['attempts'])
        self.budget.bytes = dict(budget['body_bytes_charged'])
        self.written, self.control, self.events = total, total-metadata_bytes, 12
        return bodies, pages, reads[0]

    def run(self):
        c.need(not any(p.is_symlink() for p in (self.scope, *self.scope.parents)), 'OUTPUT_ALIAS')
        c.need(not self.scope.exists(), 'SUCCESSOR_ALREADY_CONSUMED')
        bodies, pages, reads = self.predecessor()
        self.budget.check()
        self.scope.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.scope.mkdir(mode=0o700, exist_ok=False)
        fd = os.open(self.scope.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.write('STARTED.json', c.packed({'kind': 'P1_SUCCESSOR_STARTED_NO_RETRY',
            'methods_sha256': c.sha(c.packed(self.methods)), 'base_code_sha256': BASE_SHA,
            'code_sha256': c.sha(Path(__file__).read_bytes()), 'predecessor': self.methods['predecessor'],
            'predecessor_read_bytes_charged': reads, 'time_utc': self.utc().isoformat(),
            'cumulative_caps': c.CAPS, 'separate_continuation_wall_CPU_seconds': [120, 30], 'no_retry': True}))
        status, reason, lock_ref = 'FAILED_OR_UNKNOWN_NO_RETRY', None, None
        try:
            self.phase = 'CACHED_METADATA'
            for name, raw in bodies.items():
                if name.startswith('metadata/'):
                    self.write(name, raw, False)
            self.write('ancestry.json', c.packed({'predecessor': self.methods['predecessor'],
                'legacy_event_kind_finding_preserved': True,
                'old_first_page_complete_derived_from_pinned_control_flow_not_retained_headers': True,
                'old_advisories_diagnosis_only_not_current_security': True,
                'five_package_metadata_bodies_dated_identity_evidence_not_fresh_HTTP': True}))
            selected = []
            for name in c.VERSIONS:
                item = c.select_wheel(name, c.json_body(bodies['metadata/' + name + '.json']))
                item['metadata_ref'] = next(r for r in self.refs if r['path'] == 'metadata/' + name + '.json')
                selected.append(item)
            self.phase = 'ADVISORIES'
            diagnosis = assess_advisories(pages)
            self.write('advisory-diagnosis-predecessor.json', c.packed(diagnosis))
            raw, headers, _ = self.fetch(c.API, 'metadata', 'metadata/advisories-current.json')
            fresh = c.json_body(raw)
            next_url = c.next_advisory(headers, fresh, 1)
            c.need(len(fresh) < 100 and next_url is None, 'FRESH_ADVISORY_SINGLE_PAGE_CAP')
            assessment = assess_advisories([fresh])
            assessment['fresh_current_response'] = True
            self.write('advisory-assessment.json', c.packed(assessment))
            c.need(assessment['status'] != 'BLOCKED_APPLICABLE_ADVISORY', 'APPLICABLE_ADVISORY')
            self.phase = 'PROVENANCE'
            raw, _, ref = self.fetch(c.PROVENANCE, 'metadata', 'metadata/pypdf-provenance.json')
            proof = c.provenance_binding(c.json_body(raw))
            self.write('selected.prepared.json', c.packed({'candidate': '7.0.1', 'wheels': selected,
                'provenance_ref': ref, 'provenance_scope': proof, 'ready_for_install': False}))
            self.phase = 'WHEELS'
            entries = inflated = 0
            for item in selected:
                raw, _, ref = self.fetch(item['url'], 'wheel', 'wheels/' + item['filename'], item['filename'])
                c.need(len(raw) == item['size'] and c.sha(raw) == item['sha256'], 'WHEEL_IDENTITY')
                self.budget.check()
                inspection = c.inspect_wheel(raw, item['name'], item['filename'], self.budget,
                    c.CAPS['ZIP_entries']-entries, c.CAPS['ZIP_uncompressed_bytes']-inflated)
                self.budget.check()
                entries += inspection['entries']
                inflated += inspection['uncompressed_bytes']
                c.need(entries <= c.CAPS['ZIP_entries'] and inflated <= c.CAPS['ZIP_uncompressed_bytes'], 'ZIP_AGGREGATE_CAP')
                item.update(artifact_ref=ref, inspection=inspection)
            lock_ref = self.write('hashlock.json', c.packed({'kind': 'P1_FIVE_WHEEL_HASHLOCK_V1', 'schema_version': 1,
                'methods_sha256': c.sha(c.packed(self.methods)), 'target': c.TARGET, 'wheels': selected,
                'advisory_assessment_sha256': c.sha(c.packed(assessment)), 'provenance_scope': proof,
                'not_latest': True, 'ready_for_install': False, 'qualification_or_source_authority': False,
                'predecessor_terminal_sha256': self.methods['predecessor']['refs']['TERMINAL.json']['sha256']}))
            status = 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION'
        except BaseException as exc:
            reason = str(exc) if type(exc) is c.Refused else type(exc).__name__
        finally:
            self.write('TERMINAL.json', c.packed({'kind': 'P1_TERMINAL_V1_1', 'status': status,
                'phase': self.phase, 'reason': reason, 'budget': self.budget.record(), 'current_request': self.current_request,
                'artifacts': self.refs, 'predecessor': self.methods['predecessor'], 'no_retry': True,
                'cumulative_owned_write_bytes_charged_before_terminal': self.written,
                'model_calls': 0, 'cost_usd': 0, 'installation': False, 'package_imports': False,
                'extraction': False, 'source_or_campaign_authority': False}))
        return {'status': status, 'scope': str(self.scope), 'reason': reason, 'budget': self.budget.record(),
                'hashlock_ref': lock_ref, 'model_calls': 0, 'cost_usd': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--methods-sha256', required=True)
    args = parser.parse_args()
    root, path = Path.cwd().absolute(), Path.cwd().absolute() / METHODS
    c.need(not any(p.is_symlink() for p in (path, *path.parents)), 'METHODS_ALIAS')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as source:
        c.need(stat.S_ISREG(os.fstat(source.fileno()).st_mode), 'METHODS_TYPE')
        raw = source.read(65537)
    c.need(len(raw) <= 65536 and c.sha(raw) == args.methods_sha256, 'METHODS_HASH')
    methods = c.json_body(raw)
    c.need(raw == c.packed(methods), 'METHODS_NONCANONICAL')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (29, 30))
    def deadline(*_):
        raise c.Refused('CONTINUATION_DEADLINE_SIGNAL')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.setitimer(signal.ITIMER_REAL, 120)
    result = Collector(root, methods, c.HTTPTransport(), signals=True).run()
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(c.packed(result).decode())
    return 0 if result['status'].startswith('ACQUISITION_COMPLETE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
