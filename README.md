## pyRpc
### A simple remote procedure call module using ZeroMQ

Remote Procedure Call support, for exposing local function as public
services, and calling public services on remote applications.

Wraps around ZeroMQ for messaging.
http://www.zeromq.org/

This is a very basic module that allows you to create an application which exports various
functions as services, and then to have client apps call these services almost like
a native python call. 

### Requirements

This module uses ZeroMQ for the messaging functionality: http://www.zeromq.org/
It should get installed by the setup.py installation process. But on some
systems you may need to install this seperately.

The GUI-based examples require PyQt4:
http://www.riverbankcomputing.co.uk/software/pyqt/download
http://qt.nokia.com/downloads

### Install

Download and:
<code>>>> python setup.py install</code>

or 
<code>>>> pip install pyRpc</code>

or
<code>>>> easy_install pyRpc</code>


### Basic Example

#### Exporting functions as services (server)

```python
import time
from pyRpc import PyRpc

def add(a, b):
	""" Returns a + b """
	return a+b

def favoriteColor():
	""" Tell you our favorite color """
	return "red"

myRpc = PyRpc("com.myCompany.MyApplication") 
time.sleep(.1)

myRpc.publishService(add)
myRpc.publishService(favoriteColor)
myRpc.start()

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    myRpc.stop()

```

#### Calling remote services from a client

```python
import time
from pyRpc import RpcConnection

def response(resp):
	print "Got response:", resp
	print "1 + 2 =", resp.result
	 
remote = RpcConnection("com.myCompany.MyApplication")
time.sleep(.1)

# we can ask the remote server what services are available
resp = remote.availableServices()
for service in resp.result:
	print "\nService: %(service)s \nDescription: %(doc)s \nUsage: %(format)s\n" % service


# calls remote add() and does not wait. Result will be returned to response()
remote.call("add", args=(1, 2), callback=response)

# blocks while waiting for a response
resp = remote.call("favoriteColor")
print "Favorite color:", resp.result

time.sleep(1)

remote.close()

time.sleep(1)

```

