from io import BytesIO
from urllib.parse import urlparse, urlunparse
from xmlrpc.client import ServerProxy, Transport
import os

from requests_futures.sessions import FuturesSession
from requests_cache import core as cache_core

from plover.oslayer.config import CONFIG_DIR


CACHE_NAME = os.path.join(CONFIG_DIR, '.cache', 'plugins')


class CachedSession(cache_core.CachedSession):

    def __init__(self):
        dirname = os.path.dirname(CACHE_NAME)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        super().__init__(
            cache_name=CACHE_NAME, backend='sqlite', expire_after=600,
            # Note: cache POST requests used by XmlrpcProxy too.
            allowable_methods=('GET', 'POST'),
        )
        self.remove_expired_responses()


class CachedFuturesSession(FuturesSession):

    def __init__(self, session=None):
        if session is None:
            session = CachedSession()
        super().__init__(session=session, max_workers=4)


class XmlrpcTransport(Transport):

    def __init__(self, index_url, session, use_datetime=False):
        super().__init__(use_datetime)
        index_parts = urlparse(index_url)
        self._scheme = index_parts.scheme
        self._session = session
        self.verbose = False

    def request(self, host, handler, request_body, verbose=False):
        self.verbose = verbose
        url = urlunparse((self._scheme, host, handler, None, None, None))
        response = self._session.post(url, data=request_body,
                                      headers={'Content-Type': 'text/xml'})
        response.raise_for_status()
        return self.parse_response(BytesIO(response.content))


class XmlrpcProxy(ServerProxy):

    def __init__(self, url, session=None):
        if session is None:
            session = CachedSession()
        transport = XmlrpcTransport(url, session)
        super().__init__(url, transport)
