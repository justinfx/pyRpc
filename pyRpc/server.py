
"""
pyRpc -server.py 

Remote Procedure Call support, for exposing local function as public
services, and calling public services on remote applications
Wraps around ZeroMQ for messaging.

Written by:

    Justin Israel (justinisrael@gmail.com)
    justinfx.com
    March 22, 2011


Copyright (c) 2012, Justin Israel (justinisrael@gmail.com) 
All rights reserved. 

Redistribution and use in source and binary forms, with or without 
modification, are permitted provided that the following conditions are met: 

 * Redistributions of source code must retain the above copyright notice, 
   this list of conditions and the following disclaimer. 
 * Redistributions in binary form must reproduce the above copyright 
   notice, this list of conditions and the following disclaimer in the 
   documentation and/or other materials provided with the distribution. 
 * Neither the name of justinfx.com nor the names of its contributors may 
   be used to endorse or promote products derived from this software 
   without specific prior written permission. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
POSSIBILITY OF SUCH DAMAGE. 

"""

from threading import Thread, current_thread
import logging
import inspect

import zmq
from zmq import ZMQError

from pyRpc.constants import TEMPDIR

logger = logging.getLogger(__name__)

############################################################# 
#############################################################
######## PyRpc
############################################################# 
############################################################# 
class PyRpc(Thread):
    """
    PyRpc (threading.Thread)
    
    Used by a class that wants to publish local methods and
    functions for public availability. Runs as a thread.

    By default a new PyRpc object uses the ipc protocol, which
    is meant for processes running on the same host machine.
    If you would like to export your services over tcp, you 
    can optionally specificy a tcpaddr ip:port to use.
    
    Usage:
        myRpc = PyRpc("com.myCompany.MyApplication") # can be any useful name
        myRpc.publishService(myFunction)
        myRpc.publishService(myFunction2)
        myRpc.start()
    """
    
    
    def __init__(self, name, tcpaddr=None, context=None, workers=1):
        """
        __init__(str name, str tcpaddr=None, Context content=None)

        Create a new RPC object that can export services to clients.

        str name    - the name of this Application
        str tcpaddr - if None, use a local IPC connection. 
                        Otherwise this should be a ip:port address (127.0.0.1:8000)

        context     - Optionally pass in another pyzmq Context
        int workers - Specify the number of worker threads to start, for 
                        processing incoming requests. Default is to only start 
                        a single worker.

        Please note that the Context will be closed when the server is stopped. 
        """

        super(PyRpc, self).__init__()
        
        self._context = context or zmq.Context.instance()

        if tcpaddr:
            self._address = "tcp://%s" % tcpaddr
        else:
            self._address = "ipc://%s/%s.ipc" % (TEMPDIR, name)
        
        self.exit_request = False
        
        self._services = {}
        self._worker_url = "inproc://workers"

        self._num_threads = max(int(workers), 1)

        self.receiver = self.dealer = None


    def _worker_routine(self):
        socket = self._context.socket(zmq.REP)
        socket.connect(self._worker_url)

        while not self.exit_request:

            try:

                req = socket.recv_pyobj()
                logger.debug("request received by thread %s: %s" % (current_thread().name, req))

                resp = RpcResponse()
        
                if req.method == "__services__":
                    service = {'method' : self._serviceListReq}
                else:
                    service = self.services.get(req.method, None)

                if not service:
                    resp.result = None
                    resp.status = -1
                    resp.error = "Non-existant service: %s" % req.method

                else:
                    try:
                        resp.result = service['method'](*req.args, **req.kwargs)
                        resp.status = 0
                    except Exception as e:
                        resp.status = 1
                        resp.result = None
                        resp.error = str(e)

                socket.send_pyobj(resp)
                logger.debug("sent response: %s" % resp)
            
            except ZMQError as e:
                if e.errno == zmq.ETERM and self.exit_request:
                    break
                else:
                    socket.close()
                    raise

        socket.close()
        logger.debug("Worker thread %s exiting" % current_thread().name)


    def run(self):
        """ Not to be called directly. Use start() """

        logger.debug("Starting RPC thread loop w/ %d worker(s)" % self._num_threads)
       
        self.receiver = self._context.socket(zmq.ROUTER)
        self.receiver.bind(self._address)
        logger.debug("Listening @ %s" % self._address)

        self.dealer = self._context.socket(zmq.DEALER)
        self.dealer.bind(self._worker_url)

        for i in range(self._num_threads):
            thread = Thread(target=self._worker_routine, name="RPC-Worker-%d" % (i+1))
            thread.daemon=True
            thread.start()

        try:
            # blocking
            ret = zmq.device(zmq.QUEUE, self.receiver, self.dealer)

        except ZMQError as e:
            # stop() generates a valid ETERM, otherwise its unexpected
            if not (e.errno == zmq.ETERM and self.exit_request):
                raise
        finally:
            self.receiver.close()
            self.dealer.close()

    def start(self):
        """
        start()

        Start the RPC server.
        """
        if self.receiver is not None:
            raise RuntimeError("Cannot start RPC Server more than once.")

        super(PyRpc, self).start()  

    def stop(self):
        """ 
        stop()
        
        Stop the server thread process
        """
        logger.debug("Stop request made for RPC thread loop")
        self.exit_request = True

        if self.receiver:
            self.receiver.close()
        if self.dealer:
            self.dealer.close()

        self._context.term()

    def publishService(self, method):
        """
        publishService (object method)
        
        Publishes the given callable, to be made available to
        remote procedure calls.
        """
        name = method.__name__
        argSpec = inspect.getargspec(method)
        spec = argSpec.args
        if argSpec.varargs:
            spec.append("*%s" % argSpec.varargs)
        if argSpec.keywords:
            spec.append("**%s" % argSpec.keywords)
        
        self._services[name] = {'format' : "%s(%s)" % (name, ', '.join(spec)), 'method' : method, 'doc' : method.__doc__}
    
    def _serviceListReq(self):
        services = []
        for name, v in self.services.items():
            services.append({'service' : name, 'format' : v['format'], 'doc' : v['doc']})
        return services
    
    @property
    def services(self):
        """
        Property for returning the currently published services
        """
        return self._services


           
############################################################# 
#############################################################
######## RpcResponse
############################################################# 
#############################################################     
class RpcResponse(object):
    """
    RpcResponse
    
    Represents a response message from a remote call.
    Wraps around the result from the remote call.
    Used by splRpc when replying to a call from RpcConnection.
    """
    
    def __init__(self, result=None, status=-1, error=None):
        self._status = status
        self._result = result
        self._error  = error

    def __repr__(self):
        return "<%s: status:%d>" % (self.__class__.__name__, self.status)
            
    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, v):
        if not isinstance(v, int):
            raise TypeError("status value must be an int")
        self._status = v
        
    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, v):
        self._result = v
        
    @property
    def error(self):
        return self._error
    
    @error.setter
    def error(self, v):
        self._error = v
