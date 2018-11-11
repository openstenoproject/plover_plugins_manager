import pytest

from . import VirtualEnv


@pytest.fixture
def virtualenv(workspace):
    virtualenv = VirtualEnv(workspace)
    virtualenv.freeze()
    yield virtualenv
    virtualenv.thaw()
    # Workaround workspace not cleaning itself as it should...
    virtualenv.workspace.delete = True
    virtualenv.workspace.teardown()
