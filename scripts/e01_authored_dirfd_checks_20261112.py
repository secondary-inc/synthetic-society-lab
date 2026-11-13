"""Eight source-free checks; definitions only until reviewed harness execution."""
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock
from e01_authored_dirfd_guard_20261112 import DirectoryFdGuard,GuardRefused

ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN=ROOT/'data/raw/AUTHORED_GUARD_NEVER_OPEN'


def policy(path,flags):
    lexical=Path(os.path.abspath(path));resolved=Path(os.path.realpath(path))
    if any(p.is_relative_to(ROOT/'data') or p.name.startswith('.env') for p in (lexical,resolved)):
        raise GuardRefused('FORBIDDEN_DATA_OR_CREDENTIALS')


class DirectoryFdChecks(unittest.TestCase):
    def guard(self):return DirectoryFdGuard(policy)
    def blocked_without_effect(self,guard,operation):
        previous=guard.raw_open
        spy=Mock(side_effect=AssertionError('PROTECTED_EFFECT_MUST_NEVER_EXECUTE'))
        guard.raw_open=spy
        try:
            with self.assertRaises(GuardRefused):operation()
            spy.assert_not_called()
        finally:guard.raw_open=previous

    def test_owned_temporary_cleanup(self):
        guard=self.guard()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'data').mkdir();(root/'data/file').write_bytes(b'AUTHORED')
            fd=guard.open(root,os.O_RDONLY)
            try:
                child=guard.open('data',os.O_RDONLY,dir_fd=fd)
                try:
                    body=guard.open('file',os.O_RDONLY,dir_fd=child)
                    try:self.assertEqual(os.read(body,16),b'AUTHORED')
                    finally:guard.close(body)
                finally:guard.close(child)
            finally:guard.close(fd)
        self.assertFalse(Path(folder).exists())

    def test_two_directories_thread_local_isolation(self):
        guard=self.guard();barrier=threading.Barrier(2);errors=[];seen=[]
        with tempfile.TemporaryDirectory() as folder:
            roots=[Path(folder).resolve()/name for name in ('one','two')]
            for root in roots:root.mkdir();(root/'file').write_bytes(b'AUTHORED')
            fds=[guard.open(root,os.O_RDONLY) for root in roots];original=guard.raw_open
            def spy(*args,**kwargs):
                if args[0]=='file':
                    before=guard.event_path('file');barrier.wait(timeout=2)
                    self.assertEqual(guard.event_path('file'),before);seen.append(before)
                return original(*args,**kwargs)
            guard.raw_open=spy
            def run(fd):
                try:
                    opened=guard.open('file',os.O_RDONLY,dir_fd=fd);guard.close(opened)
                    self.assertIsNone(getattr(guard.local,'pending',None))
                except BaseException as exc:errors.append(exc)
            threads=[threading.Thread(target=run,args=(fd,)) for fd in fds]
            try:
                for t in threads:t.start()
                for t in threads:t.join(timeout=3)
                self.assertFalse(any(t.is_alive() for t in threads));self.assertEqual(errors,[])
                self.assertCountEqual(seen,[root/'file' for root in roots])
                self.assertIsNone(getattr(guard.local,'pending',None))
            finally:
                guard.raw_open=original
                for fd in fds:guard.close(fd)

    def test_unknown_fd(self):
        guard=self.guard()
        with tempfile.TemporaryDirectory() as folder:
            fd=os.open(Path(folder).resolve(),os.O_RDONLY)  # Not registered in this guard.
            try:self.blocked_without_effect(guard,lambda:guard.open('file',os.O_RDONLY,dir_fd=fd))
            finally:os.close(fd)

    def test_closed_reused_or_aliased_fd(self):
        guard=self.guard()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();one=root/'one';two=root/'two';one.mkdir();two.mkdir()
            fd=guard.open(one,os.O_RDONLY)
            os.close(fd)  # Deliberately bypass local guard; stale registry must not suffice.
            self.blocked_without_effect(guard,lambda:guard.open('file',os.O_RDONLY,dir_fd=fd))
            reused=os.open(two,os.O_RDONLY)
            try:
                if reused!=fd:os.dup2(reused,fd)
                self.blocked_without_effect(guard,lambda:guard.open('file',os.O_RDONLY,dir_fd=fd))
            finally:
                guard.close(fd)
                if reused!=fd:os.close(reused)
            fd=guard.open(one,os.O_RDONLY);moved=root/'moved';one.rename(moved);one.symlink_to(two,target_is_directory=True)
            try:self.blocked_without_effect(guard,lambda:guard.open('file',os.O_RDONLY,dir_fd=fd))
            finally:
                one.unlink();moved.rename(one);guard.close(fd)

    def test_regular_file_fd(self):
        guard=self.guard()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder).resolve()/'file';p.write_bytes(b'AUTHORED');fd=guard.open(p,os.O_RDONLY)
            try:self.blocked_without_effect(guard,lambda:guard.open('next',os.O_RDONLY,dir_fd=fd))
            finally:guard.close(fd)

    def test_forbidden_absolute_ignores_valid_dirfd_but_still_denies(self):
        guard=self.guard()
        with tempfile.TemporaryDirectory() as folder:
            fd=guard.open(Path(folder).resolve(),os.O_RDONLY)
            try:self.blocked_without_effect(guard,lambda:guard.open(FORBIDDEN,os.O_RDONLY,dir_fd=fd))
            finally:guard.close(fd)

    def test_symlink_to_forbidden_data(self):
        guard=self.guard()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'link').symlink_to(FORBIDDEN)
            fd=guard.open(root,os.O_RDONLY)
            try:self.blocked_without_effect(guard,lambda:guard.open('link',os.O_RDONLY,dir_fd=fd))
            finally:guard.close(fd)

    def test_context_restoration_and_original_raw_arguments_after_error(self):
        guard=self.guard()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();fd=guard.open(root,os.O_RDONLY);marker=object();guard.local.pending=marker
            original=guard.raw_open;seen=[]
            def fail(*args,**kwargs):
                seen.append((args,kwargs));self.assertEqual(guard.event_path('never-created'),root/'never-created')
                raise OSError('AUTHORED_OPEN_FAILURE')
            guard.raw_open=fail
            try:
                with self.assertRaises(OSError):guard.open('never-created',os.O_CREAT|os.O_WRONLY,0o640,dir_fd=fd)
                self.assertIs(guard.local.pending,marker)
                self.assertEqual(seen,[(('never-created',os.O_CREAT|os.O_WRONLY,0o640),{'dir_fd':fd})])
                self.assertFalse((root/'never-created').exists())
            finally:
                guard.raw_open=original;guard.local.pending=None;guard.close(fd)
            # An absolute permitted path ignores an unknown numeric dir_fd too.
            absolute=root/'absolute';absolute.write_bytes(b'AUTHORED')
            opened=guard.open(absolute,os.O_RDONLY,dir_fd=-123456)
            guard.close(opened)
