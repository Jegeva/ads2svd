# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
from com.arm.debug.dtsl import DTSLException
from com.arm.rddi import RDDI_ACC_SIZE
from struct import pack, unpack
from jarray import zeros

NUM_CORES_CORTEX_A9 = 1
ATB_ID_BASE = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 4
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
CORTEX_A9_TRACE_OPTIONS = 0

'''
Because of slow connection over CMSIS-DAP, replace download
with simple memWrites so there isn't a queue of download packets
'''
class CoreNoDownload(Device):
    def __init__(self, config, id, name):
        Device.__init__(self, config, id, name)
        self.downloading = False
        self.dlStart = 0
        self.dlErrorEncountered = False

    def memDownload(self, page, address, size, rule, check, count, data):
        try:
            if (self.downloading == False):
                self.dlStart = address
                self.downloading = True
            self.memWrite( page, address, size, rule, check, count, data)
        except NativeException, e:
            if (self.dlErrorEncountered == False):
                self.dlError = e
                self.dlErrorEncountered = True


    def memDownloadEnd(self, values, pages, addresses, offsets):
        self.downloading = False
        if (self.dlErrorEncountered == True):
            self.dlErrorEncountered = False
            values[0] = self.dlError.getRDDIErrorCode()
            raise self.dlError
        else:
            values[0] = 0


