"""Finite reviewer subprocesses; fixed pure controls and one inert integration."""
from pathlib import Path
import hashlib
import json
import os
import resource
import selectors
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
PYTHONS = {"311": ROOT / "data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11",
           "312": ROOT / ".venv/bin/python"}


def run(label, command):
    directory = EVIDENCE / label
    directory.mkdir(exist_ok=False)
    (directory / "before.json").write_text(json.dumps({"argv": command, "environment": "Fixed clean offline environment; no inherited secrets", "wall_seconds": 900, "CPU_seconds": 600, "console_bytes_max": 65536}, indent=2))
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    environment = {"PATH": os.defpath, "PAID_API_ENABLED": "false", "MAX_SPEND_USD": "0", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    process = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    reason = None
    total = 0
    digest = hashlib.sha256()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    with (directory / "console.log").open("xb", buffering=0) as stream:
        while selector.get_map():
            if time.monotonic() - started >= 900:
                reason = "WALL_LIMIT"
                break
            for key, _ in selector.select(.1):
                body = os.read(key.fileobj.fileno(), 65536)
                if not body:
                    selector.unregister(key.fileobj)
                    continue
                total += len(body)
                if total > 65536:
                    reason = "OUTPUT_LIMIT"
                    break
                digest.update(body)
                stream.write(body)
            if reason:
                break
    if reason:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=3)
    process.stdout.close()
    selector.close()
    end = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {"label": label, "exit_code": process.returncode, "reason": reason,
              "wall_seconds": time.monotonic()-started,
              "child_CPU_seconds": end.ru_utime+end.ru_stime-usage.ru_utime-usage.ru_stime,
              "console_bytes": total, "console_sha256": digest.hexdigest()}
    (directory / "execution.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


if __name__ == "__main__":
    controls = "import sys,runpy;sys.path.insert(0," + repr(str(ROOT / "src")) + ");sys.argv=[" + repr(str(ROOT / "tests/test_wrapper_canary_failure_diagnostic_v1.py")) + "];runpy.run_path(sys.argv[0],run_name='__main__')"
    results = []
    for version in ("311", "312"):
        result = run("pure-"+version, [str(PYTHONS[version].resolve()), "-I", "-B", "-S", "-c", controls])
        results.append(result)
        assert result["exit_code"] == 0 and result["reason"] is None, "PURE_REVIEW_FAILED_INTEGRATION_NOT_RUN"
    result = run("integration-312-once", [str(PYTHONS["312"].resolve()), "-I", "-B", "-S", str(EVIDENCE / "integration_observer.py")])
    results.append(result)
    (EVIDENCE / "EXECUTIONS.json").write_text(json.dumps(results, indent=2)+"\n")
    print(json.dumps(results))
