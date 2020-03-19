#! /usr/bin/env python
# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.
from org.apache.log4j import Logger
from org.apache.log4j import Level
from org.apache.log4j import BasicConfigurator
from com.arm.debug.dtsl import ConnectionManager
from com.arm.debug.dtsl import DTSLException
from com.arm.debug.dtsl.components import ConnectableDevice
from com.arm.rddi import RDDIException
import sys
import math
import struct
from org.python.core import PyException
from dapexception import DAPException
from dap import DAPRegAccessJTAG
from dap import DAPRegAccessDAPTemplate
from dap import APBAPMemAccess
from dap import AHBAPCortexMMemAccess
from jtag import JTAG
from jtag import JTAGIDCODE
from dtslhelper import showDTSLException
from dtslhelper import showJythonException
from dtslhelper import createDSTREAMDTSL
from dtslhelper import connectToDevice
from dtslhelper import getRDDIDeviceByName
from options import ProgramOptions
from jarray import zeros
from time import sleep
from java.lang import StringBuilder
from progress import Progress

# import sys;
# sys.path.append(r'C:\Users\tarmitst\eclipse4.3-64\plugins\'
#                 'org.python.pydev_3.2.0.201312292215\pysrc')
# import pydevd

VERSION = "1.0"

SCC_APB_BASE = 0xFFFFF000
SCC_APB_SCAN_DEBUG_CTRL_REG = 0x88
SCDBG_MASTER_EN = 0x00000001
SCDBG_TRIG_WDOG = 0x00000002
SCDBG_TRIG_DBGACK_ATL0 = 0x00000004
SCDBG_TRIG_DBGACK_ATL1 = 0x00000008
SCDBG_TRIG_DBGACK_APL0 = 0x00000010
SCDBG_TRIG_DBGACK_APL1 = 0x00000020
SCDBG_TRIG_DBGACK_APL2 = 0x00000040
SCDBG_TRIG_DBGACK_APL3 = 0x00000080
SCDBG_TRIG_MANUAL = 0x00000100
SCDBG_TRIGGER = 0x00000200


class ProgramException(Exception):

    def __init__(self, description, cause=None):
        self.description = description
        self.cause = cause

    def getCause(self):
        return self.cause

    def __str__(self):
        msg = "ProgramException: %s" % (self.description)
        if self.cause is not None:
            msg = msg + "\nCaused by:\n%s" % (self.cause.__str__())
        return msg

    def getMessage(self):
        return "ProgramException: %s" % (self.description)


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
    return "0x%s" % ("0000000000000000%X" %
                     (rVal & 0xffffffffffffffff))[-16:]


