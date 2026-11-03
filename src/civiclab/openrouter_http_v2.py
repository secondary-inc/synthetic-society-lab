"""Unreleased low-level OpenRouter HTTPS component; no credential loading.

Production factories remain disabled. Callers must first provide accepted owner,
study, price, reservation and phase controls. This module alone grants no spend.
"""
import json
import re
import ssl
import time
import urllib.error
import urllib.request

from .common import canonical_bytes
from .model import ExecutionBlocked

BASE = 'https://openrouter.ai/api/v1'
MAX_RESPONSE_BYTES = 2_000_000
MAX_REQUEST_BYTES = 262_144
SOCKET_TIMEOUT_SECONDS = 15
TOTAL_SECONDS = 30


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON member')
        result[key] = value
    return result


def _nonfinite(_):
    raise ValueError('nonfinite JSON number')


class _OpenRouterHTTPS:
    """Internal transport, awaiting separate admission/client integration review.

    The key is injected explicitly; no environment, files or keychain are read.
    Exceptions omit URL, headers, response body and underlying error messages.
    Limits are cooperative with socket timeouts, not an OS wall-clock guarantee.
    """
    def __init__(self, key):
        if (not isinstance(key, str) or not 16 <= len(key) <= 4096
            or any(not 33 <= ord(c) <= 126 for c in key)):
            raise ExecutionBlocked('invalid injected credential shape')
        self._key = key
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        self._opener.addheaders = []

    def __repr__(self):
        return '<unreleased OpenRouter HTTPS transport; credential omitted>'

    def post(self, payload):
        try:
            if not isinstance(payload, dict): raise ValueError()
            body = canonical_bytes(payload)
            if len(body) > MAX_REQUEST_BYTES: raise ValueError()
        except (ValueError, TypeError, RecursionError):
            raise ExecutionBlocked('invalid or oversized request; no dispatch') from None
        return self._request(BASE + '/chat/completions', 'POST', body)

    def stats(self, identity):
        if (not isinstance(identity, str) or len(identity) > 128
            or re.fullmatch(r'gen-[0-9A-Za-z-]+', identity) is None):
            raise ExecutionBlocked('invalid generation identity; no lookup')
        return self._request(BASE + '/generation?id=' + identity, 'GET', None)

    def _request(self, url, method, body):
        response = None
        started = time.monotonic()
        try:
            req = urllib.request.Request(url, data=body, method=method, headers={
                'Authorization': 'Bearer ' + self._key, 'Accept': 'application/json',
                'Accept-Encoding': 'identity', 'Content-Type': 'application/json',
                'Connection': 'close'})
            response = self._opener.open(req, timeout=SOCKET_TIMEOUT_SECONDS)
            if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
            if response.status != 200 or response.geturl() != url: raise ValueError()
            # Reject ambiguous/unsupported framing rather than decompressing.
            headers = response.headers
            lengths = headers.get_all('Content-Length', [])
            encodings = headers.get_all('Content-Encoding', [])
            types = headers.get_all('Content-Type', [])
            transfers = headers.get_all('Transfer-Encoding', [])
            if len(transfers) > 1 or (transfers and (lengths or transfers[0].strip().lower() != 'chunked')): raise ValueError()
            if len(lengths) > 1 or len(encodings) > 1 or len(types) != 1: raise ValueError()
            if encodings and encodings[0].strip().lower() != 'identity': raise ValueError()
            if types[0].split(';', 1)[0].strip().lower() != 'application/json': raise ValueError()
            expected = None
            if lengths:
                if not re.fullmatch(r'[0-9]{1,10}', lengths[0]): raise ValueError()
                expected = int(lengths[0])
                if expected > MAX_RESPONSE_BYTES: raise ValueError()
            chunks = []; size = 0
            while True:
                if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
                chunk = response.read(min(65536, MAX_RESPONSE_BYTES + 1 - size))
                if not isinstance(chunk, bytes): raise ValueError()
                if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES: raise ValueError()
                if not chunk: break
                chunks.append(chunk)
            if expected is not None and size != expected: raise ValueError()
            result = json.loads(b''.join(chunks).decode('utf-8'),
                                object_pairs_hook=_strict_object, parse_constant=_nonfinite)
            if not isinstance(result, dict): raise ValueError()
            # Reject float overflow such as 1e999 as well as named constants.
            canonical_bytes(result)
            if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
            return result
        except urllib.error.HTTPError as error:
            try: error.close()
            except Exception: pass
            raise ExecutionBlocked('OpenRouter transport unresolved; no automatic retry') from None
        except Exception:
            raise ExecutionBlocked('OpenRouter transport unresolved; no automatic retry') from None
        finally:
            if response is not None:
                try: response.close()
                except Exception: pass


def create_live_transport(*args, **kwargs):
    raise ExecutionBlocked('live HTTP admission unavailable; owner/study/price/global-ledger release required')
