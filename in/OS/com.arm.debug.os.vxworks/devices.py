# Copyright (C) 2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for Wind River VxWorks RTOS
"""

from osapi import *
from utils import *

class Devices(Table):

    def __init__(self):
        cid = "dev"

        fields = [ createPrimaryField( cid, "id", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "drvtype", TEXT ) )
        fields.append( createField( cid, "drvnum", DECIMAL ) )
        fields.append( createField( cid, "drvinvocations", DECIMAL ) )
        fields.append( createField( cid, "drvflags", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord(self, debugSession, devPtr, drvNumMap):
        devStruct = devPtr.dereferencePointer()
        dev = devStruct.getStructureMembers()

        # Read the device structure members.
        devAddr = devPtr.readAsAddress()
        devName = getClassName(devStruct)
        drvNum = dev['drvNum'].readAsNumber()
        drvName = drvNumMap[drvNum] if drvNum in drvNumMap else None
        drvInvocationCount = dev['drvRefCount'].readAsNumber()
        drvFlags = longToHex(dev['drvRefFlag'].readAsNumber(), 32)

        # Submit the cells.
        cells = []
        cells.append(createAddressCell(devAddr))
        cells.append(createTextCell(devName))
        cells.append(createLocalisedTextCell(drvName))
        cells.append(createNumberCell(drvNum))
        cells.append(createNumberCell(drvInvocationCount))
        cells.append(createTextCell(drvFlags))

        return self.createRecord( cells )

    def getRecords(self, debugSession):
        devPtrList = readDeviceList(debugSession)
        drvNumMap = getDriverNumberMap(debugSession)
        return [ self.readRecord(debugSession, devPtr, drvNumMap) for devPtr in devPtrList ]

def getDriverNumberMap(debugger):
    """
    @brief  Builds a mapping of driver numbers (drvNum), as returned by
            iosDrvInstall to a localisation key describing the 'type' of device
            the driver represents. This only works for known driver types -
            those part of the core OS or one of the shipped device drivers. It
            is robust to the drivers not being installed.
            This is the only way of getting this string, even though it is not
            hugely robust as it only catches known driver types and will need
            updating if the hard-coded static field per driver changes.
    @param  debugger    DebugSession to query for drivers on.
    @return Dictionary mapping integer driver numbers to a string localisation
            key for a string describing the type of device the driver is for.
    """
    # Reads the given symbol and, if present, adds to given typeString (a
    # localisation key) to the given map.
    def _addDriverNumber(debugger, symbol, typeString, map):
        if debugger.symbolExists(symbol):
            drvNum = debugger.evaluateExpression(symbol).readAsNumber()
            if drvNum > 0:
                map[drvNum] = typeString

    drvNumMap = {}

    # Core OS devices
    # Null device
    drvNumMap[0] = 'dev.drvtype.null'
    # Kernel File Descriptor device
    if debugger.symbolExists('"iosKfdLib.c"::iosKfdHdr'):
        drvNum = debugger.evaluateExpression('"iosKfdLib.c"::iosKfdHdr').getStructureMembers()['drvNum'].readAsNumber()
        if drvNum > 0:
            drvNumMap[drvNum] = 'dev.drvtype.kfd'
    # Pseudo-Terminal Slave device
    _addDriverNumber(debugger, '"ptyDrv.c"::ptySlaveDrvNum', 'dev.drvtype.ptyslave', drvNumMap)
    # Pseudo-Terminal Master device
    _addDriverNumber(debugger, '"ptyDrv.c"::ptyMasterDrvNum', 'dev.drvtype.ptymaster', drvNumMap)
    # Terminal device
    _addDriverNumber(debugger, '"ttyDrv.c"::ttyDrvNum', 'dev.drvtype.tty', drvNumMap)
    # Pipe device
    _addDriverNumber(debugger, '"pipeDrv.c"::pipeDrvNum', 'dev.drvtype.pipe', drvNumMap)
    # RAM device
    _addDriverNumber(debugger, '"memDrv.c"::memDrvNum', 'dev.drvtype.mem', drvNumMap)
    # MVar device
    _addDriverNumber(debugger, '"mvarDrv.c"::mvarDrvNum', 'dev.drvtype.mvar', drvNumMap)
    # We could theoretically get the driver numbers of all virtual filesystems
    # too, however this is non-trivial and requires walking numerous data
    # structures.

    # POSIX drivers
    # POSIX Device Memory device
    _addDriverNumber(debugger, '"devMemFsLib.c"::devMemFsDrvNum', 'dev.drvtype.devmemfs', drvNumMap)
    # POSIX Shared Memory device
    _addDriverNumber(debugger, '"shmFsLib.c"::shmFsDrvNum', 'dev.drvtype.shmfs', drvNumMap)

    # Other official drivers
    # Virtual TCF device
    _addDriverNumber(debugger, '"hostFsLib.c"::hostFsDrvNum', 'dev.drvtype.hostfs', drvNumMap)
    # EEPROM device
    _addDriverNumber(debugger, '"vxbEeprom.c"::eepromDrvNum', 'dev.drvtype.eeprom', drvNumMap)
    # RTP ioctl interrupt node device
    _addDriverNumber(debugger, '"vxbRtpIoctlLib.c"::vxbRtpIrqNum', 'dev.drvtype.rtpirq', drvNumMap)
    # RTP ioctl device node device
    _addDriverNumber(debugger, '"vxbRtpIoctlLib.c"::vxbRtpDevNum', 'dev.drvtype.rtpdev', drvNumMap)
    # VxBus ioctl device
    _addDriverNumber(debugger, '"vxbIoctlLib.c"::vxbDrvNum', 'dev.drvtype.vxbus', drvNumMap)
    # HVFS device
    _addDriverNumber(debugger, '"hvfsLib.c"::hvfsFsDrvNum', 'dev.drvtype.hvfs', drvNumMap)
    # USB Printer device
    _addDriverNumber(debugger, '"usb2Prn.c"::usb2PrnDrvNum', 'dev.drvtype.usbprn', drvNumMap)
    # USB Serial device
    _addDriverNumber(debugger, '"usb2Serial.c"::usb2SerialDrvNum', 'dev.drvtype.usbser', drvNumMap)
    # USB Storage device
    _addDriverNumber(debugger, '"usb2MscDirectAccess.c"::usb2MscDrvNum', 'dev.drvtype.usbstr', drvNumMap)
    # USB Keyboard device
    _addDriverNumber(debugger, '"usb2Kbd_raw.c"::usb2KbdDrvNum', 'dev.drvtype.usbkbd', drvNumMap)
    # USB Mouse device
    _addDriverNumber(debugger, '"usb2Mse_raw.c"::usb2MseDrvNum', 'dev.drvtype.usbmse', drvNumMap)
    # USB-OTG device
    _addDriverNumber(debugger, '"usbOtg.c"::usbOtgDrvNum', 'dev.drvtype.usbotg', drvNumMap)
    # Virtual Root FS device
    _addDriverNumber(debugger, '"vrfsLib.c"::vrfsDrvNum', 'dev.drvtype.vrfs', drvNumMap)
    # Virtual Disk FS device
    _addDriverNumber(debugger, '"vdFsLib.c"::vdFsDrvNum', 'dev.drvtype.vdfs', drvNumMap)
    # Raw FS device
    _addDriverNumber(debugger, '"rawFsLib.c"::rawFsDrvNum', 'dev.drvtype.rawfs', drvNumMap)
    # VFS device
    _addDriverNumber(debugger, '"vnodeAff.c"::vnodeAffDriverNumber', 'dev.drvtype.vfs', drvNumMap)
    # CD-ROM FS device
    _addDriverNumber(debugger, '"cdromFsLib.c"::cdromFsDrvNum', 'dev.drvtype.cdrom', drvNumMap)
    # NFS2 device
    _addDriverNumber(debugger, '"nfs2Drv.c"::nfs2DrvNum', 'dev.drvtype.nfs2', drvNumMap)
    # NFS3 device
    _addDriverNumber(debugger, '"nfs3Drv.c"::nfs3DrvNum', 'dev.drvtype.nfs3', drvNumMap)
    # ROM FS device
    _addDriverNumber(debugger, '"romfsLib.c"::romfsFsDrvNum', 'dev.drvtype.romfs', drvNumMap)
    # DOS FS device
    _addDriverNumber(debugger, '"dosFsLib.c"::dosFsDrvNum', 'dev.drvtype.dosfs', drvNumMap)
    # Network File device
    _addDriverNumber(debugger, '"netDrv.c"::netDrvNum', 'dev.drvtype.net', drvNumMap)
    # Socket device
    if debugger.symbolExists('"ipcom_vxworks.c"::ipcom_port'):
        portStruct = debugger.evaluateExpression('"ipcom_vxworks.c"::ipcom_port').getStructureMembers()
        ethDevStruct = portStruct['dev_hdr'].getStructureMembers()
        devStruct = ethDevStruct['dev_hdr'].getStructureMembers()
        drvNum = devStruct['drvNum'].readAsNumber()
        if drvNum > 0:
            drvNumMap[drvNum] = 'dev.drvtype.sock'

    return drvNumMap
