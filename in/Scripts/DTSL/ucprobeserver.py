'''
ucprobeserver.py

A UDP server used to allow uC/Probe to issue memory read/write requests
to a DTSL device. This device could be a core or (more likely) a MEM-AP
type device. The latter allows memory access independently from the
execution state of the core.

Copyright (c) 2013 ARM Ltd. All rights reserved.
'''

import threading
import select
import socket
from SocketServer import ThreadingMixIn
from SocketServer import UDPServer
from ucpackethandler import UCUDPHandler
from java.lang import Thread as JThread
from java.lang import InterruptedException


class DeviceUDPServer(UDPServer):
    '''A UDP server which contains a DTSL Device'''
    def __init__(self, server_address, RequestHandlerClass):
        '''Constructor'''
        self.memAccessDevice = None
        UDPServer.__init__(self, server_address, RequestHandlerClass)

    def setMemAccessDevice(self, memAccessDevice):
        self.memAccessDevice = memAccessDevice

    def getMemAccessDevice(self):
        return self.memAccessDevice


class DeviceThreadingUDPServer(ThreadingMixIn, DeviceUDPServer):
    ''' A UDP server which runs in a thread'''

    def __init__(self, server_address, RequestHandlerClass):
        '''Constructor'''
        DeviceUDPServer.__init__(self, server_address, RequestHandlerClass)
        # Set the socket into non-blocking mode
        if self.socket != None:
            self.socket.setblocking(False)
        self.myThread = None

    def interrupt(self):
        '''Gets the thread out of any system calls'''
        if self.myThread != None:
            # Since we know we are Jython, our threading
            # implementation is Java threads. So we have
            # java.lang.thread available to us
            JThread.interrupt(self.myThread)

    def get_request(self):
        data = None
        clientAddress = None
        socketReadyToRead = False
        try:
            readersReady = select.select([self.socket], [], [])[0]
#            do_read = bool(r)
            if len(readersReady) > 0:
                if readersReady[0] == self.socket:
                    socketReadyToRead = True
        except socket.error:
            self.socketError = True
            raise
        except InterruptedException:
            pass
        if socketReadyToRead:
            data, clientAddress = self.socket.recvfrom(self.max_packet_size)
        return (data, self.socket), clientAddress

    def serve_forever(self):
        '''This is the server thread method
        '''
        # Record our thread for use by interrupt()
        self.myThread = threading.currentThread()
        self.socketError = False
        while self.socketError == False:
            self.handle_request()

    def handle_error(self, request, client_address):
        '''Handles any error during the processing of a request
        We override this to prevent the base class printing out
        an error message - which it always does during server
        shutdown.
        '''
        pass


class UCProbeServer(object):
    '''
    A server which handles Micrium's uC-Probe request/response protocol
    to access target memory read/write requests.
    '''
    # The default port that uC-Probe uses
    PROBE_COM_DEFAULT_PORT = 9930

    def __init__(self, memAccessDevice, port):
        '''Constructor
        Parameters:
            memAccessDevice
                The DTSL IDevice object which we are to use for accessing
                memory values
            port
                The UDP port the server should listen on. If this value is passed
                in as < 1 (e.g. 0) we will use the default uC/Probe port number.
        '''
        self.memAccessDevice = memAccessDevice
        if port < 1:
            port = UCProbeServer.PROBE_COM_DEFAULT_PORT
        self.server = DeviceThreadingUDPServer(("localhost", port), UCUDPHandler)
        self.server.setMemAccessDevice(self.memAccessDevice)
        self.serverThread = threading.Thread(target=self.server.serve_forever)

    def start(self):
        '''Start the server
        '''
        self.serverThread.start()

    def stop(self):
        '''Stop the server
        Returns:
            True if stopped OK, False if failed to halt server thread
        '''
        if self.server != None:
            self.server.server_close()
            self.server.interrupt()
        if self.serverThread != None:
            self.serverThread.join(5)
            if self.serverThread.isAlive():
                return False
        return True
