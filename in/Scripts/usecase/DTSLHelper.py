from jarray import array
from jarray import zeros
from java.lang import Long
from java.lang import StringBuilder
import math
import os
import sys

from com.arm.debug.dtsl import ConnectionManager
from com.arm.debug.dtsl import ConnectionParameters
from com.arm.debug.dtsl.components import ConnectableDevice
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.interfaces import IDevice


def toHex32(rVal):
    """ Converts an integer value to a hex string
    Returns a string of the form 0xhhhhhhhh which is the hex
    value of rVal
    Parameters:
        rVal - the integer value to be converted
    """
    return "0x%s" % ("00000000%X" % (rVal & 0xffffffff))[-8:]


def toHex64(rVal):
    """ Converts an long value to a hex string
    Returns a string of the form 0xhhhhhhhhhhhhhhhh which is the hex
    value of rVal
    Parameters:
        rVal - the long value to be converted
    """
    return "0x%s" % ("0000000000000000%X" % (rVal & 0xffffffffffffffff))[-16:]


def toHex(rVal, bitLength):
    """ Converts an value to a hex string
    Returns a string of the form 0xhhhh which is the hex value of rVal using
    as many nibble values required for the bitLength
    Parameters:
        rVal - the long value to be converted
    """
    if bitLength == 64:
        return toHex64(rVal)
    if bitLength == 32:
        return toHex32(rVal)
    nibbleLength = int((bitLength + 3) / 4)
    mask = int(math.floor(math.ldexp(1, 4 * nibbleLength) - 1))
    lStr = ("%s%X" % ("0" * nibbleLength, rVal & mask))
    hStr = lStr[-nibbleLength:]
    return "0x%s" % (hStr)


def formTraceSizeString(byteCount):
    """ Converts a byte count value into a size string suitable for display
    Parameters:
        byteCount the trace size value
    Returns:
        a string of the form <size> <"bytes" | "KB" | "MB" | "GB">
    """
    if byteCount < 1024:
        units = "bytes"
        divisor = 1.0
    elif byteCount < 1024 * 1024:
        units = "KB"
        divisor = 1024.0
    elif byteCount < 1024 * 1024 * 1024:
        units = "MB"
        divisor = 1024.0 * 1024.0
    else:
        units = "GB"
        divisor = 1024.0 * 1024.0 * 1024.0
    return "%.2f %s" % (byteCount / divisor, units)


def formRateString(byteCount, time):
    rateString = ""
    rate = byteCount/time;
    if rate < 1024.0:
        rateString = "%.2f bytes/s" % rate
    elif rate/1024.0 < 1024.0:
        rateString = "%.2f KBytes/s" % (rate / 1024.0)
    elif rate/(1024.0*1024.0) < 1024.0:
        rateString = "%.2f MBytes/s" % (rate / (1024.0*1024.0))
    else:
        rateString = "%.2f GBytes/s" % (rate / (1024.0*1024.0*1024.0))
    return rateString;


def formTimeStringFromNanoSeconds(nsTime):
    timeString = ""
    if nsTime < 1000:
        timeString = "%d ns" % nsTime
    elif nsTime < 1000*1000:
        timeString = "%.2f us" % (nsTime / 1000.0)
    elif nsTime < 1000*1000*1000:
        timeString = "%.2f ms" % (nsTime / (1000.0*1000.0))
    else:
        timeString = "%.2f s" % (nsTime / (1000.0*1000.0*1000.0))
    return timeString;


def getDTSLDeviceByName(dtslConfiguration, deviceName):
    """ Returns a device object referenced by name
    Parameters:
        dtslConfiguration - the DTSL configuration object
        deviceName - the device name e.e. "Cortex-A9_0" or "TPIU"
    NOTE: the device object we return implements the IDevice interface
    """
    assert isinstance(dtslConfiguration, DTSLv1)
    deviceList = dtslConfiguration.getDevices()
    for device in deviceList:
        assert isinstance(device, IDevice)
        if deviceName == device.getName():
            return device
    return None


def showDTSLDevices(dtslConfiguration):
    """ Prints a list of DTSL devices contained in the configuration
    Parameters:
        dtslConfiguration - the DTSL configuration object
    """
    assert isinstance(dtslConfiguration, DTSLv1)
    deviceList = dtslConfiguration.getDevices()
    print "DTSL Device list (device count = %d):" % (len(deviceList))
    print "-----------+------------------"
    print "    ID     | DTSL Device Name"
    print "-----------+------------------"
    for device in deviceList:
        assert isinstance(device, IDevice)
        print "%10d | %s" % (device.getID(), device.getName())


