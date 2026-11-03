"""One ordinary verified HTTPS request. No redirects, authentication or retries."""
import ssl
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PublicResponse:
    def __init__(self, response):
        self.response=response
        self.status=response.code
        self.url=response.geturl()
        self.headers={k.lower():v for k,v in response.headers.items()}
    def read(self, count):
        # read1 uses a bounded underlying read rather than waiting to fill count
        # through an unbounded succession of trickled socket reads.
        return self.response.read1(count)
    def close(self):self.response.close()


class PublicHTTP:
    def open(self, url, timeout):
        opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        request=urllib.request.Request(url,headers={'Accept-Encoding':'identity','User-Agent':'SyntheticSocietyLab/0.1'},method='GET')
        try:response=opener.open(request,timeout=timeout)
        except urllib.error.HTTPError as error:response=error
        return PublicResponse(response)
