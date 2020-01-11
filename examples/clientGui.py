#!/usr/bin/env python

import sys
from PySide2 import QtCore, QtWidgets

from pyRpc import RpcConnection, RpcResponse


class Window(QtWidgets.QMainWindow):
    remoteCallFinished = QtCore.Signal(RpcResponse)

    def __init__(self):
        super(Window, self).__init__()

        widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(widget)

        self.button = QtWidgets.QPushButton("Send command", widget)
        layout.addWidget(self.button)

        self.textEdit = QtWidgets.QPlainTextEdit("Ready to send remote command...", widget)
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)

        self.setCentralWidget(widget)
        self.resize(640, 480)
        self.setWindowTitle("Client Application")

        self._remote = RpcConnection("Server", tcpaddr="127.0.0.1:40000")

        self.remoteCallFinished.connect(self.handleResponse)
        self.button.clicked.connect(self.sendRequest)

    @QtCore.Slot(RpcResponse)
    def handleResponse(self, resp):
        self.textEdit.appendPlainText("""
        Received reply from remote application: 
            Object: %s
            Status: %s
            Error: %s
            Result: %r
        """ % (str(resp), resp.status, resp.error, resp.result))

    def sendRequest(self):
        self.textEdit.appendPlainText("\nSending a remote call to myFunction()...")
        self._remote.call("myFunction",
                          callback=self.remoteCallFinished.emit,
                          args=(1, "a"),
                          kwargs={'flag': True, 'option': "blarg"})

        self.textEdit.appendPlainText("\nSending a remote call to noReturn()...")
        self._remote.call("noReturn", callback=self.remoteCallFinished.emit)

        self.textEdit.appendPlainText("\nSending an async remote call to noReturn()...")
        self._remote.call("noReturn", callback=self.remoteCallFinished.emit, is_async=True)


if __name__ == "__main__":
    import logging

    logger = logging.getLogger("clientGui")
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ch)

    app = QtWidgets.QApplication(sys.argv)
    win = Window()
    win.show()
    app.exec_()
