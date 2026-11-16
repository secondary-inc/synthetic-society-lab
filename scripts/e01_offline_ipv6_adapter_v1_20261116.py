"""Narrow capability override for a separately released offline guest only.

Not a supported pip offline API, network exemption, sandbox or historical cause
diagnosis. No work occurs at import. Authored tests must use fabricated modules.
"""
import _imp
import _thread
import hashlib
import importlib
import importlib.machinery
import os
from pathlib import Path
import sys
import threading
from types import ModuleType

TARGET = 'pip._vendor.urllib3.util.connection'
PREFIX = 'pip._vendor.urllib3'
MAX_MODULES = 256
MAX_SOURCE_BYTES = 16777216
MAX_FILE_BYTES = 8388608
SOCKET_REF = {
    'bytes': 37815,
    'sha256': '7d4d4c66e6f4bcc961ab462c4f08002ca97def8713a4be1c7373bdbd970a5274'}
_ACTIVE = None
_FAILED = False


class CompatibilityRefused(RuntimeError):
    pass


def need(value, code):
    if not value:
        raise CompatibilityRefused(code)


class Owner:
    def __init__(self):
        self.pid = os.getpid()
        self.thread = threading.get_ident()
        self.poisoned = False


def single_owner(owner):
    need(os.getpid() == owner.pid and threading.get_ident() == owner.thread
         and threading.current_thread() is threading.main_thread()
         and threading.active_count() == 1 and _thread._count() == 0,
         'COMPATIBILITY_PROCESS_THREAD_OWNER')


def regular_path(path):
    path = Path(path)
    need(path.is_absolute() and '..' not in path.parts
         and not any(p.is_symlink() for p in (path, *path.parents)),
         'COMPATIBILITY_ORIGIN_ALIAS')
    need(path.is_file(), 'COMPATIBILITY_ORIGIN_NOT_FILE')
    return path


class Closure:
    """Bounded import origins; pip sources pinned, stdlib hashes recorded.

    The stdlib source hashes other than socket are observations of the bound
    runtime, not independently pinned source attestations. Unknown origins and
    nonstandard loaders are refused before their new modules execute.
    """
    def __init__(self, root, binding, reader):
        self.root, self.binding, self.reader = Path(root), binding, reader
        self.base = Path(binding['base_prefix'])/'lib/python3.12'
        self.sources, self.names = {}, {}
        self.bytes = 0
        self.previous_finders = tuple(sys.meta_path)

    def source(self, path):
        path = regular_path(path)
        key = str(path)
        if key in self.sources:
            return self.sources[key]
        relative = str(path.relative_to(self.root)) if path.is_relative_to(self.root) else None
        if relative in self.binding['pip_files']:
            ref = {'path': relative, **self.binding['pip_files'][relative]}
            absolute = False
        else:
            need(path.is_relative_to(self.base)
                 and not path.is_relative_to(self.base/'site-packages'),
                 'COMPATIBILITY_UNBOUND_IMPORT_ORIGIN')
            before = path.stat(follow_symlinks=False)
            size = before.st_size
            need(size <= MAX_FILE_BYTES, 'COMPATIBILITY_SOURCE_FILE_CAP')
            # Reader checks size, type, no aliases and stable file identity.
            # Its expected hash is obtained from this bounded runtime read.
            self.bytes += size+1
            need(self.bytes <= MAX_SOURCE_BYTES, 'COMPATIBILITY_CLOSURE_READ_CAP')
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                opened = os.fstat(stream.fileno())
                identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
                need(identity(before) == identity(opened), 'COMPATIBILITY_SOURCE_CHANGED')
                raw = stream.read(size+1)
                need(identity(opened) == identity(os.fstat(stream.fileno())),
                     'COMPATIBILITY_SOURCE_CHANGED')
            need(len(raw) == size, 'COMPATIBILITY_SOURCE_CHANGED')
            ref = {'path': key, 'bytes': size, 'sha256': hashlib.sha256(raw).hexdigest()}
            absolute = True
        self.bytes += ref['bytes']+1
        need(ref['bytes'] <= MAX_FILE_BYTES and self.bytes <= MAX_SOURCE_BYTES,
             'COMPATIBILITY_CLOSURE_READ_CAP')
        self.reader.read(ref, absolute=absolute)
        self.sources[key] = ref
        return ref

    def spec(self, name, spec):
        need(type(name) is str and len(name) <= 256 and spec is not None,
             'COMPATIBILITY_IMPORT_SPEC')
        need(len(self.names) < MAX_MODULES or name in self.names,
             'COMPATIBILITY_CLOSURE_MODULE_CAP')
        origin = spec.origin
        if origin == 'built-in':
            need(spec.loader is importlib.machinery.BuiltinImporter,
                 'COMPATIBILITY_IMPORT_LOADER')
            record = {'name': name, 'origin': origin}
        elif origin == 'frozen':
            need(spec.loader is importlib.machinery.FrozenImporter,
                 'COMPATIBILITY_IMPORT_LOADER')
            record = {'name': name, 'origin': origin}
        else:
            need(type(spec.loader) in {importlib.machinery.SourceFileLoader,
                                      importlib.machinery.ExtensionFileLoader},
                 'COMPATIBILITY_IMPORT_LOADER')
            record = {'name': name, 'origin': str(origin), 'source_ref': self.source(origin)}
        if name in self.names:
            need(self.names[name] == record, 'COMPATIBILITY_IMPORT_ORIGIN_DRIFT')
        self.names[name] = record
        return spec

    def find_spec(self, fullname, path=None, target=None):
        need(target is None, 'COMPATIBILITY_RELOAD_DENIED')
        for finder in self.previous_finders:
            found = finder.find_spec(fullname, path, target)
            if found is not None:
                return self.spec(fullname, found)
        # Preserve ordinary optional-import absence; no module code executes.
        # The attempt is still part of the bounded closure record.
        need(len(self.names) < MAX_MODULES, 'COMPATIBILITY_CLOSURE_MODULE_CAP')
        self.names[fullname] = {'name': fullname, 'origin': 'not-found'}
        raise ModuleNotFoundError(fullname)