class TraceRangeOptions:
    def __init__(self, coreTraceName = None, dtsl = None):
        if coreTraceName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("options.trace.%s.traceRange" % coreTraceName)
            self.traceRangeStart = dtsl.getOptionValue("options.trace.%s.traceRange.start" % coreTraceName)
            self.traceRangeEnd = dtsl.getOptionValue("options.trace.%s.traceRange.end" % coreTraceName)
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
                DTSLv1.tabPage("trace", "Trace", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("DSTREAM", "DSTREAM 4GB Trace Buffer"), ("ETF", "On Chip Trace Buffer (ETF)")],
                        setter=DtslScript_DSTREAM.setTraceCaptureMethod),
                    DTSLv1.booleanOption('cortexA9coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A9_%d' % c, "Enable Cortex-A9 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_A9) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", isDynamic=True, defaultValue=False) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the output of context ID values into the PTM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ])
                            ] +
                            # Pull in common options for PTMs (cycle accurate etc)
                            PTMTraceSource.defaultOptions(DtslScript_DSTREAM.getPTMs) +
                            [ # Trace range selection (e.g. for linux kernel)
                            DTSLv1.booleanOption('traceRange', 'Trace capture range',
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
                            ]
                        ),
                ])
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # only AHB/APB are managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB)
        self.mgdPlatformDevs.add(self.APB)

        self.exposeCores()

        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)
        self.setupETFTrace()

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-A9 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+
    def ReadModifyWrite(self, address, mask, newValue):
        buffer = zeros(4, 'b')

        self.cortexA9cores[0].memRead(0x4300, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, 0x10000, 4, buffer)

        value = unpack('<I', buffer)[0]
        value &= mask
        value |= newValue

        self.cortexA9cores[0].memWrite(0x4300, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, 0x10000, False, 4, pack('<I', value))


    def doPinmux(self):
        # Set up pinmuxing
        # The bits we are interested in are port_3[11:8] (trace data) and port_3[15:14] (trace clock and CTL)
        # We need to set these as output, alternative use 5
        baseAddress = 0xFCFE3000
        PM_3 =    baseAddress + 0x030C        # Port Mode
        PMC_3 =   baseAddress + 0x040C        # Port Mode Control
        PFC_3 =   baseAddress + 0x050C        # Port Function Control
        PFCE_3 =  baseAddress + 0x060C        # Port Function Control Expansion
        PFCAE_3 = baseAddress + 0x0A0C        # Port Function Control Additional Expansion
        PIPC_3 =  baseAddress + 0x420C        # Port IP Control
        self.ReadModifyWrite(PM_3,    0xFFFF30FF, 0x00000000)
        self.ReadModifyWrite(PMC_3,   0xFFFF30FF, 0x0000CF00)
        self.ReadModifyWrite(PFC_3,   0xFFFF30FF, 0x00000000)
        self.ReadModifyWrite(PFCE_3,  0xFFFF30FF, 0x00000000)
        self.ReadModifyWrite(PFCAE_3, 0xFFFF30FF, 0x0000CF00)
        self.ReadModifyWrite(PIPC_3,  0xFFFF30FF, 0x0000CF00)

    def postConnect(self):
        coreTraceEnabled = self.getOptionValue("options.trace.cortexA9coreTrace")
        if coreTraceEnabled:
            if self.tpiu.getEnabled():
                self.doPinmux()
        DTSLv1.postConnect(self)

    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        cortexA9coreDev = 0
        self.cortexA9cores = []

        streamID = ATB_ID_BASE

        # Trace start/stop CTI
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")
        coreCTIDev = outCTIDev
        self.CTIs  = []
        self.cortexA9ctiMap = {} # map cores to associated CTIs

        ptmDev = 1
        self.PTMs  = []

        for i in range(0, NUM_CORES_CORTEX_A9):
            # create core
            cortexA9coreDev = self.findDevice("Cortex-A9", cortexA9coreDev+1)
            dev = Device(self, cortexA9coreDev, "Cortex-A9")
            self.cortexA9cores.append(dev)

            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)
            self.cortexA9ctiMap[dev] = coreCTI

            # create the PTM for this core
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            ptm = PTMTraceSource(self, ptmDev, streamID, "PTM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            ptm.setEnabled(False)
            self.PTMs.append(ptm)

        # DSTREAM
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

        # Funnel 0
        funnelDev0 = self.findDevice("CSTFunnel")
        self.funnel0 = self.createFunnel(funnelDev0, "Funnel_0")

        # ETF
        tmcDev = self.findDevice("CSTMC")
        self.etf = CSTMC(self, tmcDev, "ETF")
        self.etf.setMode(CSTMC.Mode.ETF)

        # ETF can also be used as a trace buffer
        self.etfTrace = TMCETBTraceCapture(self, self.etf, "ETF")


    def exposeCores(self):
        for core in self.cortexA9cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def setupDSTREAMTrace(self, portwidth):
        '''Setup DSTREAM trace capture'''

        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        self.tpiu.setPortSize(portwidth)

        # configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.DSTREAM.setPortWidth(portwidth)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.tpiu, self.etf, self.funnel0 ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.funnel0, self.outCTI, self.tpiu, self.etf, self.DSTREAM ])

        # register trace sources
        self.registerTraceSources(self.DSTREAM)

    def setupETFTrace(self):
        '''Setup ETF trace capture'''

        # use continuous mode
        self.etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETF and register ETF with configuration
        self.etfTrace.setTraceComponentOrder([ self.funnel0 ])
        self.addTraceCaptureInterface(self.etfTrace)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETF", [self.funnel0, self.outCTI, self.tpiu, self.etfTrace])

        # register trace sources
        self.registerTraceSources(self.etfTrace)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == self.DSTREAM:
            # TPIU trigger input is CTI out 3
            return (self.outCTI, 3, CTM_CHANNEL_TRACE_TRIGGER)
        # no associated CTI
        return (None, None, None)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a source
        return (None, None, None) if no associated CTI
        '''
        if source in self.PTMs:
            coreNum = self.PTMs.index(source)
            # PTM trigger is on input 6
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

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.tpiu.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def setETFTraceEnabled(self, enabled):
        '''Enable/disable ETF trace capture'''
        if enabled:
            # ensure TPIU is disabled
            self.tpiu.setEnabled(False)
        self.enableCTIsForSink(self.etfTrace, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A9):
            self.registerCoreTraceSource(traceCapture, self.cortexA9cores[c], self.PTMs[c])


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

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnel ports
        portMap = {}
        for i in range(0, NUM_CORES_CORTEX_A9):
            portMap[self.PTMs[i]] = self.getFunnelPortForCore(i)


        return portMap.get(source, None)

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

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
        traceMode = optionValues.get("options.trace.traceCapture")
        self.setManagedDevices(self.getManagedDevices(traceMode))

        coreTraceEnabled = self.getOptionValue("options.trace.cortexA9coreTrace")
        for i in range(0, NUM_CORES_CORTEX_A9):
            thisCoreTraceEnabled = self.getOptionValue("options.trace.cortexA9coreTrace.Cortex_A9_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            self.setTraceSourceEnabled(self.PTMs[i], enableSource)
            self.setTriggerGeneratesDBGRQ(self.PTMs[i], self.getOptionValue("options.trace.cortexA9coreTrace.triggerhalt"))
            self.setContextIDEnabled(self.PTMs[i],
                                     self.getOptionValue("options.trace.cortexA9coreTrace.contextIDs"),
                                     self.getOptionValue("options.trace.cortexA9coreTrace.contextIDs.contextIDsSize"))

        ptmStartIndex = 0
        ptmEndIndex = 0

        ptmEndIndex += NUM_CORES_CORTEX_A9
        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A9_TRACE_OPTIONS], TraceRangeOptions("cortexA9coreTrace", self), self.PTMs[ptmStartIndex:ptmEndIndex])
        ptmStartIndex += NUM_CORES_CORTEX_A9

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setDSTREAMTraceEnabled(False)
            self.setETFTraceEnabled(False)
        elif method == "DSTREAM":
            self.etf.setMode(CSTMC.Mode.ETF)
            self.setDSTREAMTraceEnabled(True)
            self.setETFTraceEnabled(False)
        elif method == "ETF":
            self.etf.setMode(CSTMC.Mode.ETB)
            self.setDSTREAMTraceEnabled(False)
            self.setETFTraceEnabled(True)


    def getPTMs(self):
        '''Get the PTMs'''
        return self.PTMs

    def setCoreTraceEnabled(self, enabled):
        '''Enable/disable the core trace sources'''
        for t in self.PTMs:
            self.setTraceSourceEnabled(t, enabled)


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

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP_1")])

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

    def enableCTIOutput(self, cti, output, channel, enabled):
        '''Enable/disable cross triggering between a channel and an output'''
        if enabled:
            cti.enableOutputEvent(output, channel)
        else:
            cti.disableOutputEvent(output, channel)

    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, funnelDev, name)
        funnel.setAllPortsDisabled() # Will enable for each source later
        return funnel

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        port = self.getFunnelPortForSource(source)
        if enabled:
            self.funnel0.setPortEnabled(port)
        else:
            self.funnel0.setPortDisabled(port)

    def getFunnelPortForCore(self, core):
        ''' Funnel port-to-core mapping can be customized here'''
        port = core
        return port

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

    def verify(self):
        mask = [ 0xF, 0x0, 0x0, 0x0, 0xFF, 0xFF, 0xF, 0x0 ]
        expectedA9 = [ 4L, 0L, 0L, 0L, 9L, 188L, 11L, 0L ]
        addrA9 = 0x80030fd0
        expectedTMC = [ 4L, 0L, 0L, 0L, 97L, 185L, 11L, 0L ]
        addrTMC = 0x80021fd0
        expectedROMTable = [ 4L, 0L, 0L, 0L, 18L, 48L, 10L, 0L ]
        addrROMTable = 0x80000fd0
        return self.confirmValue(addrROMTable, expectedROMTable, mask) and self.confirmValue(addrA9, expectedA9, mask) and self.confirmValue(addrTMC, expectedTMC, mask)

    def confirmValue(self, addr, expected, mask):
        actual = zeros(len(expected), 'l')
        for i in range(0,len(expected)-1) :
            j = i*4
            buffer = zeros(4, 'b')
            try:
                self.cortexA9cores[0].memRead(1, addr+j, RDDI_ACC_SIZE.RDDI_ACC_DEF, 0x20000, 4, buffer)
            except DTSLException:
                return False
            actual[i] = unpack('<I', buffer)[0]
            if ((actual[i] & mask[i]) != (expected[i] & mask[i])):
                return False
        return True


class DtslScript_ULINK(DtslScript_DSTREAM):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF)")],
                        setter=DtslScript_ULINK.setTraceCaptureMethod),
                    DTSLv1.booleanOption('cortexA9coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A9_%d' % c, "Enable Cortex-A9 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_A9) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", isDynamic=True, defaultValue=False) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the output of context ID values into the PTM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ])
                            ] +
                            # Pull in common options for PTMs (cycle accurate etc)
                            PTMTraceSource.defaultOptions(DtslScript_ULINK.getPTMs) +
                            [ # Trace range selection (e.g. for linux kernel)
                            DTSLv1.booleanOption('traceRange', 'Trace capture range',
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
                            ]
                        ),
                ])
            ])
        ]


# These are simple wrapper classes to the base DtslScript_ULINK class.
# For each platform, Arm DS creates a folder named after the DTSL Class to store
# the DTSL options file.
# Forcing each target connection to use a different class means that
# different DTSL options files are created for each connection type.
# If you want to have a shared options file, then use the same class name for
# each connection type
class DtslScript_ULINKpro(DtslScript_ULINK):
    pass

class DtslScript_CMSIS(DtslScript_ULINK):
    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        cortexA9coreDev = 0
        self.cortexA9cores = []

        streamID = ATB_ID_BASE

        # Trace start/stop CTI
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")
        coreCTIDev = outCTIDev
        self.CTIs  = []
        self.cortexA9ctiMap = {} # map cores to associated CTIs

        ptmDev = 1
        self.PTMs  = []

        for i in range(0, NUM_CORES_CORTEX_A9):
            # create core
            cortexA9coreDev = self.findDevice("Cortex-A9", cortexA9coreDev+1)
            dev = CoreNoDownload(self, cortexA9coreDev, "Cortex-A9")
            self.cortexA9cores.append(dev)

            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)
            self.cortexA9ctiMap[dev] = coreCTI

            # create the PTM for this core
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            ptm = PTMTraceSource(self, ptmDev, streamID, "PTM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            ptm.setEnabled(False)
            self.PTMs.append(ptm)

        # DSTREAM
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

        # Funnel 0
        funnelDev0 = self.findDevice("CSTFunnel")
        self.funnel0 = self.createFunnel(funnelDev0, "Funnel_0")

        # ETF
        tmcDev = self.findDevice("CSTMC")
        self.etf = CSTMC(self, tmcDev, "ETF")
        self.etf.setMode(CSTMC.Mode.ETF)

        # ETF can also be used as a trace buffer
        self.etfTrace = TMCETBTraceCapture(self, self.etf, "ETF")

class DtslScript_ULINK2(DtslScript_ULINK):
    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        cortexA9coreDev = 0
        self.cortexA9cores = []

        streamID = ATB_ID_BASE

        # Trace start/stop CTI
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")
        coreCTIDev = outCTIDev
        self.CTIs  = []
        self.cortexA9ctiMap = {} # map cores to associated CTIs

        ptmDev = 1
        self.PTMs  = []

        for i in range(0, NUM_CORES_CORTEX_A9):
            # create core
            cortexA9coreDev = self.findDevice("Cortex-A9", cortexA9coreDev+1)
            dev = CoreNoDownload(self, cortexA9coreDev, "Cortex-A9")
            self.cortexA9cores.append(dev)

            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)
            self.cortexA9ctiMap[dev] = coreCTI

            # create the PTM for this core
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            ptm = PTMTraceSource(self, ptmDev, streamID, "PTM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            ptm.setEnabled(False)
            self.PTMs.append(ptm)

        # DSTREAM
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

        # Funnel 0
        funnelDev0 = self.findDevice("CSTFunnel")
        self.funnel0 = self.createFunnel(funnelDev0, "Funnel_0")

        # ETF
        tmcDev = self.findDevice("CSTMC")
        self.etf = CSTMC(self, tmcDev, "ETF")
        self.etf.setMode(CSTMC.Mode.ETF)

        # ETF can also be used as a trace buffer
        self.etfTrace = TMCETBTraceCapture(self, self.etf, "ETF")

class DtslScript_RVI(DtslScript_ULINK):
    pass
