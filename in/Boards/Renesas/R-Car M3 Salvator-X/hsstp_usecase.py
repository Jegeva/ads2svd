"""
Copyright (c) 2018-2019 Arm Limited (or its affiliates). All rights reserved.
Use, modification and redistribution of this file is subject to your possession of a
valid End User License Agreement for the Arm Product of which these examples are part of
and your compliance with all applicable terms and conditions of such licence agreement.
"""

from com.arm.debug.dtsl.components import DSTREAMHTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture

"""
USECASE

$Title$ HSSTP Link Training
$Description$ Run this use case script with the "default" configuration to retrain the HSSTP probe link
$Run$ hsstp_usecase_main
$Help$
Run this use case script with the "default" configuration to retrain the HSSTP probe link
$Help$
"""

def configureTargetHSSTPLink(memAccessDevice):
    '''
    Target specific function to configure the HSSTP link(e.g. clock speeds etc)
    '''
    '''
    [Procedure No.0]
    Unlock the Lock access Register
    '''
    memAccessDevice.writeMem(0xEA100FB0, 0xC5ACCE55)

    for RetryCount in range(100):
        status = memAccessDevice.readMem(0xEA100FB4)
        if (status == 0x00000001):
            break
    if (status != 0x00000001):
        return False


    '''
    [Procedure No.0.5]
    trace problem work around
    '''
    memAccessDevice.writeMem(0xEA0F0FB0, 0xC5ACCE55)
    memAccessDevice.writeMem(0xEA0F0100, 0x00000200)
    memAccessDevice.writeMem(0xEA0F0100, 0x00000201)

    # PCIE physical unit Initialization.
    '''
    [Procedure No.1]
    DBE setting for PCIE physical unit selection.
     DBGREG9 (KEY Register)
     Address : 0xE6100040
      Write 0x0000A500 to DBGREG9
      (1st step to allow the access to DBGREG1)
      Write 0x0000A501 to DBGREG9
      (2nd step to allow the access to DBGREG1)
     DBGREG1 (Debug Function Selection Register)
     Address : 0xE6100020
      Write 0b10 to Bit[11:10]
      (for using PCIE1 physical unit)
    '''
    memAccessDevice.writeMem(0xE6100040, 0x0000A500)
    memAccessDevice.writeMem(0xE6100040, 0x0000A501)

    value = memAccessDevice.readMem(0xE6100020)
    valueNew = value | 0x00000800
    memAccessDevice.writeMem(0xE6100020, valueNew)

    # Coresight Trace Setting
    '''
    Transmission setting of the TPIU
     It is possible when procedure before No.8 "STP_PWRUP assert" or
     procedure after No.13 "STP_EN assert" because clock is supplied to all TPIU.
     If it is set before No.8, TPIU output will start after assertion of STP_EN.
     If it is set after No.14, TPIU output will start immediately.
    '''


    '''
    Target specific function to start training sequence on HSSTP link
    Return boolean True if target link has started training successfully else return False
    This function will possibly be retried multiple times
    '''
    '''
    [Procedure No.2]
    Release MSTP on PCIE1 physical unit
     RMSTPCR3 Address : 0xE615011C
      Prepare Write Value for the following steps:
      1. Read RMSTPCR3. We call the value (A).
      2. Clear Bit[18] of (A). We call the value (B).
      3. Inverse all bits of (B). We call the value (C).
     CPGWPR Address : 0xE6150900
      Write (C) to CPGWPR
     RMSTPCR3 Address : 0xE615011C
      Write (B) to SMSTPCR3
     MSTPCR3 Address : 0xE6150048
      Poll Bit[18] until 0 (for confirming MSTP release)
    '''
    valueA = memAccessDevice.readMem(0xE615011C)
    valueB = valueA & 0xFFFBFFFF
    valueC = ~valueB
    memAccessDevice.writeMem(0xE6150900, valueC)
    memAccessDevice.writeMem(0xE615011C, valueB)
    for RetryCount in range(100):
        value = memAccessDevice.readMem(0xE6150048)
        status = value & 0x00040000
        if (status == 0):
            break
    if (status != 0):
        return False

    '''
    [Procedure No.3]
    PCIE1 Link setting
     PCIE1 PHY PCIEPHYSR Address : 0xEE8007F0
      Poll PCIEPHYSR until 0x00010001
      Bit[16] indicates that PCIE physical unit is ready to use.
      Bit[0] indicates that the clock from PCIE physical unit to Aurora LINK is locked.
    '''
    for RetryCount in range(100):
        status = memAccessDevice.readMem(0xEE8007F0)
        if (status == 0x00010001):
            break
    if (status != 0x00010001):
        return False

    # De-Emphasis
    # Address : 0xE65DC02C (AXI_0)
    # bit[5] = 1
    #  0x0020
    # below section only for R-Car M3

    value = memAccessDevice.readMem(0xE65DC02C)
    mask = 0xFFFFFFDF
    valueMasked = value & mask
    valueNew = valueMasked | 0x00000020
    memAccessDevice.writeMem(0xE65DC02C, valueNew)
    valueVerify = memAccessDevice.readMem(0xE65DC02C)

    # VBOOST
    # Address : 0xE65DC010 (AXI_0)
    # default value : 0x0400
    #  0x0700 : max boost
    #  0x0000 : min boost
    value = memAccessDevice.readMem(0xE65DC010)
    mask = 0xFFFFF0FF
    valueMasked = value & mask
    valueNew = valueMasked | 0x00000700
    memAccessDevice.writeMem(0xE65DC010, valueNew)

    #mesg = ("VBOOST newValue = 0x%x", valueNew)

    '''
    [Procedure No.4]
    PCIE1 physical unit setting
     * If the clock frequency of Aurora link does not have to be changed from 125MHz, this item is not necessary.
     PCIE1 PHY OVERRIDE Address : 0xE65DC02C
      Write 1 to Bit[1]
      (Later change to PCIE1 physical unit register is valid.)
     PCIE1 PHY PIPEINTFACE Address : 0xE65DC014
      Write 1 to Bit[8]
      (The clock frequency is changed from 125MHz (2.5Gbps) to 250MHz (5Gbps))
     Control Output Characteristics
      Write 1 to Bit[5]
    '''
    value = memAccessDevice.readMem(0xE65DC02C)
    valueNew = value | 0x00000002
    memAccessDevice.writeMem(0xE65DC02C, valueNew)

    value = memAccessDevice.readMem(0xE65DC014)
    valueNew = value | 0x00000100
    memAccessDevice.writeMem(0xE65DC014, valueNew)

    value = memAccessDevice.readMem(0xEA10054C)
    valueNew = 0x00000020
    memAccessDevice.writeMem(0xEA10054C, value | valueNew)

    '''
    [Procedure No.5]
    PHYENABLE assert (software setting)
     APCR offset : 0x630 (CPU View Address : 0xEA100630 / Debugger View Address : 0x80100630)
      Write 1 to Bit[3]
    '''
    value = memAccessDevice.readMem(0xEA100630)
    valueNew = value | 0x00000008
    memAccessDevice.writeMem(0xEA100630, valueNew)

    '''
    [Procedure No.6]
    Poll COSPLLLOCK
     APSR offset : 0x638 (CPU View Address : 0xEA100638 / Debugger View Address : 0x80100638)
      Poll [0] until 1 (PLL Lock Detection)
    '''
    for RetryCount in range(100):
        mask = 1
        status = memAccessDevice.readMem(0xEA100638) & mask
        if (status == 1):
            break
    if (status != 1):
        return False

    return True

