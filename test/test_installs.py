import ast
import distutils
import importlib
import os
import textwrap

from path import Path
from virtualenv import create_environment
import pkg_resources
import pytest


TEST_DIR = Path(__file__).parent
TEST_DIST = 'plover-template-system==0.1.0'
TEST_SDIST = TEST_DIR / 'plover_template_system-0.1.0.tar.gz'
TEST_WHEEL = TEST_DIR / 'plover_template_system-0.1.0-py2.py3-none-any.whl'
MANAGER_DIST = str(pkg_resources.get_distribution('plover_plugins_manager').as_requirement())


def DALS(s):
    "dedent and left-strip"
    return textwrap.dedent(s).lstrip()

def lndir(src, dst):
    os.mkdir(dst)
    dst_to_src = os.path.relpath(src, dst)
    for dirpath, dirnames, filenames in os.walk(src):
        src_path = os.path.join(src, dirpath)
        dst_path = os.path.join(dst, os.path.relpath(dirpath, src))
        for d in dirnames:
            d = os.path.join(dst_path, d)
            os.mkdir(d)
        for f in filenames:
            l = os.path.join(dst_path, f)
            t = os.path.join(src_path, f)
            os.link(t, l)


class VirtualEnv(object):

    def __init__(self, workspace, use_venv=False):
        self.workspace = workspace
        self.venv = workspace.workspace / 'venv'
        self.site_packages = Path(distutils.sysconfig.get_python_lib(prefix=self.venv))
        create_environment(self.venv, no_setuptools=True, no_pip=True, no_wheel=True)
        (self.venv / 'plover.cfg').touch()

    def clone_distribution(self, dist_name, hardlink=False, verbose=False):
        """
        Clone a distribution from the current
        environment to the virtual environment.
        """
        def clone(src_path):
            dst_path = self.site_packages / src_path.name
            isdir = src_path.isdir()
            if hardlink:
                if isdir:
                    lndir(src_path, dst_path)
                else:
                    src_path.link(dst_path)
            else:
                (src_path.copytree if isdir else src_path.copyfile)(dst_path)
        src_dist = pkg_resources.get_distribution(dist_name)
        # Copy distribution info.
        clone(Path(src_dist.egg_info))
        # Copy top-level modules.
        src_location = Path(src_dist.location)
        modules = list(src_dist._get_metadata('top_level.txt'))
        for modname in modules or (dist_name,):
            origin = Path(importlib.util.find_spec(modname).origin)
            if origin.name == '__init__.py':
                origin = origin.parent
            clone(origin)

    def run(self, cmd, capture=False):
        env = dict(os.environ)
        env.update(dict(
            VIRTUAL_ENV=self.venv.abspath(),
            PATH=os.pathsep.join((self.venv.realpath() / 'bin', env['PATH'])),
        ))
        return self.workspace.run(cmd, capture=capture, env=env,
                                  cwd=self.venv.abspath())

    def pyrun(self, args, capture=False):
        return self.run(['python'] + args, capture=capture)

    def pyexec(self, script, capture=False):
        return self.pyrun(['-c', DALS(script)], capture=capture)

    def pyeval(self, script):
        return ast.literal_eval(self.pyexec(script, capture=True))


@pytest.fixture
def virtualenv(workspace):
    virtualenv = VirtualEnv(workspace)
    deps = set()
    def resolve_deps(dist):
        if dist in deps:
            return
        deps.add(dist)
        for req in dist.requires():
            resolve_deps(pkg_resources.get_distribution(req))
    resolve_deps(pkg_resources.get_distribution('plover_plugins_manager'))
    resolve_deps(pkg_resources.get_distribution('PyQt5'))
    for dist_name in sorted(dist.project_name for dist in deps):
        virtualenv.clone_distribution(dist_name, hardlink=True)
    yield virtualenv
    # Workaround workspace not cleaning itself as it should...
    virtualenv.workspace.delete = True
    virtualenv.workspace.teardown()


def list_plugins_dir_dists(virtualenv):
    return virtualenv.pyeval(
        '''
        from pkg_resources import find_distributions
        from plover.oslayer.config import PLUGINS_DIR
        print(repr([str(d.as_requirement())
        for d in find_distributions(PLUGINS_DIR)]))
        '''
    )

def install_plugins(virtualenv, args):
    return virtualenv.pyrun('-m plover_plugins_manager install'.split() + args)

def uninstall_plugins(virtualenv, args):
    return virtualenv.pyrun('-m plover_plugins_manager uninstall -y'.split() + args)


def test_list_plugins(virtualenv):
    assert virtualenv.pyrun('-m plover_plugins_manager '
                            'list_plugins --freeze'.split(),
                            capture=True) == DALS(
                                '''
                                %s
                                ''' % MANAGER_DIST)

def test_sdist_install(virtualenv):
    install_plugins(virtualenv, [TEST_SDIST])
    assert list_plugins_dir_dists(virtualenv) == [TEST_DIST]
    uninstall_plugins(virtualenv, ['plover-template-system'])
    assert list_plugins_dir_dists(virtualenv) == []

def test_wheel_install(virtualenv):
    install_plugins(virtualenv, [TEST_WHEEL])
    assert list_plugins_dir_dists(virtualenv) == [TEST_DIST]
    uninstall_plugins(virtualenv, ['plover-template-system'])
    assert list_plugins_dir_dists(virtualenv) == []
