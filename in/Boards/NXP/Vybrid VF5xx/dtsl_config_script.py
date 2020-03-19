# Copyright (C) 2013-2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl.components import MemoryRouter
from com.arm.debug.dtsl.components import DapMemoryAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import GenericTraceDevice
from com.arm.debug.dtsl import DTSLException
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE
from jtagap import JTAGAP
import jtag

from java.lang import StringBuilder
from struct import pack, unpack
from jarray import array, zeros

NUM_CORES_CORTEX_A5 = 1
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
CYCLE_ACCURATE_DESCRIPTION = '''Enable cycle accurate trace'''
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
ITMA5_ATB_ID = 1
ATB_ID_BASE = 3
CORTEX_A5_TRACE_OPTIONS = 0

CTICTRL  =  0x000
CTIINTACK = 0x004
CTIINEN  =  0x008
CTIOUTEN =  0x028

TRIG_STOP  = 0
TRIG_START = 7

class SWO(GenericTraceDevice):
    def postConnect(self):
        GenericTraceDevice.postConnect(self)

        ITATBCTR0 = 0x03C0 # Integration Test ATB Control Register 0
        ITATBCTR2 = 0x03BC # Integration Test ATB Control Register 2
        self.writeRegister(ITATBCTR0, 0x00000001)
        self.writeRegister(ITATBCTR2, 0x00000001)

class TraceRangeOptions:
    def __init__(self, coreTraceName = None, dtsl = None):
        if coreTraceName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("%s.traceRange" % coreTraceName)
            self.traceRangeStart = dtsl.getOptionValue("%s.traceRange.start" % coreTraceName)
            self.traceRangeEnd = dtsl.getOptionValue("%s.traceRange.end" % coreTraceName)
            self.traceRangeIDs = None

    def defaultSetup(self):
        self.traceRangeEnable = False
        self.traceRangeStart = None
        self.traceRangeEnd = None
        self.traceRangeIDs = None