def startTargetHSSTPTraining(memAccessDevice):

    # HSSTP Initialization

    #Force STP reset via the STP Control Register
    memAccessDevice.writeMem(0xEA100504, 0)


    '''
    [Step 7]
    STP_PWRUP assert
     STPCR offset : 0x504 (CPU View Address : 0xEA100504 / Debugger View Address : 0x80100504)
      Set 1 to Bit [0]
    '''
    value = memAccessDevice.readMem(0xEA100504)
    valueNew = 1
    memAccessDevice.writeMem(0xEA100504, value | valueNew)

    '''
    [Step 8]
    Register initial setting
     Update the settings upon necessity.
     PCSR offset : 0x50C (CPU View Address : 0xEA10050C / Debugger View Address : 0x8010050C)
      Bit [15:0] is clock compensation (CC) generation interval.
      Initial value : 0x2710
      (CC is inserted each 0x2710*2 Byte data out)
     LLIR offset : 0x510 (CPU View Address : 0xEA100510 / Debugger View Address : 0x80100510)
      Bit [30:22] is VERIFY_LEN
      Bit [12:0] is ALIGN_LEN
      Initial value : 0x1FC01368
      (VERIFY_LEN: 0x07F, ALIGN_LEN: 0x1368)
     LLIR2 *4 offset : 0x51C (CPU View Address : 0xEA10051C / Debugger View Address : 0x8010051C)
      Bit [15:12] is VERIFY_MUL
      Bit [7:4] is ALIGN_MUL
      Initial value : 0x00000001
      (VERIFY_MUL: 0x0, ALIGN_MUL: 0x0)
     TSSR offset : 0x5C0 (CPU View Address : 0xEA1005C0 / Debugger View Address : 0x801005C0)
      Bit [3:0] is Trace Source Select
      Initial value : 0x1
      (Trace Source is CR7SS)
        0x0 : CSDBGSS TPIU is selected
        0x1 : CR7SS TPIU is selected
        0x2 : CA53SS TPIU is selected
        0x3 : CA57SS TPIU is selected
        Other : Reserved for future use
     PCSR2 offset : 0x540 (CPU View Address : 0xEA100540 / Debugger View Address : 0x80100540)
      Bit [21:16] is the output period of the CC.
      Initial value : 0x1A06
     TXFLR offset : 0x544 (CPU View Address : 0xEA100544 / Debugger View Address : 0x80100544)
      Bit [15:0] is frame size
      Initial value : 0xFFFF(65535cycle*Byte / frame)
    '''
    # Select Trace Source to CSD
    value = memAccessDevice.readMem(0xEA1005C0)
    mask = 0xFFFFFFF0
    value = value & mask
    memAccessDevice.writeMem(0xEA1005C0, value )

    # Set alignment pattern multiplier
    # LLIR2.ALIGN_MUL = 7 (Alignment Pattern Multiplier = 128).  ALIGN_MUL occupies bits[7:4] of register LLIDR2.
    value = memAccessDevice.readMem(0xEA10051C)
    valueNew = 0x00000070
    memAccessDevice.writeMem(0xEA10051C, value | valueNew)


    '''
    [Step 9]
    STP_nRST negate
     STPCR offset : 0x504 (CPU View Address : 0xEA100504 / Debugger View Address : 0x80100504)
      Write 1 to Bit [2]
      * Please don't control both STP_PWRUP and STP_nRST at the same time.
    '''
    value = memAccessDevice.readMem(0xEA100504)
    valueNew = 0x00000004
    memAccessDevice.writeMem(0xEA100504, value | valueNew)

    '''
    [Step 10]
    Poll LANE_UP
     STPSR offset : 0x500 (CPU View Address : 0xEA100500 / Debugger View Address : 0x80100500)
      Poll [0] until 1 (LANE_UP[0])
    '''
    for RetryCount in range(100):
        mask = 0x00000001
        status = memAccessDevice.readMem(0xEA100500) & mask
        if (status == 0x00000001):
            break
    if (status != 0x00000001):
        return False



    '''
    [Step 11]
    Poll CHANNEL_UP
     STPSR offset : 0x500 (CPU View Address : 0xEA100500 / Debugger View Address : 0x80100500)
      Poll [6] until 1 (CHANNEL_UP[0])
    '''
    for RetryCount in range(100):
        status = memAccessDevice.readMem(0xEA100500) & 0x00000040
        if (status == 0x00000040):
            break
    if (status != 0x00000040):
        return False


    # Trace Transmission Setting
    '''
    [Step 12]
    STP_nSWRST negate
     STPCR offset : 0x504 (CPU View Address : 0xEA100504 / Debugger View Address : 0x80100504)
      Write 1 to Bit [3]
    '''
    value = memAccessDevice.readMem(0xEA100504)
    valueNew = 0x00000008
    memAccessDevice.writeMem(0xEA100504, value | valueNew)


    '''
    [Step 13]
    STP_EN assert
     STPCR offset : 0x504 (CPU View Address : 0xEA100504 / Debugger View Address : 0x80100504)
      Write 1 to Bit [1]
    '''
    value = memAccessDevice.readMem(0xEA100504) & 0xFFFFFFFD

    memAccessDevice.writeMem(0xEA100504, value)

    memAccessDevice.writeMem(0xEA100504, value | 0x00000002)

    # All is well - the target link is up
    return True


