
from collections import OrderedDict, namedtuple
import atexit
import cgi
import itertools
import os
import sys

from docutils.core import publish_parts

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QDialog, QTableWidgetItem

from plover.gui_qt.tool import Tool

from plover_plugins_manager.gui_qt.manager_ui import Ui_PluginsManager
from plover_plugins_manager.gui_qt.run_dialog import RunDialog
from plover_plugins_manager import global_registry, local_registry
from plover_plugins_manager.__main__ import pip


def _rst_to_html(text):
    html = publish_parts(text, writer_name='s5_html')
    return html['stylesheet'], html['html_title'] + html['body']


class PluginsManager(Tool, Ui_PluginsManager):

    TITLE = 'Plugins Manager'
    ROLE = 'plugins_manager'
    ICON = ':/icon.svg'

    class PackageState(object):

        def __init__(self, status, name, current, latest):
            self.status = status
            self.name = name
            self.current = current
            self.latest = latest

        @property
        def metadata(self):
            return self.current or self.latest

        def __getitem__(self, key):
            if key == 'name':
                return self.name
            if key == 'status':
                return self.status
            m = self.metadata
            if m:
                return getattr(m, key)
            return ''


    # We use a class instance so the state is persistent
    # accross different executions of the dialog when
    # the user does not restart.
    _packages = OrderedDict()

    def __init__(self, engine):
        super(PluginsManager, self).__init__(engine)
        self.setupUi(self)
        self._engine = engine
        self.table.sortByColumn(1, Qt.AscendingOrder)
        if not self._packages:
            self._update_packages()
        for state in self._packages.values():
            if state.status in ('updated', 'removed'):
                need_restart = True
                break
        else:
            need_restart = False
        self.restart_button.setEnabled(need_restart)
        self._update_table()

    def _update_packages(self):
        installed_plugins = local_registry.list_plugins()
        available_plugins = global_registry.list_plugins()
        for name, installed, available in sorted(
            (name,
             installed_plugins.get(name, []),
             available_plugins.get(name, []))
            for name in set(itertools.chain(installed_plugins,
                                            available_plugins))
        ):
            current = installed[-1] if installed else None
            latest = available[-1] if available else None
            if current:
                if latest and latest.parsed_version > current.parsed_version:
                    status = 'outdated'
                else:
                    status = 'installed'
            else:
                status = ''
            self._packages[name] = self.PackageState(status, name, current, latest)

    def _update_table(self):
        self.table.setRowCount(0)
        row = 0
        for state in self._packages.values():
            self.table.insertRow(row)
            for column, field in enumerate('status name version summary'.split()):
                item = QTableWidgetItem(state[field])
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, item)
            row += 1
        self.table.resizeColumnsToContents()
        self.uninstall_button.setEnabled(False)
        self.install_button.setEnabled(False)

    def _get_state(self, row):
        name = self.table.item(row, 1).data(Qt.DisplayRole)
        return self._packages[name]

    def _get_selection(self):
        can_install = []
        can_uninstall = []
        for item in self.table.selectedItems():
            if item.column() != 0:
                continue
            state = self._get_state(item.row())
            if state.status in ('installed', 'updated'):
                can_uninstall.append(state.name)
            elif state.status in ('outdated',):
                can_uninstall.append(state.name)
                can_install.append(state.name)
            elif state.latest:
                can_install.append(state.name)
        return can_install, can_uninstall

    def _run(self, args):
        dialog = RunDialog(args, popen=pip)
        code = dialog.exec_()
        # dialog.destroy()
        return code

    def on_selection_changed(self):
        can_install, can_uninstall = self._get_selection()
        self.uninstall_button.setEnabled(bool(can_uninstall))
        self.install_button.setEnabled(bool(can_install))
        self.info.setUrl(QUrl(''))
        current_item = self.table.currentItem()
        if current_item is None:
            return
        metadata = self._get_state(current_item.row()).metadata
        if metadata is None:
            return
        prologue = '<h1>%s (%s)</h1>' % (
            cgi.escape(metadata.name),
            cgi.escape(metadata.version),
        )
        if metadata.author and metadata.author_email:
            prologue += '<p><b>Author: </b><a href="mailto:%s">%s</a></p>' % (
                cgi.escape(metadata.author_email),
                cgi.escape(metadata.author),
            )
        if metadata.home_page:
            prologue += '<p><b>Home page: </b><a href="%s">%s</a></p>' % (
                metadata.home_page,
                cgi.escape(metadata.home_page),
            )
        prologue += '<hr>'
        css, description = _rst_to_html(metadata.description or metadata.summary)
        self.info.setHtml(css + prologue + description)

    def on_restart(self):
        if self._engine is not None:
            self._engine.restart()
        else:
            atexit._run_exitfuncs()
            args = sys.argv[:]
            if args[0].endswith('.py') or args[0].endswith('.pyc'):
                args.insert(0, sys.executable)
            os.execv(args[0], args)

    def on_install(self):
        packages = self._get_selection()[0]
        code = self._run(
            ['install'] +
            [self._packages[name].latest.requirement
             for name in packages]
        )
        if code == QDialog.Accepted:
            for name in packages:
                state = self._packages[name]
                state.current = state.latest
                state.status = 'updated'
            self._update_table()
            self.restart_button.setEnabled(True)

    def on_uninstall(self):
        packages = self._get_selection()[1]
        code = self._run(['uninstall', '-y'] + packages)
        if code == QDialog.Accepted:
            for name in packages:
                state = self._packages[name]
                state.current = None
                state.status = 'removed'
            self._update_table()
            self.restart_button.setEnabled(True)


if '__main__' == __name__:
    from PyQt5.QtWidgets import QApplication
    from plover.registry import registry
    registry.update()
    app = QApplication([])
    dlg = PluginsManager(None)
    dlg.show()
    app.exec_()
