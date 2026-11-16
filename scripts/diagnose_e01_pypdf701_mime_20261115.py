"""Two fixed public HEAD requests; no response body, retry, or installation."""
from pathlib import Path
import hashlib
import http.client
import json
import os
import signal
import ssl
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/processed/e01_pypdf701_mime_diagnostic_20261115_01'
SELECTED = ROOT / 'data/processed/e01_pypdf701_build_v1/acquisition-v1_1-20261115/selected.prepared.json'
SELECTED_SHA = '9be26163c5514b8679eb21cba3f65979bfffd774b41abe7e10bc77c63f79c919'


def write(name, value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    with os.fdopen(os.open(BASE / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())


def main():
    with SELECTED.open('rb') as source:
        raw = source.read(3089)
    if len(raw) != 3088 or hashlib.sha256(raw).hexdigest() != SELECTED_SHA:
        raise RuntimeError('selected artifact binding differs')
    wheels = json.loads(raw)['wheels'][:2]
    if [row['name'] for row in wheels] != ['pypdf', 'cffi']:
        raise RuntimeError('fixed two artifacts required')
    if any(p.is_symlink() for p in (BASE, *BASE.parents)):
        raise RuntimeError('scope alias')
    BASE.mkdir(mode=0o700, exist_ok=False)
    write('STARTED.json', dict(HEAD_max=2, application_body_reads=0, retries=0,
                              redirects=0, authorization_headers=0, request_seconds=20,
                              total_wall_seconds=40, selected_sha256=SELECTED_SHA,
                              existing_acquisition_allowances_or_charges_changed=False))
    started = time.monotonic()
    attempts = 0
    observations = []
    def timeout(*_):
        raise TimeoutError('HEAD deadline')
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, 40)
    try:
        for row in wheels:
            parts = urlsplit(row['url'])
            if parts.scheme != 'https' or parts.netloc != 'files.pythonhosted.org' or parts.query or parts.fragment:
                raise RuntimeError('fixed artifact host required')
            attempts += 1
            write(f'HEAD-{attempts}-intent.json', dict(url=row['url'], method='HEAD'))
            connection = http.client.HTTPSConnection(parts.netloc, timeout=min(20, 40-(time.monotonic()-started)), context=ssl.create_default_context())
            response = None
            try:
                connection.request('HEAD', parts.path, headers={'Accept-Encoding': 'identity'})
                response = connection.getresponse()
                headers = {key: response.getheader(key) for key in
                           ['Content-Type', 'Content-Length', 'Content-Encoding', 'Date', 'ETag', 'Location']}
                observation = dict(url=row['url'], HTTP_status=response.status, headers=headers,
                                   application_body_bytes_read=0)
                write(f'HEAD-{attempts}-response.json', observation)
                observations.append(observation)
                if response.status != 200 or headers['Location'] is not None:
                    raise RuntimeError('HEAD status or redirect')
            finally:
                if response is not None:
                    response.close()
                connection.close()
        result = dict(status='HEAD_METADATA_ONLY_COMPLETE', HEAD_attempts=attempts,
                      observations=observations, elapsed_seconds=time.monotonic()-started,
                      model_calls=0, cost_USD=0, application_body_bytes_read=0)
        write('TERMINAL.json', result)
        print(json.dumps(result, sort_keys=True))
    except BaseException as error:
        write('TERMINAL.json', dict(status='STOPPED_NO_RETRY', HEAD_attempts=attempts,
                                   error_type=type(error).__name__, observations=observations))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    main()
