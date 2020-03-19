"""
Copyright (c) 2014-2019 Arm Limited (or its affiliates). All rights reserved.
Use, modification and redistribution of this file is subject to your possession of a
valid End User License Agreement for the Arm Product of which these examples are part of
and your compliance with all applicable terms and conditions of such licence agreement.
"""

from com.arm.debug.dtsl.components import DSTREAMHTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from time import sleep

"""
USECASE

$Title$ HSSTP Link Training
$Description$ Run this use case script with the "default" configuration to retrain the HSSTP probe link
$Run$ hsstp_usecase_main
$Help$
Run this use case script with the "default" configuration to retrain the HSSTP probe link
$Help$
"""

def configureTargetHSSTPLink(ahbMemAccess, apbMemAccess, dtslConfigScript):
    '''
    Target specific function to configure the target side HSSTP link
    This function will be run once per trace session
    '''
    # ATB_CLK
    ahbMemAccess.writeMem(0xD000A878, 0x15300D3)

    # SETM_TMX_CLK   TBG/2
    value = ahbMemAccess.readMem(0xD000A834)
    value |=   0x00000002 #clk/2
    value &= 0xFFFFFFDF #enable AES clock
    ahbMemAccess.writeMem(0xD000A834, value)

    portWidthInput = int(dtslConfigScript.getOptionValue("options.HSSTP_options.portWidth"))

    if portWidthInput == 32:
        apbMemAccess.writeMem(0x8000A000, 0x00012961)
    elif portWidthInput == 16:
        apbMemAccess.writeMem(0x8000A000, 0x0000A561)
    elif portWidthInput == 8:
        apbMemAccess.writeMem(0x8000A000, 0x00002161)

    # SETM phy--for address 0xE000A000-0xE000B034
    #   off then on
    apbMemAccess.writeMem(0x8000B004, 0x00000010)
    apbMemAccess.writeMem(0x8000B028 , 0x0000A280)

    #   Vpp = 640mVpp
    apbMemAccess.writeMem(0x8000B030, 0x0004080)

    #Power up the PLL and transmitters
    #PU_PLL(bit 15), PU_TX_A(bit 14), PU_TX_B(bit13), all high 0xE000A140
    ahbMemAccess.writeMem(0xE000A140, 0x0000E622)   #6Gb
    #ahbMemAccess.writeMem(0xE000A140, 0x0000E621)  #3Gb
    #ahbMemAccess.writeMem(0xE000A140, 0x0000E620)  #1.5Gb

    ahbMemAccess.writeMem(0xE000A144, 0x00000008)

    # XTAL freq 0xF010 for 25Mhz, 0xF020 for 30Mhz,0xf030 for 40MHZ
    XTALFreq = dtslConfigScript.getOptionValue("options.HSSTP_options.targetClocks.FrefInput")
    apbMemAccess.writeMem(0x8000B004, int(XTALFreq, 16))

    #Calibration routine...
    apbMemAccess.writeMem(0x8000B008, 0x8480)  #bit 15 starts the calibration cycle

    #wait for calibration complete...
    i=0
    while( i < 10):
        i += 1
        value = apbMemAccess.readMem(0x8000B008)
        if(value & 0x10 != 0):
            break
        sleep(0.1)

    # phy pattern
    apbMemAccess.writeMem(0x8000B01C, 0x00000000)

    #release the logic reset to start..
    if portWidthInput == 32:
        apbMemAccess.writeMem(0x8000A000, 0x000129F1)
    elif portWidthInput == 16:
        apbMemAccess.writeMem(0x8000A000, 0x0000A5F1)
    elif portWidthInput == 8:
        apbMemAccess.writeMem(0x8000A000, 0x000021F1)

def startTargetHSSTPTraining(apbMemAccess):
    '''
    Target specific function to start training sequence on HSSTP link
    Return boolean True if target link has started training successfully else return False
    This function will possibly be retried multiple times
    '''
    pllLocked = False
    ready=False

    #Check for PLL Lock
    i=0
    while(i < 10):
        i += 1
        value = apbMemAccess.readMem(0x8000B004 )
        if (value & 0x400):
            pllLocked = True
            break
        sleep(0.1)

    #Check for the READY flag
    i=0
    while(i<10):
        i += 1
        value = apbMemAccess.readMem(0x8000A004  )
        if (value & 0x4):
            ready=True
            break
        sleep(0.1)

    return (pllLocked and ready)

def resetSCLKDomain(apbMemAccess, dtslConfigScript):
    apOpen = False
    try:
        apbMemAccess.connect()
        apOpen = True
    except:
        # Failed to open AP, will already be open in this configuration
        pass

    try:
        portWidthInput = int(dtslConfigScript.getOptionValue("options.HSSTP_options.portWidth"))

        if portWidthInput == 32:
            apbMemAccess.writeMem(0x8000A000, 0x00012961)
            apbMemAccess.writeMem(0x8000A000, 0x000129F1)
        elif portWidthInput == 16:
            apbMemAccess.writeMem(0x8000A000, 0x0000A561)
            apbMemAccess.writeMem(0x8000A000, 0x0000A5F1)
        elif portWidthInput == 8:
            apbMemAccess.writeMem(0x8000A000, 0x00002161)
            apbMemAccess.writeMem(0x8000A000, 0x000021F1)
    finally:
        if apOpen:
            apbMemAccess.disconnect()


def configureLink(dstream, output=False, linkCount=10, probeCount=4):
    ahbOpen = False
    apbOpen = False
    ahbMemAccess = dstream.ahb
    apbMemAccess = dstream.apb
    probeRetries = probeCount
    targetRetries = linkCount
    try:
        ahbMemAccess.connect()
        ahbOpen = True
    except:
        # Failed to open AHB, will already be open in this configuration
        pass
    try:
        apbMemAccess.connect()
        apbOpen = True
    except:
        # Failed to open APB, will already be open in this configuration
        pass

    try:
        # Run target specific HSSTP configuration function
        configureTargetHSSTPLink(ahbMemAccess, apbMemAccess, dstream.dtslConfigScript)
        targetLinkUp = False
        probeLinkUp = False
        while (not(targetLinkUp) or not(probeLinkUp)) and linkCount > 0:
            # Run target specific HSSTP link training function
            targetLinkUp = startTargetHSSTPTraining(apbMemAccess)
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
        # Close connection to APs if we opened here
        if ahbOpen:
            ahbMemAccess.disconnect()
        if apbOpen:
            apbMemAccess.disconnect()

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
