'''
ucpackethandler.py

Processes UDP packets issued by the uC/Probe application.

Copyright (c) 2013 ARM Ltd. All rights reserved.
'''

import SocketServer
from com.arm.debug.dtsl.interfaces import IDeviceConnection
from com.arm.debug.dtsl.interfaces import IDevice
from com.arm.debug.dtsl import DTSLException
from com.arm.rddi import RDDI_ACC_SIZE
import jarray
import array
import struct


class UCUDPHandler(SocketServer.BaseRequestHandler):
    '''
    Handles the request/response protocol from Micrium's uC-Probe
    '''
    PROBE_COM_FMT_TX_ERROR = 0x8000
    # The uC Probe protocol request/response codes
    PROBE_COM_FMT_RX_QUERY = 0x0001
    PROBE_COM_FMT_TX_QUERY = 0x8001
    PROBE_COM_FMT_RX_RD = 0x0002
    PROBE_COM_FMT_TX_RD = 0x8002
    PROBE_COM_FMT_RX_WR = 0x0003
    PROBE_COM_FMT_TX_WR = 0x8003
    PROBE_COM_FMT_RX_RD_MULTI = 0x0007
    PROBE_COM_FMT_TX_RD_MULTI = 0x8007
    PROBE_COM_FMT_RX_WR_MULTI = 0x0008
    PROBE_COM_FMT_TX_WR_MULTI = 0x8008
    PROBE_COM_FMT_RX_STR_OUT = 0x0009
    PROBE_COM_FMT_TX_STR_OUT = 0x8009
    PROBE_COM_FMT_RX_STR_IN = 0x000A
    PROBE_COM_FMT_TX_STR_IN = 0x800A
    PROBE_COM_FMT_RX_TERMINAL_EXEC = 0x000B
    PROBE_COM_FMT_TX_TERMINAL_EXEC = 0x800B
    PROBE_COM_FMT_RX_TERMINAL_OUT = 0x000C
    PROBE_COM_FMT_TX_TERMINAL_OUT = 0x800C
    PROBE_COM_FMT_RX_TERMINAL_IN = 0x000D
    PROBE_COM_FMT_TX_TERMINAL_IN = 0x800D
    # The uC Probe status codes
    PROBE_COM_STATUS_OK = 0x01
    PROBE_COM_STATUS_TERMINAL_EXEC_NOT_RDY = 0xF4
    PROBE_COM_STATUS_TERMINAL_IN_OVF = 0xF5
    PROBE_COM_STATUS_TERMINAL_OUT_NONE = 0xF6
    PROBE_COM_STATUS_STR_IN_OVF = 0xF7
    PROBE_COM_STATUS_STR_OUT_NONE = 0xF8
    PROBE_COM_STATUS_UNKNOWN_REQUEST = 0xF9
    PROBE_COM_STATUS_QUERY_NOT_SUPPORTED = 0xFC
    PROBE_COM_STATUS_TX_PKT_TOO_LARGE = 0xFD
    PROBE_COM_STATUS_RX_PKT_WRONG_SIZE = 0xFE
    PROBE_COM_STATUS_FAIL = 0xFF
    # The uC Probe modifier codes
    PROBE_COM_MODIFIER_NONE = 0x00
    PROBE_COM_MODIFIER_STR_OUT_AVAIL = 0x01
    PROBE_COM_MODIFIER_TERMINAL_EXEC_DONE = 0x02
    PROBE_COM_MODIFIER_TERMINAL_OUT_AVAIL = 0x04
    # The uC Probe QUERY codes
    PROBE_COM_QUERY_MAX_RX_SIZE = 0x0101
    PROBE_COM_QUERY_MAX_TX_SIZE = 0x0102
    PROBE_COM_QUERY_ENDIANNESS_TEST = 0x0201
    PROBE_COM_QUERY_STATUS = 0x0202
    PROBE_COM_QUERY_FMT_SUPPORT = 0x1001
    PROBE_COM_QUERY_VERSUIB = 0x1002
    # The header used in all packets
    PROBE_COM_HDR = 'uCPr'
    # This holds a list of supported message formats
    supportedFormats = [
        PROBE_COM_FMT_RX_QUERY,
        PROBE_COM_FMT_RX_RD,
        PROBE_COM_FMT_RX_WR,
        PROBE_COM_FMT_RX_RD_MULTI,
        PROBE_COM_FMT_RX_WR_MULTI
    ]

    def __init__(self, request, client_address, server):
        '''
        Constructor
        '''
        self.memAccessDevice = None
        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)

    def formErrorResponse(self, status):
        '''Generates an error response (with no data)
        Parameters:
            status
                the Status field - one of the PROBE_COM_STATUS_xxxxx values
        Returns:
            responseData
                a packet with the following format:
            +-----+-----+-----+-----+
            |  u  |  C  |  P  |  r  |
            +-----+-----+-----+-----+
            |     Len   |  0  |  0  |
            +-----+-----+-----+-----+
            |  0x8000   | Stat|  0 |
            +-----+-----+-----+-----+
            | chk |  /  |
            +-----+-----+
        '''
        rawResponse = array.array('c', ' ' * 14)
        struct.pack_into('<4sHxxHBxxc', rawResponse, 0,
            UCUDPHandler.PROBE_COM_HDR,
            4,
            UCUDPHandler.PROBE_COM_FMT_TX_ERROR,
            status,
            '/')
        return rawResponse

    def formNoDataResponse(self, format, status, modifier):
        '''Generates a response with no data
        Parameters:
            format
                the Format field - one of the PROBE_COM_FMT_TX_xxxx values
            status
                the Status field - one of the PROBE_COM_STATUS_xxxxx values
            modifier
                the Modifier field - one of the PROBE_COM_MODIFIER_xxxx values
        Returns:
            responseData
                a packet with the following format:
            +-----+-----+-----+-----+
            |  u  |  C  |  P  |  r  |
            +-----+-----+-----+-----+
            |     Len   |  0  |  0  |
            +-----+-----+-----+-----+
            |  Format   | Stat| Mod |
            +-----+-----+-----+-----+
            | chk |  /  |
            +-----+-----+
        '''
        rawResponse = array.array('c', ' ' * 14)
        fmt = '<4sHxxHBBxc'
        struct.pack_into(fmt, rawResponse, 0,
            UCUDPHandler.PROBE_COM_HDR,
            4,
            format,
            status,
            modifier,
            '/')
        return rawResponse

    def formDataResponse(self, format, status, modifier, data):
        '''Generates a response with no data
        Parameters:
            format
                the Format field - one of the PROBE_COM_FMT_TX_xxxx values
            status
                the Status field - one of the PROBE_COM_STATUS_xxxxx values
            modifier
                the Modifier field - one of the PROBE_COM_MODIFIER_xxxx values
            data
                an array of string values to return as the packet data
        Returns:
            responseData
                a packet with the following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |     Len   |  0  |  0  |
                +-----+-----+-----+-----+
                |  Format   | Stat| Mod |
                +-----+-----+-----+-----+
                |                       |
                |      data values      |
                |                       |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
        '''
        totalLength = 0
        for idx in range(len(data)):
            totalLength = totalLength + len(data[idx])
        rawResponse = array.array('c', ' ' * (14 + totalLength))
        struct.pack_into('<4sHxxHBB', rawResponse, 0,
            UCUDPHandler.PROBE_COM_HDR,
            totalLength + 4,
            format,
            status,
            modifier)
        offset = 12
        for idx in range(len(data)):
            blkLen = len(data[idx])
            fmt = "<%ds" % (blkLen)
            struct.pack_into(fmt, rawResponse, offset, data[idx])
            offset = offset + blkLen
        struct.pack_into('xc', rawResponse, offset, '/')
        return rawResponse

    def getMemAccessDevice(self):
        '''Gets the DTSL device we are to use for memory access
        Returns:
            the connected DTSL device (IDevice) or None if there
            is no device or it has notbeen connected yet
        '''
        memAccessDevice = self.server.getMemAccessDevice()
        if memAccessDevice == None:
            return None
        if isinstance(memAccessDevice, IDeviceConnection):
            if memAccessDevice.isConnected() == False:
                return None
        assert isinstance(memAccessDevice, IDevice)
        return memAccessDevice

    def value32BitToString(self, value):
        '''Converts a value into a 32 bit (4 byte) string containing
           the bytes of the value in little endian order
        Parameters:
            value
                the data value e.g. 0x12345678
        Returns:
            a 4 character string containing the 4 bytes of the 32 bit
            value in little endian order e.g. '\x12\x34\x56\x78'
        '''
        rawString = array.array('c', ' ' * 4)
        struct.pack_into('<L', rawString, 0, value)
        return rawString.tostring()

    def formSupportedQueryFormatsList(self):
        '''Forms a string containing two bytes for each supported
           Format value in little endian order
        Returns:
            if we support [PROBE_COM_FMT_RX_QUERY, PROBE_COM_FMT_RX_RD,
            PROBE_COM_FMT_RX_WR] we would return a 6 char string
            containing the format values in little endian order
            e.g. '\x01\x00\x02\x00\x03\x00'

        '''
        formatCount = len(UCUDPHandler.supportedFormats)
        rawString = array.array('c', ' ' * (2 * formatCount))
        for idx in range(formatCount):
            struct.pack_into('<H', rawString, idx * 2, UCUDPHandler.supportedFormats[idx])
        return rawString.tostring()

    def handleQUERY(self, rawRequest, length):
        '''Handles the PROBE_COM_FMT_RX_QUERY packet
        This is how the uC-Probe program discovers our capabilities
        Parameters:
            rawRequest
                a packet with the following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |  0x0004   |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x0001   |  QValue   |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
            length
                the total length of the received packet (14)
        Returns:
            responseData
                a packet with the following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |    Len    |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x8001   |  1  |  0  |
                +-----+-----+-----+-----+
                |                       |
                |      data values      |
                |                       |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
        '''
        qValue = struct.unpack_from('<H', rawRequest, 10)[0]
        if qValue == UCUDPHandler.PROBE_COM_QUERY_MAX_RX_SIZE:
            rawResponse = self.formDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_QUERY,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE,
                [self.value32BitToString(256)])
        elif qValue == UCUDPHandler.PROBE_COM_QUERY_MAX_TX_SIZE:
            rawResponse = self.formDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_QUERY,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE,
                [self.value32BitToString(256)])
        elif qValue == UCUDPHandler.PROBE_COM_QUERY_ENDIANNESS_TEST:
            rawResponse = self.formDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_QUERY,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE,
                [self.value32BitToString(0x12345678)])
        elif qValue == UCUDPHandler.PROBE_COM_QUERY_STATUS:
            rawResponse = self.formDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_QUERY,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE,
                [self.value32BitToString(0)])
        elif qValue == UCUDPHandler.PROBE_COM_QUERY_FMT_SUPPORT:
            rawResponse = self.formDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_QUERY,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE,
                [self.formSupportedQueryFormatsList()])
        elif qValue == UCUDPHandler.PROBE_COM_QUERY_VERSUIB:
            rawResponse = self.formDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_QUERY,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE,
                [self.value32BitToString(0x10000000)])
        else:
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_QUERY_NOT_SUPPORTED)
        return rawResponse

    def handleRD(self, rawRequest, length):
        '''Handles the PROBE_COM_FMT_RX_RD packet
        This is how the uC-Probe program reads memory values.
        The packet size field tells us how many bytes to read and
        the packet address field tells us the address to read from.
        Parameters:
            rawRequest
                a packet with the following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |     8     |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x0002   |   size    |
                +-----+-----+-----+-----+
                |        Address        |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
            length
                the total length of the received packet (18)
        Returns:
            responseData
                if the read is good we return a packet with the
                following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |    Len    |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x8002   |  1  |  0  |
                +-----+-----+-----+-----+
                |                       |
                |      data values      |
                |                       |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
                if the read is bad we return a packet with the
                following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |     4     |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x8000   | 0xFF|  0  |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
        '''
        size, address = struct.unpack_from('<HL', rawRequest, 10)
        mad = self.getMemAccessDevice()
        memData = jarray.zeros(size, 'b')
        rawResponse = None
        try:
            mad.memRead(0, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, 0, size, memData)
            rawResponse = self.formDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_RD,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE,
                [memData.tostring()])
        except DTSLException, e:  # @UnusedVariable
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_FAIL)
        except Exception, e:  # @UnusedVariable
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_FAIL)
        return rawResponse

    def handleWR(self, rawRequest, length):
        '''Handles the PROBE_COM_FMT_RX_WR packet
        This is how the uC-Probe program writes memory values.
        The packet size field tells us how many bytes to write and
        the packet address field tells us the address to write.
        Parameters:
            rawRequest
                a packet with the following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |    Len    |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x0003   |   size    |
                +-----+-----+-----+-----+
                |        Address        |
                +-----+-----+-----+-----+
                |                       |
                |      data values      |
                |                       |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
            length
                the total length of the received packet (18+data length)
        Returns:
            responseData
                if the write is good we return a packet with the
                following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |    Len    |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x8003   |  1  |  0  |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
                if the write is bad we return a packet with the
                following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |     4     |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x8000   | 0xFF|  0  |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
        '''
        size, address = struct.unpack_from('<HL', rawRequest, 10)
        data = struct.unpack_from('%ds' % (size), rawRequest, 16)[0]
        mad = self.getMemAccessDevice()
        memData = jarray.array(data, 'b')
        rawResponse = None
        try:
            mad.memWrite(0, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, 0, False, size, memData)
            rawResponse = self.formNoDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_WR,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE)
        except DTSLException, e:  # @UnusedVariable
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_FAIL)
        except Exception, e:  # @UnusedVariable
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_FAIL)
        return rawResponse

    def handleRD_MULTI(self, rawRequest, length):
        '''Handles the PROBE_COM_FMT_RX_RD_MULTI packet
        This allows uC-Probe to issue multiple read requests
        in a single packet (subject to max size of 255 bytes
        per request).
        Parameters:
            rawRequest
                a packet with the following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |    Len    |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x0007   |  S0 |A0[0]|
                +-----+-----+-----+-----+
                |A0[1]|A0[2]|A0[3]| S1  |
                +-----+-----+-----+-----+
                |A1[0]|A1[1]|A1[2]|A1[3]|
                +-----+-----+-----+-----+
                |  S2 |A2[0]|A2[1]|A2[2]|
                +-----+-----+-----+-----+
                ... 5 bytes per read request
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
            length
                the total length of the received packet (12+5*#readreq)
        Returns:
            responseData
                if the read is good we return a packet with the
                following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |    Len    |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x8007   |  1  |  0  |
                +-----+-----+-----+-----+
                |                       |
                |      data values      |
                |                       |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
                if the read is bad we return a packet with the
                following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |     4     |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x8000   | 0xFF|  0  |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
        '''
        mad = self.getMemAccessDevice()
        rawResponse = None
        # Calculate the total size required
        blocks = (length - 2) / 5
        memBlocks = []
        try:
            for blk in range(blocks):
                size, address = struct.unpack_from('<BL', rawRequest, 10 + 5 * blk)
                memData = jarray.zeros(size, 'b')
                mad.memRead(0, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, 0, size, memData)
                memBlocks.append(memData.tostring())
            rawResponse = self.formDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_RD_MULTI,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE,
                memBlocks)
        except DTSLException, e:  # @UnusedVariable
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_FAIL)
        except Exception, e:  # @UnusedVariable
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_FAIL)
        return rawResponse

    def handleWR_MULTI(self, rawRequest, length):
        '''Handles the PROBE_COM_FMT_RX_WR_MULTI packet
        This allows uC-Probe to issue multiple write requests
        in a single packet (subject to max size of 255 bytes
        per request).
        Parameters:
            rawRequest
                a packet with the following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |    Len    |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x0008   |  S0 |A0[0]|
                +-----+-----+-----+-----+
                |A0[1]|A0[2]|A0[3]|D0[0]|
                +-----+-----+-----+-----+
                |D0[1]|D0[2]|D0[3]| ... |
                +-----+-----+-----+-----+
                ... 5 bytes + data per write request
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
            length
                the total length of the received packet
        Returns:
            responseData
                if the write is good we return a packet with the
                following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |     4     |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x8008   |  1  |  0  |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
                if the write is bad we return a packet with the
                following format:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |     4     |  0  |  0  |
                +-----+-----+-----+-----+
                |  0x8000   | 0xFF|  0  |
                +-----+-----+-----+-----+
                | chk |  /  |
                +-----+-----+
        '''
        mad = self.getMemAccessDevice()
        dataLeft = length - 2 # the data content of the packet
        offset = 10 # start of first size field (S0)
        try:
            while dataLeft >= 5: # need at least 5 bytes per entry
                size, address = struct.unpack_from('<BL', rawRequest, offset)
                offset = offset + 5
                dataLeft = dataLeft - 5
                if dataLeft < size:
                    rawResponse = self.formErrorResponse(
                        UCUDPHandler.PROBE_COM_STATUS_RX_PKT_WRONG_SIZE)
                    break
                elif size > 0:
                    data = struct.unpack_from('<%ds' % (size), rawRequest, offset)[0]
                    offset = offset + size
                    dataLeft = dataLeft - size
                    memData = jarray.array(data, 'b')
                    mad.memWrite(0, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, 0, False, size, memData)
            rawResponse = self.formNoDataResponse(
                UCUDPHandler.PROBE_COM_FMT_TX_WR_MULTI,
                UCUDPHandler.PROBE_COM_STATUS_OK,
                UCUDPHandler.PROBE_COM_MODIFIER_NONE)
        except DTSLException, e:  # @UnusedVariable
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_FAIL)
        except Exception, e:  # @UnusedVariable
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_FAIL)
        return rawResponse

    def handleSTR_OUT(self, rawRequest, length):
        rawResponse = self.formErrorResponse(
            UCUDPHandler.PROBE_COM_STATUS_QUERY_NOT_SUPPORTED)
        return rawResponse

    def handleSTR_IN(self, rawRequest, length):
        rawResponse = self.formErrorResponse(
            UCUDPHandler.PROBE_COM_STATUS_QUERY_NOT_SUPPORTED)
        return rawResponse

    def handleTERMINAL_EXEC(self, rawRequest, length):
        rawResponse = self.formErrorResponse(
            UCUDPHandler.PROBE_COM_STATUS_QUERY_NOT_SUPPORTED)
        return rawResponse

    def handleTERMINAL_OUT(self, rawRequest, length):
        rawResponse = self.formErrorResponse(
            UCUDPHandler.PROBE_COM_STATUS_QUERY_NOT_SUPPORTED)
        return rawResponse

    def handleTERMINAL_IN(self, rawRequest, length):
        rawResponse = self.formErrorResponse(
            UCUDPHandler.PROBE_COM_STATUS_QUERY_NOT_SUPPORTED)
        return rawResponse

    def handle(self):
        '''Processes a received packet from uC-Probe
        All packets start with the following 10 bytes:
                +-----+-----+-----+-----+
                |  u  |  C  |  P  |  r  |
                +-----+-----+-----+-----+
                |    Len    |  0  |  0  |
                +-----+-----+-----+-----+
                |  Format   |
                +-----+-----+
        with the Format field defining the type of packet
        '''
        (rawRequest, socket) = self.request
        # Extract fields
        header, length, format = struct.unpack_from('<4sHxxH', rawRequest, 0)
        # If header does not match we ignore the packet
        if header != 'uCPr':
            return
        try:
            if format == UCUDPHandler.PROBE_COM_FMT_RX_QUERY:
                rawResponse = self.handleQUERY(rawRequest, length)
            elif format == UCUDPHandler.PROBE_COM_FMT_RX_RD:
                rawResponse = self.handleRD(rawRequest, length)
            elif format == UCUDPHandler.PROBE_COM_FMT_RX_WR:
                rawResponse = self.handleWR(rawRequest, length)
            elif format == UCUDPHandler.PROBE_COM_FMT_RX_RD_MULTI:
                rawResponse = self.handleRD_MULTI(rawRequest, length)
            elif format == UCUDPHandler.PROBE_COM_FMT_RX_WR_MULTI:
                rawResponse = self.handleWR_MULTI(rawRequest, length)
            elif format == UCUDPHandler.PROBE_COM_FMT_RX_STR_OUT:
                rawResponse = self.handleSTR_OUT(rawRequest, length)
            elif format == UCUDPHandler.PROBE_COM_FMT_RX_STR_IN:
                rawResponse = self.handleSTR_IN(rawRequest, length)
            elif format == UCUDPHandler.PROBE_COM_FMT_RX_TERMINAL_EXEC:
                rawResponse = self.handleTERMIN_EXEC(rawRequest, length)
            elif format == UCUDPHandler.PROBE_COM_FMT_RX_TERMINAL_OUT:
                rawResponse = self.handleTERMINAL_OUT(rawRequest, length)
            elif format == UCUDPHandler.PROBE_COM_FMT_RX_TERMINAL_IN:
                rawResponse = self.handleTERMINAL_IN(rawRequest, length)
            else:
                # Unknown format code
                rawResponse = self.formErrorResponse(
                    UCUDPHandler.PROBE_COM_STATUS_UNKNOWN_REQUEST)
        except Exception, e: # @UnusedVariable
            # Something went bad :-(
            rawResponse = self.formErrorResponse(
                UCUDPHandler.PROBE_COM_STATUS_FAIL)
        # Send response to uC-Probe
        socket.sendto(rawResponse.tostring(), self.client_address)
