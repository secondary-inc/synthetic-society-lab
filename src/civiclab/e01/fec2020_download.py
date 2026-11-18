"""Reproduce one pinned public FEC source; never adopt election counts.

The CLI has a 60-second wall limit, one GET and no redirects or retries.
Existing matching bytes need no network. A changed upstream file is refused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import tempfile
import urllib.request

URL = "https://www.fec.gov/resources/cms-content/documents/federalelections2020.xlsx"
DISCOVERY_URL = "https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2020/"
RELATIVE_PATH = Path("data/raw/e01_fec2020_workbook_20261118/federalelections2020.xlsx")
EXPECTED_BYTES = 6_251_110
EXPECTED_SHA256 = "5073b6d2c76c86c941508dfb1a11cc497e8529b0068c5132aceb0f385c19352e"


class SourceRefused(ValueError):
    """A fixed, nonsecret error code for a source that was not accepted."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if fp is not None:
            try:
                fp.close()
            except Exception:
                # Resource cleanup must not replace the redirect refusal.
                pass
        raise SourceRefused("REDIRECT_REFUSED")


def _verify(data: bytes) -> None:
    if len(data) != EXPECTED_BYTES:
        raise SourceRefused("SIZE_MISMATCH")
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise SourceRefused("HASH_MISMATCH")


def obtain(root: Path, *, fetch: bool = False) -> dict:
    """Verify the local candidate, optionally obtaining missing bytes once.

    No credential, outcome parsing, manifest promotion, or model call is used.
    The network timeout is 30 seconds; callers needing a whole-operation wall
    limit should use the bounded CLI entry below.
    """
    root = Path(root).resolve()
    path = root / RELATIVE_PATH
    if not path.parent.resolve().is_relative_to(root) or path.is_symlink():
        raise SourceRefused("UNSAFE_DESTINATION")
    requests = 0
    if path.exists():
        with path.open("rb") as stream:
            _verify(stream.read(EXPECTED_BYTES + 1))
        status = "VERIFIED_LOCAL_CANDIDATE"
    else:
        if not fetch:
            raise SourceRefused("MISSING_USE_FETCH")
        # Direct public URL, no redirect or environment-proxy credential route.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        request = urllib.request.Request(URL, headers={"User-Agent": "SyntheticSocietyLab source reproduction"})
        requests = 1
        with opener.open(request, timeout=30) as response:
            if response.status != 200 or response.geturl() != URL:
                raise SourceRefused("HTTP_IDENTITY_MISMATCH")
            data = response.read(EXPECTED_BYTES + 1)
        _verify(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".fec2020-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            # Exclusive publication: never replace an existing raw source.
            os.link(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        status = "DOWNLOADED_VERIFIED_CANDIDATE"
    return {"status": status, "path": str(RELATIVE_PATH), "sha256": EXPECTED_SHA256,
            "bytes": EXPECTED_BYTES, "url": URL, "discovery_url": DISCOVERY_URL,
            "physical_http_GETs": requests, "retries": 0, "redirects": 0,
            "source_adoption": False, "forecast_consumption": False, "model_calls": 0,
            "limitation": "Pinned byte integrity only; candidate totals, election stages, party mappings and reuse remain separate gates."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--fetch", action="store_true", help="Allow one public GET only if the candidate is absent")
    args = parser.parse_args(argv)

    def expired(signum, frame):
        raise SourceRefused("WALL_LIMIT")

    old_handler = signal.signal(signal.SIGALRM, expired)
    signal.alarm(60)
    try:
        result = obtain(args.root, fetch=args.fetch)
    except Exception as error:
        code = str(error) if type(error) is SourceRefused else type(error).__name__
        print(json.dumps({"status": "BLOCKED", "error": code, "source_adoption": False}))
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
