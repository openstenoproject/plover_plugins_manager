
from threading import Thread
import atexit
import html
import os
import sys

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QMessageBox, QTableWidgetItem, QInputDialog

from plover.gui_qt.tool import Tool

from plover_plugins_manager.gui_qt.info_browser import InfoBrowser
from plover_plugins_manager.gui_qt.manager_ui import Ui_PluginsManager
from plover_plugins_manager.gui_qt.run_dialog import RunDialog
from plover_plugins_manager.registry import Registry
from plover_plugins_manager.utils import description_to_html
from plover_plugins_manager.__main__ import pip


class PluginsManager(Tool, Ui_PluginsManager):

    TITLE = 'Plugins Manager'
    ROLE = 'plugins_manager'
    ICON = ':/plugins_manager/icon.svg'

    # We use a class instance so the state is persistent
    # accross different executions of the dialog when
    # the user does not restart.
    _packages = None
    _packages_updated = pyqtSignal()

    def __init__(self, engine):
        super().__init__(engine)
        self.setupUi(self)
        self.uninstall_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self._engine = engine
        self.info = InfoBrowser()
        self.info_frame.layout().addWidget(self.info)
        self.table.sortByColumn(1, Qt.AscendingOrder)
        self._packages_updated.connect(self._on_packages_updated)
        if self._packages is None:
            PluginsManager._packages = Registry()
        self._on_packages_updated()
        self.on_refresh()

    def _need_restart(self):
        for state in self._packages:
            if state.status in ('removed', 'updated'):
                return True
        return False

    def _on_packages_updated(self):
        self.restart_button.setEnabled(self._need_restart())
        self.progress.hide()
        self.refresh_button.show()
        self._update_table()
        self.setEnabled(True)

    def _update_table(self):
        self.table.setCurrentItem(None)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._packages))
        for row, state in enumerate(self._packages):
            for column, attr in enumerate('status name version summary'.split()):
                item = QTableWidgetItem(getattr(state, attr, "N/A"))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

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

    @staticmethod
    def _run(args):
        dialog = RunDialog(args, popen=pip)
        code = dialog.exec_()
        # dialog.destroy()
        return code

    def on_selection_changed(self):
        can_install, can_uninstall = self._get_selection()
        self.uninstall_button.setEnabled(bool(can_uninstall))
        self.install_button.setEnabled(bool(can_install))
        self._clear_info()
        current_item = self.table.currentItem()
        if current_item is None:
            return
        metadata = self._get_state(current_item.row()).metadata
        if metadata is None:
            return
        prologue = '<h1>%s (%s)</h1>' % (
            html.escape(metadata.name),
            html.escape(metadata.version),
        )
        if metadata.author and metadata.author_email:
            prologue += '<p><b>Author: </b><a href="mailto:%s">%s</a></p>' % (
                html.escape(metadata.author_email),
                html.escape(metadata.author),
            )
        if metadata.home_page:
            prologue += '<p><b>Home page: </b><a href="%s">%s</a></p>' % (
                metadata.home_page,
                html.escape(metadata.home_page),
            )
        prologue += '<hr>'
        if metadata.description:
            description = metadata.description
            description_content_type = metadata.description_content_type
        else:
            description = metadata.summary
            description_content_type = None
        css, description = description_to_html(description, description_content_type)
        self.info.setHtml(css + prologue + description)

    def on_restart(self):
        if self._engine is not None:
            self._engine.restart()
        else:
            atexit._run_exitfuncs()
            args = [sys.executable, '-m', __spec__.name]
            os.execv(args[0], args)

    def _update_packages(self):
        self._packages.update()
        self._packages_updated.emit()

    def _clear_info(self):
        self.info.setHtml('')

    def on_refresh(self):
        Thread(target=self._update_packages).start()
        self._clear_info()
        self.setEnabled(False)
        self.refresh_button.hide()
        self.progress.show()

    def on_install_git(self):
        url, ok = QInputDialog.getText(
            self, "Install from Git repo", 
            'Enter repository link for plugin\n'
            '(will look similar to '
            'https://github.com/user/repository.git): '
            )
        if not ok:
            return
        if QMessageBox.warning(
            self, 'Install from Git repo', 
            'Installing plugins is a <b>security risk</b>. '
            'A plugin from a Git repo can contain malicious code. '
            'Only install it if you got it from a trusted source.'
            ' Are you sure you want to proceed?'
            ,
            buttons=QMessageBox.Yes | QMessageBox.No,
            defaultButton=QMessageBox.No
        ) != QMessageBox.Yes:
            return
        code = self._run(
            ['install'] +
            ['git+' + url]
        )
        if code == QDialog.Accepted:
            self._update_table()
            self.restart_button.setEnabled(True)
           
    def on_install(self):
        packages = self._get_selection()[0]
        if QMessageBox.warning(
            self, 'Install ' + ', '.join(packages), 
            'Installing plugins is a <b>security risk</b>. '
            'A plugin can contain virus/malware. '
            'Only install it if you got it from a trusted source.'
            ' Are you sure you want to proceed?'
            ,
            buttons=QMessageBox.Yes | QMessageBox.No,
            defaultButton=QMessageBox.No
        ) != QMessageBox.Yes:
            return
        code = self._run(
            ['install'] +
            [self._packages[name].latest.requirement
             for name in packages]
        )
        if code == QDialog.Accepted:
            for name in packages:
                state = self._packages[name]
                state.current = state.latest
            self._update_table()
            self.restart_button.setEnabled(True)

    def on_uninstall(self):
        packages = self._get_selection()[1]
        code = self._run(['uninstall', '-y'] + packages)
        if code == QDialog.Accepted:
            for name in packages:
                state = self._packages[name]
                state.current = None
            self._update_table()
            self.restart_button.setEnabled(True)


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    dlg = PluginsManager(None)
    dlg.show()
    app.exec_()
