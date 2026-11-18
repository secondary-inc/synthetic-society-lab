"""Recorded FEC-A01 child invocation; one fixed source and private output."""
from pathlib import Path
import hashlib
import json
import os
import resource
import signal
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "data/processed/e01_fec2020_candidate_actual_20261118_01"
SOURCE = ROOT / "data/raw/e01_fec2020_workbook_20261118/federalelections2020.xlsx"
PARSER = ROOT / "src/civiclab/e01/fec2020_parser_v1.py"
CONTRACT = ROOT / "configs/e01_fec2020_senate_mapping_v1.json"
OUTPUT = SCOPE / "candidate-audit.local.json"
MIME = Path("/private/etc/apache2/mime.types")


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (119, 120))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4194304, 4194304))
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(120)
    os.environ["OPENPYXL_LXML"] = "False"
    os.environ["OPENPYXL_DEFUSEDXML"] = "False"
    runtime = Path(sys.base_prefix).resolve()
    for path in (SCOPE, SOURCE, PARSER, CONTRACT):
        assert not any(p.is_symlink() for p in (path, *path.parents))
    claim = SCOPE / "reader-claim.local.json"
    with claim.open("xb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(b'{"reader_calls_reserved":1,"retries":0}\n')
        stream.flush()
        os.fsync(stream.fileno())
    reads = [0]
    def guard(event, args):
        if event.startswith("socket.") or event in {
            "subprocess.Popen", "os.fork", "os.posix_spawn", "os.system", "sqlite3.connect"
        }:
            raise RuntimeError("FEC_A01_NO_NETWORK_OR_PROCESS")
        if event == "ctypes.dlopen" and args != (None,):
            raise RuntimeError("FEC_A01_NO_FOREIGN_DLOPEN")
        if event == "open" and not isinstance(args[0], int):
            path = Path(args[0]).resolve()
            flags = args[2]
            writing = flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            if writing:
                if path != OUTPUT or not flags & os.O_EXCL:
                    raise RuntimeError("FEC_A01_WRITE_SCOPE")
            else:
                if not (path in {SOURCE, PARSER, CONTRACT, MIME} or path.is_relative_to(runtime)):
                    raise RuntimeError("FEC_A01_READ_SCOPE")
                if path.is_file():
                    reads[0] += path.stat().st_size
                if reads[0] > 67108864:
                    raise RuntimeError("FEC_A01_READ_BOUND")
    sys.addaudithook(guard)
    mime = MIME.read_bytes()
    assert len(mime) == 61375 and hashlib.sha256(mime).hexdigest() == "57265fdf030202387c23e44283d440cab368a031214566b538b4b27064ed23df"
    code = PARSER.read_bytes()
    assert hashlib.sha256(code).hexdigest() == "0795e2012be6b0cd36bb7c2a4805320c773f654260bfd764f9ae039740c1a2dc"
    module = types.ModuleType("fec_a01_exact_reviewed_parser")
    module.__file__ = str(PARSER)
    sys.modules[module.__name__] = module
    exec(compile(code, str(PARSER), "exec"), module.__dict__)
    contract = module.load_contract(CONTRACT)
    with SOURCE.open("rb") as stream:
        raw = stream.read(6251111)
    source = {"source_id": "FEC2020_WORKBOOK_CANDIDATE_20261118", "bytes": 6251110,
              "sha256": "5073b6d2c76c86c941508dfb1a11cc497e8529b0068c5132aceb0f385c19352e",
              "provenance": "CANDIDATE_NOT_ADOPTED"}
    result = module.read_candidate_bytes(raw, contract, source)
    payload = module.packed(result)
    assert len(payload) <= 4194304 and len(result["cohort"]) == 33
    assert result["features"] == [] and all(result[k] is False for k in module.FALSE_FLAGS)
    with OUTPUT.open("xb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    assert hashlib.sha256(MIME.read_bytes()).hexdigest() == "57265fdf030202387c23e44283d440cab368a031214566b538b4b27064ed23df"
    print(json.dumps({"status": "CANDIDATE_READ_COMPLETE_NOT_ADOPTED", "reader_calls": 1,
                      "records": len(result["records"]), "cohort_slots": 33, "features": 0,
                      "result_bytes": len(payload), "result_sha256": hashlib.sha256(payload).hexdigest(),
                      "reader": {k:v for k,v in result["reader"].items() if k != "warnings"},
                      "reader_warning_count": len(result["reader"]["warnings"]), "archive": result["archive"],
                      "logical_file_read_reservations": reads[0], "wall_seconds": time.monotonic()-started,
                      "network_calls": 0, "model_calls": 0, **module.FALSE_FLAGS}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        # No raw cell or arbitrary exception text is printed.
        print(json.dumps({"status": "STOPPED_NO_RETRY", "error_type": type(error).__name__}))
        raise SystemExit(1)
