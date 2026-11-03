"""Bounded descriptor inspection of newly authored input ONLY; actual entry disabled."""
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import zlib
import zipfile

from ..common import canonical_hash
from .national_budget import Blocked
from .full_adult_types_v1_2 import strict_json
from .f_actual_admission_v1_1 import create_fixture, require_fixture, detached, FixtureAdmission

_TOKEN = object()


def inspect_actual(*args, **kwargs):
    raise Blocked('no actual inspection authority or reviewed implementation release')


@dataclass(frozen=True)
class AuthoredBundle:
    root: Path
    source: object
    binding_json: str
    rows_json: str
    token: object

    @property
    def binding(self): return strict_json(self.binding_json)


def make_fixture(root, rows):
    rows = detached(rows)
    root = Path(root).resolve()
    root.mkdir(exist_ok=False)
    source = create_fixture(root / 'source', rows)
    binding = {'kind': 'MOCK_AUTHORED_BOOTSTRAP_ONLY', 'root': str(root), 'source_root': str(source.root),
               'source_path': str(source.path), 'source_manifest': source.manifest,
               'config_hash': canonical_hash(source.config), 'rows_hash': canonical_hash(rows)}
    text = json.dumps(binding, sort_keys=True)
    (root / 'BUNDLE.local.json').write_text(text)
    return AuthoredBundle(root, source, text, json.dumps(rows, sort_keys=True), _TOKEN)


def require_bundle(b):
    # Refuse types/paths before any source filesystem I/O; no external archive argument.
    if type(b) is not AuthoredBundle or b.token is not _TOKEN or type(b.binding_json) is not str or type(b.rows_json) is not str:
        raise Blocked('new authored bundle required')
    v = b.binding
    if type(b.root) is not type(Path.cwd()) or v.get('kind') != 'MOCK_AUTHORED_BOOTSTRAP_ONLY' or str(b.root) != v.get('root'):
        raise Blocked('bundle root differs from mint')
    a = b.source
    if type(a) is not FixtureAdmission or type(a.root) is not type(b.root) or type(a.path) is not type(b.root):
        raise Blocked('exact minted authored source fields required')
    if str(a.root) != str(b.root / 'source') or str(a.path) != str(b.root / 'source/inputs/authored-WY.zip'):
        raise Blocked('external source override refused')
    require_fixture(a)
    if v['source_manifest'] != a.manifest or v['config_hash'] != canonical_hash(a.config) or v['rows_hash'] != canonical_hash(strict_json(b.rows_json)):
        raise Blocked('bundle metadata changed')
    if (b.root / 'BUNDLE.local.json').is_symlink() or (b.root / 'BUNDLE.local.json').read_text() != b.binding_json:
        raise Blocked('original authored bundle missing or changed')
    return b


