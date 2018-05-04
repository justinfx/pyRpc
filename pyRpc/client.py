
"""
pyRpc - client.py 

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

import logging
from uuid import uuid4 
from threading import Thread, current_thread

import zmq
from zmq import ZMQError

from pyRpc.constants import TEMPDIR
from pyRpc.server import RpcResponse 

logger = logging.getLogger(__name__)

            
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
    
    def __init__(self, name, tcpaddr=None, context=None, workers=1):
        
        self._context = context or zmq.Context.instance()

        if tcpaddr:
            self._address = "tcp://%s" % tcpaddr
        else:
            self._address = "ipc://%s/%s.ipc" % (TEMPDIR, name)
        
        self._work_address = "inproc://workRequest"

        self._async_sender = self._context.socket(zmq.PUSH)
        self._async_sender.bind(self._work_address)   

        self._main_sender = None 

        self.exit_request = False
        self._callbacks = {}
        
        for i in range(max(int(workers), 1)):
            t = Thread(target=self._worker_routine, 
                        args=(self._context, self._address, self._work_address))
            t.daemon = True
            t.start()
    
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

        if async or callback:
            # push the request down to the workers
            self._async_sender.send_pyobj(req, protocol=2)
            return RpcResponse(None, 0, None)

        # otherwise, we are running this as a blocking call
        if self._main_sender is None:
            logger.debug("Making connection to RPC server at: %s" % self._address)
            self._main_sender = self._context.socket(zmq.REQ)
            self._main_sender.connect(self._address)  
                      
        self._main_sender.send_pyobj(req, protocol=2)
        resp = self._main_sender.recv_pyobj()
        
        logger.debug("Got reply to method %s: %s" % (method, resp))
        
        return resp

    def _worker_routine(self, context, remote_address, work_address):
        """
        Worker loop for processing rpc calls.
        """
        logger.debug("Starting local worker thread: %s" % current_thread().name)
        
        receiver = context.socket(zmq.PULL)
        receiver.connect(work_address)

        logger.debug("Making connection to RPC server at: %s" % remote_address)
        remote = context.socket(zmq.REQ)
        remote.connect(remote_address)

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
                              
                if cbk:
                    logger.debug("Response received from server. Running callback.")
                    cbk(resp)

    
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
    
    def __init__(self):
        self._method = ""
        self._args   = []
        self._kwargs = {}
        self._callback = False
        self._async = False
        
        self._callback_id = uuid4().int
    
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


    