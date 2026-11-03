"""Private fixed-path transport, usable only through reviewed admission.

No key loading, owner creation, retry or public opener/URL injection.
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


class _CheckedHTTPS(_OpenRouterHTTPS):
    """Same bounded parser with explicit observed close failure propagation.

    Calling close successfully is still no absolute OS shutdown guarantee.
    The accepted older HTTP component remains unchanged.
    """
    def _request(self, url, method, body):
        response = None; started = time.monotonic()
        try:
            request = urllib.request.Request(url, data=body, method=method, headers={
                'Authorization': 'Bearer ' + self._key, 'Accept': 'application/json',
                'Accept-Encoding': 'identity', 'Content-Type': 'application/json',
                'Connection': 'close'})
            response = self._opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS)
            if time.monotonic() - started > TOTAL_SECONDS or response.status != 200 or response.geturl() != url:
                raise ValueError()
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
                if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
                block = response.read(min(65536, MAX_RESPONSE_BYTES + 1 - size))
                if type(block) is not bytes or time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
                size += len(block)
                if size > MAX_RESPONSE_BYTES: raise ValueError()
                if not block: break
                parts.append(block)
            if expected is not None and size != expected: raise ValueError()
            result = json.loads(b''.join(parts).decode('utf-8'), object_pairs_hook=_strict_object,
                                parse_constant=_nonfinite)
            if type(result) is not dict: raise ValueError()
            canonical_bytes(result)
            if time.monotonic() - started > TOTAL_SECONDS: raise ValueError()
            return result
        except urllib.error.HTTPError as error:
            response = error
            raise ExecutionBlocked('compatibility HTTP unresolved; no retry') from None
        except Exception:
            raise ExecutionBlocked('compatibility HTTP unresolved; no retry') from None
        finally:
            if response is not None:
                active = sys.exc_info()[1]
                try:
                    response.close()
                except Exception:
                    if not isinstance(active, (KeyboardInterrupt, SystemExit)):
                        raise ExecutionBlocked('compatibility response close failed; no retry') from None


class _CompatibilityTransportV4:
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
