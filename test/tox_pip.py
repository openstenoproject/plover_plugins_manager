import sys

import pkg_resources


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    pip_dist = pkg_resources.get_distribution('pip')
    pip_main = pip_dist.load_entry_point('console_scripts', 'pip')
    command = None
    for a in args:
        if not a.startswith('-'):
            command = a
            break
    if command == 'install' and '-e' in args and \
       pip_dist.parsed_version >= pkg_resources.parse_version('19.0'):
        args.append('--no-use-pep517')
    return pip_main(args)

if __name__ == '__main__':
    sys.exit(main())
