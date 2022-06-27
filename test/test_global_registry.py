import sys

import pytest

from . import DALS


DEP_SPECS = (
    'pip==18.0', 'pip==latest',
)

_py_ver = sys.version_info[:2]

if _py_ver < (3, 9):
    DEP_SPECS += (
        'requests-cache==0.5.0',
        'requests-cache==0.7.0',
    )
    if _py_ver >= (3, 7):
        DEP_SPECS += (
            'requests-cache==0.8.0',
        )

if _py_ver >= (3, 7):
    DEP_SPECS += (
        'requests-cache==0.9.1',
    )

DEP_SPECS += (
    'requests-cache==latest',
)


@pytest.mark.parametrize('dep_spec', DEP_SPECS)
def test_global_registry_deps_support(virtualenv, dep_spec):
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
