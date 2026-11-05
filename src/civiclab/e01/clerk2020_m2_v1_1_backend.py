"""Authored fake-PDF byte fixture and private bounded format projection.

The container is deliberately not a real PDF. No pypdf import, filesystem access,
native-resource probe, candidate parser or actual source adapter exists here.
"""
from civiclab.e01.clerk2020_m2_v1_1_contracts import (
    Counters, Refused, canonical, decode, exact, hex64, identifier, require, sha,
)

MAGIC = b'%CLERK_M2_V1_1_AUTHORED_FAKE_PDF_ONLY\n'
FLAGS = ('encrypted', 'warning', 'active', 'malformed')
PAGE_FIELDS = frozenset({
    'source_id', 'source_sha256', 'physical_pdf_page_1_based',
    'printed_page_label_UNKNOWN', 'full_extracted_text_utf8_sha256',
    'full_extracted_text_characters', 'full_extracted_text_utf8_bytes',
    'line_count', 'blank_line_count', 'line_length_min_max',
    'non_ascii_character_count', 'snippet_windows', 'retained_byte_intervals',
    'omitted_text_utf8_bytes', 'retained_whole_page',
    'source_role_UNKNOWN_UNREVIEWED', 'layout_quality_UNKNOWN_UNVERIFIED',
})


def authored_fake_pdf(source_id, pages, **flags):
    require(identifier(source_id) and source_id.startswith('DEMO_'))
    require(type(pages) is list and 1 <= len(pages) <= 100
            and all(type(t) is str and len(t) <= 40000 for t in pages))
    require(set(flags) <= set(FLAGS) and all(type(v) is bool for v in flags.values()))
    body = {'label': 'MOCK', 'source_id': source_id, 'pages': pages,
            **{k: flags.get(k, False) for k in FLAGS}}
    raw = MAGIC + canonical(body)
    require(len(raw) <= 1048576)
    return raw


def _clip(raw, start, end):
    # A continuation byte cannot start a code point. End moves left until the
    # selected interval is independently valid UTF-8; at most three bytes move.
    while start < end and raw[start] & 0xC0 == 0x80:
        start += 1
    while end > start:
        try:
            raw[start:end].decode('utf8')
            return start, end
        except UnicodeDecodeError:
            end -= 1
    return start, start


