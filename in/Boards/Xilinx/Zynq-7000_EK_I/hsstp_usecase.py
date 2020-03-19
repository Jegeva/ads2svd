"""
Copyright (c) 2016-2019 Arm Limited (or its affiliates). All rights reserved.
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
    return

def startTargetHSSTPTraining(memAccessDevice):
    '''
    Target specific function to start training sequence on HSSTP link
    Return boolean True if target link has started training successfully else return False
    This function will possibly be retried multiple times
    '''
    memAccessDevice.writeMem(0x41210000, 0x7)
    memAccessDevice.writeMem(0x41210000, 0xF)
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