def configureLink(dstream, output=False, linkCount=10, probeCount=4):
    dapOpen = False
    memAccessDevice = dstream.memAccessDevice
    probeRetries = probeCount
    targetRetries = linkCount
    try:
        memAccessDevice.connect()
        dapOpen = True
    except:
        # Failed to open DAP, will already be open in this configuration
        pass
    try:
        # Run target specific HSSTP configuration function
        configureTargetHSSTPLink(memAccessDevice)
        targetLinkUp = False
        probeLinkUp = False
        while (not(targetLinkUp) or not(probeLinkUp)) and linkCount > 0:
            # Run target specific HSSTP link training function
            targetLinkUp = startTargetHSSTPTraining(memAccessDevice)
            while targetLinkUp and not(probeLinkUp) and probeCount > 0:
                probeLinkUp = dstream.isProbeLinkUp()
                probeCount -= 1
            linkCount -= 1
        if output:
            if probeLinkUp:
                print("Probe link successfully trained")
            else:
                if not targetLinkUp:
                    print("Target link still down after %d retries" % (targetRetries))
                else:
                    print("Probe link still down after %d retries" % (probeRetries*targetRetries))
    finally:
        # Close connection to DAP if we opened it here
        if dapOpen:
            memAccessDevice.disconnect()

def getDTSLConnection():
    from arm_ds.debugger_v1 import Debugger
    from com.arm.debug.dtsl import ConnectionManager
    # Get the debugger connection
    debugger = Debugger()
    # Get the DTSL configuration
    dtslConnectionConfigurationKey = debugger.getConnectionConfigurationKey()
    dtslConnection = ConnectionManager.openConnection(
        dtslConnectionConfigurationKey)
    dtslCfg = dtslConnection.getConfiguration()
    return dtslCfg

