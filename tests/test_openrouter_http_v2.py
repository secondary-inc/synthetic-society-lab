"""Network-free transport checks; all credentials and responses are authored."""
from email.message import Message
import io
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from civiclab.model import ExecutionBlocked
from civiclab.openrouter_http_v2 import _OpenRouterHTTPS, _NoRedirect, create_live_transport, BASE

KEY = 'AUTHORED-TRANSPORT-TEST-CREDENTIAL'


class Response(io.BytesIO):
    def __init__(self, body=b'{"id":"gen-example"}', *, url=BASE+'/chat/completions', status=200, headers=None):
        super().__init__(body); self.status = status; self.url = url
        self.read_bytes = 0
        self.headers = Message()
        for k, v in (headers if headers is not None else [('Content-Type','application/json')]): self.headers[k]=v
    def geturl(self): return self.url
    def read(self, size=-1):
        value=super().read(size);self.read_bytes+=len(value);return value


class Opener:
    def __init__(self, response=None, error=None):
        self.response=response; self.error=error; self.calls=[]
    def open(self, request, **kwargs):
        self.calls.append((request, kwargs))
        if self.error: raise self.error
        return self.response


class TransportTests(unittest.TestCase):
    def make(self, response=None, error=None):
        client=_OpenRouterHTTPS(KEY); opener=Opener(response,error); client._opener=opener
        return client,opener

    def test_exact_endpoints_methods_and_minimal_headers(self):
        for stats in (False,True):
            url=BASE+('/generation?id=gen-example' if stats else '/chat/completions')
            reply=Response(url=url); client,opener=self.make(reply)
            result=client.stats('gen-example') if stats else client.post({'model':'AUTHORED'})
            self.assertEqual(result,{'id':'gen-example'}); self.assertTrue(reply.closed)
            req,kwargs=opener.calls[0]
            self.assertEqual(req.full_url,url); self.assertEqual(req.get_method(),'GET' if stats else 'POST')
            self.assertEqual(kwargs,{'timeout':15}); self.assertEqual(req.get_header('Authorization'),'Bearer '+KEY)
            self.assertEqual(set(k.lower() for k in req.headers),{'authorization','accept','accept-encoding','content-type','connection'})
            self.assertIsNone(req.data) if stats else self.assertEqual(req.data,b'{"model":"AUTHORED"}')
            self.assertNotIn(KEY,repr(client))

    def test_pre_dispatch_rejections_make_zero_requests(self):
        for value in ('../gen-x','gen-x&key=bad','gen-x\n','gen-'+'a'*129,None):
            client,opener=self.make()
            with self.assertRaises(ExecutionBlocked):client.stats(value)
            self.assertEqual(opener.calls,[])
        for value in ([1], {'n':float('nan')},{'x':'a'*262145}):
            client,opener=self.make()
            with self.assertRaises(ExecutionBlocked):client.post(value)
            self.assertEqual(opener.calls,[])

    def test_bad_status_destination_and_headers_close_without_retry(self):
        cases=[{'status':429},{'status':302},{'url':'https://other.invalid/'},
               {'headers':[]},{'headers':[('Content-Type','text/html')]},
               {'headers':[('Content-Type','application/json'),('Content-Encoding','gzip')]},
               {'headers':[('Content-Type','application/json'),('Content-Length','2000001')]},
               {'headers':[('Content-Type','application/json'),('Content-Length','1'),('Content-Length','1')]},
               {'headers':[('Content-Type','application/json'),('Content-Length','-1')]},
               {'headers':[('Content-Type','application/json'),('Content-Length','1'),('Transfer-Encoding','chunked')]},
               {'headers':[('Content-Type','application/json'),('Content-Length','1')]}]
        for case in cases:
            with self.subTest(case=case):
                reply=Response(**case);client,opener=self.make(reply)
                with self.assertRaises(ExecutionBlocked):client.post({})
                self.assertTrue(reply.closed);self.assertEqual(len(opener.calls),1)

    def test_strict_json_and_streaming_limit(self):
        for body in (b'[]', b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'\xff',b'bad',b' '*2_000_001):
            with self.subTest(size=len(body)):
                reply=Response(body);client,opener=self.make(reply)
                with self.assertRaises(ExecutionBlocked):client.post({})
                self.assertTrue(reply.closed);self.assertEqual(len(opener.calls),1)
                if len(body)>2_000_000:self.assertEqual(reply.read_bytes,2_000_001)

    def test_timeouts_and_error_bodies_never_leak_or_retry(self):
        for error in (TimeoutError(KEY),urllib.error.HTTPError(BASE,401,KEY,{},io.BytesIO(KEY.encode()))):
            client,opener=self.make(error=error)
            with self.assertRaises(ExecutionBlocked) as seen:client.post({})
            self.assertNotIn(KEY,str(seen.exception));self.assertIsNone(seen.exception.__cause__)
            self.assertEqual(len(opener.calls),1)
            if isinstance(error,urllib.error.HTTPError):self.assertTrue(error.fp.closed)

    def test_total_elapsed_checks_and_close(self):
        for times in ([0,31], [0,0,0,31]):
            response=Response();client,opener=self.make(response)
            with patch('civiclab.openrouter_http_v2.time.monotonic',side_effect=times):
                with self.assertRaises(ExecutionBlocked):client.post({})
            self.assertTrue(response.closed);self.assertEqual(len(opener.calls),1)

    def test_proxy_redirect_cookie_and_default_header_policy(self):
        client=_OpenRouterHTTPS(KEY)
        self.assertEqual(client._opener.addheaders,[])
        self.assertFalse(any(isinstance(h,urllib.request.HTTPCookieProcessor) for h in client._opener.handlers))
        self.assertFalse(any(isinstance(h,urllib.request.ProxyHandler) and h.proxies for h in client._opener.handlers))
        self.assertIsNone(_NoRedirect().redirect_request(None,None,302,'',{},'https://other.invalid'))

    def test_disabled_factory_never_constructs_or_reads_credentials(self):
        with patch('civiclab.openrouter_http_v2._OpenRouterHTTPS') as constructor:
            with self.assertRaises(ExecutionBlocked):create_live_transport()
            constructor.assert_not_called()
        for key in ('short','x'*16+'\n','x'*4097,'x'*16+'é'):
            with self.assertRaises(ExecutionBlocked):_OpenRouterHTTPS(key)
