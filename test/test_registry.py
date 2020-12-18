import tarfile
import sys

import pkg_resources
import pytest

from plover_plugins_manager.registry import Registry
from plover_plugins_manager.plugin_metadata import PluginMetadata


@pytest.fixture
def fake_global_registry(monkeypatch):
    monkeypatch.setattr('plover_plugins_manager.global_registry.find_plover_plugins_releases', lambda: [])

@pytest.fixture
def fake_local_registry(tmpdir, monkeypatch):
    # Fake user site.
    tmp_user_site = tmpdir / 'user_site'
    tmp_user_site.mkdir()
    monkeypatch.setattr('site.USER_SITE', str(tmp_user_site))
    # Fake install prefix.
    tmp_prefix = tmpdir / 'prefix'
    tmp_prefix.mkdir()
    with tarfile.open('test/data/prefix.tar') as prefix:
        prefix.extractall(path=str(tmp_prefix))
    new_path = list(map(str, tmp_prefix.listdir('*.egg'))) + [str(tmp_prefix)]
    pr_state = pkg_resources.__getstate__()
    old_path = sys.path[:]
    try:
        sys.path[:] = new_path
        yield
    finally:
        sys.path[:] = old_path
        pkg_resources.__setstate__(pr_state)

@pytest.fixture
def fake_env(fake_global_registry, fake_local_registry):
    pass


def test_fake_registry(fake_env):
    r = Registry()
    r.update()
    assert len(r) == 3
    local_egg_info = r['local-egg-info']
    assert local_egg_info.current == PluginMetadata.from_kwargs(
        author='Local Egg-info',
        author_email='local.egg-info@mail.com',
        description='A macro plugin for Plover.',
        description_content_type='',
        home_page='http://localhost',
        keywords='',
        license='GNU General Public License v2 or later (GPLv2+)',
        name='local_egg_info',
        summary='Macro for Plover',
        version='2.0'
    )
    assert local_egg_info.available == []
    assert local_egg_info.latest is None
    assert local_egg_info.metadata is local_egg_info.current
    # Local only, .dist-info metadata, no metadata.json.
    local_dist_info = r['local-dist-info']
    assert local_dist_info.current == PluginMetadata.from_kwargs(
        author='Local Dist-info',
        author_email='local.dist-info@mail.com',
        description='A dictionary plugin for Plover.',
        description_content_type='',
        home_page='http://localhost',
        keywords='',
        license='GNU General Public License v2 or later (GPLv2+)',
        name='local_dist_info',
        summary='Macro for Plover',
        version='1.0.0'
    )
    assert local_dist_info.available == []
    assert local_dist_info.latest is None
    assert local_dist_info.metadata is local_dist_info.current
    # Local only, zipped egg distribution.
    local_dist_info = r['zipped-egg-plugin']
    assert local_dist_info.current == PluginMetadata.from_kwargs(
        author='Foo Bar',
        author_email='foo.bar@foobar.com',
        description='Zipped egg plugin for Plover\n============================\n',
        description_content_type='',
        home_page='http://localhost',
        keywords=['plover plover_plugin'],
        license='GNU General Public License v2 or later (GPLv2+)',
        name='zipped-egg-plugin',
        summary='Zipped egg plugin for Plover',
        version='0.1.0'
    )
    assert local_dist_info.available == []
    assert local_dist_info.latest is None
    assert local_dist_info.metadata is local_dist_info.current
