"""Unreleased diagnostic candidate. No live release, key loading or retries.

Closed diagnostic fields never include exception strings, bodies or headers.
Executed v4 transport remains unchanged.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request

from .common import canonical_bytes
from .model import ExecutionBlocked
from .openrouter_http_v2 import (_OpenRouterHTTPS, BASE, MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES, SOCKET_TIMEOUT_SECONDS, TOTAL_SECONDS, _strict_object, _nonfinite)
from .production_admission_v4 import _Credential


_STAGES = frozenset(('BUILD_REQUEST', 'OPEN', 'HTTP_STATUS', 'DESTINATION',
    'HEADERS', 'READ', 'BODY_LIMIT', 'BODY_LENGTH', 'JSON', 'DEADLINE', 'CLOSE'))
_CATEGORIES = frozenset(('HTTP_STATUS', 'TIMEOUT', 'TRANSPORT_FAILURE',
    'INVALID_RESPONSE', 'RESPONSE_CLOSE'))


class _SafeTransportFailure(ExecutionBlocked):
    def __init__(self, stage, category, http_status=None, close_failed=False):
        if (type(stage) is not str or stage not in _STAGES
            or type(category) is not str or category not in _CATEGORIES
            or (http_status is not None and
                (type(http_status) is not int or not 100 <= http_status <= 599))
            or type(close_failed) is not bool):
            raise ValueError('closed diagnostic fields required')
        self._fields = (stage, category, http_status, close_failed)
        super().__init__('compatibility transport stopped; no retry')

    def diagnostic(self):
        stage, category, status, close = self._fields
        # Revalidate even if a caller has tampered with exception attributes.
        checked = _SafeTransportFailure(stage, category, status, close)
        return dict(zip(('stage', 'category', 'http_status', 'close_failed'), checked._fields))


class _CheckedHTTPS(_OpenRouterHTTPS):
    """Same bounded parser with explicit observed close failure propagation.

    Calling close successfully is still no absolute OS shutdown guarantee.
    The accepted older HTTP component remains unchanged.
    """
    def _request(self, url, method, body):
        response = None; started = time.monotonic()
        stage = 'BUILD_REQUEST'; status = None
        try:
            request = urllib.request.Request(url, data=body, method=method, headers={
                'Authorization': 'Bearer ' + self._key, 'Accept': 'application/json',
                'Accept-Encoding': 'identity', 'Content-Type': 'application/json',
                'Connection': 'close'})
            stage = 'OPEN'
            response = self._opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS)
            stage = 'DEADLINE'
            if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
            stage = 'HTTP_STATUS'
            observed = response.status
            status = observed if type(observed) is int and 100 <= observed <= 599 else None
            if status != 200: raise _SafeTransportFailure(stage, 'HTTP_STATUS', status)
            stage = 'DESTINATION'
            if response.geturl() != url: raise ValueError()
            stage = 'HEADERS'
            headers = response.headers
            lengths = headers.get_all('Content-Length', [])
            encodings = headers.get_all('Content-Encoding', [])
            types = headers.get_all('Content-Type', [])
            transfers = headers.get_all('Transfer-Encoding', [])
            if len(transfers) > 1 or (transfers and (lengths or transfers[0].strip().lower() != 'chunked')):
                raise ValueError()
            if len(lengths) > 1 or len(encodings) > 1 or len(types) != 1:
                raise ValueError()
            if encodings and encodings[0].strip().lower() != 'identity': raise ValueError()
            if types[0].split(';', 1)[0].strip().lower() != 'application/json': raise ValueError()
            expected = None
            if lengths:
                if not re.fullmatch(r'[0-9]{1,10}', lengths[0]): raise ValueError()
                expected = int(lengths[0])
                if expected > MAX_RESPONSE_BYTES: raise ValueError()
            parts = []; size = 0
            while True:
                stage = 'DEADLINE'
                if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
                stage = 'READ'
                block = response.read(min(65536, MAX_RESPONSE_BYTES + 1 - size))
                if type(block) is not bytes: raise ValueError()
                stage = 'DEADLINE'
                if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
                stage = 'BODY_LIMIT'
                size += len(block)
                if size > MAX_RESPONSE_BYTES: raise ValueError()
                if not block: break
                parts.append(block)
            stage = 'BODY_LENGTH'
            if expected is not None and size != expected: raise ValueError()
            stage = 'JSON'
            result = json.loads(b''.join(parts).decode('utf-8'), object_pairs_hook=_strict_object,
                                parse_constant=_nonfinite)
            if type(result) is not dict: raise ValueError()
            canonical_bytes(result)
            stage = 'DEADLINE'
            if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
            return result
        except urllib.error.HTTPError as error:
            response = error
            observed = error.code
            status = observed if type(observed) is int and 100 <= observed <= 599 else None
            raise _SafeTransportFailure('HTTP_STATUS', 'HTTP_STATUS', status) from None
        except _SafeTransportFailure:
            raise
        except TimeoutError:
            raise _SafeTransportFailure(stage, 'TIMEOUT', status) from None
        except Exception:
            category = 'TRANSPORT_FAILURE' if stage in ('BUILD_REQUEST', 'OPEN', 'READ') else 'INVALID_RESPONSE'
            raise _SafeTransportFailure(stage, category, status) from None
        finally:
            if response is not None:
                active = sys.exc_info()[1]
                try:
                    response.close()
                except Exception:
                    if not isinstance(active, (KeyboardInterrupt, SystemExit)):
                        if type(active) is _SafeTransportFailure:
                            fields = active.diagnostic()
                            raise _SafeTransportFailure(fields['stage'], fields['category'],
                                fields['http_status'], True) from None
                        raise _SafeTransportFailure('CLOSE', 'RESPONSE_CLOSE', status, True) from None


class _CompatibilityTransportV4_2:
    def __init__(self, credential):
        if type(credential) is not _Credential:
            raise ExecutionBlocked('admitted opaque credential required')
        self._http = _CheckedHTTPS(credential._value)

    def __repr__(self):
        return '<private compatibility HTTPS transport; credential omitted>'

    def post_bytes(self, body):
        if type(body) is not bytes or not 0 < len(body) <= MAX_REQUEST_BYTES:
            raise ExecutionBlocked('bounded admitted request bytes required')
        # The executor supplies canonical bytes of its independently rederived
        # admitted payload. Sending bytes directly avoids a second derivation.
        return self._http._request(BASE + '/chat/completions', 'POST', body)

    def statistics(self, identity):
        if type(identity) is not str or len(identity) > 128 or re.fullmatch(r'gen-[0-9A-Za-z-]+', identity) is None:
            raise ExecutionBlocked('safe generation identity required')
        return self._http.stats(identity)
