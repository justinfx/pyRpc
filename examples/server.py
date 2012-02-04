#!/usr/bin/env python

import sys, time
from PyQt4 import QtCore

import pyRpc

def main():
    
    app = QtCore.QCoreApplication(sys.argv)
    server = pyRpc.PyRpc("Server", tcpaddr="127.0.0.1:40000")
    server.publishService(myFunction)
    server.publishService(noReturn)
    server.start()
    
    
    try:
        while True:
            time.sleep(.5)
    except KeyboardInterrupt:
        server.stop()
    

def myFunction(*args, **kwargs):
    "This does something and returns values"
    time.sleep(2)
    return args, kwargs

def noReturn(value=1):
    "This does something and returns nothing"
    print "noReturn() called!"
    time.sleep(2)
    print "noReturn() done!"
    return 1


if __name__ == "__main__":
    main()