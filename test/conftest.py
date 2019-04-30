import pytest

from . import VirtualEnv


@pytest.fixture
def virtualenv(workspace):
    venv = VirtualEnv(workspace)
    venv.freeze()
    yield venv
    venv.thaw()
    # Workaround workspace not cleaning itself as it should...
    venv.workspace.delete = True
    venv.workspace.teardown()
