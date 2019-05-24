from concurrent.futures import as_completed
import json
import os

from plover_plugins_manager.requests import CachedFuturesSession, XmlrpcProxy


PYPI_URL = 'https://pypi.org/pypi'


def find_plover_plugins_releases(pypi_url=None, capture=None):

    if pypi_url is None:
        pypi_url = os.environ.get('PYPI_URL')

    if pypi_url is not None and os.path.exists(pypi_url):
        assert capture is None
        # Test code path.
        with open(pypi_url) as fp:
            return json.load(fp)

    if pypi_url is None:
        pypi_url = PYPI_URL

    session = CachedFuturesSession()
    index = XmlrpcProxy(pypi_url, session=session.session)

    in_progress = set()
    all_releases = {}

    def fetch_release(name, version):
        if (name, version) in all_releases:
            return
        all_releases[(name, version)] = None
        in_progress.add(session.get('%s/%s/%s/json' % (pypi_url, name, version)))

    with session:

        for match in index.search({'keywords': 'plover_plugin'}):
            fetch_release(match['name'], match['version'])

        while in_progress:
            for future in as_completed(list(in_progress)):
                in_progress.remove(future)
                if not future.done():
                    continue
                resp = future.result()
                if resp.status_code != 200:
                    # Can happen if a package has been deleted.
                    continue
                release = resp.json()
                info = release['info']
                if 'plover_plugin' not in info['keywords'].split():
                    # Not a plugin.
                    continue
                name, version = info['name'], info['version']
                all_releases[(name, version)] = release
                for version in release['releases'].keys():
                    fetch_release(name, version)

    all_releases = [
        release
        for release in all_releases.values()
        if release is not None
    ]

    if capture is not None:
        with open(capture, 'w') as fp:
            json.dump(all_releases, fp, indent=2, sort_keys=True)

    return all_releases