def toHex(rVal, bitLength=32):
    """ Converts an value to a hex string
    Returns a string of the form 0xhhhh which is the hex value of rVal
    using as many nibble values required for the bitLength
    Parameters:
        rVal - the long value to be converted
        bitLength - number of bits to display (defaults to 32)
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


def getDTSLConfiguration(debugger):
    """ Returns the DTSL configuration object
        currently being used by the Arm Debugger
    Parameters:
        debugger - the Arm Debugger interface
    """
    dtslConnectionConfigurationKey = debugger.getConnectionConfigurationKey()
    dtslConnection = ConnectionManager.openConnection(
        dtslConnectionConfigurationKey)
    return dtslConnection.getConfiguration()


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


def showDAPException(e):
    """ Prints out a DAPException
    The exception chain is traversed and non-duplicated
    information from all levels is displayed
    Parameters:
        e - the DAPException object
    """
    print >> sys.stderr, "Caught DAP exception:"
    cause = e
    lastMessage = ""
    while cause is not None:
        nextMessage = cause.getMessage()
        if nextMessage != lastMessage:
            if nextMessage is not None:
                print >> sys.stderr, nextMessage
            lastMessage = nextMessage
        cause = cause.getCause()


def showProgramException(e):
    """ Prints out a ProgramException
    The exception chain is traversed and non-duplicated
    information from all levels is displayed
    Parameters:
        e - the ProgramException object
    """
    print >> sys.stderr, "Caught program exception:"
    cause = e
    lastMessage = ""
    while cause is not None:
        nextMessage = cause.getMessage()
        if nextMessage != lastMessage:
            if nextMessage is not None:
                print >> sys.stderr, nextMessage
            lastMessage = nextMessage
        cause = cause.getCause()


def isARMDAP(idcodeVal):
    """Determines if a JTAG IDCODE value matches an ARM DAP device
    Params:
        idcodeVal - the 32 bit IDCODE value
    Returns:
         True if idcodeVal is an ARM DAP
         False if not
    """
    Company_ARM = 0x23B
    PartCode_DAP = 0xBA00
    isDAP = False
    idcode = JTAGIDCODE(idcodeVal)
    if idcode.getCompany() == Company_ARM:
        if idcode.getPart() == PartCode_DAP:
            isDAP = True
    return isDAP


def isJunoJTAGChain(debugJTAG):
    """Inspects the devices on the JTAG scan chain and decides if it looks
       like a Juno board.
    Params:
        debugJTAG - the JTAG object we use to do scans
    Returns:
        True if the JTAG chain looks like Juno
        False if the JTAG chain does not looks like Juno
    """
    deviceCount = debugJTAG.countJTAGDevices()
#    print "Detected %d JTAG devices on the chain" % (deviceCount)
    if deviceCount > 0:
        idcodes = debugJTAG.readIDCodes(deviceCount)
#        print "IDCODES = "
#        for dev in range(deviceCount):
#            idcode = JTAGIDCODE(idcodes[dev])
#            print "%s (Manufacturer: %s, Part: %s, Rev: %s)" % (
#                    toHex(idcodes[dev]),
#                    toHex(idcode.getCompany()),
#                    toHex(idcode.getPart()),
#                    toHex(idcode.getRev()))
    # We should see two DAPs
    looksLikeJuno = False
    if deviceCount == 2:
        if (isARMDAP(idcodes[0]) and (isARMDAP(idcodes[1]))):
            looksLikeJuno = True
    return looksLikeJuno


def checkIsJuno(memAccess):
    """Reads the Peripheral & component ID regs to check for Juno platform
    Params:
        memAccess - the object we use to perform memory reads
    Returns:
        True if ID tests pass, False if fail
    """
    idRegs = [
        ('Peripheral ID 0', 0xFE0, 0xAD, 0xFF),
        ('Peripheral ID 1', 0xFE4, 0xB0, 0xFF),
        ('Peripheral ID 2', 0xFE8, 0x0B, 0xFF),
        ('Peripheral ID 3', 0xFEC, 0x00, 0xFF),
        ('Peripheral ID 4', 0xFD0, 0x04, 0xFF),
        ('Component ID 0',  0xFF0, 0x0D, 0xFF),
        ('Component ID 1',  0xFF4, 0xF0, 0xFF),
        ('Component ID 2',  0xFF8, 0x05, 0xFF),
        ('Component ID 3',  0xFFC, 0xB1, 0xFF)
    ]
    isJuno = True
    for idReg in idRegs:
        name = idReg[0]
        offset = idReg[1]
        expectedValue = idReg[2]
        mask = idReg[3]
        idRegVal = memAccess.readAPMemBlock32(
            address=SCC_APB_BASE + offset,
            nWords=1)[0] & mask
        if idRegVal != expectedValue:
            print("checkIsJuno: "
                  "Register %s failed check; "
                  "read %s expected %s" % (
                      name, toHex(idRegVal), toHex(expectedValue)))
            isJuno = False
    return isJuno


def readAPB32(memAccess, apbAddress):
    return memAccess.readAPMemBlock32(address=apbAddress, nWords=1)[0]


def showPCSMControlRegs(memAccess, title, apbBaseAddr):
    print "%s PCSM Registers:" % (title)
    mode = readAPB32(memAccess, apbBaseAddr)
    print "   PCSM_MODE          = %s" % (toHex(mode))
    trickleDelay = readAPB32(memAccess, apbBaseAddr + 0x04)
    print "   PCSM_TRICKLE_DELAY = %s" % (toHex(trickleDelay))
    hammerDelay = readAPB32(memAccess, apbBaseAddr + 0x08)
    print "   PCSM_HAMMER_DELAY  = %s" % (toHex(hammerDelay))
    ramDelay = readAPB32(memAccess, apbBaseAddr + 0x0C)
    print "   PCSM_RAM_DELAY     = %s" % (toHex(ramDelay))
    manualPwrup = readAPB32(memAccess, apbBaseAddr + 0x10)
    print "   PCSM_MANUAL_PWRUP  = %s" % (toHex(manualPwrup))
    pwrupAck = readAPB32(memAccess, apbBaseAddr + 0x14)
    print "   PCSM_PWRUPACK      = %s" % (toHex(pwrupAck))


def installJunoStopClockTriggers(memAccess, triggerSources):
    """Installs the stop clock triggers for single chain debug mode.
       When one of the triggers fires it will sets the DFT Bist JTAG port
       into single chain debug mode which allows the flop chains to be
       scanned out. If the triggerSources[] has TRIG_MANUAL set, this will
       cause an immediate entry into stop clock mode.
       NOTE: The DFT Bist JTAG port is _not_ the DAP debug JTAG port
    Params:
        memAccess - the object we use to perform memory reads
        triggerSources - dictionary of triggers sources and whether they
                         are enabled
    """
    if False:
        showPCSMControlRegs(memAccess, 'Cortex-A57_0', SCC_APB_BASE + 0x200)
        showPCSMControlRegs(memAccess, 'Cortex-A57_1', SCC_APB_BASE + 0x300)
        showPCSMControlRegs(memAccess, 'Cortex-A57_L2', SCC_APB_BASE + 0x400)
        showPCSMControlRegs(memAccess, 'Cortex-A53_0', SCC_APB_BASE + 0x500)
        showPCSMControlRegs(memAccess, 'Cortex-A53_1', SCC_APB_BASE + 0x600)
        showPCSMControlRegs(memAccess, 'Cortex-A53_2', SCC_APB_BASE + 0x700)
        showPCSMControlRegs(memAccess, 'Cortex-A53_3', SCC_APB_BASE + 0x800)
        showPCSMControlRegs(memAccess, 'Cortex-A53_L2', SCC_APB_BASE + 0x900)
    # Read the existing register value
    # Bit assignments are:
    #  [0]    SCDBG_MASTER_EN          RW Scan-based debug master enable
    #  [1]    SCDBG_TRIG_WDOG          RW Include watchdog time-out as a
    #                                     trigger
    #  [2]    SCDBG_TRIG_DBGACK_ATL[0] RW Include Atlas CPU 0 debug
    #                                     acknowledge as a trigger
    #  [3]    SCDBG_TRIG_DBGACK_ATL[1] RW Include Atlas CPU 1 debug
    #                                     acknowledge as a trigger
    #  [4]    SCDBG_TRIG_DBGACK_APL[0] RW Include Apollo CPU 0 debug
    #                                     acknowledge as a trigger
    #  [5]    SCDBG_TRIG_DBGACK_APL[1] RW Include Apollo CPU 1 debug
    #                                     acknowledge as a trigger
    #  [6]    SCDBG_TRIG_DBGACK_APL[2] RW Include Apollo CPU 2 debug
    #                                     acknowledge as a trigger
    #  [7]    SCDBG_TRIG_DBGACK_APL[3] RW Include Apollo CPU 3 debug
    #                                     acknowledge as a trigger
    #  [8]    SCDBG_TRIG_MANUAL        RW Include a manual trigger, which
    #                                     is a write to SCDBG_TRIGGER register
    #  [9]    SCDBG_ TRIGGER           RW Writing 0x1 to this register will
    #                                     trigger scan-based dump if the
    #                                     SCDBG_TRIG_MANUAL is enabled
    # [10]    SCDBG_MODE_STATUS        RO Sticky active HIGH signal which
    #                                     indicates that Juno has entered
    #                                     into Scan-based debug mode
    # [15:11] Reserved                 RW
    # [31:16] SCDBG_DELAY              RW Number of AON_REF_CLK cycles to
    #                                     wait after a write to SCDBG_TRIGGER
    #                                     register. Default is 0 and maximum
    #                                     manualTriggerDelay is 64K cycles.
    cfgreg = memAccess.readAPMemBlock32(
        address=SCC_APB_BASE + SCC_APB_SCAN_DEBUG_CTRL_REG,
        nWords=1)
    # Clear the master enable
    cfgreg[0] = cfgreg[0] & ~SCDBG_MASTER_EN
    # Now inspect each source and if found enabled we enable the source and
    # set the master enable
    if triggerSources[ProgramOptions.TRIG_MANUAL]:
        cfgreg[0] = cfgreg[0] | (SCDBG_MASTER_EN |
                                 SCDBG_TRIG_MANUAL |
                                 SCDBG_TRIGGER)
        cfgreg[0] = cfgreg[0] | (
            (triggerSources[ProgramOptions.TRIG_MANUAL_DELAY] & 0xFFFF) << 16)
        # Note: There is no point in an else: clause here because if the bit
        # was set previously the system would already be halted!
    if triggerSources[ProgramOptions.TRIG_WATCHDOG]:
        cfgreg[0] = cfgreg[0] | (SCDBG_MASTER_EN |
                                 SCDBG_TRIG_WDOG)
    else:
        cfgreg[0] = cfgreg[0] & ~SCDBG_TRIG_WDOG
    if triggerSources[ProgramOptions.TRIG_CORTEX_A57_0]:
        cfgreg[0] = cfgreg[0] | (SCDBG_MASTER_EN |
                                 SCDBG_TRIG_DBGACK_ATL0)
    else:
        cfgreg[0] = cfgreg[0] & ~SCDBG_TRIG_DBGACK_ATL0
    if triggerSources[ProgramOptions.TRIG_CORTEX_A57_1]:
        cfgreg[0] = cfgreg[0] | (SCDBG_MASTER_EN |
                                 SCDBG_TRIG_DBGACK_ATL1)
    else:
        cfgreg[0] = cfgreg[0] & ~SCDBG_TRIG_DBGACK_ATL1
    if triggerSources[ProgramOptions.TRIG_CORTEX_A53_0]:
        cfgreg[0] = cfgreg[0] | (SCDBG_MASTER_EN |
                                 SCDBG_TRIG_DBGACK_APL0)
    else:
        cfgreg[0] = cfgreg[0] & ~SCDBG_TRIG_DBGACK_APL0
    if triggerSources[ProgramOptions.TRIG_CORTEX_A53_1]:
        cfgreg[0] = cfgreg[0] | (SCDBG_MASTER_EN |
                                 SCDBG_TRIG_DBGACK_APL1)
    else:
        cfgreg[0] = cfgreg[0] & ~SCDBG_TRIG_DBGACK_APL1
    if triggerSources[ProgramOptions.TRIG_CORTEX_A53_2]:
        cfgreg[0] = cfgreg[0] | (SCDBG_MASTER_EN |
                                 SCDBG_TRIG_DBGACK_APL2)
    else:
        cfgreg[0] = cfgreg[0] & ~SCDBG_TRIG_DBGACK_APL2
    if triggerSources[ProgramOptions.TRIG_CORTEX_A53_3]:
        cfgreg[0] = cfgreg[0] | (SCDBG_MASTER_EN |
                                 SCDBG_TRIG_DBGACK_APL3)
    else:
        cfgreg[0] = cfgreg[0] & ~SCDBG_TRIG_DBGACK_APL3
    try:
        memAccess.writeAPMemBlock32(
            address=SCC_APB_BASE + SCC_APB_SCAN_DEBUG_CTRL_REG,
            data32=cfgreg)
    except:
        # For some target connections, once stop clock mode has been manually
        # triggered the memory write call will appear to fail. It most likely
        # did not fail to do the write itself, but failed on anything attempted
        # as a target interaction after its clocks were halted. So we can
        # safely ignore any such error.
        pass
    # NOTE: If TRIG_MANUAL was enabled the DAP is now dead


def preventCorePowerDown(memAccess):
    """Tries to stop the cores from powering down.
    Params:
        memAccess - the object we use to perform memory accesses
    """
    CA57_0_BASE_ADDRESS = 0x82010000
    CA57_1_BASE_ADDRESS = 0x82110000
    CA53_0_BASE_ADDRESS = 0x83010000
    CA53_1_BASE_ADDRESS = 0x83110000
    CA53_2_BASE_ADDRESS = 0x83210000
    CA53_3_BASE_ADDRESS = 0x83310000
    EDPRCR_OFFSET = 0x310
    EDPRCR_CORENPDRQ = 0x00000001
    EDPRCR_COREPURQ = 0x00000008
    coreBases = [
        CA57_0_BASE_ADDRESS,
        CA57_1_BASE_ADDRESS,
        CA53_0_BASE_ADDRESS,
        CA53_1_BASE_ADDRESS,
        CA53_2_BASE_ADDRESS,
        CA53_3_BASE_ADDRESS
    ]
    for coreBase in coreBases:
        # Read the existing EDPRCR register value
        edprcr = memAccess.readAPMemBlock32(
            address=coreBase + EDPRCR_OFFSET,
            nWords=1)
        # Set the CORENPDRQ bit in an attempt to prevent true power down
        edprcr[0] = edprcr[0] | EDPRCR_CORENPDRQ
        # Request that the core power up
        edprcr[0] = edprcr[0] | EDPRCR_COREPURQ
        # Write the new value back
        memAccess.writeAPMemBlock32(
            address=coreBase + EDPRCR_OFFSET,
            data32=edprcr)


def powerUpDAP(DAP):
    dapPoweredUp = False
    if DAP.powerUp():
        dapPoweredUp = True
    else:
        for _ in range(5):
            if DAP.isPoweredUp():
                dapPoweredUp = True
                break
            sleep(0.050)  # kip for 50ms
    return dapPoweredUp


def preventCortexAFromPowerDown(cortexADAP):
    memAccess = APBAPMemAccess(dapRegAccess=cortexADAP, apIdx=1)
    preventCorePowerDown(memAccess)


def configureJunoStopClockTriggers(cortexMDAP, triggerSources):
    """Places the scan chain into stop clock mode
    Params:
        debugJTAG - the JTAG object we use to do debug chain scans
        triggerSources - dictionary of triggers sources and whether they
                         are enabled
    """
    memAccess = AHBAPCortexMMemAccess(dapRegAccess=cortexMDAP, apIdx=0)
    isJuno = checkIsJuno(memAccess)
    if isJuno:
        installJunoStopClockTriggers(memAccess, triggerSources)
        print "Manually enabled single chain mode"
    else:
        raise ProgramException(
            "Platform does not have Juno Peripheral/Component IDs")


def configureStopClockTriggersByJTAG(debugDSTREAM, triggerSources):
    """Configures the stop clock mode triggers on the Juno platform. The
       mechanism by which we do this is to use direct JTAG access to access
       the Cortex-M sub-system DAP.
    Params:
        debugDSTREAM - the connection string for the DSTREAM unit plugged
                       in to J25
        triggerSources - dictionary of triggers sources and whether they
                         are enabled
    """
    debugJTAG = None
    debug = None
    try:
        if debugDSTREAM == ProgramOptions.DS_DSTREAM:
            debugDTSLConnection = getDSDTSL()
            debugJTAG = JTAG(
                getIJTAGFromDTSLConnection(debugDTSLConnection),
                debugDSTREAM)
            debug = getIDEBUGFromDTSLConnection(debugDTSLConnection)
            print "Pausing Arm DS Debug session"
            debug.setConfig(0, "SessionPause", "1")
        else:
            debugDTSLConnection = createDSTREAMDTSL(debugDSTREAM)
            debugJTAG = JTAG(
                getIJTAGFromDTSLConnection(debugDTSLConnection),
                debugDSTREAM)
            print "Connecting direct Debug JTAG access: %s" % (
                debugJTAG.getConnectionAddress())
        debugJTAG.connect()
        debugJTAG.rddiJTAG().setJTAGClock(10000000)
        debugJTAG.rddiJTAG().setUseRTCLK(0)
        debugJTAG.rddiJTAG().nTRST(1)
        debugJTAG.rddiJTAG().nTRST(0)
        debugJTAG.tapReset()
        if (not isJunoJTAGChain(debugJTAG)):
            raise ProgramException(
                "The JTAG chain does not look like Juno")
        # There is a possibility that powering up the main debug DAP will
        # prevent the SCP from actually powering down the Cortex-A cores.
        # This is required for Juno_r0 to ensure an intact flop chain is
        # scanned out.
        # Configure the scan chain for the Cortex-Ax DAP
        # TDI -> IR:4 -> IR:4 -> TDO
        #        DAP(*)  DAP
        debugJTAG.rddiJTAG().configScanChain(4, 0, 1, 0)
        cortexADAP = DAPRegAccessJTAG(debugJTAG)
        if not powerUpDAP(cortexADAP):
            raise ProgramException(
                "Failed to power up the Cortex-A DAP")
        preventCortexAFromPowerDown(cortexADAP)
        debugJTAG.rddiJTAG().configScanChain(0, 4, 0, 1)
        cortexMDAP = DAPRegAccessJTAG(debugJTAG)
        if not powerUpDAP(cortexMDAP):
            raise ProgramException(
                "Failed to power up the Cortex-M DAP")
        configureJunoStopClockTriggers(cortexMDAP, triggerSources)
    finally:
        if (debugJTAG is not None) and debugJTAG.isConnected():
            print "Disconnecting direct Debug JTAG access"
            debugJTAG.disconnect()
        if debug is not None:
            print "Resuming Arm DS Debug session"
            debug.setConfig(0, "SessionPause", "0")


def configureStopClockTriggersByDAPTemplate(debugDSTREAM, triggerSources):
    """Configures the stop clock mode triggers on the Juno platform. The
       mechanism by which we do this is to use the DAP template within
       DSTREAM to access the Cortex-M sub-system DAP.
    Params:
        debugDSTREAM - the connection string for the DSTREAM unit plugged
                       in to J25
        triggerSources - dictionary of triggers sources and whether they
                         are enabled
    """
    debug = None
    didDebugConnect = False
    try:
        if debugDSTREAM == ProgramOptions.DS_DSTREAM:
            debugDTSLConnection = getDSDTSL()
            debug = getIDEBUGFromDTSLConnection(debugDTSLConnection)
            # Coming from Arm DS, we assume the debug connection is already
            # connected to the DSTREAM
        else:
            debugDTSLConnection = createDSTREAMDTSL(debugDSTREAM)
            debug = getIDEBUGFromDTSLConnection(debugDTSLConnection)
            print "Connecting to DAP templates on: %s" % (
                debugDSTREAM)
            debug.connect(None, None, None, None)
            didDebugConnect = True
        debugDTSLConfiguration = debugDTSLConnection.getConfiguration()
        # Get the DAP for the Cortex-A subsystem
        devID = getRDDIDeviceByName(debugDTSLConfiguration, "CortexA-DAP")
        csdapA = ConnectableDevice(
            debugDTSLConfiguration, devID, "CortexA-DAP")
        connectToDevice(csdapA)
        csdapA.setConfig("DAP_POWER_UP", "1")
        cortexADAP = DAPRegAccessDAPTemplate(csdapA)
        preventCortexAFromPowerDown(cortexADAP)
        csdapA.closeConn()
        # Get the DAP for the Cortex-M subsystem
        devID = getRDDIDeviceByName(debugDTSLConfiguration, "CortexM-DAP")
        csdapM = ConnectableDevice(
            debugDTSLConfiguration, devID, "CortexM-DAP")
        connectToDevice(csdapM)
        csdapM.setConfig("DAP_POWER_UP", "1")
        cortexMDAP = DAPRegAccessDAPTemplate(csdapM)
        configureJunoStopClockTriggers(cortexMDAP, triggerSources)
        csdapM.closeConn()
    finally:
        if debug is not None:
            if didDebugConnect:
                print "Disconnecting from DAP templates"
                debug.disconnect(1)


def genIDBlock(buffer, offset):
    """Creates a marker of 8 x 32 bit words which should be visible as text
       within a binary data stream of arbitrary bit length. What this means
       is that when viewing the 8 x 32 bit words as ASCII, the word 'ARM'
       will be visible at some point within the block'
    Params:
        buffer - into which we write the 8 x 32 bit block
        offset - the start offset within buffer to place the block
    """
    # Start with '0ARM' as a 32 bit word, then generate this pattern
    # 7 more times successively shifted right by a bit. Then no matter
    # what bit shift we end up with MOD (0..7) we will see the text 'ARM'
    # at some point in the block
    idAtom = (ord('A') << 16) + (ord('R') << 8) + (ord('M'))
    for _ in range(8):
        buffer[offset + 0] = (idAtom >> 24) & 0xFF
        buffer[offset + 1] = (idAtom >> 16) & 0xFF
        buffer[offset + 2] = (idAtom >> 8) & 0xFF
        buffer[offset + 3] = (idAtom) & 0xFF
        idAtom = idAtom << 1
        offset = offset + 4


def writeBitStreamToDumpFile(dumpFile, bitStream, bitLength, isInverted):
    """Writes a stream of scan bits to a dump file in a format compatible
       with the map_scan_data.pl script. This seems to be a byte per bit
       format.
    Params:
        dumpFile - the open, binary file we write to
        bitStream - the byte array containing the scan bits
        bitLength - the number of bits in the stream
        isInverted - whether to invert the bits as we write them
    Returns:
        the number of bytes written to the file
    """
    bytesUsed = 0
    if False:
        zero = zeros(1, 'B')
        one = zeros(1, 'B')
        if isInverted:
            one[0] = 0
            zero[0] = 1
        else:
            one[0] = 1
            zero[0] = 0
        mask = 0x01
        idx = 0
        for _ in range(bitLength):
            if bitStream[idx] & mask == 0:
                dumpFile.write(zero)
            else:
                dumpFile.write(one)
            mask = mask << 1
            if mask == 0x100:
                mask = 1
                idx = idx + 1
        bytesUsed = bitLength
    else:
        if isInverted:
            for idx in range(len(bitStream)):
                bitStream[idx] = ~bitStream[idx]
        if bitLength == len(bitStream):
            dumpFile.write(bitStream)
        else:
            dumpFile.write(bitStream.tostring()[:1 + (bitLength - 1) / 8])
        bytesUsed = int((bitLength + 7) / 8)
    return bytesUsed


def scanDump(scanJTAG, dumpFilename, IRValue, isInverted, bitCount):
    """Pulls a scan dump off chip and writes it to a (binary) file
    Params:
        scanJTAG - the JTAG object we use to do stop clock chain scans
        dumpFile - the file name we should store the scan data into
        IRValue - the JTAG instruction register value we write (26 bits)
        isInverted - whether the scan chain is inverted or not
        bitCount - the bit length of the chain to dump
    """
    progress = Progress()
    progress.setRange(0, bitCount)
    progress.setCurrentOperation("Writing: %s" % (dumpFilename))
    dumpFile = open(dumpFilename, 'wb')
    bitProgress = 0
    fileByteCount = 0
    try:
        # Write the IR value
        irBits = struct.pack('<I', IRValue)
        # The DR scan chain is registered which causes a 1 bit delay, so we
        # write the IR and junk the first DR bit
        zbits = zeros(1, 'b')
        scanJTAG.rddiJTAG().scanIRDR(26, irBits, 1, zbits, zbits,
                                     JTAG.PAUSE_DR, True)
        # Do scans in largest available block size
        subBlockSize = scanJTAG.getMaxJTAGBlockSize()
        # The data block we write out starts with the bottom 16 bits of DRValue
        # This enables us to check the chain integrity when we have finished
        # scanning out all data
        DRValue = 0xABCD
        txBits = zeros(subBlockSize / 8, 'B')
        txBits[0] = (DRValue >> 0) & 0xFF
        txBits[1] = (DRValue >> 8) & 0xFF
        # genIDBlock(txBits, 2)
        txBits = txBits.tostring()
        rxBits = zeros(subBlockSize / 8, 'b')
        while bitCount > 0:
            scanLen = min(bitCount, subBlockSize)
            scanJTAG.rddiJTAG().scanIO(JTAG.DR, scanLen,
                                       txBits,
                                       rxBits,
                                       JTAG.PAUSE_DR, True)
            # NOTE: If the scan data is inverted, we dont invert the data
            #       when we write it to file because the post processing
            #       scripts are expecting inverted data
            fileByteCount += writeBitStreamToDumpFile(dumpFile, rxBits,
                                                      scanLen, False)
            bitCount = bitCount - scanLen
            bitProgress = bitProgress + scanLen
            progress.setProgress(bitProgress)
        # We should now be able to read back the initial txBits.
        # We only check the first 16 bits - but since the flop chain is 1 bit
        # delayed, we scan out/in 17 bits and junk the 1st one received back
        scanJTAG.rddiJTAG().scanIO(JTAG.DR, 17, None, rxBits,
                                   JTAG.RTI, True)
        check = (struct.unpack('<I', rxBits.tostring()[:4])[0] >> 1) & 0xFFFF
        if isInverted:
            check = ~check & 0xFFFF
        if check != DRValue:
            # This check will always fail on Juno_r0 when any core in the
            # chain was powered down. So for now we just show a warning message
            # rather than throwing an exception
            progress.error("scanDump DR check failed, read %s expected %s.\n"
                           "It is likely that one or more cores were not "
                           "powered up\nand so the chain data may be "
                           "incomplete."
                           % (toHex(check, 16), toHex(DRValue, 16)))
#            raise ProgramException(
#                    "scanDump DR check failed, read %s expected %s" % (
#                                toHex(check), toHex(DRCheck)))
    finally:
        dumpFile.close()
        progress.setCompleted("Wrote %d bits as %d bytes" % (
                              bitProgress,
                              fileByteCount))


def getScanJTAG(scanDSTREAM):
    """Creates a JTAG interface to the scan DSTREAM box. If the DSTREAM box
       is also being used by Arm DS, we also return the debug interface so that
       it may be paused (if required).
    Params:
        scanDSTREAM - the connection string for the JTAG scan DSTREAM box
    """
    debug = None
    if scanDSTREAM == ProgramOptions.DS_DSTREAM:
        scanDTSLConnection = getDSDTSL()
        scanJTAG = JTAG(
            getIJTAGFromDTSLConnection(scanDTSLConnection),
            scanDSTREAM)
        debug = getIDEBUGFromDTSLConnection(scanDTSLConnection)
    else:
        if scanDSTREAM == ProgramOptions.DS_DTSLOPTS:
            # We should get the DSTREAM address from the debugger's DTSL
            # options. Note the dependency on the name path of the DTSL option!
            dsDTSLConnection = getDSDTSL()
            dtslConfiguration = dsDTSLConnection.getConfiguration()
            scanDSTREAM = dtslConfiguration.getOptionValue(
                "options.stopclock.enable.scanDSTREAM")
        scanDTSLConnection = createDSTREAMDTSL(scanDSTREAM)
        scanJTAG = JTAG(getIJTAGFromDTSLConnection(scanDTSLConnection),
                        scanDSTREAM)
    return scanJTAG, debug


def scanFlopChains(scanDSTREAM, doScanA57, a57File, doScanA53, a53File):
    """Scans out the flop chains for the ARM Cortex cores.
    Params:
        scanDSTREAM - the connection string for the JTAG scan DSTREAM box
        cortexA57File - the file name we should store the Cortex-A57 scan data
                        into. This is None if no store of the scan data is
                        required.
        cortexA53File - the file name we should store the Cortex-A57 scan data
                        into. This is None if no store of the scan data is
                        required.
    """
    scanJTAG, debug = getScanJTAG(scanDSTREAM)
    if debug is not None:
        print "Pausing Arm DS Debug session"
        debug.setConfig(0, "SessionPause", "1")
    print "Connecting direct Scan JTAG access: %s" % (
        scanJTAG.getConnectionAddress())
    scanJTAG.connect()
    try:
        scanJTAG.rddiJTAG().setJTAGClock(10000000)
        scanJTAG.rddiJTAG().setUseRTCLK(0)
        scanJTAG.rddiJTAG().configScanChain(0, 0, 0, 0)
        scanJTAG.rddiJTAG().nTRST(1)
        scanJTAG.rddiJTAG().nTRST(0)
        if doScanA57:
            scanJTAG.tapReset()
            IRValue = 0x206075A
            isInverted = True
            bitCount = 494248
            scanDump(scanJTAG, a57File, IRValue, isInverted, bitCount)
        if doScanA53:
            scanJTAG.tapReset()
            IRValue = 0x206065A
            isInverted = False
            bitCount = 247391
            scanDump(scanJTAG, a53File, IRValue, isInverted, bitCount)
    finally:
        if (scanJTAG is not None) and scanJTAG.isConnected():
            # We leave nTRST active on exit - so we behave as if the nTRST
            # shorting jumper is in place
            scanJTAG.rddiJTAG().nTRST(1)
            print "Disconnecting direct Scan JTAG access"
            scanJTAG.disconnect()
        if debug is not None:
            print "Resuming Arm DS Debug session"
            debug.setConfig(0, "SessionPause", "0")


def setScanJumper(scanDSTREAM):
    """Sets the scan JTAG nTRST active low to simulate the operation of the
       jumper usually connected to J76
    Params:
        scanDSTREAM - the connection string for the JTAG scan DSTREAM box
    """
    scanJTAG, debug = getScanJTAG(scanDSTREAM)
    if debug is not None:
        print "Pausing Arm DS Debug session"
        debug.setConfig(0, "SessionPause", "1")
    print "Connecting direct Scan JTAG access: %s" % (
        scanJTAG.getConnectionAddress())
    scanJTAG.connect()
    try:
        # We leave nTRST active on exit - so we behave as if the nTRST
        # shorting jumper is in place
        scanJTAG.rddiJTAG().nTRST(1)
    finally:
        if (scanJTAG is not None) and scanJTAG.isConnected():
            print "Disconnecting direct Scan JTAG access"
            scanJTAG.disconnect()
        if debug is not None:
            print "Resuming Arm DS Debug session"
            debug.setConfig(0, "SessionPause", "0")


def getIJTAGFromDTSLConnection(dtslConnection):
    """Gets hold of the IJTAG interface from a DTSLConfiguration
    Params:
        dtslConnection the DTSLConnection from which we get the IJTAG interface
    """
    return dtslConnection.getConfiguration().getJTAG()


def getIDEBUGFromDTSLConnection(dtslConnection):
    """Gets hold of the IDEBUG interface from a DTSLConfiguration
    Params:
        dtslConnection the DTSLConnection from which we get the
        IDEBUG interface
    """
    return dtslConnection.getConfiguration().getDebug()


def detectDS():
    """Detects if we have been launched from within Arm DS
    Returns:
        True if lauched from Arm DS
        False if not i.e. run outside of a Arm DS debug session
    """
    fromDS = False
    try:
        from arm_ds.debugger_v1 import Debugger  # @UnusedImport
        fromDS = True
    except ImportError:
        fromDS = False
        setupLogging()
    return fromDS


def getDSDTSL():
    """For an existing Arm DS connection, we return the DTSL connection
    Returns:
        the DTSLConnection instance
    """
    try:
        from arm_ds.debugger_v1 import Debugger
        debugger = Debugger()
        dtslConfigurationKey = debugger.getConnectionConfigurationKey()
        dtslConnection = ConnectionManager.openConnection(
            dtslConfigurationKey)
    except ImportError:
        dtslConnection = None
    return dtslConnection


def setupLogging():
    """Initialises the log4j logger"""
    BasicConfigurator.configure()
    logger = Logger.getRootLogger()
    assert isinstance(logger, Logger)
    logger.setLevel(Level.ERROR)  # use Level.DEBUG for lots of logging


def getVCCLevel(debug):
    """Tries to determine the Vcc level on the JTAG connector
    Params:
        debug - the RDDI-DEBUG connection
    Returns:
        "H" if Vcc considered high,
        "L" if Vcc considered low,
        "X" if failed to determine Vcc level
    """
    try:
        output = StringBuilder(128)
        debug.getConfig(0, "VCC", output)
        vccValue = int(output.toString())
        if vccValue == 0x10000000:
            return "X"
        elif vccValue == 0x20000000:
            return "L"
        elif vccValue == 0x30000000:
            return "H"
        elif vccValue < 20000:
            if (vccValue / 1000.0) < 0.5:
                return "L"
            return "H"
        return "X"
    except Exception:
        return "X"


def waitForDSTREAMUnplugged(debug):
    """Tries to detect DSTREAM being unplugged from a powered target
    Params:
        debug the RDDI-DEBUG interface
    """
    # Wait until target Vcc is seen as consistently low for 1 sec
    lowCount = 0
    while lowCount < 5:
        if getVCCLevel(debug) == "L":
            lowCount = lowCount + 1
        else:
            lowCount = 0
        sleep(0.2)


def waitForDSTREAMPluggedIn(debug):
    """Tries to detect DSTREAM being plugged from a powered target
    Params:
        debug the RDDI-DEBUG interface
    """
    # Wait until target Vcc is seen as consistently high for 1 sec
    highCount = 0
    while highCount < 5:
        if getVCCLevel(debug) == "H":
            highCount = highCount + 1
        else:
            highCount = 0
        sleep(0.2)


def guideUserToSwapDSTREAMConnectors(dstream):
    """Guides the user to swap the DSTREAM unit from J25 to J76
    Params:
        dstream - the DSTREAM connection address of the unit to swap
    """
    try:
        if dstream == "DS:":
            debugDTSLConnection = getDSDTSL()
            debug = getIDEBUGFromDTSLConnection(debugDTSLConnection)
        else:
            debugDTSLConnection = createDSTREAMDTSL(dstream)
            debug = getIDEBUGFromDTSLConnection(debugDTSLConnection)
            userName = "junostopclock"
            clientInfo = StringBuilder(1024)
            iceInfo = StringBuilder(1024)
            copyrightInfo = StringBuilder(1024)
            debug.connect(userName, clientInfo, iceInfo, copyrightInfo)
        print("Please:\n"
              "  1. unplug DSTREAM [%s] from J25\n"
              "  2. remove any shorting link between pins 3 & 4 of J76\n"
              "  3. plug DSTREAM into J76"
              % (dstream)
              )
        waitForDSTREAMUnplugged(debug)
        print("Detected DSTREAM being unplugged, now plug it into J76")
        waitForDSTREAMPluggedIn(debug)
        print("Detected DSTREAM being plugged in")
        sleep(1.0)  # Give some time to make sure seated correctly
    finally:
        if dstream != "DS:":
            debug.disconnect(0)


if __name__ == "__main__":
    # pydevd.settrace(stdoutToServer=True, stderrToServer=True)
    fromDS = detectDS()
    options = ProgramOptions("JunoStopClock", VERSION, fromDS)
    if options.processOptions():
        try:
            # Have we been asked to trigger stop clock mode?
            if options.hasTriggerRequests():
                if options.getUseVSTREAM():
                    configureStopClockTriggersByDAPTemplate(
                        options.getDebugDSTREAM(),
                        options.getTriggerSources())
                else:
                    configureStopClockTriggersByJTAG(
                        options.getDebugDSTREAM(),
                        options.getTriggerSources())
            if options.getDebugDSTREAM() == options.getScanDSTREAM():
                # The same DSTREAM unit is being used for both debug and
                # flop scan, so guide the user to swap from J25 to J76
                guideUserToSwapDSTREAMConnectors(options.getDebugDSTREAM())
            # Have we been asked to scan out the A57 or A53 chains?
            if options.getScanA57() or options.getScanA53():
                scanFlopChains(options.getScanDSTREAM(),
                               options.getScanA57(),
                               options.getCortexA57File(),
                               options.getScanA53(),
                               options.getCortexA53File())
            # Have we been asked to drive nTRST low on J67?
            if options.getScanJumper():
                setScanJumper(options.getScanDSTREAM())
        except RDDIException, eRDDI:
            showRDDIException(eRDDI)
        except DTSLException, eDTSL:
            showDTSLException(eDTSL)
        except DAPException, eDAP:
            showDAPException(eDAP)
        except ProgramException, eProgram:
            showProgramException(eProgram)
        except PyException, e:
            showJythonException(e)
        except RuntimeError, e:
            print >> sys.stderr, e
    else:
        print "Failed to process options"