def getHSSTP():
    dtsl = getDTSLConnection()
    traceCaptures = dict(dtsl.getTraceCaptureInterfaces())
    traceCaptures.update(dict(dtsl.getStreamTraceCaptureInterfaces()))
    if 'DSTREAM' in traceCaptures:
        hsstp = traceCaptures['DSTREAM']
        return hsstp
    return None

def dstreamHT_main(dstreamHT):
    configureLink(dstreamHT, output=True)

def dstreamHSSTP_main(dstreamHSSTP):
    traceOpen = False
    try:
        dstreamHSSTP.trace = dstreamHSSTP.configuration.getTrace();
        dstreamHSSTP.traceConn = dstreamHSSTP.trace.connect();
        traceOpen = True
        configureLink(dstreamHSSTP, output=True)
    finally:
        if traceOpen:
            dstreamHSSTP.trace.disconnect(dstreamHSSTP.traceConn)
            dstreamHSSTP.traceConn = None

def hsstp_usecase_main(options):
    # Import the packages for usecase scripts
    from arm_ds.usecase_script import UseCaseScript, UseCaseError
    hsstp = getHSSTP()
    if not hsstp:
        raise UseCaseError("HSSTP trace capture interface cannot be found for this connection")
    print("Attempting to configure HSSTP link...")
    # If connected via DSTREAM-HT
    if isinstance(hsstp, DSTREAMHTStoreAndForwardTraceCapture):
        dstreamHT_main(hsstp)
    # If connected via DSTREAM-HSSTP probe
    elif isinstance(hsstp, DSTREAMTraceCapture):
        dstreamHSSTP_main(hsstp)
    else:
        raise UseCaseError("The DSTREAM found for this connection does not support HSSTP link training")
    print("Configuration complete")
