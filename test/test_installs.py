from path import Path

import pkg_resources
import pytest

from . import DALS


TEST_DIR = Path(__file__).parent
TEST_DIST = 'plover-template-system'
TEST_DIST_0_1_0 = TEST_DIST + '==0.1.0'
TEST_DIST_0_2_0 = TEST_DIST + '==0.2.0'
TEST_SDIST_0_1_0 = TEST_DIR / 'plover_template_system-0.1.0.tar.gz'
TEST_WHEEL_0_1_0 = TEST_DIR / 'plover_template_system-0.1.0-py3-none-any.whl'
TEST_WHEEL_0_2_0 = TEST_DIR / 'plover_template_system-0.2.0-py3-none-any.whl'
MANAGER_DIST = str(pkg_resources.get_distribution('plover_plugins_manager').as_requirement())


def test_list_plugins(virtualenv):
    assert virtualenv.list_all_plugins() == {MANAGER_DIST}
    assert virtualenv.list_user_plugins() == set()

def test_sdist_install(virtualenv):
    virtualenv.install_plugins([TEST_SDIST_0_1_0])
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_1_0}
    virtualenv.uninstall_plugins([TEST_DIST])
    assert virtualenv.list_user_plugins() == set()

def test_wheel_install(virtualenv):
    virtualenv.install_plugins([TEST_WHEEL_0_1_0])
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_1_0}
    virtualenv.uninstall_plugins([TEST_DIST])
    assert virtualenv.list_user_plugins() == set()

def test_plugin_update(virtualenv):
    virtualenv.install_plugins([TEST_WHEEL_0_1_0])
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_1_0}
    virtualenv.install_plugins([TEST_WHEEL_0_2_0])
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_2_0}

def test_plugin_downgrade(virtualenv):
    virtualenv.install_plugins([TEST_WHEEL_0_2_0])
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_2_0}
    virtualenv.install_plugins([TEST_WHEEL_0_1_0])
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_1_0}

def test_system_plugin_update(virtualenv):
    virtualenv.thaw()
    virtualenv.run('python -m pip install'.split() + [TEST_WHEEL_0_1_0])
    virtualenv.freeze()
    assert virtualenv.list_all_plugins() == {MANAGER_DIST, TEST_DIST_0_1_0}
    assert virtualenv.list_user_plugins() == set()
    virtualenv.install_plugins([TEST_WHEEL_0_2_0])
    assert virtualenv.list_all_plugins() == {MANAGER_DIST, TEST_DIST_0_2_0}
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_2_0}
    virtualenv.uninstall_plugins([TEST_DIST])
    assert virtualenv.list_all_plugins() == {MANAGER_DIST, TEST_DIST_0_1_0}
    assert virtualenv.list_user_plugins() == set()

@pytest.mark.parametrize('enable_user_site', (True, False))
def test_system_plugin_downgrade(virtualenv, enable_user_site):
    virtualenv.thaw()
    virtualenv.run('python -m pip install'.split() + [TEST_WHEEL_0_2_0], enable_user_site=enable_user_site)
    virtualenv.freeze()
    assert virtualenv.list_all_plugins(enable_user_site=enable_user_site) == {MANAGER_DIST, TEST_DIST_0_2_0}
    assert virtualenv.list_user_plugins() == set()
    virtualenv.install_plugins([TEST_WHEEL_0_1_0], enable_user_site=enable_user_site)
    assert virtualenv.list_all_plugins(enable_user_site=enable_user_site) == {MANAGER_DIST, TEST_DIST_0_1_0}
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_1_0}
    virtualenv.uninstall_plugins([TEST_DIST], enable_user_site=enable_user_site)
    assert virtualenv.list_all_plugins(enable_user_site=enable_user_site) == {MANAGER_DIST, TEST_DIST_0_2_0}
    assert virtualenv.list_user_plugins() == set()

def test_with_user_site_disabled(virtualenv):
    real_user_site = virtualenv.pyeval(DALS(
        '''
        import site
        print(repr(site.USER_SITE))
        '''
    ))
    virtualenv.run('python -m pip install --user'.split() +
                   [TEST_WHEEL_0_1_0], enable_user_site=False)
    assert virtualenv.list_distributions(real_user_site) == {TEST_DIST_0_1_0}
    assert virtualenv.list_all_plugins(enable_user_site=False) == {TEST_DIST_0_1_0, MANAGER_DIST}
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_1_0}
    virtualenv.uninstall_plugins([TEST_DIST_0_1_0], enable_user_site=False)
    assert virtualenv.list_all_plugins(enable_user_site=False) == {MANAGER_DIST}
    assert virtualenv.list_user_plugins() == set()

def test_install_to_venv(naked_virtualenv):
    naked_virtualenv.install_plugins([TEST_WHEEL_0_2_0])
    assert naked_virtualenv.list_user_plugins() == set()
    assert naked_virtualenv.list_all_plugins() == {TEST_DIST_0_2_0, MANAGER_DIST}
    naked_virtualenv.uninstall_plugins([TEST_DIST_0_2_0])
    assert naked_virtualenv.list_all_plugins() == {MANAGER_DIST}