def getDTSLTraceCaptureDeviceNames(dtslConfiguration):
    """ Returns an array of DTSL trace capture device names
    Parameters:
        dtslConfiguration - the DTSL configuration object
    Returns:
        an array of capture device names or None if there are none
    """
    assert isinstance(dtslConfiguration, DTSLv1)
    traceCaptureDevices = dtslConfiguration.getTraceCaptureInterfaces()
    if traceCaptureDevices is None:
        return None
    return traceCaptureDevices.keySet().toArray()


def getDTSLTraceCaptureDevice(
    dtslConfiguration,
    traceCaptureDeviceName
):
    traceCaptureDevices = dtslConfiguration.getTraceCaptureInterfaces()
    if traceCaptureDevices is None or traceCaptureDevices.isEmpty():
        traceCaptureDevice = None
    else:
        traceCaptureDevice = traceCaptureDevices.get(traceCaptureDeviceName)
    return traceCaptureDevice


def findDTSLTraceSourceForATBID(
    traceCaptureDevice,
    atbid
):
    traceSource = traceCaptureDevice.findTraceSourceByID(atbid)
    return traceSource


def showDTSLTraceCaptureDevices(dtslConfiguration):
    """ Prints a list of DTSL trace capture devices contained in the
        configuration
    Parameters:
        dtslConfiguration - the DTSL configuration object
    """
    assert isinstance(dtslConfiguration, DTSLv1)
    print "DTSL Trace Capture Devices:"
    print "+------------------+-------------------------+"
    print "| DTSL Device Name |    Contains / Size      |"
    print "+------------------+-------------------------+"
    traceCaptureDevices = dtslConfiguration.getTraceCaptureInterfaces()
    if traceCaptureDevices is None or traceCaptureDevices.isEmpty():
        print("DTSL Configuration %s has no trace capture devices" %
              dtslConfiguration.getName())
    else:
        for traceCaptureName in traceCaptureDevices.keySet().toArray():
            traceCaptureDevice = traceCaptureDevices.get(traceCaptureName)
            if traceCaptureDevice.isActive():
                if traceCaptureDevice.canQueryCaptureSizeWhenRunning():
                    contentsStr = formTraceSizeString(
                        traceCaptureDevice.getCaptureSize())
                else:
                    contentsStr = "?"
            else:
                captureSize = traceCaptureDevice.getCaptureSize()
                contentsStr = formTraceSizeString(captureSize)
            contentsStr += (" / " + formTraceSizeString(
                traceCaptureDevice.getMaxCaptureSize()))
            print "| %16s | %23s |" % (
                traceCaptureDevice.getName().center(16),
                contentsStr.center(23)
            )
        print "+------------------+-------------------------+"


def showDTSLTraceSourcesForCaptureDevice(
    dtslConfiguration,
    traceCaptureDeviceName
):
    """ Prints a list of DTSL trace sources that are associated with a
        trace capture device
    Parameters:
        dtslConfiguration - the DTSL configuration object
        traceCaptureDeviceName - the name of the trace capture device
    """
    assert isinstance(dtslConfiguration, DTSLv1)
    print "DTSL Trace Sources for %s:" % traceCaptureDeviceName
    print "+-------------------+-------------+--------------------------------"
    print "| Trace Source Name |  Stream ID  | Encoding "
    print "+-------------------+-------------+--------------------------------"
    traceCaptureDevices = dtslConfiguration.getTraceCaptureInterfaces()
    if traceCaptureDevices is None or traceCaptureDevices.isEmpty():
        print("DTSL Configuration %s has no trace capture devices" %
              dtslConfiguration.getName())
    else:
        traceCaptureDevice = traceCaptureDevices.get(traceCaptureDeviceName)
        if traceCaptureDevice is None:
            print("DTSL Configuration %s has no trace capture device names %s"
                  % traceCaptureDeviceName)
        else:
            traceSources = traceCaptureDevice.getTraceSources()
            if traceSources is None or traceSources.isEmpty():
                print("Trace capture device %s has no configured trace sources"
                      % traceCaptureDeviceName)
            else:
                for traceSource in traceSources:
                    print "| %17s | %11s | %s" % (
                        traceSource.getName().center(17),
                        str(traceSource.getStreamID()).center(11),
                        traceSource.getEncodingDisplayName())
    print "+-------------------+-------------+--------------------------------"


