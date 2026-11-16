#!/usr/bin/env python3
"""One read-only key-status GET after the retained E02 HTTP 402 stop."""
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import runpy
import signal
import ssl
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/processed/openrouter_key_status_20261116_01'
READER = ROOT / 'scripts/collect_connectivity_billing_once.py'
READER_SHA = '0b5ea3cca5d6d71550985d1da12f9264f223662af7d6429ecab4d88b4cb8f4a7'


def write_once(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def safe_projection(body):
    """Keep only typed numeric/boolean limits; never identities or key fragments."""
    data = body.get('data') if type(body) is dict else None
    if type(data) is not dict:
        raise ValueError('schema')
    result = {}
    for name in ('limit', 'limit_remaining', 'usage', 'usage_daily', 'usage_weekly', 'usage_monthly'):
        if name not in data:
            continue
        value = data[name]
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            raise ValueError('number')
        result[name] = value
    for name in ('is_free_tier', 'include_byok_in_limit'):
        if name in data:
            if type(data[name]) is not bool:
                raise ValueError('boolean')
            result[name] = data[name]
    for name in ('budgets', 'effective_budget'):
        if name not in data:
            continue
        items = data[name] if name == 'budgets' else [data[name]]
        if items is None:
            items = []
        if type(items) is not list or len(items) > 32:
            raise ValueError('budgets')
        projected = []
        for item in items:
            if item is None:
                continue
            if type(item) is not dict:
                raise ValueError('budget')
            clean = {}
            for key in ('limit_usd', 'remaining_usd', 'spend_usd'):
                if key not in item:
                    continue
                v = item[key]
                if v is not None and (type(v) not in (int, float) or not math.isfinite(v)):
                    raise ValueError('budget number')
                clean[key] = v
            if item.get('scope') in ('member', 'api_key', 'workspace', 'key_limit', 'workspace_default_member', 'workspace_default_key'):
                clean['scope'] = item['scope']
            projected.append(clean)
        result[name] = projected
    return result


def timeout_handler(*_):
    raise TimeoutError('deadline')


def main():
    # Creating this directory consumes this diagnostic; all subsequent calls refuse.
    BASE.mkdir(mode=0o700, exist_ok=False)
    started = {'kind': 'READONLY_OPENROUTER_KEY_STATUS_ONCE',
               'started_at_utc': datetime.now(timezone.utc).isoformat(),
               'reason': 'Diagnose retained HTTP 402 after 44 committed E02 responses.',
               'GET_limit': 1, 'POST_limit': 0, 'retries': 0,
               'socket_seconds': 15, 'total_seconds': 35, 'body_bytes_limit': 65536,
               'owner_reads': 0, 'owner_writes': 0, 'purchases': 0,
               'documentation': 'https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key'}
    write_once(BASE / 'started.json', started)
    result = {'status': 'STOPPED', 'GET_attempts': 0, 'POST_attempts': 0,
              'retries': 0, 'owner_writes': 0, 'purchases': 0,
              'credential_logged': False, 'raw_body_retained': False}
    connection = None
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(35)
    try:
        if READER.is_symlink() or hashlib.sha256(READER.read_bytes()).hexdigest() != READER_SHA:
            raise ValueError('reader pin')
        credential = runpy.run_path(str(READER))['_credential'](ROOT)
        connection = http.client.HTTPSConnection('openrouter.ai', timeout=15, context=ssl.create_default_context())
        result['GET_attempts'] = 1
        # http.client has no automatic redirects, retries or environment proxy handling.
        connection.request('GET', '/api/v1/key', headers={
            'Authorization': 'Bearer ' + credential._value,
            'Accept': 'application/json', 'Accept-Encoding': 'identity', 'Connection': 'close'})
        response = connection.getresponse()
        result['http_status'] = response.status
        if response.status != 200:
            raise ValueError('http status')
        if response.getheader('Content-Encoding', 'identity') != 'identity':
            raise ValueError('encoding')
        if response.getheader('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            raise ValueError('content type')
        raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError('body cap')
        result['key_status'] = safe_projection(json.loads(raw))
        result['status'] = 'READONLY_STATUS_OBSERVED'
        result['account_credit_balance'] = 'NOT_PROVIDED_BY_THIS_ENDPOINT'
    except Exception as error:
        # No exception message, request header, raw response or secret fingerprint.
        result['error_type'] = type(error).__name__
    finally:
        if connection is not None:
            connection.close()
        signal.alarm(0)
    result['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    write_once(BASE / 'result.json', result)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
