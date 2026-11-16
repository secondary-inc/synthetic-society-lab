"""Pure fixed-fixture wheel validation and bounded read-only source.

No installer/tool/payload import, execution, extraction or filesystem operation.
The supported subset is deliberately the five-member generated fixture, not a
general wheel installer. Private-state mutation and hostile concurrency are out
of scope; returned payloads are immutable bytes, never writable buffer views.
"""
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import re
import stat
import struct
import zipfile

FILENAME = 'ssl_fixture_payload-1.0.0-py3-none-any.whl'
DIST = 'ssl_fixture_payload-1.0.0.dist-info/'
PAYLOAD = 'ssl_fixture_payload/__init__.py'
MEMBERS = frozenset({PAYLOAD, DIST+'METADATA', DIST+'WHEEL', DIST+'entry_points.txt', DIST+'RECORD'})
MAX_ARCHIVE = 16384
MAX_ENTRIES = 32
MAX_INFLATION = 32768
MAX_MEMBER = 8192
_SEAL = object()


class WheelRefused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(value, code):
    if not value: raise WheelRefused(code)


def _digest(raw): return hashlib.sha256(raw).hexdigest()


class ReadBudget:
    """Shared monotone logical-read budget; exhaustion is sticky.

    Validation charges input hashing, compressed archive reads and each declared
    decompressed member before reading it. All token streams share this budget.
    Caller owns any wider run authority; this object does not grant execution.
    """
    __slots__ = ('_limit', '_used', '_failed')
    def __init__(self, limit):
        need(type(limit) is int and 0 <= limit <= 67108864, 'READ_LIMIT')
        self._limit, self._used, self._failed = limit, 0, False
    @property
    def limit(self): return self._limit
    @property
    def used(self): return self._used
    @property
    def failed(self): return self._failed
    def _reserve(self, amount):
        need(type(amount) is int and amount >= 0, 'READ_AMOUNT')
        need(not self._failed, 'READ_BUDGET_FAILED')
        if amount > self._limit-self._used:
            self._failed = True
            raise WheelRefused('READ_BUDGET_EXHAUSTED')
        self._used += amount


class ReadOnlyWheelStream:
    """Named seekable file-like object, not a mutable BytesIO subclass.

    No writable buffer protocol, mutable getbuffer, descriptor or public data
    setter. read/readinto return/copy bytes outward only. Context close never
    masks a primary exception. It is usable as a stdlib ZipFile source only;
    actual PyPA compatibility is not established by this component.
    """
    __slots__ = ('_raw', '_name', '_budget', '_position', '_closed')
    def __init__(self, raw, name, budget):
        need(type(raw) is bytes and type(name) is str and name == FILENAME, 'STREAM_BINDING')
        need(type(budget) is ReadBudget, 'READ_BUDGET_TYPE')
        budget._reserve(0)
        self._raw, self._name, self._budget = raw, name, budget
        self._position, self._closed = 0, False
    @property
    def name(self): return self._name
    @property
    def closed(self): return self._closed
    def _check(self):
        if self._closed: raise ValueError('CLOSED_WHEEL_STREAM')
    def readable(self): self._check(); return True
    def seekable(self): self._check(); return True
    def writable(self): self._check(); return False
    def tell(self): self._check(); return self._position
    def seek(self, offset, whence=0):
        self._check()
        need(type(offset) is int and type(whence) is int and whence in (0,1,2), 'SEEK_ARGUMENT')
        position = offset + (0 if whence == 0 else self._position if whence == 1 else len(self._raw))
        need(0 <= position <= len(self._raw), 'SEEK_RANGE')
        self._position = position
        return position
    def read(self, size=-1):
        self._check()
        need(type(size) is int and size >= -1, 'READ_SIZE')
        count = len(self._raw)-self._position
        if size != -1: count = min(count,size)
        self._budget._reserve(count)
        result = self._raw[self._position:self._position+count]
        self._position += count
        return result
    def readinto(self, destination):
        self._check()
        view = memoryview(destination)
        if view.readonly: raise TypeError('READINTO_REQUIRES_WRITABLE_DESTINATION')
        view = view.cast('B')
        count = min(len(view),len(self._raw)-self._position)
        self._budget._reserve(count)
        view[:count] = self._raw[self._position:self._position+count]
        self._position += count
        return count
    def getvalue(self):
        self._check(); self._budget._reserve(len(self._raw)); return self._raw
    def write(self, *_): raise io.UnsupportedOperation('READ_ONLY_WHEEL_SOURCE')
    def writelines(self, *_): raise io.UnsupportedOperation('READ_ONLY_WHEEL_SOURCE')
    def truncate(self, *_): raise io.UnsupportedOperation('READ_ONLY_WHEEL_SOURCE')
    def getbuffer(self, *_): raise io.UnsupportedOperation('NO_MUTABLE_WHEEL_BUFFER')
    def fileno(self): raise io.UnsupportedOperation('NO_WHEEL_DESCRIPTOR')
    def detach(self): raise io.UnsupportedOperation('NO_DETACHABLE_WHEEL_BUFFER')
    def flush(self): self._check()
    def close(self): self._closed = True
    def __enter__(self): self._check(); return self
    def __exit__(self, *_): self.close()