class DtslScript_DSTREAM(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")], isDynamic=False),
                    ]),
                ]),
                DTSLv1.tabPage("cortexA5", "Cortex-A5", childOptions=[
                    DTSLv1.booleanOption('cortexA5coreTrace', 'Cortex-A5 trace', defaultValue=False,
                        description="Enable trace from the Cortex-A5 module",
                        childOptions =
                            [ DtslScript_DSTREAM.getTraceCaptureOption() ] +
                            ETMv3_5TraceSource.defaultOptions(DtslScript_DSTREAM.getA5ETM) +
                            [
                            DtslScript_DSTREAM.getContextIdsOption(),
                            ETMv3_5TraceSource.dataOption(DtslScript_DSTREAM.getA5ETM),
                            DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable ETM triggers to halt execution", defaultValue=False),
                            DtslScript_DSTREAM.getTraceRangeOption(),
                            DtslScript_DSTREAM.getItmOption()
                            ]
                        ),
                ]),
                DtslScript_DSTREAM.getSjcTabPage()
            ])
        ]

    @staticmethod
    def getTraceCaptureOption():
        return DTSLv1.enumOption('A5traceCapture', 'Trace capture method', defaultValue="none",
            values = [("none", "None"), ("ETB_A5", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
            setter=DtslScript_DSTREAM.setA5TraceCaptureMethod)

    @staticmethod
    def getContextIdsOption():
        return DTSLv1.booleanOption('contextIDs', "ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
            childOptions = [
                DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                    values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
        ])

    @staticmethod
    def getTraceRangeOption():
        # Trace range selection (e.g. for linux kernel)
        return DTSLv1.booleanOption('traceRange', 'Trace capture range',
            description=TRACE_RANGE_DESCRIPTION,
            defaultValue = False,
            childOptions = [
                DTSLv1.integerOption('start', 'Start address',
                    description='Start address for trace capture',
                    defaultValue=0,
                    display=IIntegerOption.DisplayFormat.HEX),
                DTSLv1.integerOption('end', 'End address',
                    description='End address for trace capture',
                    defaultValue=0xFFFFFFFF,
                    display=IIntegerOption.DisplayFormat.HEX)
        ])

    @staticmethod
    def getItmOption():
        return DTSLv1.booleanOption('itm', 'ITM trace', defaultValue=False,
           description="Enable trace from the ITM",
           setter=DtslScript_DSTREAM.setITMEnabledA5)

    @staticmethod
    def getSjcTabPage():
        return DTSLv1.tabPage("sjc", "Secure Debug", childOptions=[
            DTSLv1.booleanOption('sjcUnlock', 'Configure the SJC',
                defaultValue = False,
                setter=DtslScript_DSTREAM.setUnlockSJC,
                childOptions = [
                    DTSLv1.integerOption('key', 'SJC key',
                        description='56-bit SJC unlock code',
                        defaultValue=0x123456789ABCDE,
                        display=IIntegerOption.DisplayFormat.HEX)
                    ]
                )
        ])

    def setUnlockSJC(self, required):
        self.sjcUnlockReqd = required


    def __init__(self, root):
        DTSLv1.__init__(self, root)
        self.ctiConfigDone = False

        self.enableA5TraceClock = False
        self.enableA5TPIUPinmux = False

        self.sjcUnlockReqd = False

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # only DAP device is managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.dap)

        self.exposeCores()

        self.setupETBTrace()

        self.setupDSTREAMTrace()

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-A5 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    # ACK all the stop triggers on the CTIs so that all cores can start
    # If we haven't yet configured the CTIs and cores for sync execution, do so now
    def clearTriggers(self):
        if not self.ctiConfigDone:
            if self.cortexA5cores[0].isConnected():
                self.getDebug().setConfig(8, "CTI_SYNCH_START", "1")

        self.ctiConfigDone = True

    def enableClocks(self):
        script = """from LDDI import *
import sys

A5_ID = 8
A5_OFFSET = 0xC0088000
A5_AP = 1

RVM_PROCBRK_INFO = 0
RVM_PROCBRK_ENA = 1
RVM_PROCBRK_DIS = 2
ResetVecEncoding = [0x54455352]  # 'RSET' in ASCII

POST_RST_STATE_RUN = 0
POST_RST_STATE_STOP = 1

targetConfigured = False

def HandleOpenConn(DevID,type,state):
    if type==1:
        configureTarget()
    return handleOpenConn(DevID,type,state)


def isCoreConnected(id):
    err, configTest = getConfig(id,'CONFIG_ITEMS')
    return err == 0

def dapPowerCheckBase(dapdev):
    # check DAP power status
    err, powerState = getConfig(dapdev, 'DAP_POWER_UP')
    if err == 0 and powerState != 1:
        # not powered - try to power up
        for t in range(10):
            # the DAP_POWER_UP state is reference counted, so try get it in sync with reality
            err = setConfig(dapdev, 'DAP_POWER_UP', 0)
            # power up the DAP
            err = setConfig(dapdev, 'DAP_POWER_UP', 1)
            # read status
            err, powerState = getConfig(dapdev, 'DAP_POWER_UP')
            if powerState == 1:
                break
            if t < 9:
                print 'Failed to power up DAP: Retrying'
            else:
                print 'Failed to power up DAP'
                err = 9 # EMUERR_TARGSTATE
    return err

def configureTarget(force=False):
    global targetConfigured
    if targetConfigured and not force:
        # already setup
        return 0

    err, id, version, message = Debug_OpenConn(1)
    if err == 0x101: # already open
        dapOpened = False
    elif err != 0:
        print >> sys.stderr, "Failed to open DAP: %04x" % err
        return err
    else:
        dapOpened = True
    err = dapPowerCheckBase(1)
    if err != 0:
        print >> sys.stderr, "Failed to powerup DAP: %04x" % err
        if dapOpened:
            Debug_CloseConn(1)
        return err
"""
        if self.enableA5TraceClock:
            script = script + """
    value = [ 0, 0, 0, 0 ]
    err = Debug_MemRead(1, 0x4300, 0x4006B01C, 4, 0x320, 4, value)
    if err == 0:
        value[3] |= 0x04
        Debug_MemWrite(1,0x4300,0x4006B01C,4,0x0320,0,value)
"""
        if self.enableA5TPIUPinmux:
            script = script + """
    for address in range(0x40048014, 0x40048058, 4):
        Debug_MemWrite(1,0x4300,address,4,0x0320,0,[0xC2, 0x31, 0x10, 0x00])
    Debug_MemWrite(1,0x4300,0x40048058,4,0x0320,0,[0xC2, 0x31, 0x30, 0x00])
"""

        script = script + """
    if dapOpened:
        Debug_CloseConn(1)
    targetConfigured = True
    return 0

def UnknownStateRecovery():
    configureTarget(force=True)

def HandleExeReset(flags):
    A5SavedBrkPointInfo = [ '0' ]
    # Handle stop for A5
    if isCoreConnected(A5_ID):
        Err, postRstState = getConfig(A5_ID, 'POST_RESET_STATE')
        if postRstState == POST_RST_STATE_STOP:
            Err, A5SavedBrkPointInfo = Debug_BrkProcessor(A5_ID, RVM_PROCBRK_INFO, ResetVecEncoding)
            Err = Debug_BrkProcessor(A5_ID, RVM_PROCBRK_ENA, ResetVecEncoding)
        handleExeGo(A5_ID)

    err, id, version, message = Debug_OpenConn(1)
    # Write the reset
    Debug_MemWrite(1,0x4300,0x4006e000,4,0x0320,0,[ 0x0A, 0x15, 0, 0 ])
    if err == 0:
        Debug_CloseConn(1)

    configureTarget(force=True)

    if A5SavedBrkPointInfo[0] == '-':
        Debug_BrkProcessor(A5_ID, RVM_PROCBRK_DIS, ResetVecEncoding)
    return False
"""
        self.getDebug().setConfig(0, "PythonScript", script)


    def connectManagedDevices(self):
        self.enableClocks()

        # Unlock debug if required
        # For this we need an open DAP connection
        if self.sjcUnlockReqd:
            dapOpen = False

            try:
                self.dap.openConn(zeros(1, 'i'), zeros(1, 'i'), StringBuilder(1024))
                dapOpen = True
            except:
                pass

            try:
                self.unlockSJC()
            finally:
                if dapOpen:
                    self.dap.closeConn()

        DTSLv1.connectManagedDevices(self)


    def unlockSJC(self):
        # Create JTAG-AP handler
        jtagAP = JTAGAP(self.dap, 2)

        jtagAP.setPort(0)
        jtagAP.tapReset(jtag.JTAGS_RTI)

        # Scan out challenge value
        SJC_CHALLENGE = [ 0x0C ]
        challenge = [ 0 ] * 8
        jtagAP.scanIO(jtag.JTAGS_IR, 5, SJC_CHALLENGE, None, jtag.JTAGS_PIR, 1)
        jtagAP.scanIO(jtag.JTAGS_DR, 63, None, challenge, jtag.JTAGS_RTI, 1)
        #print 'SJC challenge', challenge

        # Get response value from options
        response = []
        keySJC = self.getOptionValue("options.sjc.sjcUnlock.key")
        for i in range(7):
            x = keySJC & 0xFF
            response.append(x)
            keySJC = keySJC >> 8
        #print 'SJC response', response

        # Scan in response value
        SJC_RESPONSE = [ 0x0D ]
        jtagAP.scanIO(jtag.JTAGS_IR, 5, SJC_RESPONSE, None, jtag.JTAGS_PIR, 1)
        jtagAP.scanIO(jtag.JTAGS_DR, 56, response, None, jtag.JTAGS_RTI, 1)

        # read MDM AP STATUS Register - expect Debug Enabled and Secure DEbug bits to be set
        # check MDM-AP status
        mdmStat = self.dap.readAPRegister(4, 0)
        #print 'MDM status %08x' % mdmStat
        if (mdmStat & 0x08) != 0x08:
            challStr = '0x' + ''.join([ '%02x' % i for i in reversed(challenge) ])
            raise DTSLException("""Secure debug is not enabled.
Please reconfigure connection with correct response for challenge %s and reset target before reconnecting
MDM-AP status = 0x%08X""" % (challStr, mdmStat))



    def discoverDevices(self):
        '''find and create devices'''

        dapDev = self.findDevice("ARMCS-DP")
        self.dap = CSDAP(self, dapDev, "DAP")

        cortexA5coreDev = 0
        self.cortexA5cores = []

        streamID = ATB_ID_BASE

        coreCTIDev = 1
        self.CTIs  = []
        self.cortexA5ctiMap = {} # map cores to associated CTIs

        etmDev = 1
        self.ETMs  = []

        for i in range(0, NUM_CORES_CORTEX_A5):
            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)

            # create core
            cortexA5coreDev = self.findDevice("Cortex-A5", cortexA5coreDev+1)
            dev = Device(self, cortexA5coreDev, "Cortex-A5_%d" % i)
            self.cortexA5cores.append(dev)
            self.cortexA5ctiMap[dev] = coreCTI

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev+1)
            etm = ETMv3_5TraceSource(self, etmDev, streamID, "ETM_A5_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)

        # ETB
        etbDevA5 = self.findDevice("CSETB")
        self.ETBA5 = ETBTraceCapture(self, etbDevA5, "ETB_A5")

        # DSTREAM
        self.createDSTREAM()

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

        # Funnel 0
        # This is the master funnel that serves the TPIU
        funnelDevMaster = self.findDevice("CSTFunnel")
        self.funnelMaster = self.createFunnel(funnelDevMaster, "Funnel_0")

        # Funnel 1
        # A5 funnel
        funnelDevA5 = self.findDevice("CSTFunnel", funnelDevMaster+1)
        self.funnelA5 = self.createFunnel(funnelDevA5, "Funnel_1")

        # ITM
        itmDevA5 = self.findDevice("CSITM")
        self.ITMA5 = self.createITM(itmDevA5, ITMA5_ATB_ID, "ITM_A5")

        # SWO
        swoDev = self.findDevice("CSSWO")
        self.swo = SWO(self, swoDev, "SWO")


    def exposeCores(self):
        for core in self.cortexA5cores:
            self.addDeviceInterface(self.createDAPWrapper(core))

    def setupETBTrace(self):
        '''Setup ETB trace capture'''

        # use continuous mode
        self.ETBA5.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETB and register ETB with configuration
        self.ETBA5.setTraceComponentOrder([ self.funnelMaster, self.funnelA5 ])
        self.addTraceCaptureInterface(self.ETBA5)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETB_A5", [ self.funnelA5, self.funnelMaster, self.tpiu, self.ETBA5 ])

        # register trace sources
        self.registerA5TraceSources(self.ETBA5)

    def setupDSTREAMTrace(self):
        '''Setup DSTREAM trace capture'''
        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)

        # configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.funnelA5, self.funnelMaster, self.tpiu  ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.funnelA5, self.funnelMaster, self.tpiu, self.swo, self.DSTREAM ])

        # register trace sources
        self.registerA5TraceSources(self.DSTREAM)

    def setPortWidth(self, portWidth):
        self.tpiu.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == self.ETBA5:
            # ETB trigger input is CTI out 1
            return (self.outCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)
        if sink == self.DSTREAM:
            # TPIU trigger input is CTI out 3
            return (self.outCTI, 3, CTM_CHANNEL_TRACE_TRIGGER)
        # no associated CTI
        return (None, None, None)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a source
        return (None, None, None) if no associated CTI
        '''
        if source in self.ETMs:
            coreNum = self.ETMs.index(source)
            # ETM trigger is on input 6
            if coreNum < len(self.CTIs):
                return (self.CTIs[coreNum], 6, CTM_CHANNEL_TRACE_TRIGGER)

        # no associated CTI
        return (None, None, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # disable the TPIU by default to allow ETB to work at full rate
        tpiu.setEnabled(False)
        return tpiu

    def setETBTraceEnabled(self, source, enabled):
        '''Enable/disable ETB trace capture'''
        source.setEnabled(enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.tpiu.setEnabled(enabled)

    def registerA5TraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A5):
            self.registerCoreTraceSource(traceCapture, self.cortexA5cores[c], self.ETMs[c])
        self.registerTraceSource(traceCapture, self.ITMA5)

    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

        # CTI (if present) is also managed by the configuration
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.addManagedTraceDevices(traceCapture.getName(), [ cti ])

    def EnableInvasive(self, enabled):
        for core in self.cortexA5cores:
            core.enableInvasive(enabled)

    def EnableXTrig(self, enabled):
        for core in self.cortexA5cores:
            core.enableXTrig(enabled)

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

    def setTimestampingEnabled(self, xtm, state):
        xtm.setTimestampingEnabled(state)

    def setContextIDEnabled(self, xtm, state, size):
        if state == False:
            xtm.setContextIDs(False, IARMCoreTraceSource.ContextIDSize.NONE)
        else:
            contextIDSizeMap = {
                 "8":IARMCoreTraceSource.ContextIDSize.BITS_7_0,
                "16":IARMCoreTraceSource.ContextIDSize.BITS_15_0,
                "32":IARMCoreTraceSource.ContextIDSize.BITS_31_0 }
            xtm.setContextIDs(True, contextIDSizeMap[size])

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()
        traceMode = optionValues.get("options.cortexA5.cortexA5coreTrace.A5traceCapture")
        self.setManagedDevices(self.getManagedDevices(traceMode))

        coreTraceEnabled = self.getOptionValue("options.cortexA5.cortexA5coreTrace")
        A5traceMode = self.getOptionValue("options.cortexA5.cortexA5coreTrace.A5traceCapture")
        for i in range(0, NUM_CORES_CORTEX_A5):
            etm = self.ETMs[i]
            self.setTraceSourceEnabled(etm, coreTraceEnabled)
            self.enableMasterFunnelPort(A5traceMode == 'DSTREAM')

            self.setTriggerGeneratesDBGRQ(self.ETMs[i], self.getOptionValue("options.cortexA5.cortexA5coreTrace.triggerhalt"))
            self.setContextIDEnabled(self.ETMs[i],
                                     self.getOptionValue("options.cortexA5.cortexA5coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexA5.cortexA5coreTrace.contextIDs.contextIDsSize"))

        etmStartIndex = 0
        etmEndIndex = 0

        etmEndIndex += NUM_CORES_CORTEX_A5
        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A5_TRACE_OPTIONS], TraceRangeOptions("options.cortexA5.cortexA5coreTrace", self), self.ETMs[etmStartIndex:etmEndIndex])
        etmStartIndex += NUM_CORES_CORTEX_A5

        portWidthOpt = self.getOptions().getOption("options.trace.offChip.tpiuPortWidth")
        if portWidthOpt:
            portWidth = self.getOptionValue("options.trace.offChip.tpiuPortWidth")
            self.setPortWidth(int(portWidth))

        traceBufferOpt = self.getOptions().getOption("options.trace.offChip.traceBufferSize")
        if traceBufferOpt:
            traceBufferSize = self.getOptionValue("options.trace.offChip.traceBufferSize")
            self.setTraceBufferSize(traceBufferSize)

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def setA5TraceCaptureMethod(self, method):
        if method == "none":
            self.enableA5TraceClock = False
            self.enableA5TPIUPinmux = False
#            self.setETBTraceEnabled(self.ETM_A5, False)
            self.setDSTREAMTraceEnabled(self.enableA5TPIUPinmux)
        elif method == "ETB_A5":
            self.enableA5TraceClock = True
            self.enableA5TPIUPinmux = False
#            self.setETBTraceEnabled(self.ETM_A5, True)
            self.setDSTREAMTraceEnabled(self.enableA5TPIUPinmux)
        elif method == "DSTREAM":
            self.enableA5TraceClock = True
            self.enableA5TPIUPinmux = True
#            self.setETBTraceEnabled(self.ETM_A5, False)
            self.setDSTREAMTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def getA5ETM(self):
        return self.ETMs[0]

    def setITMEnabledA5(self, enabled):
        '''Enable/disable the ITM trace source'''
        self.ITMA5.setEnabled(enabled)
        if (enabled == True):
            self.funnelA5.setPortEnabled(1)
        else:
            self.funnelA5.setPortDisabled(1)

    def checkSecondaryCoreClock(self, connectingTo):
        if not self.secondaryCoreClockChecked:
            if not self.confirmValue(0, 0x4006B08C, [0x00010000], [0x00010000]):
                raise DTSLException, "Secondary core clock must be enabled before connecting to %s" % connectingTo
            self.secondaryCoreClockChecked = True


    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the set of devices managed by the configuration'''
        for d in devs:
            self.mgdPlatformDevs.add(d)

    def registerTraceSource(self, traceCapture, source):
        '''Register trace source with trace capture device'''
        traceCapture.addTraceSource(source)
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

    def addManagedTraceDevices(self, traceKey, devs):
        '''Add devices to the set of devices managed by the configuration for this trace mode'''
        traceDevs = self.mgdTraceDevs.get(traceKey)
        if not traceDevs:
            traceDevs = set()
            self.mgdTraceDevs[traceKey] = traceDevs
        for d in devs:
            traceDevs.add(d)

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def createDAPWrapper(self, core):
        '''Add a wrapper around a core to allow access to AHB and APB via the DAP'''
        return MemoryRouter(
            [DapMemoryAccessor("AHB", self.dap, 0, "AHB bus accessed via AP_0 on DAP_0"),
             DapMemoryAccessor("APB", self.dap, 1, "APB bus accessed via AP_1 on DAP_0")],
            core)

    def enableCTIInput(self, cti, input, channel, enabled):
        '''Enable/disable cross triggering between an input and a channel'''
        if enabled:
            cti.enableInputEvent(input, channel)
        else:
            cti.disableInputEvent(input, channel)

    def enableCTIsForSink(self, sink, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, output, channel = self.getCTIForSink(sink)
        if cti:
            self.enableCTIOutput(cti, output, channel, enabled)

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.enableCTIInput(cti, input, channel, enabled)

    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, funnelDev, name)
        funnel.setAllPortsDisabled() # Will enable for each source later
        return funnel

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        # A5 is on port 0
        if enabled:
            self.funnelA5.setPortEnabled(0)
        else:
            self.funnelA5.setPortDisabled(0)

    def enableMasterFunnelPort(self, enabled):
        # A5 is on port 1
        if enabled:
            self.funnelMaster.setPortEnabled(1)
        else:
            self.funnelMaster.setPortDisabled(1)


    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, itmDev, streamID, name)
        # disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

    def setInternalTraceRange(self, currentTraceOptions, newTraceOptions, traceMacrocells):
        # values are different to current config
        if (newTraceOptions.traceRangeEnable != currentTraceOptions.traceRangeEnable) or \
            (newTraceOptions.traceRangeStart != currentTraceOptions.traceRangeStart) or \
            (newTraceOptions.traceRangeEnd != currentTraceOptions.traceRangeEnd):

            # clear existing ranges
            if currentTraceOptions.traceRangeIDs:
                for i in range(0, len(traceMacrocells)):
                    traceMacrocells[i].clearTraceRange(currentTraceOptions.traceRangeIDs[i])
                currentTraceOptions.traceRangeIDs = None

            # set new ranges
            if newTraceOptions.traceRangeEnable:
                currentTraceOptions.traceRangeIDs = [
                    traceMacrocells[i].addTraceRange(newTraceOptions.traceRangeStart, newTraceOptions.traceRangeEnd)
                    for i in range(0, len(traceMacrocells))
                    ]

            currentTraceOptions.traceRangeEnable = newTraceOptions.traceRangeEnable
            currentTraceOptions.traceRangeStart = newTraceOptions.traceRangeStart
            currentTraceOptions.traceRangeEnd = newTraceOptions.traceRangeEnd


