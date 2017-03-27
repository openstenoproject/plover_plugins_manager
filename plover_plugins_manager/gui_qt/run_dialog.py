
from PyQt5.QtWidgets import QDialogButtonBox, QDialog

from plover_plugins_manager.gui_qt.console_widget import ConsoleWidget
from plover_plugins_manager.gui_qt.run_dialog_ui import Ui_RunDialog


class RunDialog(QDialog, Ui_RunDialog):

    def __init__(self, run_args, popen=None):
        super(RunDialog, self).__init__()
        self.setupUi(self)
        self._console = ConsoleWidget(popen)
        self.layout().replaceWidget(self.console, self._console)
        self.buttonBox.button(QDialogButtonBox.Ok).setDisabled(True)
        self._console.processFinished.connect(self.on_process_finished)
        self._console.run(run_args)
        self._successful = None

    def on_process_finished(self, returncode):
        self._successful = returncode == 0
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(self._successful)
        self.buttonBox.button(QDialogButtonBox.Cancel).setDisabled(self._successful)

    def reject(self):
        if self._successful is not None:
            super(RunDialog, self).reject()
            return
        self._console.terminate()
        self.buttonBox.button(QDialogButtonBox.Cancel).setDisabled(True)


if '__main__' == __name__:
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    dlg = RunDialog(sys.argv[1:])
    dlg.show()
    app.exec_()