class _ValidatedWheel:
    __slots__ = ('_raw','_hash','_members','_budget')
    def __init__(self, seal, raw, hash_value, members, budget):
        need(seal is _SEAL, 'VALIDATION_SEAL')
        object.__setattr__(self,'_raw',raw)
        object.__setattr__(self,'_hash',hash_value)
        object.__setattr__(self,'_members',members)
        object.__setattr__(self,'_budget',budget)
    def __setattr__(self, *_): raise AttributeError('READ_ONLY_VALIDATION_TOKEN')
    @property
    def filename(self): return FILENAME
    @property
    def sha256(self): return self._hash
    @property
    def archive_size(self): return len(self._raw)
    @property
    def members(self): return self._members
    @property
    def read_bytes_used(self): return self._budget.used
    def open(self): return ReadOnlyWheelStream(self._raw,FILENAME,self._budget)


def _directory(raw):
    end = raw.rfind(b'PK\x05\x06',max(0,len(raw)-65557))
    need(end >= 0 and end+22 == len(raw), 'ZIP_EOCD')
    disk,cd_disk,count_disk,count,size,offset,comment = struct.unpack_from('<4H2IH',raw,end+4)
    need(disk == cd_disk == comment == 0 and count_disk == count and 0 < count <= MAX_ENTRIES
         and offset+size == end, 'ZIP_LAYOUT')
    cursor,seen,declared = offset,0,0
    folded,local_offsets,entries = set(),set(),[]
    while cursor < end:
        need(cursor+46 <= end and raw[cursor:cursor+4] == b'PK\x01\x02','ZIP_DIRECTORY')
        version,flags,compression = struct.unpack_from('<3H',raw,cursor+6)
        crc,compressed,uncompressed = struct.unpack_from('<3I',raw,cursor+16)
        n,e,c = struct.unpack_from('<3H',raw,cursor+28)
        disk_start = struct.unpack_from('<H',raw,cursor+34)[0]
        attributes,local_offset = struct.unpack_from('<2I',raw,cursor+38)
        record_end = cursor+46+n+e+c
        need(record_end <= end,'ZIP_DIRECTORY')
        need(version in (10,20) and not flags & ~0x800 and compression in (0,8)
             and disk_start == e == c == 0,'ZIP_TYPE_OR_FEATURE')
        need(compressed <= MAX_ARCHIVE and uncompressed <= MAX_MEMBER,'MEMBER_SIZE_CAP')
        declared += uncompressed
        need(declared <= MAX_INFLATION,'INFLATION_CAP')
        name_bytes = raw[cursor+46:cursor+46+n]
        need(0 < n <= 240 and all(32 <= b < 127 for b in name_bytes),'ZIP_PATH')
        name = name_bytes.decode('ascii')
        directory = name.endswith('/')
        clean = name[:-1] if directory else name
        need(not name.startswith('/') and '\\' not in name and ':' not in name
             and all(p not in {'','.','..'} for p in clean.split('/')),'ZIP_PATH')
        need(clean.casefold() not in folded,'ZIP_DUPLICATE')
        folded.add(clean.casefold())
        kind = stat.S_IFMT(attributes >> 16)
        need(kind in (0,stat.S_IFDIR,stat.S_IFREG),'ZIP_TYPE_OR_FEATURE')
        need(not (kind == stat.S_IFDIR and not directory)
             and not (kind == stat.S_IFREG and directory),'ZIP_TYPE_ALIAS')
        if directory:
            need(clean in {'ssl_fixture_payload',DIST[:-1]} and uncompressed == 0,'DIRECTORY_SUBSET')
        else:
            need(name in MEMBERS,'MEMBER_SUBSET')
            need(not (attributes >> 16) & 0o111,'EXECUTABLE_MEMBER')
        need(local_offset not in local_offsets and local_offset+30 <= offset,'ZIP_LOCAL_ALIAS')
        local_offsets.add(local_offset)
        entries.append((local_offset,name_bytes,version,flags,compression,crc,compressed,uncompressed))
        cursor = record_end; seen += 1
        need(seen <= MAX_ENTRIES,'ZIP_DIRECTORY')
    need(cursor == end and seen == count,'ZIP_DIRECTORY')
    spans = []
    for local,name_bytes,version,flags,compression,crc,compressed,uncompressed in entries:
        need(raw[local:local+4] == b'PK\x03\x04','ZIP_LOCAL_HEADER')
        local_version,local_flags,local_compression = struct.unpack_from('<3H',raw,local+4)
        local_crc,local_compressed,local_uncompressed = struct.unpack_from('<3I',raw,local+14)
        local_n,local_e = struct.unpack_from('<2H',raw,local+26)
        payload_end = local+30+local_n+local_e+compressed
        need(local_version == version and (local_flags,local_compression,local_crc,
             local_compressed,local_uncompressed) == (flags,compression,crc,compressed,uncompressed)
             and local_n == len(name_bytes) and local_e == 0 and payload_end <= offset
             and raw[local+30:local+30+local_n] == name_bytes,'ZIP_LOCAL_HEADER')
        need(compression != 0 or compressed == uncompressed,'ZIP_LOCAL_HEADER')
        spans.append((local,payload_end))
    spans.sort()
    need(all(left[1] <= right[0] for left,right in zip(spans,spans[1:])), 'ZIP_LOCAL_ALIAS')
    return count