class DtslScript_DSTREAM_ST_Family(DtslScript_DSTREAM):

    def setupDSTREAMTrace(self):
        '''Setup DSTREAM trace capture'''

        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.funnelA5, self.funnelMaster, self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.funnelA5, self.funnelMaster, self.tpiu, self.swo, self.DSTREAM ])

        # register trace sources
        self.registerA5TraceSources(self.DSTREAM)


class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")], isDynamic=False),
                        DTSLv1.enumOption('traceBufferSize', 'Trace Buffer Size', defaultValue="4GB",
                            values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"), ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"), ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                    ]),
                ]),
                DTSLv1.tabPage("cortexA5", "Cortex-A5", childOptions=[
                    DTSLv1.booleanOption('cortexA5coreTrace', 'Cortex-A5 trace', defaultValue=False,
                        description="Enable trace from the Cortex-A5 module",
                        childOptions =
                            [ DtslScript_DSTREAM_ST.getTraceCaptureOption() ] +
                            ETMv3_5TraceSource.defaultOptions(DtslScript_DSTREAM.getA5ETM) +
                            [
                            DtslScript_DSTREAM.getContextIdsOption(),
                            ETMv3_5TraceSource.dataOption(DtslScript_DSTREAM.getA5ETM),
                            DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable ETM triggers to halt execution", defaultValue=False),
                            DtslScript_DSTREAM.getTraceRangeOption(),
                            DtslScript_DSTREAM.getItmOption()
                            ]
                        ),
                ]),
                DtslScript_DSTREAM.getSjcTabPage()
            ])
        ]

    @staticmethod
    def getTraceCaptureOption():
        return DTSLv1.enumOption('A5traceCapture', 'Trace capture method', defaultValue="none",
            values = [("none", "None"), ("ETB_A5", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM-ST Streaming Trace")],
            setter=DtslScript_DSTREAM.setA5TraceCaptureMethod)

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMSTStoredTraceCapture(self, "DSTREAM")

    def setTraceBufferSize(self, mode):
        '''Configuration option setter method for the trace cache buffer size'''
        cacheSize = 64*1024*1024
        if (mode == "64MB"):
            cacheSize = 64*1024*1024
        if (mode == "128MB"):
            cacheSize = 128*1024*1024
        if (mode == "256MB"):
            cacheSize = 256*1024*1024
        if (mode == "512MB"):
            cacheSize = 512*1024*1024
        if (mode == "1GB"):
            cacheSize = 1*1024*1024*1024
        if (mode == "2GB"):
            cacheSize = 2*1024*1024*1024
        if (mode == "4GB"):
            cacheSize = 4*1024*1024*1024
        if (mode == "8GB"):
            cacheSize = 8*1024*1024*1024
        if (mode == "16GB"):
            cacheSize = 16*1024*1024*1024
        if (mode == "32GB"):
            cacheSize = 32*1024*1024*1024
        if (mode == "64GB"):
            cacheSize = 64*1024*1024*1024
        if (mode == "128GB"):
            cacheSize = 128*1024*1024*1024

        self.DSTREAM.setMaxCaptureSize(cacheSize)


class DtslScript_DSTREAM_PT(DtslScript_DSTREAM_ST_Family):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")], isDynamic=False)
                    ]),
                ]),
                DTSLv1.tabPage("cortexA5", "Cortex-A5", childOptions=[
                    DTSLv1.booleanOption('cortexA5coreTrace', 'Cortex-A5 trace', defaultValue=False,
                        description="Enable trace from the Cortex-A5 module",
                        childOptions =
                            [ DtslScript_DSTREAM_PT.getTraceCaptureOption() ] +
                            ETMv3_5TraceSource.defaultOptions(DtslScript_DSTREAM.getA5ETM) +
                            [
                            DtslScript_DSTREAM.getContextIdsOption(),
                            ETMv3_5TraceSource.dataOption(DtslScript_DSTREAM.getA5ETM),
                            DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable ETM triggers to halt execution", defaultValue=False),
                            DtslScript_DSTREAM.getTraceRangeOption(),
                            DtslScript_DSTREAM.getItmOption()
                            ]
                        ),
                ]),
                DtslScript_DSTREAM.getSjcTabPage()
            ])
        ]

    @staticmethod
    def getTraceCaptureOption():
        return DTSLv1.enumOption('A5traceCapture', 'Trace capture method', defaultValue="none",
            values = [("none", "None"), ("ETB_A5", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer")],
            setter=DtslScript_DSTREAM.setA5TraceCaptureMethod)

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")


class DtslScript_NoDSTREAM(DtslScript_DSTREAM):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("cortexA5", "Cortex-A5", childOptions=[
                    DTSLv1.booleanOption('cortexA5coreTrace', 'Cortex-A5 trace', defaultValue=False,
                        description="Enable trace from the Cortex-A5 module",
                        childOptions =
                            [ DtslScript_NoDSTREAM.getTraceCaptureOption() ] +
                            ETMv3_5TraceSource.defaultOptions(DtslScript_DSTREAM.getA5ETM) +
                            [
                            DtslScript_DSTREAM.getContextIdsOption(),
                            ETMv3_5TraceSource.dataOption(DtslScript_DSTREAM.getA5ETM),
                            DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable ETM triggers to halt execution", defaultValue=False),
                            DtslScript_DSTREAM.getTraceRangeOption(),
                            DtslScript_DSTREAM.getItmOption()
                            ]
                        ),
                ]),
                DTSLv1.tabPage("sjc", "Secure Debug", childOptions=[
                    DTSLv1.booleanOption('sjcUnlock', 'Configure the SJC',
                        defaultValue = False,
                        setter=DtslScript_DSTREAM.setUnlockSJC,
                        childOptions = [
                            DTSLv1.integerOption('key', 'SJC key',
                                description='56-bit SJC unlock code',
                                defaultValue=0x123456789ABCDE,
                                display=IIntegerOption.DisplayFormat.HEX)
                            ]
                        )
                ])
            ])
        ]

    @staticmethod
    def getTraceCaptureOption():
        return DTSLv1.enumOption('A5traceCapture', 'Trace capture method', defaultValue="none",
            values = [("none", "None"), ("ETB_A5", "On Chip Trace Buffer (ETB)")],
            setter=DtslScript_DSTREAM.setA5TraceCaptureMethod)


class DtslScript_ULINKpro(DtslScript_NoDSTREAM):
    @staticmethod
    def getOptionList():
        return DtslScript_NoDSTREAM.getOptionList()

class DtslScript_ULINKproD(DtslScript_NoDSTREAM):
    @staticmethod
    def getOptionList():
        return DtslScript_NoDSTREAM.getOptionList()

class DtslScript_CMSIS(DtslScript_NoDSTREAM):
    @staticmethod
    def getOptionList():
        return DtslScript_NoDSTREAM.getOptionList()

class DtslScript_RVI(DtslScript_NoDSTREAM):
    @staticmethod
    def getOptionList():
        return DtslScript_NoDSTREAM.getOptionList()
