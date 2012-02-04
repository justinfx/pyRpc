#!/usr/bin/env python

import sys, time
from PyQt4 import QtCore, QtGui

from pyRpc import PyRpc


class Window(QtGui.QMainWindow):
    
    feedbackReady = QtCore.pyqtSignal(str)
    
    def __init__(self):
        super(Window, self).__init__()

        widget = QtGui.QWidget(self)
        layout = QtGui.QVBoxLayout(widget)
        
        self.textEdit = QtGui.QPlainTextEdit("Waiting on remote commands...", widget)
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)
       
        self.setCentralWidget(widget)
        self.resize(640,480)
        self.setWindowTitle("Server Application")
        
        self.feedbackReady.connect(self._handleFeedback)
        
        #
        # Set up the RPC service
        #
        self._server = PyRpc("Server", tcpaddr="127.0.0.1:40000")
        self._server.publishService(self.myFunction)
        self._server.publishService(self.noReturn)
        self._server.start()
    
    def closeEvent(self, event):
        self._server.stop()
        super(Window, self).closeEvent(event)
    
    def myFunction(self, *args, **kwargs):
        "This does something and returns values"
        self.feedbackReady.emit("Received remote function call\n")
        time.sleep(2)
        self.feedbackReady.emit("Sending back return values\n")
        return args, kwargs
    
    def noReturn(self, value=1):
        "This does something and returns nothing"
        self.feedbackReady.emit("Received remote function call to method with no return\n")
        time.sleep(2)


    @QtCore.pyqtSlot(str)
    def _handleFeedback(self, val):
        self.textEdit.appendPlainText(val)
        
    
if __name__ == "__main__":

    import logging

    logger = logging.getLogger("clientGui")
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    
    app = QtGui.QApplication(sys.argv)
    win = Window()
    win.show()
    app.exec_()  
    
    
      