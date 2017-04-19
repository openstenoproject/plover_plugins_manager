#!/usr/bin/env python3

from setuptools import setup
from setuptools.command.build_py import build_py


build_dependencies = []
cmdclass = {}


class CustomBuildPy(build_py):

    def run(self):
        for command in build_dependencies:
            self.run_command(command)
        build_py.run(self)

cmdclass['build_py'] = CustomBuildPy


try:
    from pyqt_distutils.build_ui import build_ui
except ImportError:
    pass
else:
    class BuildUi(build_ui):

        def run(self):
            build_ui.run(self)

    cmdclass['build_ui'] = BuildUi
    build_dependencies.append('build_ui')


setup(cmdclass=cmdclass)