def _metadata(bodies):
    metadata = BytesParser().parsebytes(bodies[DIST+'METADATA'])
    wheel = BytesParser().parsebytes(bodies[DIST+'WHEEL'])
    for key,value in (('Metadata-Version','2.1'),('Name','ssl_fixture_payload'),
                      ('Version','1.0.0'),('Requires-Python','>=3.10')):
        need(metadata.get_all(key) == [value], 'METADATA_IDENTITY')
    need(not metadata.get_all('Requires-Dist'), 'METADATA_DEPENDENCY')
    for key,value in (('Wheel-Version','1.0'),('Root-Is-Purelib','true'),('Tag','py3-none-any')):
        need(wheel.get_all(key) == [value], 'WHEEL_IDENTITY')
    need(bodies[DIST+'entry_points.txt'] == b'[console_scripts]\nfixture-cli = ssl_fixture_payload:main\n',
         'ENTRYPOINT_SUBSET')


def validate_wheel(raw, *, expected_sha256, filename, budget):
    """Validate the exact fixed generated-fixture subset, returning a sealed view.

    Primary stdlib CRC/parser/hash failures propagate unchanged. No catch block
    converts failures to success or resets budget. No filesystem hashing sink.
    """
    need(type(raw) is bytes, 'IMMUTABLE_BYTES_REQUIRED')
    need(type(filename) is str and filename == FILENAME, 'FILENAME_BINDING')
    need(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_sha256), 'HASH_BINDING')
    need(type(budget) is ReadBudget, 'READ_BUDGET_TYPE')
    need(0 < len(raw) <= MAX_ARCHIVE, 'ARCHIVE_SIZE_CAP')
    budget._reserve(len(raw))
    need(_digest(raw) == expected_sha256, 'ARCHIVE_HASH')
    count = _directory(raw)
    bodies,member_rows,folded,all_names = {},[],set(),set()
    declared = 0
    with ReadOnlyWheelStream(raw,filename,budget) as stream:
        with zipfile.ZipFile(stream,mode='r') as archive:
            infos = archive.infolist()
            need(len(infos) == count, 'ZIP_DIRECTORY')
            for info in infos:
                name = info.filename
                clean = name[:-1] if info.is_dir() else name
                need(name == info.orig_filename and 0 < len(name.encode()) <= 240
                     and all(32 <= ord(c) < 127 for c in name) and not name.startswith('/')
                     and '\\' not in name and ':' not in name
                     and all(p not in {'','.','..'} for p in clean.split('/')), 'ZIP_PATH')
                need(clean.casefold() not in folded, 'ZIP_DUPLICATE')
                folded.add(clean.casefold()); all_names.add(clean)
                kind = stat.S_IFMT(info.external_attr >> 16)
                need(kind in (0,stat.S_IFDIR,stat.S_IFREG) and not info.flag_bits & ~0x800
                     and not info.extra and info.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),
                     'ZIP_TYPE_OR_FEATURE')
                need(not (kind == stat.S_IFDIR and not info.is_dir())
                     and not (kind == stat.S_IFREG and info.is_dir()), 'ZIP_TYPE_ALIAS')
                need(0 <= info.file_size <= MAX_MEMBER, 'MEMBER_SIZE_CAP')
                declared += info.file_size
                need(declared <= MAX_INFLATION, 'INFLATION_CAP')
                if info.is_dir():
                    need(clean in {'ssl_fixture_payload',DIST[:-1]} and info.file_size == 0, 'DIRECTORY_SUBSET')
                else:
                    need(name in MEMBERS, 'MEMBER_SUBSET')
                    need(not (info.external_attr >> 16) & 0o111, 'EXECUTABLE_MEMBER')
            file_names = {info.filename for info in infos if not info.is_dir()}
            need(file_names == MEMBERS, 'MEMBER_SET')
            need(not any('/'.join(name.split('/')[:i]) in file_names
                for name in all_names for i in range(1,len(name.split('/')))), 'ZIP_PARENT_ALIAS')
            for info in infos:
                if info.is_dir(): continue
                budget._reserve(info.file_size)
                with archive.open(info,'r') as member:
                    body = member.read(info.file_size)
                    need(len(body) == info.file_size and member.read(1) == b'', 'MEMBER_SIZE')
                bodies[info.filename] = body
                member_rows.append((info.filename,len(body),_digest(body)))
    _metadata(bodies)
    seen = set()
    for row in csv.reader(io.StringIO(bodies[DIST+'RECORD'].decode('utf-8'),newline=''),strict=True):
        need(len(row) == 3 and row[0] not in seen, 'RECORD_UNIQUE_SCHEMA')
        name,hash_text,size_text = row
        need(name in bodies, 'RECORD_EXTRA_NAME')
        seen.add(name)
        if name == DIST+'RECORD':
            need(hash_text == size_text == '', 'RECORD_SELF_EXCEPTION')
        else:
            need(re.fullmatch(r'0|[1-9][0-9]{0,9}',size_text) is not None
                 and int(size_text) == len(bodies[name]), 'RECORD_SIZE')
            expected = 'sha256='+base64.urlsafe_b64encode(hashlib.sha256(bodies[name]).digest()).rstrip(b'=').decode('ascii')
            need(hash_text == expected, 'RECORD_HASH')
    need(seen == set(bodies), 'RECORD_MISSING_NAME')
    return _ValidatedWheel(_SEAL,raw,expected_sha256,tuple(sorted(member_rows)),budget)
