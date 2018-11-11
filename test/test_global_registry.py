import pytest

from . import DALS


@pytest.mark.parametrize('pip_spec', (
    'pip==9.0.3', 'pip==10.0', 'pip==18.0', 'pip==latest'
))
def test_global_registry_pip_support(virtualenv, pip_spec):
    # Simple test to check the code relying on pip's internals work.
    virtualenv.thaw()
    if pip_spec == 'pip==latest':
        pip_spec = 'pip'
    virtualenv.pyrun(('-m', 'pip',
                      '--disable-pip-version-check',
                      'install', '-U', pip_spec))
    virtualenv.pyexec(DALS(
        '''
        from plover_plugins_manager import global_registry
        global_registry.list_plugins()
        '''
    ))
