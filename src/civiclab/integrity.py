"""Verify obtained bytes; never confuse integrity with licensing or validity."""
from pathlib import Path
import json
import zipfile
from importlib import import_module
from .common import sha256_file


def contained(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("inventory path escapes project")
    return path


def validate_sources(root, fixture_only=False):
    root = Path(root)
    checks = []

    def check(name, expected, label):
        try:
            path = contained(root, name)
            if not path.is_file():
                status = "MISSING"
            else:
                status = "PASS" if sha256_file(path) == expected else "MISMATCH"
            checks.append({"path": name, "type": label, "status": status})
        except ValueError:
            checks.append({"path": name, "type": label, "status": "UNSAFE_PATH"})
        return checks[-1]["status"] == "PASS"

    fixture = json.loads((root / "tests/fixtures/gdelt/manifest.json").read_text())
    check(fixture["path"], fixture["sha256"], "versioned_fixture")
    if not fixture_only:
        inventory = json.loads((root / "configs/SOURCE_INVENTORY.json").read_text())
        for entry in inventory["archives"] + inventory.get("documents", []):
            name = entry.get("local_archive", entry.get("local_path"))
            if not name:  # Byte-identical aliases point to the obtained copy.
                continue
            valid = check(name, entry["sha256"], "source")
            if valid and name.endswith(".zip"):
                with zipfile.ZipFile(contained(root, name)) as archive:
                    checks.append({"path": name, "type": "zip_crc",
                                   "status": "PASS" if archive.testzip() is None else "MISMATCH"})
            for member in entry.get("members", []):
                path = str(Path(name).parent / "extracted" / member["name"]) if name.endswith(".zip") else name
                check(path, member["sha256"], "member")
        # Module manifests are separate from the historical received-file inventory.
        # A present manifest is mandatory to verify in a full local check; absence of
        # its raw cache blocks that check rather than silently reducing coverage.
        validators=(
            ('configs/e01_official_sources.json','civiclab.e01.historical','verify_sources'),
            ('configs/e02_official_stimuli.json','civiclab.e02.stimuli','verify_corpus'),
            ('configs/e02_citizen_benchmark_acquisition.json','civiclab.e02.citizen_benchmark','verify'),
        )
        for manifest,module,function in validators:
            if not (root/manifest).exists():continue
            try:
                detail=getattr(import_module(module),function)(root)
                checks.append({'path':manifest,'type':'module_source_verifier','status':'PASS','detail':detail})
            except (ValueError,OSError,KeyError,TypeError,zipfile.BadZipFile) as error:
                checks.append({'path':manifest,'type':'module_source_verifier','status':'BLOCKED','error_type':type(error).__name__})
    return {"status": "PASS" if all(c["status"] == "PASS" for c in checks) else "BLOCKED",
            "scope": "fixture" if fixture_only else "local_registered_sources", "checks": checks,
            "limitation": "Byte integrity only; not source authenticity, reuse permission or scientific validity."}
