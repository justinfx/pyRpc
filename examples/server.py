#!/usr/bin/env python

import sys, time
import pyRpc

def main():
    
    # using local IPC communication    
    server = pyRpc.PyRpc("Server")

    # Could have used a TCP connection if we wanted:
    # server = pyRpc.PyRpc("Server", tcpaddr="127.0.0.1:40000")


    time.sleep(.1)

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
    print "myFunction() called! Doing some stuff."
    time.sleep(2)
    print "Done!"
    return args, kwargs

def noReturn(value=1):
    "This does something and returns nothing"
    print "noReturn() called!"
    time.sleep(2)
    print "noReturn() done!"
    return 1


if __name__ == "__main__":
    main()