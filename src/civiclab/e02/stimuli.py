"""Allowlisted acquisition and exact-excerpt checks for official E02 candidates.

Original US statutory text is kept distinct from journalism and from DEMO data.
Source byte integrity does not substitute for independent content/rights audit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

from ..common import atomic_json, canonical_hash, sha256_file, utc_now

BASE = 'https://www.govinfo.gov/'
CONTENT_URLS = {
    'foia': BASE + 'content/pkg/USCODE-2024-title5/html/USCODE-2024-title5-partI-chap5-subchapII-sec552.htm',
    'labor': BASE + 'content/pkg/USCODE-2024-title29/html/USCODE-2024-title29-chap7-subchapII-sec157.htm',
    'air': BASE + 'content/pkg/USCODE-2024-title42/html/USCODE-2024-title42-chap85-subchapI-partA-sec7401.htm',
}
URLS = {**CONTENT_URLS, 'policies': BASE + 'about/policies',
        **{key + '-mods': BASE + 'metadata/granule/' + url.split('/pkg/')[1].replace('/html/', '/').replace('.htm', '/mods.xml')
           for key, url in CONTENT_URLS.items()}}


class Paragraphs(HTMLParser):
    """Extract paragraph text without executing scripts or following links."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.skip = 0
        self.parts = []
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'p' and not self.skip:
            if self.depth:
                raise ValueError('nested paragraph structure is ambiguous')
            self.depth = 1
            self.parts = []
        elif tag == 'br' and self.depth:
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag == 'p' and self.depth:
            self.paragraphs.append(' '.join(''.join(self.parts).split()))
            self.depth = 0

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.parts.append(data)


def extract_excerpt(raw: bytes, prefixes: list[str]) -> str:
    if len(raw) > 2_000_000:
        raise ValueError('source exceeds bounded importer size')
    parser = Paragraphs()
    parser.feed(raw.decode('utf-8'))
    selected = []
    for prefix in prefixes:
        matches = [text for text in parser.paragraphs if text.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError('selector missing or ambiguous: ' + prefix)
        selected.append(matches[0])
    if not selected or not all(selected):
        raise ValueError('empty official excerpt')
    return '\n\n'.join(selected)


def metadata_dates(raw):
    if len(raw) > 2_000_000 or b'<!ENTITY' in raw or b'<!DOCTYPE' in raw:
        raise ValueError('unsupported metadata XML')
    root = ET.fromstring(raw)
    fields = ('dateIssued', 'dateIngested', 'recordCreationDate', 'recordChangeDate', 'lawsInEffectAsOfDate')
    return {field: [node.text for node in root.iter() if node.tag.rsplit('}', 1)[-1] == field]
            for field in fields}


def http_get(url):
    if url not in URLS.values():
        raise ValueError('source URL is not allowlisted')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    req = urllib.request.Request(url, headers={'User-Agent': 'SyntheticSocietyLab/0.1 research-source-registration'})
    with urllib.request.build_opener(NoRedirect).open(req, timeout=30) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError('source exceeds bounded importer size')
    return raw


def acquire(root, transport=http_get):
    """Recreate the exact frozen source cache, stopping on drift without replacement."""
    root = Path(root)
    manifest = json.loads((root / 'configs/e02_official_stimuli.json').read_text())
    folder = root / 'data/raw/e02_official_sources'
    folder.mkdir(parents=True, exist_ok=True)
    statuses = []
    for source in manifest['sources']:
        key = source['source_key']
        if key not in URLS or source['url'] != URLS[key]:
            raise ValueError('manifest changed allowlisted source identity')
        target = folder / source['filename']
        if not target.resolve().is_relative_to(folder.resolve()):
            raise ValueError('source filename escapes cache')
        if target.exists():
            raw = target.read_bytes()
        else:
            raw = transport(source['url'])
        digest = sha256(raw).hexdigest()
        if digest != source['sha256']:
            # Never overwrite obtained source bytes or silently change registration.
            quarantine = folder / (key + '-DRIFT-' + digest)
            if not quarantine.exists():
                quarantine.write_bytes(raw)
            raise ValueError('source drift; preserved for review: ' + key)
        if not target.exists():
            with target.open('xb') as stream:
                stream.write(raw)
        statuses.append({'source_key': key, 'sha256': digest, 'status': 'PASS'})
    result = verify_corpus(root)
    result['sources_acquired_or_verified'] = statuses
    atomic_json(root / 'data/processed/e02/official-stimulus-integrity.json', result)
    return result


def verify_corpus(root):
    root = Path(root)
    manifest = json.loads((root / 'configs/e02_official_stimuli.json').read_text())
    if manifest.get('schema_version') != 1 or not manifest.get('sources') or not manifest.get('stimuli'):
        raise ValueError('nonempty versioned corpus required')
    folder = root / 'data/raw/e02_official_sources'
    source_map = {}
    for source in manifest['sources']:
        key = source['source_key']
        if key in source_map or key not in URLS or source['url'] != URLS[key]:
            raise ValueError('duplicate or unapproved source')
        path = folder / source['filename']
        if not path.resolve().is_relative_to(folder.resolve()):
            raise ValueError('source path escapes cache')
        if sha256_file(path) != source['sha256']:
            raise ValueError('official source hash mismatch: ' + key)
        source_map[key] = source
    seen_ids, seen_texts = set(), set()
    for stimulus in manifest['stimuli']:
        if stimulus['id'] in seen_ids or stimulus['text_sha256'] in seen_texts:
            raise ValueError('duplicate stimulus identity or underlying text')
        seen_ids.add(stimulus['id']); seen_texts.add(stimulus['text_sha256'])
        source = source_map[stimulus['source_key']]
        exact = extract_excerpt((folder / source['filename']).read_bytes(), stimulus['paragraph_prefixes'])
        if exact != stimulus['text'] or sha256(exact.encode()).hexdigest() != stimulus['text_sha256']:
            raise ValueError('stimulus differs from registered original statutory paragraphs')
        if stimulus['kind'] != 'OFFICIAL_POLICY_TEXT' or stimulus['forecast_admissible'] is not False:
            raise ValueError('official-text / forecast scope mislabeled')
        if stimulus['rights_basis'] != 'US_FEDERAL_STATUTORY_TEXT_PUBLIC_DOMAIN':
            raise ValueError('unverified reuse basis')
        metadata_key = stimulus['source_key'] + '-mods'
        if metadata_key not in source_map:
            raise ValueError('source granule metadata missing')
        metadata = (folder / source_map[metadata_key]['filename']).read_bytes()
        if metadata_dates(metadata) != stimulus['source_dates']:
            raise ValueError('registered source dates differ from official metadata')
    return {'status': 'PASS_PROVENANCE_CHECKS', 'stimuli': len(seen_ids),
            'manifest_sha256': sha256_file(root / 'configs/e02_official_stimuli.json'),
            'corpus_hash': canonical_hash(manifest['stimuli']),
            'checked_at_utc': utc_now(),
            'independent_rights_and_content_audit': 'PENDING',
            'scientific_gate': 'NOT_OPENED; public original statutes are not current journalism, a representative corpus, or evidence of effects.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('acquire', 'verify'))
    parser.add_argument('--root', type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = acquire(args.root) if args.command == 'acquire' else verify_corpus(args.root)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
