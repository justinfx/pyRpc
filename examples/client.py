#!/usr/bin/env python

"""
In this example, make sure to start the server first,
as this client will try and communicate immediately.
"""

import time
from pyRpc import RpcConnection


if __name__ == "__main__":

	remote = RpcConnection("Server", tcpaddr="127.0.0.1:40000")
	time.sleep(.1)

	print "Calling myFunction()"

	resp = remote.call("myFunction", 
				args=(1, "a"), 
				kwargs={'flag':True, 'option':"blarg"})

	print resp, resp.result
