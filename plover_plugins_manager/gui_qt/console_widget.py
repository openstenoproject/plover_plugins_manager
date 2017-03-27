
import os
import signal
import subprocess
import threading

from PyQt5.QtCore import (
    QVariant,
    pyqtSignal,
)
from PyQt5.QtGui import QFontDatabase, QFontMetrics
from PyQt5.QtWidgets import QWidget

from plover_plugins_manager.gui_qt.console_widget_ui import Ui_ConsoleWidget


NULL = open(os.devnull, 'r+b')


class ConsoleWidget(QWidget, Ui_ConsoleWidget):

    textOutput = pyqtSignal(str)
    processFinished = pyqtSignal(QVariant)

    def __init__(self, popen=None):
        super(ConsoleWidget, self).__init__()
        self.setupUi(self)
        self.textOutput.connect(self.output.append)
        self._popen = subprocess.Popen if popen is None else popen
        self._proc = None
        self._thread = None
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        metrics = QFontMetrics(font)
        self.output.setMinimumSize(80 * metrics.maxWidth(),
                                   24 * metrics.height())
        self.output.setCurrentFont(font)

    def run(self, args):
        assert self._thread is None
        self._proc = self._popen(args, stdin=NULL,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        self._thread = threading.Thread(target=self._subprocess)
        self._thread.start()

    def terminate(self):
        assert self._proc is not None
        self._proc.send_signal(signal.SIGINT)
        self._proc.stdout.close()
        self._proc.terminate()
        self._thread.join()

    def _subprocess(self):
        while True:
            try:
                line = self._proc.stdout.readline()
            except:
                break
            if not line:
                break
            line = line.decode()
            if line.endswith(os.linesep):
                line = line[:-len(os.linesep)]
            print(line)
            self.textOutput.emit(line)
        self.processFinished.emit(self._proc.wait())