def checked_socket(binding, reader):
    module = sys.modules.get('socket')
    need(type(module) is ModuleType and module.__name__ == 'socket',
         'COMPATIBILITY_EXACT_SOCKET_MODULE')
    path = regular_path(Path(binding['base_prefix'])/'lib/python3.12/socket.py')
    spec = module.__spec__
    need(spec is not None and spec.origin == str(path) and module.__file__ == str(path)
         and type(spec.loader) is importlib.machinery.SourceFileLoader
         and not getattr(spec, '_initializing', False), 'COMPATIBILITY_SOCKET_ORIGIN')
    reader.read({'path': str(path), **SOCKET_REF}, absolute=True)
    return module


def scoped(socket_module, initialize, check):
    """Internal core: fabricated module tests never change the real socket.

    Detected reentry is sticky even if its exception is caught. Exit-state
    checks cannot see transient drift restored before callback exit. No hostile
    callback/private-state mutation or native-thread sandbox claim is made.
    """
    global _ACTIVE, _FAILED
    need(type(socket_module) is ModuleType, 'COMPATIBILITY_EXACT_SOCKET_MODULE')
    if _ACTIVE is not None:
        _ACTIVE.poisoned = True
        _FAILED = True
        raise CompatibilityRefused('COMPATIBILITY_REENTRY')
    need(_FAILED is False, 'COMPATIBILITY_PRIOR_FAILURE_NO_RETRY')
    need(socket_module.has_ipv6 is True, 'COMPATIBILITY_ORIGINAL_NOT_TRUE')
    owner = Owner()
    single_owner(owner)
    _ACTIVE = owner
    original = socket_module.has_ipv6
    primary = None
    try:
        socket_module.has_ipv6 = False
        result = initialize()
        need(owner.poisoned is False and _FAILED is False,
             'COMPATIBILITY_STICKY_FAILURE')
        single_owner(owner)
        need(_ACTIVE is owner and socket_module.has_ipv6 is False,
             'COMPATIBILITY_SCOPE_DRIFT')
        check(result)
        return result
    except BaseException as exc:
        primary = exc
        owner.poisoned = True
        _FAILED = True
        raise
    finally:
        socket_module.has_ipv6 = original
        _ACTIVE = None
        if socket_module.has_ipv6 is not original:
            _FAILED = True
            if primary is None:
                raise CompatibilityRefused('COMPATIBILITY_RESTORE_FAILED')


