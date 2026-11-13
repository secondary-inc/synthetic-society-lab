"""Directory-FD context for one authored test harness; no hook on import.

Preserves raw os.open arguments. Trusted local test process, not a hostile-host
sandbox. Only two verified conventional Darwin root aliases are normalized;
user-created symlink origins are refused. No /dev/fd probing or file body reads.
"""
import os
from pathlib import Path
import stat
import threading


class GuardRefused(RuntimeError):
    pass


class DirectoryFdGuard:
    def __init__(self, policy, *, raw_open=None, raw_close=None):
        self.policy=policy
        self.raw_open=os.open if raw_open is None else raw_open
        self.raw_close=os.close if raw_close is None else raw_close
        self.fstat=os.fstat
        self.local=threading.local();self.records={};self.lock=threading.RLock();self.serial=0
        self.aliases=[]
        for name,target in [('/var','/private/var'),('/tmp','/private/tmp')]:
            path=Path(name)
            if path.is_symlink() and os.path.realpath(name)==target:
                self.aliases.append((path,Path(target)))

    @staticmethod
    def identity(st):return st.st_dev,st.st_ino,st.st_mode

    def absolute(self,value):
        raw=os.fsdecode(os.fspath(value))
        if '..' in Path(raw).parts:raise GuardRefused('RAW_PARENT_TRAVERSAL')
        path=Path(os.path.abspath(raw))
        for alias,target in self.aliases:
            if path.is_relative_to(alias):return target/path.relative_to(alias)
        return path

    @staticmethod
    def no_alias(path):
        if any(p.is_symlink() for p in (path,*path.parents)):
            raise GuardRefused('ALIASED_DESCRIPTOR_ORIGIN')

    def directory(self,fd):
        if type(fd) is not int:raise GuardRefused('UNKNOWN_DIRECTORY_DESCRIPTOR')
        try:actual=self.fstat(fd)
        except OSError:raise GuardRefused('CLOSED_DIRECTORY_DESCRIPTOR') from None
        if not stat.S_ISDIR(actual.st_mode):raise GuardRefused('NON_DIRECTORY_DESCRIPTOR')
        with self.lock:record=self.records.get(fd)
        if record is None:raise GuardRefused('UNKNOWN_DIRECTORY_DESCRIPTOR')
        origin,identity,generation=record
        try:
            self.no_alias(origin)
            current=origin.stat(follow_symlinks=False)
        except OSError:raise GuardRefused('UNAVAILABLE_DIRECTORY_ORIGIN') from None
        if self.identity(actual)!=identity or self.identity(current)!=identity:
            raise GuardRefused('REUSED_OR_MOVED_DIRECTORY_DESCRIPTOR')
        if os.path.realpath(origin)!=str(origin):raise GuardRefused('ALIASED_DIRECTORY_DESCRIPTOR')
        with self.lock:
            if self.records.get(fd)!=record:raise GuardRefused('DESCRIPTOR_GENERATION_CHANGED')
        return record

    def event_path(self,value):
        raw=os.fsdecode(os.fspath(value));pending=getattr(self.local,'pending',None)
        if os.path.isabs(raw):return self.absolute(raw)  # POSIX ignores dir_fd.
        if pending is None:return self.absolute(raw)
        if type(pending) is not tuple or len(pending)!=4 or raw!=pending[0]:
            raise GuardRefused('UNBOUND_RELATIVE_OPEN_EVENT')
        _,fd,record,candidate=pending
        if self.directory(fd)!=record:raise GuardRefused('DESCRIPTOR_CHANGED_BEFORE_EFFECT')
        return candidate

    def open(self,*args,**kwargs):
        if len(args)<2:raise GuardRefused('UNBOUND_OPEN_ARGUMENTS')
        value,flags=args[:2]
        if type(flags) is not int:raise GuardRefused('UNBOUND_OPEN_FLAGS')
        raw=os.fsdecode(os.fspath(value))
        if '..' in Path(raw).parts:raise GuardRefused('RAW_PARENT_TRAVERSAL')
        fd=kwargs.get('dir_fd');record=None
        if not os.path.isabs(raw) and fd is not None:
            record=self.directory(fd)
            candidate=self.absolute(record[0]/raw)
        else:candidate=self.absolute(raw)
        # Enforce policy before calling raw_open, including effect-spy negatives.
        self.policy(candidate,flags)
        self.no_alias(candidate)
        prior=getattr(self.local,'pending',None)
        self.local.pending=(raw,fd,record,candidate) if record is not None else None
        opened=None
        try:
            # Keep the actual syscall path/flags/mode/dir_fd completely unchanged.
            opened=self.raw_open(*args,**kwargs)
            actual=self.fstat(opened)
            if stat.S_ISDIR(actual.st_mode):
                self.no_alias(candidate)
                current=candidate.stat(follow_symlinks=False)
                if self.identity(current)!=self.identity(actual):
                    raise GuardRefused('OPENED_DIRECTORY_ORIGIN_MISMATCH')
                with self.lock:
                    self.serial+=1
                    self.records[opened]=(candidate,self.identity(actual),self.serial)
            return opened
        except BaseException:
            if opened is not None:
                with self.lock:self.records.pop(opened,None)
                self.raw_close(opened)
            raise
        finally:self.local.pending=prior

    def close(self,*args,**kwargs):
        if args:
            with self.lock:self.records.pop(args[0],None)
        return self.raw_close(*args,**kwargs)
