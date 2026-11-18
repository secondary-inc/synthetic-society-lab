"""Native deadline regression with an inert admission boundary and no owner/key."""
from pathlib import Path
import signal
import subprocess
import sys
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HardDeadlineTests(unittest.TestCase):
    def test_main_alarm_cannot_be_swallowed_by_python_cleanup(self):
        launcher = ROOT / "scripts/launch_e02_slot46_v2_20261118.py"
        child = textwrap.dedent("""
            import signal, sys, time, types
            from pathlib import Path
            path = Path(sys.argv[1])
            ns = {'__name__': '_inert_entry', '__file__': str(path)}
            exec(compile(path.read_bytes(), str(path), 'exec'), ns)
            ns['read_exact'] = lambda *a, **k: {}
            def forbidden(*a, **k):
                raise AssertionError('owner/key/transport boundary reached')
            ns['_make_owner'] = ns['_credential'] = ns['_make_transport'] = forbidden
            client = types.ModuleType('civiclab.e02.wrapper_crossmodel_slot46_v2_client')
            def stubborn_admission(*a):
                print('ENTERED_INERT_ADMISSION', flush=True)
                stop = time.monotonic() + 0.75
                while time.monotonic() < stop:
                    try:
                        time.sleep(0.01)
                    except BaseException:
                        print('PYTHON_EXCEPTION_CAUGHT', flush=True)
                raise AssertionError('survived wall deadline')
            client.validate_release = stubborn_admission
            client.execute = forbidden
            for name in ('civiclab', 'civiclab.e02'):
                module = types.ModuleType(name)
                module.__path__ = []
                sys.modules[name] = module
            sys.modules[client.__name__] = client
            native_timer = signal.setitimer
            def scaled_timer(which, seconds):
                assert which == signal.ITIMER_REAL and seconds in (0, 240)
                if seconds:
                    print('REQUESTED_WALL_SECONDS=240', flush=True)
                return native_timer(which, 0.05 if seconds else 0)
            signal.setitimer = scaled_timer
            sys.argv = [str(path), '--packet-sha256', '0'*64,
                        '--release-sha256', '0'*64]
            ns['main']()
        """)
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-S", "-c", child, str(launcher)],
            capture_output=True, text=True, timeout=5, check=False,
        )
        self.assertEqual(result.returncode, -signal.SIGALRM, result.stderr)
        self.assertIn("REQUESTED_WALL_SECONDS=240", result.stdout)
        self.assertIn("ENTERED_INERT_ADMISSION", result.stdout)
        self.assertNotIn("PYTHON_EXCEPTION_CAUGHT", result.stdout)


if __name__ == "__main__":
    unittest.main()
