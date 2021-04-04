import pytest

from . import VirtualEnv


def _virtualenv_fixture(cloaked):
    def fn(workspace):
        venv = VirtualEnv(workspace, cloaked=cloaked)
        if cloaked:
            venv.freeze()
        yield venv
        if cloaked:
            venv.thaw()
        # Workaround workspace not cleaning itself as it should...
        venv.workspace.delete = True
        venv.workspace.teardown()
    return fn

virtualenv = pytest.fixture(_virtualenv_fixture(True))
naked_virtualenv = pytest.fixture(_virtualenv_fixture(False))
