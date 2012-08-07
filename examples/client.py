#!/usr/bin/env python

"""
In this example, make sure to start the server first,
as this client will try and communicate immediately.
"""

import time
from pyRpc import RpcConnection

import logging
# logging.basicConfig(level=logging.DEBUG)

ASYNC_CALLS = 0

def callback(resp, *args, **kwargs):
	global ASYNC_CALLS
	print "Got slow response:", resp.result
	ASYNC_CALLS += 1

if __name__ == "__main__":

	remote = RpcConnection("Server", workers=1)

	# if the server were using a TCP connection:
	# remote = RpcConnection("Server", tcpaddr="127.0.0.1:40000")

	time.sleep(.1)

	print "Calling slow()"

	for i in xrange(5):	
		remote.call("slow", async=True, callback=callback)

	print "Calling fast()"
	resp = remote.call("fast")
	print "Got fast response:", resp.result

	print "Waiting on async calls to finish"
	while ASYNC_CALLS < 5:
		time.sleep(.1)

