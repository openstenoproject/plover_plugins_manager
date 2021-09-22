import pytest

from . import DALS


@pytest.mark.parametrize('dep_spec', (
    'pip==9.0.3', 'pip==10.0', 'pip==18.0', 'pip==latest',
    'requests-cache==0.5.0', 'requests-cache==0.7.0',
    'requests-cache==0.8.0', 'requests-cache==latest'
))
def test_global_registry_deps_support(virtualenv, dep_spec):
    # Simple test to check the code relying on pip's internals work.
    virtualenv.thaw()
    if dep_spec.endswith('==latest'):
        dep_spec = dep_spec[:-len('==latest')]
    virtualenv.pyrun(('-m', 'pip',
                      '--disable-pip-version-check',
                      'install', '-U', dep_spec))
    virtualenv.pyexec(DALS(
        '''
        from plover_plugins_manager import global_registry
        global_registry.list_plugins()
        '''
    ))
