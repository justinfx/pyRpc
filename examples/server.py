#!/usr/bin/env python

import sys, time
import pyRpc

import logging

logging.basicConfig(level=logging.DEBUG)


def main():
    
    # using local IPC communication    
    server = pyRpc.PyRpc("Server", workers=2)

    # Could have used a TCP connection if we wanted:
    # server = pyRpc.PyRpc("Server", tcpaddr="127.0.0.1:40000")


    time.sleep(.1)

    server.publishService(slow)
    server.publishService(fast)
    server.publishService(noReturn)
    server.start()
    
    
    try:
        while True:
            time.sleep(.5)
    except KeyboardInterrupt:
        server.stop()
    
counter = 0

def slow(*args, **kwargs):
    "This does something and returns values"

    global counter 

    print "slow() called! Doing some stuff."
    time.sleep(3)
    print "Done!"
    counter += 1
    return counter

def fast(*args, **kwargs):
    "This does something and returns values"

    global counter 

    print "fast() called! Doing some stuff."
    counter += 1
    return counter

def noReturn(value=1):
    "This does something and returns nothing"
    print "noReturn() called!"
    time.sleep(2)
    print "noReturn() done!"
    return 1


if __name__ == "__main__":
    main()