def showDTSLException(e):
    """ Prints out a DTSLException
    The exception chain is traversed and non-duplicated
    information from all levels is displayed
    Parameters:
        e - the DTSLException object
    """
    print >> sys.stderr, "Caught DTSL exception:"
    cause = e
    lastMessage = ""
    while cause is not None:
        nextMessage = cause.getMessage()
        if nextMessage != lastMessage:
            if nextMessage is not None:
                print >> sys.stderr, nextMessage
            lastMessage = nextMessage
        cause = cause.getCause()


def showRDDIException(e):
    """ Prints out a RDDIException
    The exception chain is traversed and non-duplicated
    information from all levels is displayed
    Parameters:
        e - the RDDIException object
    """
    print >> sys.stderr, "Caught RDDI exception:"
    cause = e
    lastMessage = ""
    while cause is not None:
        nextMessage = cause.getMessage()
        if nextMessage != lastMessage:
            if nextMessage is not None:
                print >> sys.stderr, nextMessage
            lastMessage = nextMessage
        cause = cause.getCause()


def showJythonException(e):
    print >> sys.stderr, "Caught Jython exception:"
    print >> sys.stderr, e.toString()


def showRuntimeError(e):
    """ Prints out a RuntimeException
    Parameters:
        e - the RuntimeException object
    """
    print >> sys.stderr, e


def createDSTREAMDTSL(dstreamAddress, rvcFile):
    """Creates a DTSL connection from a DSTREAM connection address.
    Params:
        dstreamAddress the connection address for a DSTREAM box. This is a
                       string e.g. 'TCP:hostname' or 'USB' or 'USB:012322'
        rvcFile to make a RDDI connection we need an .rvc file. This may
                or may not be a 'full' .rvc file depending on use case.
                For example to just connect to a JTAG server, a minimal
                .rvc file is sufficient, but for a full debug connection
                a full .rvc file would be required.
    Returns:
        a DTSLConnection instance. Note that the instance has _not_ been
        connected.
    """
    myPath = os.path.abspath(sys.argv[0])
    params = ConnectionParameters()
    params.rddiConfigFile = os.path.join(
        os.path.dirname(myPath), rvcFile)
    params.address = dstreamAddress
    dtslConnection = ConnectionManager.openConnection(params)
    return dtslConnection


def connectToDTSL(dtslConfigData):
    """ Makes our connection to DTSL and returns the connection object """
    params = dtslConfigData.getDTSLConnectionParameters()
    conn = ConnectionManager.openConnection(params)
    conn.connect()
    return conn


def connectToDevice(device):
    """ Makes a connection to a core (or other device)
    Parameters:
        core - the DTSL device to connect to
    """
    assert isinstance(device, ConnectableDevice)
    deviceInfo = StringBuilder(256)
    device.openConn(None, None, deviceInfo)
    deviceName = StringBuilder(256)
    deviceDetails = StringBuilder(256)
    device.getDeviceDetails(deviceName, deviceDetails)


def cvt32x2to64(values32, offset=0):
    return (values32[offset + 1] << 32) | (values32[offset] & 0xFFFFFFFF)


def cvt32x4to128(values32, offset=0):
    return (
        (values32[offset + 3] << 96) |
        ((values32[offset + 2] << 64) & 0x00000000FFFFFFFF0000000000000000) |
        ((values32[offset + 1] << 32) & 0x0000000000000000FFFFFFFF00000000) |
        (values32[offset] & 0x000000000000000000000000FFFFFFFF))


def readReg64(device, regID):
    assert isinstance(device, IDevice)
    regIDs = array([int(regID), int(regID + 1)], 'i')
    values32 = zeros(2, 'i')
    device.regReadList(regIDs, values32)
    return cvt32x2to64(values32)


def writeReg64(device, regID, value64):
    assert isinstance(device, IDevice)
    # a 64 bit reg write takes 2 x 32 bit reg writes
    regIDs = array([regID, regID + 1], 'i')
    values32 = array([Long(value64 & 0xFFFFFFFF).intValue(),
                      Long(value64 >> 32).intValue()], 'i')
    device.regWriteList(regIDs, values32)
