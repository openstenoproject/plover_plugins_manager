import os

from requests_futures.sessions import FuturesSession
from requests_cache import CachedSession



class CachedSession(CachedSession):

    def __init__(self):
        super().__init__(backend='memory',
                         expire_after=600)
        self.cache.delete(expired=True)


class CachedFuturesSession(FuturesSession):

    def __init__(self, session=None):
        if session is None:
            session = CachedSession()
        super().__init__(session=session, max_workers=4)
