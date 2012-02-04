
"""
pyRpc

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

import sys
import time
import tempfile
import inspect
import logging

from threading import Thread, current_thread

import zmq

logger = logging.getLogger(__name__)

_TEMPDIR = tempfile.gettempdir()
_CONTEXT = zmq.Context()


############################################################# 
#############################################################
######## splRpc
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
    
    
    def __init__(self, name, tcpaddr=None, context=None):
        """
        __init__(str name, str tcpaddr=None, Context content=None)

        Create a new RPC object that can export services to clients.

        str name    - the name of this Application
        str tcpaddr - if not None, should be a ip:port address (127.0.0.1:8000)

        context     - Optionally pass in another pyzmq Context
        """

        super(PyRpc, self).__init__()
        
        self._context = context or _CONTEXT
        if tcpaddr:
            self._address = "tcp://%s" % tcpaddr
        else:
            self._address = "ipc://%s/%s.ipc" % (_TEMPDIR, name)
        
        self.exit_request = False
        
        self._services = {}

    def run(self):
        """ Not to be called directly. Use start() """

        logger.debug("Starting RPC thread loop")
        
        receiver = self._context.socket(zmq.REP)
        receiver.bind(self._address)
        logger.debug("Listening @ %s" % self._address)
        
        poller = zmq.Poller()
        poller.register(receiver, zmq.POLLIN)
        
        while True:
            
            if self.exit_request:
                logger.debug("Exiting RPC thread loop")
                return
            
            socks = dict(poller.poll(500))
            
            if socks.get(receiver, None) == zmq.POLLIN:

                req = receiver.recv_pyobj()
                logger.debug("request received: %s" % req)

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
                    except Exception, e:
                        resp.status = 1
                        resp.result = None
                        resp.error = str(e)
 
                receiver.send_pyobj(resp)
                logger.debug("sent response: %s" % resp)
    
     
    def start(self):
        """
        start()

        Start the RPC server.
        """
        super(PyRpc, self).start()  
        
    def stop(self):
        """ 
        stop()
        
        Stop the server thread process
        """
        logger.debug("Stop request made for RPC thread loop")
        self.exit_request = True

    
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
        for name, v in self.services.iteritems():
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
######## RpcConnection
############################################################# 
############################################################# 
class RpcConnection(object):
    """
    RpcConnection
    
    For making remote calls to published services in another
    application (or even the same application). Uses multiple
    worker threads to send out calls and process their
    return values.
    
    Usage:
        def processResponse(rpcResponse):
            print rpcResponse.result
    
        rpc = PyRpc.RpcConnection("com.myCompany.MyApplication")  # any useful name
        rpc.call("myFunction", callback=processResponse, args=(1, "a"), kwargs={'flag':True, 'option':"blarg"})
    """    
    
    _THREADS = []
    
    def __init__(self, name, tcpaddr=None, context=None, workers=1):
        
        self._context = context or _CONTEXT
        if tcpaddr:
            self._address = "tcp://%s" % tcpaddr
        else:
            self._address = "ipc://%s/%s.ipc" % (_TEMPDIR, name)
        
        self._sender = self._context.socket(zmq.PUSH)
        self._sender.bind("inproc://workRequest")   

        self.exit_request = False
        self._callbacks = {}
        
        for i in xrange(workers):
            t = Thread(target=self._worker_routine, args=(self._context, self._address))
            t.daemon = True
            t.start()
            self._THREADS.append(t)

        self._receiver = None
                       
    
    def __del__(self):
        logger.debug("closing connection")
        self.close()


    def close(self):
        """
        close()

        Close the client connection
        """
        self.exit_request = True
        
                
    def availableServices(self):
        """
        availableServices() -> RpcResponse
        
        Asks the remote server to tell us what services
        are published.
        Returns an RpcResponse object
        """
        return self.call("__services__")
            
    def call(self, method, callback=None, async=False, args=[], kwargs={}):
        """
        call(str method, object callback=None, bool async=False, list args=[], dict kwargs={})
        
        Make a remote call to the given service name, with an optional callback
        and arguments to be used.
        Can be run either blocking or asynchronously.
        
        By default, this method blocks until a response is received.
        If async=True, returns immediately with an empty RpcResponse. If a callback
        was provided, it will be executed when the remote call returns a result.
        """
        if self._receiver == None:
            self._receiver = self._context.socket(zmq.PULL)
            self._receiver.connect("inproc://workReply")
                      
        req = RpcRequest()
        req.method = method
        req.args   = args
        req.kwargs = kwargs
        req.async  = async
        
        if async or callback:
            if callback:
                req.callback = True
                self._callbacks[req.id] = callback
            else:
                logger.debug("Setting request to async, with no callback")
 
        logger.debug("Sending a RPC call to method: %s" % method)
        self._sender.send_pyobj(req)

        if async or callback:
            return RpcResponse(None, 0, None)
        
        resp = self._receiver.recv_pyobj()
        logger.debug("Got reply to method %s: %s" % (method, resp))
        
        return resp
 
    
    def _worker_routine(self, context, address):
        """
        Worker loop for processing rpc calls.
        """
        logger.debug("Starting local worker thread: %s" % current_thread().name)
        
        receiver = context.socket(zmq.PULL)
        receiver.connect("inproc://workRequest")

        replier = context.socket(zmq.PUSH)
        replier.bind("inproc://workReply")
        
        logger.debug("Making connection to RPC server at: %s" % address)
        remote = context.socket(zmq.REQ)
        remote.connect(address)


        poller = zmq.Poller()
        poller.register(receiver, zmq.POLLIN)
                                
        while not self.exit_request:
            
            socks = dict(poller.poll(500))
            if socks.get(receiver, None) == zmq.POLLIN:            
                msg = receiver.recv_pyobj()
    
                cbk = self._callbacks.pop(msg.id, None)
        
                logger.debug("(%s) Forwarding a RPC call to method: %s" % (current_thread().name, msg.method))
                remote.send_pyobj(msg)  
                resp = remote.recv_pyobj()
                              
                if msg.async or cbk:
                    if cbk:
                        logger.debug("Response received from server. Running callback.")
                        cbk(resp)
                else:
                    replier.send_pyobj(resp)
    
    
############################################################# 
#############################################################
######## RpcRequest
############################################################# 
############################################################# 
class RpcRequest(object):
    """
    RpcRequest
    
    Represents a request message to be sent out to a host
    with published services. Used by RpcConnection when doing
    calls.
    """
    
    REQ_COUNT = 0
    
    def __init__(self):
        self._method = ""
        self._args   = []
        self._kwargs = {}
        self._callback = False
        self._async = False
        
        self._callback_id = self.REQ_COUNT
        self.REQ_COUNT += 1
        
    
    def __repr__(self):
        return "<%s: %s (#args:%d, #kwargs:%d)>" % (self.__class__.__name__, 
                                                      self.method, 
                                                      len(self.args), 
                                                      len(self.kwargs))
 
    @property
    def async(self):
        return self._async
    
    @async.setter
    def async(self, m):
        if not isinstance(m, bool):
            raise TypeError("async value must be True or False")
        self._async = m
    
       
    @property
    def method(self):
        return self._method
    
    @method.setter
    def method(self, m):
        if not isinstance(m, str):
            raise TypeError("method value must be a string name")
        self._method = m
    
    @property
    def args(self):
        return self._args
    
    @args.setter
    def args(self, args):
        if not isinstance(args, (list, tuple)):
            raise TypeError("args parameter must be a list or tuple")
        self._args = args
    
    @property
    def kwargs(self):
        return self._kwargs
    
    @kwargs.setter
    def kwargs(self, kwargs):
        if not isinstance(kwargs, dict):
            raise TypeError("kwargs parameter must be a dict")
        self._kwargs = kwargs
    
    @property
    def callback(self):
        return self._callback
    
    @callback.setter
    def callback(self, cbk):
        
#        if cbk is None:
#            self._callback = None
#            return
#        
#        if not isinstance(cbk, str) and not hasattr(cbk, "__call__") :
#            raise TypeError("Callback value must either be a callable, or string name of callable")
        
        self._callback = cbk

    @property
    def id(self):
        return self._callback_id
           
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
        