def _identity(s):
    return {'device': s.st_dev, 'inode': s.st_ino, 'bytes': s.st_size,
            'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns}


def _open_no_follow(path):
    """No-follow every lexical ancestor, then bind a single regular descriptor."""
    if not path.is_absolute() or '..' in path.parts:
        raise Blocked('absolute fixed lexical source required')
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = following
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            os.close(fd); raise Blocked('regular source only')
        return os.fdopen(fd, 'rb'), directory
    except BaseException:
        os.close(directory); raise


def _header_only(stream, member, count, archive_bytes):
    """Cap expanded output itself; ZipExtFile may preinflate beyond read(count)."""
    stream.seek(member.header_offset)
    header = stream.read(30)
    if len(header) != 30 or header[:4] != b'PK\x03\x04':
        raise Blocked('local member header')
    name_bytes, extra_bytes = struct.unpack_from('<HH', header, 26)
    if name_bytes + extra_bytes > archive_bytes:
        raise Blocked('local header bound')
    name = stream.read(name_bytes)
    if name != member.filename.encode('ascii'):
        raise Blocked('literal local member name')
    stream.seek(extra_bytes, 1)
    if stream.tell() + member.compress_size > archive_bytes:
        raise Blocked('compressed member beyond archive')
    if member.compress_type == zipfile.ZIP_STORED:
        return stream.read(count)
    inflater = zlib.decompressobj(-15)
    remaining = member.compress_size
    result = bytearray()
    while len(result) < count and remaining:
        data = stream.read(min(65536, remaining))
        if not data: raise Blocked('truncated compressed header')
        remaining -= len(data)
        result.extend(inflater.decompress(data, count - len(result)))
    return bytes(result)


def inspect_fixture(bundle, control):
    b = require_bundle(bundle)
    if control.b.binding != b.binding:
        raise Blocked('inspection control mismatch')
    state = control.snapshot()
    if state['stages'].get('INSPECT', {}).get('status') != 'PENDING' or state['failed'] or state['shutdown'] != 'ACTIVE':
        raise Blocked('durable original INSPECT reservation required')
    control.storage()
    m = b.source.manifest; c = b.source.config
    stream, directory = _open_no_follow(b.source.path)
    try:
        with stream:
            before = _identity(os.fstat(stream.fileno()))
            if before['bytes'] != m['archive_bytes'] or before['bytes'] > c['limits']['archive_body_bytes']:
                raise Blocked('archive size mismatch')
            h = hashlib.sha256(); n = 0
            while True:
                chunk = stream.read(min(65536, m['archive_bytes'] - n + 1))
                if not chunk: break
                n += len(chunk)
                if n > m['archive_bytes']: raise Blocked('archive delivered bound')
                h.update(chunk)
            if n != m['archive_bytes'] or h.hexdigest() != m['archive_sha256']:
                raise Blocked('archive bytes/hash mismatch')
            stream.seek(0)
            expected = {x['name']: x for x in m['members']}
            with zipfile.ZipFile(stream) as archive:
                members = archive.infolist()
                if len(members) != 2 or set(x.filename for x in members) != {m['person'], m['companion']} or len({x.filename.casefold() for x in members}) != 2:
                    raise Blocked('exact two literal members required')
                if sum(x.file_size for x in members) > c['limits']['state_uncompressed_bytes']:
                    raise Blocked('declared expansion bound')
                for x in members:
                    e = expected[x.filename]
                    if '/' in x.filename or '\\' in x.filename or x.flag_bits & 1 or stat.S_ISLNK(x.external_attr >> 16) or x.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) or (x.file_size, x.compress_size, x.CRC) != (e['bytes'], e['compressed_bytes'], e['crc32']):
                        raise Blocked('member metadata/compression mismatch')
                companion = expected[m['companion']]
                if companion['bytes'] > c['limits']['companion_bytes']:
                    raise Blocked('companion native bound')
                with archive.open(m['companion']) as f:
                    digest = hashlib.sha256(); expanded = 0
                    while True:
                        data = f.read(min(65536, companion['bytes'] - expanded + 1))
                        if not data: break
                        expanded += len(data)
                        if expanded > companion['bytes']: raise Blocked('companion expansion')
                        digest.update(data)
                if expanded != companion['bytes'] or digest.hexdigest() != companion['sha256']:
                    raise Blocked('companion hash mismatch')
                if m['header_bytes'] > c['limits']['line_bytes']:
                    raise Blocked('header native bound')
                # No extra byte read from CSV, no person-row iteration or full-member CRC scan.
                header = _header_only(stream, archive.getinfo(m['person']), m['header_bytes'], m['archive_bytes'])
                if len(header) != m['header_bytes'] or hashlib.sha256(header).hexdigest() != m['header_sha256'] or not header.endswith(b'\n'):
                    raise Blocked('header hash/length mismatch')
                fields = next(csv.reader(io.StringIO(header.decode('utf-8-sig')), strict=True))
                if len(fields) != 285 or len(set(fields)) != 285 or not set(c['required_fields']).issubset(fields):
                    raise Blocked('header columns mismatch')
            after = _identity(os.fstat(stream.fileno()))
            path_after = os.stat(b.source.path.name, dir_fd=directory, follow_symlinks=False)
            if not stat.S_ISREG(path_after.st_mode) or before != after or after != _identity(path_after):
                raise Blocked('descriptor/path identity changed')
    except (OSError, ValueError, zipfile.BadZipFile, UnicodeError, csv.Error, zlib.error):
        raise Blocked('bounded inspection refused') from None
    finally:
        os.close(directory)
    control.storage()
    return {'kind': 'MOCK_AUTHORED_INSPECTION', 'identity': before, 'archive_sha256': h.hexdigest(),
            'source_manifest_hash': canonical_hash(m), 'archive_bytes_hashed': n,
            'expanded_bytes': len(header) + expanded, 'header_bytes_read': len(header),
            'person_rows_read': 0, 'full_person_crc_scan_performed': False, 'GETs': 0}
