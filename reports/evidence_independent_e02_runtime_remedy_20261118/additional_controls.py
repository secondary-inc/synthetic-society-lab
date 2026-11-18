"""Independent pure counterexample; no owner, closed state, key or network."""
from pathlib import Path
import importlib.util
import json
import resource
import signal
import sys
import sysconfig
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
STDLIB = Path(sysconfig.get_path("stdlib")).resolve()


def audit(event, args):
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.fork", "os.system", "sqlite3.connect", "ctypes.dlopen"):
        raise AssertionError("REVIEWER_PURE_NO_EXTERNAL")
    if event == "open" and not isinstance(args[0], int):
        path = Path(args[0]).resolve()
        if path.name.startswith(".env") or (path.is_relative_to(ROOT / "data") and not path.is_relative_to(STDLIB)) or "SyntheticSocietyLab" in str(path):
            raise AssertionError("REVIEWER_PURE_NO_PRIVATE_STATE")


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (119, 120))
    signal.alarm(120)
    sys.addaudithook(audit)
    sys.path.insert(0, str(ROOT / "src"))
    path = ROOT / "tests/test_wrapper_canary_failure_diagnostic_v1.py"
    spec = importlib.util.spec_from_file_location("reviewed_author_controls", path)
    controls = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controls)
    # Reuse only inert authored seams; owning the fake journal reaches the real
    # finally block omitted by the supplied-journal sequence tests.
    execute = controls.client.execute_mock
    def owned_journal(*args, **kwargs):
        journal = kwargs.pop("journal")
        def close_failure():
            raise OSError("REVIEWER_JOURNAL_CLOSE_FAILURE")
        journal.close = close_failure
        with patch.object(controls.client, "_Journal", return_value=journal):
            return execute(*args, **kwargs)
    replaced = False
    with patch.object(controls.client, "execute_mock", side_effect=owned_journal):
        try:
            controls.CleanupOrder().flow()
        except OSError as error:
            replaced = str(error) == "REVIEWER_JOURNAL_CLOSE_FAILURE"
    assert replaced, "COUNTEREXAMPLE_NOT_REPRODUCED"
    print(json.dumps({"kind": "INDEPENDENT_REMEDY_ORIGINAL_EXCEPTION_COUNTEREXAMPLE_V1",
                      "runtime": sys.version.split()[0], "counterexample_reproduced": True,
                      "original_inert_RuntimeError_replaced_by_owned_journal_close_OSError": True,
                      "source": "Successor finally own_journal journal.close; inherited predecessor behavior",
                      "scope": "Pure fake journal close failure, no actual disk/owner/model interaction",
                      "normal_owner_calls": 0, "closed_inputs": 0, "network_calls": 0}))