def initialize_offline(root, binding, reader):
    """Called once after original guards are active and pip root is bound.

    Import parents and transitive consumers run within the temporary declaration.
    Their bounded closure is recorded; this is intentionally not a claim that
    only one consumer sees the override. No pip command is run here.
    """
    global _FAILED
    socket_module = checked_socket(binding, reader)
    if _ACTIVE is not None:
        _ACTIVE.poisoned = True
        _FAILED = True
        raise CompatibilityRefused('COMPATIBILITY_REENTRY')
    owner = Owner()
    single_owner(owner)
    need(not _imp.lock_held(), 'COMPATIBILITY_IMPORT_IN_PROGRESS')
    need(len(sys.modules) <= 1024, 'COMPATIBILITY_INITIAL_MODULE_CAP')
    before = dict(sys.modules)
    need(not any(name == PREFIX or name.startswith(PREFIX+'.') for name in before),
         'COMPATIBILITY_VENDOR_PRELOADED')
    need(not any(getattr(getattr(module, '__spec__', None), '_initializing', False)
                 for module in before.values()), 'COMPATIBILITY_IMPORT_IN_PROGRESS')
    closure = Closure(root, binding, reader)
    # Verify known loaded parents before allowing their import semantics.
    for name in ('pip', 'pip._vendor'):
        if name in before:
            need(type(before[name]) is ModuleType, 'COMPATIBILITY_PARENT_MODULE')
            closure.spec(name, before[name].__spec__)
    connection_path = Path(root)/binding['pip_root']/'_vendor/urllib3/util/connection.py'
    closure.source(connection_path)
    finder_stack = tuple(sys.meta_path)
    _imp.acquire_lock()
    try:
        single_owner(owner)
        sys.meta_path.insert(0, closure)
        def initialize():
            return importlib.import_module(TARGET)
        def check(module):
            need(type(module) is ModuleType and sys.modules.get(TARGET) is module
                 and module.__file__ == str(connection_path)
                 and module.socket is socket_module
                 and module.HAS_IPV6 is False
                 and getattr(module._has_ipv6, '__globals__', None) is module.__dict__
                 and module._has_ipv6.__code__.co_filename == str(connection_path),
                 'COMPATIBILITY_VENDOR_RESULT')
            need(sys.modules.get('socket') is socket_module
                 and tuple(sys.meta_path) == (closure,)+finder_stack,
                 'COMPATIBILITY_IMPORT_STATE_DRIFT')
            need(all(sys.modules.get(name) is old for name, old in before.items()),
                 'COMPATIBILITY_PREEXISTING_MODULE_DRIFT')
            new = {name: value for name, value in sys.modules.items() if name not in before}
            need(len(new) <= MAX_MODULES, 'COMPATIBILITY_CLOSURE_MODULE_CAP')
            for name, value in new.items():
                need(type(value) is ModuleType and not getattr(value.__spec__, '_initializing', False),
                     'COMPATIBILITY_UNFINISHED_MODULE')
                closure.spec(name, value.__spec__)
        scoped(socket_module, initialize, check)
        need(socket_module.has_ipv6 is True, 'COMPATIBILITY_RESTORE_FAILED')
        return {'kind': 'E01_OFFLINE_IPV6_COMPATIBILITY_RECEIPT_V1',
                'original_has_ipv6': True, 'temporary_has_ipv6': False,
                'restored_has_ipv6': True, 'vendor_cached_ipv6': False,
                'target_module': TARGET, 'socket_ref': {'path': str(Path(binding['base_prefix'])/'lib/python3.12/socket.py'), **SOCKET_REF},
                'import_closure': [closure.names[name] for name in sorted(closure.names)],
                'closure_logical_read_bytes': closure.bytes,
                'network_permissions_changed': False,
                'parent_transitive_consumers_may_observe_false': True}
    except BaseException:
        _FAILED = True
        raise
    finally:
        # Do not silently repair unexpected finder-stack drift.
        if sys.meta_path and sys.meta_path[0] is closure:
            sys.meta_path.pop(0)
        _imp.release_lock()