def page_projection(source_id, source_hash, index, text):
    require(identifier(source_id) and source_id.startswith('DEMO_') and hex64(source_hash))
    require(type(index) is int and 1 <= index <= 100)
    require(type(text) is str and len(text) <= 40000)
    try:
        raw = text.encode('utf8')
    except UnicodeError:
        raise Refused() from None
    require(len(raw) <= 160000)
    n = len(raw)
    center = max(0, (n - 512) // 2)
    selected = [_clip(raw, a, b) for a, b in
                [(0, min(n, 256)), (max(0, n - 256), n), (center, min(n, center + 512))]]
    merged = []
    for a, b in sorted(selected):
        if a == b:
            continue
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    original = [r[:] for r in merged]
    lines = text.splitlines()
    row = {
        'source_id': source_id, 'source_sha256': source_hash,
        'physical_pdf_page_1_based': index, 'printed_page_label_UNKNOWN': 'UNKNOWN',
        'full_extracted_text_utf8_sha256': sha(raw),
        'full_extracted_text_characters': len(text), 'full_extracted_text_utf8_bytes': n,
        'line_count': len(lines), 'blank_line_count': sum(not s.strip() for s in lines),
        'line_length_min_max': [min(map(len, lines), default=0), max(map(len, lines), default=0)],
        'non_ascii_character_count': sum(ord(c) > 127 for c in text),
        'source_role_UNKNOWN_UNREVIEWED': 'UNKNOWN', 'layout_quality_UNKNOWN_UNVERIFIED': 'UNKNOWN',
    }
    while True:
        windows = []
        for i, (a, b) in enumerate(merged):
            if a == b:
                continue
            windows.append({'kind': 'POSITIONAL_MERGED', 'utf8_start': a, 'utf8_end': b,
                            'utf8_sha256': sha(raw[a:b]), 'text': raw[a:b].decode('utf8'),
                            'truncated': [a, b] != original[i]})
        retained = sum(w['utf8_end'] - w['utf8_start'] for w in windows)
        result = {**row, 'snippet_windows': windows,
                  'retained_byte_intervals': [[w['utf8_start'], w['utf8_end']] for w in windows],
                  'omitted_text_utf8_bytes': n - retained, 'retained_whole_page': retained == n}
        exact(result, PAGE_FIELDS)
        if len(canonical(result)) <= 2048:
            require(retained <= 1024)
            return result
        require(any(b > a for a, b in merged))  # Mandatory metadata never dropped.
        i = max(range(len(merged)), key=lambda j: merged[j][1] - merged[j][0])
        a, b = merged[i]
        merged[i] = list(_clip(raw, a, b - 1))


def inspect_authored(documents):
    require(type(documents) is list and len(documents) == 2
            and all(type(x) is bytes and x.startswith(MAGIC) and len(x) <= 1048576 for x in documents))
    require(sum(map(len, documents)) <= 2097152)
    projected, ids = [], set()
    total_chars = total_utf8 = 0
    for raw, expected in zip(documents, (81, 38)):
        doc = decode(raw[len(MAGIC):], 1048576)
        exact(doc, {'label', 'source_id', 'pages', *FLAGS})
        require(doc['label'] == 'MOCK' and identifier(doc['source_id'])
                and doc['source_id'].startswith('DEMO_') and doc['source_id'] not in ids)
        require(all(type(doc[k]) is bool and doc[k] is False for k in FLAGS))
        require(type(doc['pages']) is list and len(doc['pages']) == expected)
        ids.add(doc['source_id'])
        pages = []
        for i, text in enumerate(doc['pages'], 1):
            row = page_projection(doc['source_id'], sha(raw), i, text)
            total_chars += row['full_extracted_text_characters']
            total_utf8 += row['full_extracted_text_utf8_bytes']
            require(total_chars <= 4760000 and total_utf8 <= 19040000)
            pages.append(row)
        projected.append({'source_id': doc['source_id'], 'source_sha256': sha(raw),
                          'source_bytes': len(raw), 'pages': pages})
    private = {'label': 'MOCK', 'backend': 'AUTHORED_FAKE_PDF_ONLY', 'documents': projected,
               'retained_full_document': all(p['retained_whole_page'] for d in projected for p in d['pages'])}
    public = {'label': 'MOCK', 'backend': 'AUTHORED_FAKE_PDF_ONLY', 'page_counts': [81, 38],
              'text_characters': total_chars, 'text_utf8_bytes': total_utf8,
              'omitted_utf8_bytes': sum(p['omitted_text_utf8_bytes'] for d in projected for p in d['pages']),
              'unknown_role_layout_pages': 119, 'candidate_or_vote_records_parsed': 0,
              'actual_source_access': False, 'source_adoption': False, 'model_calls': 0, 'cost_usd': 0}
    provenance = {'label': 'MOCK', 'policy': 'M2_V1_1', 'source_hashes': [sha(x) for x in documents],
                  'actual_runtime_identity': None, 'actual_backend': None, 'actual_authority': None}
    out = {'inspection_projection.local.json': canonical(private),
           'inspection_diagnostics.json': canonical(public),
           'inspection_provenance.local.json': canonical(provenance)}
    require(len(out['inspection_projection.local.json']) <= 251904
            and len(out['inspection_diagnostics.json']) <= 8192
            and len(out['inspection_provenance.local.json']) <= 2048
            and sum(map(len, out.values())) <= 262144)
    return out


def actual_backend(*args, **kwargs):
    raise Refused()


class MockInspection:
    """One authored source job; pending effects settle conservatively on error.

    No external source authority is represented. Memory snapshots are consumed
    once with explicit source/backend/page reservation semantics for fixtures.
    """
    def __init__(self, counters=None):
        require(counters is None or type(counters) is Counters)
        self.counters = Counters() if counters is None else counters
        self.used = False
        self.effects = []

    def run(self, documents, crash):
        require(not self.used)
        self.used = True
        try:
            require(type(documents) is list and len(documents) == 2
                    and all(type(x) is bytes and x.startswith(MAGIC) for x in documents))
            snapshots = tuple(documents)
            amounts = {'source_jobs': 1, 'source_read_attempts': 2,
                       'source_read_bytes': 859913, 'backend_attempts': 2,
                       'page_extractions': 119}
            self.counters.transition('allocate', amounts)
            self.counters.transition('precharge', {'source_jobs': 1})
            for raw, pages in zip(snapshots, [81, 38]):
                require(len(raw) <= 1048576)
                self.counters.transition('reserve', {'source_read_attempts': 1,
                                                     'source_read_bytes': len(raw) + 1})
                crash('source.reserve')
                self.effects.append({'effect': 'AUTHORED_MEMORY_SNAPSHOT', 'sha256': sha(raw), 'bytes': len(raw)})
                crash('source.effect')
                self.counters.settle('source_read_attempts', 1, 1)
                self.counters.settle('source_read_bytes', len(raw) + 1, len(raw))
                self.counters.transition('reserve', {'backend_attempts': 1, 'page_extractions': pages})
            crash('backend.reserved')
            out = inspect_authored(list(snapshots))
            crash('backend.effect')
            self.counters.settle('backend_attempts', 2, 2)
            self.counters.settle('page_extractions', 119, 119)
            return out
        except BaseException:
            self.counters.stop_unknown()
            raise
