from distutils import sysconfig
import ast
import importlib
import os
import stat
import textwrap
import venv

from path import Path
import pkg_resources


def DALS(s):
    "dedent and left-strip"
    return textwrap.dedent(s).lstrip()

def patch_file(filename, replace_old, replace_new, optional=True):
    with open(filename, 'r') as fp:
        contents = fp.read()
    assert optional or replace_old in contents
    contents = contents.replace(replace_old, replace_new)
    with open(filename, 'w') as fp:
        fp.write(contents)


class VirtualEnv:

    def __init__(self, workspace, cloaked=True):
        self.workspace = workspace
        self.venv = workspace.workspace / 'venv'
        self.site_packages = Path(sysconfig.get_python_lib(prefix=self.venv))
        venv.create(self.venv, with_pip=False)
        # Create fake home directory.
        self.home = self.workspace.workspace / 'home'
        self.home.mkdir()
        # Create empty configuration file for Plover.
        self.plover = self.venv / 'plover'
        self.plover.mkdir()
        (self.plover / 'plover.cfg').touch()
        # Install dependencies.
        deps = set()
        resolved = set()
        def resolve_deps(req):
            if req in resolved:
                return
            if isinstance(req, str):
                req = pkg_resources.Requirement(req)
            dist = pkg_resources.get_distribution(req)
            deps.add(dist)
            for sub_req in dist.requires(req.extras):
                resolve_deps(sub_req)
        resolve_deps('plover_plugins_manager')
        for dist in sorted(deps):
            self.clone_distribution(dist)
        if cloaked:
            self._cloak()
        # Set user site packages directory.
        self.user_site = Path(self.pyeval(DALS(
            '''
            import site
            print(repr(site.USER_SITE))
            '''
        ), enable_user_site=False))

    def _cloak(self):
        # Fixup pip so using a virtualenv is not an issue.
        for pip_locations in (
            'pip/_internal/utils/virtualenv.py',
            'pip/_internal/locations.py',
            'pip/locations.py',
        ):
            pip_locations = self.site_packages / pip_locations
            if pip_locations.exists():
                break
        else:
            pip_locations = None
        patch_file(pip_locations,
                   '\ndef running_under_virtualenv():\n',
                   '\ndef running_under_virtualenv():'
                   '\n    return False\n',
                  )
        patch_file(pip_locations,
                   '\ndef virtualenv_no_global():\n',
                   '\ndef virtualenv_no_global():'
                   '\n    return False\n',
                   optional=False,
                  )
        ppm_utils_mod = self.site_packages / 'plover_plugins_manager/utils.py'
        patch_file(ppm_utils_mod,
                   '\ndef running_under_virtualenv():\n',
                   '\ndef running_under_virtualenv():'
                   '\n    return False\n',
                   optional=False,
                  )

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

    def clone_distribution(self, src_dist):
        """
        Clone a distribution from the current
        environment to the virtual environment.
        """
        def clone(src_path, dst_path=None):
            if dst_path is None:
                dst_path = self.site_packages / src_path.name
            dst_dir = dst_path.parent
            if not dst_dir.exists():
                dst_dir.makedirs()
            if src_path.isdir():
                src_path.copytree(dst_path)
            else:
                src_path.copyfile(dst_path)
        src_location = Path(src_dist.location)
        # If we have a RECORD manifest, and it's not an editable install, use that.
        if src_dist.has_metadata('RECORD') and not (src_location / (src_dist.key + '.egg-link')).exists():
            for entry in src_dist.get_metadata_lines('RECORD'):
                src_path = Path(entry.split(',')[0])
                if src_path.endswith('.pyc') or '__pycache__' in src_path.parts():
                    continue
                assert src_path.isabs
                clone(src_location / src_path, self.site_packages / src_path)
            return
        # Copy distribution info.
        clone(Path(src_dist.egg_info))
        # Copy top-level modules.
        if src_dist.has_metadata('top_level.txt'):
            modules = src_dist.get_metadata_lines('top_level.txt')
        else:
            modules = (src_dist.key.replace('-', '_'),)
        for modname in modules:
            # Fix some issue with setuptools + Python 3.6.
            # Got I hate Python packaging...
            if src_dist.key == 'setuptools' and modname == 'dist':
                continue
            spec = importlib.util.find_spec(modname)
            if spec is None or spec.origin is None:
                continue
            origin = Path(spec.origin)
            if origin.name == '__init__.py':
                origin = origin.parent
            clone(origin)
        # Fix missing cffi library...
        if src_dist.key == 'cffi':
            clone(src_location / 'cffi.libs')

    def run(self, cmd, capture=False, enable_user_site=True):
        bindir = self.venv.abspath() / 'bin'
        env = dict(os.environ)
        env.update(dict(
            HOME=str(self.home.abspath()),
            VIRTUAL_ENV=str(self.venv.abspath()),
            PYTHONUSERBASE=str(self.home.abspath()),
            PATH=os.pathsep.join((bindir, env['PATH'])),
        ))
        if enable_user_site:
            env['PYTHONPATH'] = str(self.user_site.abspath())
        elif 'PYTHONPATH' in env:
            del env['PYTHONPATH']
        cmd[0] = bindir / cmd[0]
        return self.workspace.run(cmd, capture=capture, env=env,
                                  cwd=self.plover.abspath())

    def pyrun(self, args, **kwargs):
        return self.run(['python'] + list(args), **kwargs)

    def pyexec(self, script, **kwargs):
        return self.pyrun(['-c', DALS(script)], **kwargs)

    def pyeval(self, script, **kwargs):
        return ast.literal_eval(self.pyexec(script, capture=True, **kwargs))

    def install_plugins(self, args, **kwargs):
        return self.pyrun('-m plover_plugins_manager install'.split() + args, **kwargs)

    def uninstall_plugins(self, args, **kwargs):
        return self.pyrun('-m plover_plugins_manager uninstall -y'.split() + args, **kwargs)

    @staticmethod
    def list_distributions(directory):
        return {
            str(d.as_requirement())
            for d in pkg_resources.find_distributions(directory)
        }

    def list_all_plugins(self, **kwargs):
        return set(self.pyrun('-m plover_plugins_manager '
                              'list_plugins --freeze'.split(),
                              capture=True, **kwargs).strip().split('\n'))

    def list_user_plugins(self):
        return self.list_distributions(self.user_site)
