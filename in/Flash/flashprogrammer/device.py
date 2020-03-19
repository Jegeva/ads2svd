from com.arm.rddi import RDDI_CAP_ID
from com.arm.rddi import RDDI
from com.arm.debug.dtsl.nativelayer import NativeException
from jarray import zeros
from java.lang import StringBuilder

def isDeviceOpen(dev):
    '''Test whether a device is open

    As RDDI doesn't have a call to directly determine if a device is open, an
    operation is attempted and any failure reason used to determine whether
    there is an open connection
    '''
    deviceOpen = True

    # RDDI doesn't have call to determine if a device is already open
    #  - try an operation and see how it fails
    try:
        # get device config item list - don't really care about the contents
        # but will throw with RDDI_NOCONN or RDDI_NOINIT if no connection is
        # open
        buf = StringBuilder(256)
        dev.getConfig("CONFIG_ITEMS", buf)
    except NativeException, e:
        err = e.getRDDIErrorCode()
        if err == RDDI.RDDI_NOCONN or err == RDDI.RDDI_NOINIT:
            deviceOpen = False
        # any other error means device is open

    return deviceOpen


def ensureDeviceOpen(dev):
    '''Ensure a device is open

    The script may be sharing a connection with other components of the debug
    session, so the device may already have an open connection.  The connection
    is only opened if there is no existing connection

    Returns True if device was opened, False if device was already open
    '''
    if not isDeviceOpen(dev):
        dev.openConn(None, None, None)
        return True
    else:
        return False
