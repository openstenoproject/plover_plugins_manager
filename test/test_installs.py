from path import Path
import ast
import distutils
import importlib
import os
import stat
import textwrap

from virtualenv import create_environment
import pkg_resources
import pytest


TEST_DIR = Path(__file__).parent
TEST_DIST = 'plover-template-system'
TEST_DIST_0_1_0 = TEST_DIST + '==0.1.0'
TEST_DIST_0_2_0 = TEST_DIST + '==0.2.0'
TEST_SDIST_0_1_0 = TEST_DIR / 'plover_template_system-0.1.0.tar.gz'
TEST_WHEEL_0_1_0 = TEST_DIR / 'plover_template_system-0.1.0-py2.py3-none-any.whl'
TEST_WHEEL_0_2_0 = TEST_DIR / 'plover_template_system-0.2.0-py2.py3-none-any.whl'
MANAGER_DIST = str(pkg_resources.get_distribution('plover_plugins_manager').as_requirement())


def DALS(s):
    "dedent and left-strip"
    return textwrap.dedent(s).lstrip()

def patch_file(filename, patch):
    with open(filename, 'r') as fp:
        contents = fp.read()
    contents = patch(contents)
    with open(filename, 'w') as fp:
        fp.write(contents)


class VirtualEnv(object):

    def __init__(self, workspace, use_venv=False):
        self.workspace = workspace
        self.venv = workspace.workspace / 'venv'
        self.site_packages = Path(distutils.sysconfig.get_python_lib(prefix=self.venv))
        create_environment(self.venv, no_setuptools=True, no_pip=True, no_wheel=True)
        lib_dir = self.site_packages / '..'
        (lib_dir / 'no-global-site-packages.txt').unlink()
        # Disable user' site.
        patch_file(lib_dir / 'site.py', lambda s: s.replace(
            '\nENABLE_USER_SITE = None\n',
            '\nENABLE_USER_SITE = False\n',
        ))
        # Create fake home directory.
        self.home = self.workspace.workspace / 'home'
        self.home.mkdir()
        # Create empty configuration file for Plover.
        self.plover = self.venv / 'plover'
        self.plover.mkdir()
        (self.plover / 'plover.cfg').touch()
        # Install dependencies.
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
            self.clone_distribution(dist_name)
        # Fixup pip so using a virtualenv is not an issue.
        pip_locations = self.site_packages / 'pip' / 'locations.py'
        patch_file(pip_locations, lambda s: s.replace(
            '\ndef running_under_virtualenv():\n',
            '\ndef running_under_virtualenv():'
            '\n    return False\n',
        ))
        # Set plugins directory.
        self.plugins_dir = self.pyeval(DALS(
            '''
            from plover.oslayer.config import PLUGINS_DIR
            print(repr(PLUGINS_DIR))
            '''
        ))

    def _chmod_venv(self, add_mode, rm_mode):
        plover_path = self.plover.abspath()
        for dirpath, dirnames, filenames in os.walk(self.venv.abspath(), topdown=False):
            for p in dirnames + filenames:
                p = os.path.join(dirpath, p)
                if p == plover_path:
                    continue
                st_mode = os.lstat(p).st_mode
                if stat.S_ISLNK(st_mode):
                    continue
                old_mode = stat.S_IMODE(st_mode)
                new_mode = (old_mode | add_mode) & ~rm_mode
                # print(p, oct(old_mode), oct(new_mode))
                os.chmod(p, new_mode)

    def freeze(self):
        self._chmod_venv(0, stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)

    def thaw(self):
        self._chmod_venv(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH, 0)

    def clone_distribution(self, dist_name, verbose=False):
        """
        Clone a distribution from the current
        environment to the virtual environment.
        """
        def clone(src_path):
            dst_path = self.site_packages / src_path.name
            isdir = src_path.isdir()
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
        bindir = self.venv.abspath() / 'bin'
        env = dict(os.environ)
        env.update(dict(
            HOME=str(self.home.abspath()),
            VIRTUAL_ENV=str(self.venv.abspath()),
            PATH=os.pathsep.join((bindir, env['PATH'])),
        ))
        cmd[0] = bindir / cmd[0]
        return self.workspace.run(cmd, capture=capture, env=env,
                                  cwd=self.plover.abspath())

    def pyrun(self, args, capture=False):
        return self.run(['python'] + args, capture=capture)

    def pyexec(self, script, capture=False):
        return self.pyrun(['-c', DALS(script)], capture=capture)

    def pyeval(self, script):
        return ast.literal_eval(self.pyexec(script, capture=True))

    def install_plugins(self, args):
        return self.pyrun('-m plover_plugins_manager install'.split() + args)

    def uninstall_plugins(self, args):
        return self.pyrun('-m plover_plugins_manager uninstall -y'.split() + args)

    def list_distributions(self, directory):
        return {
            str(d.as_requirement())
            for d in pkg_resources.find_distributions(directory)
        }

    def list_all_plugins(self):
        return set(self.pyrun('-m plover_plugins_manager '
                              'list_plugins --freeze'.split(),
                              capture=True).strip().split('\n'))

    def list_user_plugins(self):
        return self.list_distributions(self.plugins_dir)


@pytest.fixture
def virtualenv(workspace):
    virtualenv = VirtualEnv(workspace)
    virtualenv.freeze()
    yield virtualenv
    virtualenv.thaw()
    # Workaround workspace not cleaning itself as it should...
    virtualenv.workspace.delete = True
    virtualenv.workspace.teardown()


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

def test_system_plugin_downgrade(virtualenv):
    virtualenv.thaw()
    virtualenv.run('python -m pip install'.split() + [TEST_WHEEL_0_2_0])
    virtualenv.freeze()
    assert virtualenv.list_all_plugins() == {MANAGER_DIST, TEST_DIST_0_2_0}
    assert virtualenv.list_user_plugins() == set()
    virtualenv.install_plugins([TEST_WHEEL_0_1_0])
    assert virtualenv.list_all_plugins() == {MANAGER_DIST, TEST_DIST_0_1_0}
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_1_0}
    virtualenv.uninstall_plugins([TEST_DIST])
    assert virtualenv.list_all_plugins() == {MANAGER_DIST, TEST_DIST_0_2_0}
    assert virtualenv.list_user_plugins() == set()

def test_real_user_site_is_ignored_when_disabled(virtualenv):
    real_user_prefix, real_user_site = virtualenv.pyeval(DALS(
        '''
        import site
        print(repr((site.USER_BASE, site.USER_SITE)))
        '''
    ))
    virtualenv.run('python -m pip install --user'.split() + [TEST_WHEEL_0_1_0])
    assert virtualenv.list_distributions(real_user_site) == {TEST_DIST_0_1_0}
    assert virtualenv.list_all_plugins() == {MANAGER_DIST}
    assert virtualenv.list_user_plugins() == set()
    virtualenv.install_plugins([TEST_WHEEL_0_1_0])
    assert virtualenv.list_all_plugins() == {MANAGER_DIST, TEST_DIST_0_1_0}
    assert virtualenv.list_user_plugins() == {TEST_DIST_0_1_0}
