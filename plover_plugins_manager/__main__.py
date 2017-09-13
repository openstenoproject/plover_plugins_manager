
import itertools
import os
import subprocess
import site
import sys
import textwrap

from plover.oslayer.config import PLUGINS_BASE, PLUGINS_DIR

from plover_plugins_manager import global_registry
from plover_plugins_manager import local_registry


def list_plugins(freeze=False):
    installed_plugins = local_registry.list_plugins()
    if freeze:
        available_plugins = {}
    else:
        available_plugins = global_registry.list_plugins()
    for name, installed, available in sorted(
        (name,
         installed_plugins.get(name, []),
         available_plugins.get(name, []))
        for name in set(itertools.chain(installed_plugins,
                                        available_plugins))
    ):
        latest = available[-1] if available else None
        current = installed[-1] if installed else None
        info = latest or current
        if freeze:
            if current:
                print('%s==%s' % (current.name, current.version))
            continue
        print('%s (%s)  - %s' % (info.name, info.version, info.summary))
        if current:
            print('  INSTALLED: %s' % current.version)
            if latest:
                print('  LATEST:    %s' % latest.version)


def pip(args, stdin=None, stdout=None, stderr=None):
    cmd = [sys.executable, '-m', 'pip']
    env = dict(os.environ)
    pypath = env.get('PYTHONPATH')
    if pypath is None:
        pypath = []
    else:
        pypath = pypath.split(os.pathsep)
    if site.ENABLE_USER_SITE:
        pypath.insert(0, site.USER_SITE)
    pypath.insert(0, PLUGINS_DIR)
    env['PYTHONPATH'] = os.pathsep.join(pypath)
    env['PYTHONUSERBASE'] = PLUGINS_BASE
    command = args.pop(0)
    if command == 'check':
        cmd.append('check')
    elif command == 'install':
        cmd.extend((
            'install',
            '--user',
            '--upgrade-strategy=only-if-needed',
        ))
    elif command == 'uninstall':
        cmd.append('uninstall')
    elif command == 'list':
        cmd.extend((
            'list',
            '--format=columns',
        ))
    else:
        raise ValueError('invalid command: %s' % command)
    cmd.extend(args)
    return subprocess.Popen(cmd, env=env, stdin=stdin, stdout=stdout, stderr=stderr)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    if args[0] == 'list_plugins':
        assert len(args) <= 2
        if len(args) > 1:
            assert args[1] == '--freeze'
            freeze = True
        else:
            freeze = False
        sys.exit(list_plugins(freeze=freeze))
    proc = pip(args)
    sys.exit(proc.wait())


if '__main__' == __name__:
    main()
