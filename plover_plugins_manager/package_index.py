from xmlrpc.client import ServerProxy
import json
import os

try:
    import pip._internal as pip_internal
except ImportError:
    import pip as pip_internal


if hasattr(pip_internal.models, 'PyPI'):
    PYPI_URL = pip_internal.models.PyPI.pypi_url
else:
    PYPI_URL = pip_internal.download.PyPI.pypi_url


def find_plover_plugins_releases(pypi_url=None):
    if pypi_url is None:
        pypi_url = os.environ.get('PYPI_URL', PYPI_URL)
    if pypi_url is not None and os.path.exists(pypi_url):
        # Test code path.
        with open(pypi_url) as fp:
            yield from json.load(fp)
        return
    # Normal HTTPS path.
    session = pip_internal.download.PipSession()
    # We use pip's session/transport to avoid SSL errors on Windows/macOS...
    transport = pip_internal.download.PipXmlrpcTransport(pypi_url, session)
    pypi = ServerProxy(pypi_url, transport)
    for match in pypi.search({'keywords': 'plover_plugin'}):
        resp = session.get('%s/%s/%s/json' % (pypi_url, match['name'], match['version']))
        # Can happen if a package has been deleted.
        if resp.status_code != 200:
            continue
        yield resp.json()
