# Copyright (C) 2013-2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETMv3_4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel

NUM_CORES_CORTEX_A9 = 1
NUM_CORES_CORTEX_M3 = 1
ATB_ID_BASE = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 4
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
CORTEX_A9_TRACE_OPTIONS = 0
CORTEX_M3_TRACE_OPTIONS = 1
KERNEL_RANGE_END = 0xFFFFFFFF
KERNEL_RANGE_START = 0x7F000000

class Cortex_M_ETM(ETMv3_4TraceSource):
    """
    Cortex-M*-specific ETM configuration.
    """
    # Disable trace triggers and start stop points as currently unsupported
    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False


class TraceRangeOptions:
    def __init__(self, coreTraceName = None, dtsl = None):
        if coreTraceName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("options.coreTrace.%s.traceRange" % coreTraceName)
            self.traceRangeStart = dtsl.getOptionValue("options.coreTrace.%s.traceRange.start" % coreTraceName)
            self.traceRangeEnd = dtsl.getOptionValue("options.coreTrace.%s.traceRange.end" % coreTraceName)
            self.traceRangeIDs = None

    def defaultSetup(self):
        self.traceRangeEnable = False
        self.traceRangeStart = None
        self.traceRangeEnd = None
        self.traceRangeIDs = None


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCoreTraceTabPage()
                ]),
            ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

    @staticmethod
    def getOptionCoreTraceTabPage():
        return DTSLv1.tabPage("coreTrace", "Core Trace", childOptions=[
                   DtslScript.getOptionCortexA9BooleanOption(),
                   DtslScript.getOptionCortexM3BooleanOption()
                ])

    @staticmethod
    def getOptionCortexA9BooleanOption():
        return DTSLv1.booleanOption('cortexA9coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A9_%d' % c, "Enable Cortex-A9 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_A9) ] +
                            # Pull in common options for PTMs (cycle accurate etc)
                            PTMTraceSource.defaultOptions(DtslScript.getPTMs) +
                            [ # Trace range selection (e.g. for linux kernel)
                            DTSLv1.booleanOption('traceRange', 'Trace capture range',
                                description=TRACE_RANGE_DESCRIPTION,
                                defaultValue = False,
                                childOptions = [
                                    DTSLv1.integerOption('start', 'Start address',
                                        description='Start address for trace capture',
                                        defaultValue=KERNEL_RANGE_START,
                                        display=IIntegerOption.DisplayFormat.HEX),
                                    DTSLv1.integerOption('end', 'End address',
                                        description='End address for trace capture',
                                        defaultValue=KERNEL_RANGE_END,
                                        display=IIntegerOption.DisplayFormat.HEX)
                                ])
                            ]
                        )

    @staticmethod
    def getOptionCortexM3BooleanOption():
        return DTSLv1.booleanOption('cortexM3coreTrace', 'Enable Cortex-M3 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_M3_%d' % c, "Enable Cortex-M3 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_M3) ] +
                            # Pull in common options for ETMs (cycle accurate etc)
                            ETMv3_4TraceSource.defaultOptions(DtslScript.getETMs)
                        )

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # only AHB/APB are managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB_A9)
        self.mgdPlatformDevs.add(self.APB_A9)
        self.mgdPlatformDevs.add(self.AHB_M3)

        self.exposeCores()

        self.setupETBTrace()

        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-A9 trace options
            TraceRangeOptions(), # Cortex-M3 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB_A9 = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB_A9 = APBAP(self, apbDev, "CSMEMAP")

        ahbM3Dev = self.findDevice("CSMEMAP", apbDev+1)
        self.AHB_M3 = CortexM_AHBAP(self, ahbM3Dev, "CSMEMAP")

        cortexA9coreDev = 0
        self.cortexA9cores = []

        cortexM3coreDev = 0
        self.cortexM3cores = []

        streamID = ATB_ID_BASE

        # Trace start/stop CTI
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")

        coreCTIDev = self.findDevice("Cortex-A9") # look for core CTI devices after the first core..
        self.CTIs  = []
        self.cortexA9ctiMap = {} # map cores to associated CTIs
        self.cortexM3ctiMap = {} # map cores to associated CTIs

        ptmDev = 1
        self.PTMs  = []

        etmDev = self.findDevice("Cortex-M3") # look for ETMs after M3
        self.ETMs  = []

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

        for i in range(0, NUM_CORES_CORTEX_M3):
            # create core
            cortexM3coreDev = self.findDevice("Cortex-M3", cortexM3coreDev+1)
            dev = Device(self, cortexM3coreDev, "Cortex-M3")
            self.cortexM3cores.append(dev)

            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)
            self.cortexM3ctiMap[dev] = coreCTI

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev+1)
            etm = Cortex_M_ETM(self, etmDev, streamID, "ETM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)

        # ETB
        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")

        # DSTREAM
        self.createDSTREAM()

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

        # Funnel 0
        funnelDev0 = self.findDevice("CSTFunnel")
        self.funnel0 = self.createFunnel(funnelDev0, "Funnel_0")

        # Funnel 1
        funnelDev1 = self.findDevice("CSTFunnel", funnelDev0+1)
        self.funnel1 = self.createFunnel(funnelDev1, "Funnel_1")
        self.funnel1.setPortEnabled(0)

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def exposeCores(self):
        for core in self.cortexA9cores:
            self.registerA9Filters(core)
            self.addDeviceInterface(core)
        for core in self.cortexM3cores:
            self.registerM3Filters(core)
            self.addDeviceInterface(core)

    def setupETBTrace(self):
        '''Setup ETB trace capture'''

        # use continuous mode
        self.ETB.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETB and register ETB with configuration
        self.ETB.setTraceComponentOrder([ self.funnel1, self.funnel0 ])
        self.addTraceCaptureInterface(self.ETB)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETB", [ self.funnel1, self.funnel0, self.tpiu, self.outCTI, self.ETB ])

        # register trace sources
        self.registerTraceSources(self.ETB)

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''

        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        self.setPortWidth(portWidth)

        # configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.funnel1, self.funnel0, self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.funnel1, self.funnel0, self.outCTI, self.tpiu, self.DSTREAM ])

        # register trace sources
        self.registerTraceSources(self.DSTREAM)

    def setPortWidth(self, portWidth):
        self.tpiu.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == self.ETB:
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

    def setETBTraceEnabled(self, enabled):
        '''Enable/disable ETB trace capture'''
        self.enableCTIsForSink(self.ETB, enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.tpiu.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A9):
            self.registerCoreTraceSource(traceCapture, self.cortexA9cores[c], self.PTMs[c])
        for c in range(0, NUM_CORES_CORTEX_M3):
            self.registerCoreTraceSource(traceCapture, self.cortexM3cores[c], self.ETMs[c])

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

        for i in range(0, NUM_CORES_CORTEX_M3):
            portMap[self.ETMs[i]] = self.getFunnelPortForCore(NUM_CORES_CORTEX_A9+i)

        return portMap.get(source, None)

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()
        traceMode = optionValues.get("options.trace.traceCapture")
        self.setManagedDevices(self.getManagedDevices(traceMode))

        coreTraceEnabled = self.getOptionValue("options.coreTrace.cortexA9coreTrace")
        for i in range(0, NUM_CORES_CORTEX_A9):
            thisCoreTraceEnabled = self.getOptionValue("options.coreTrace.cortexA9coreTrace.Cortex_A9_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            self.setTraceSourceEnabled(self.PTMs[i], enableSource)

        coreTraceEnabled = self.getOptionValue("options.coreTrace.cortexM3coreTrace")
        for i in range(0, NUM_CORES_CORTEX_M3):
            thisCoreTraceEnabled = self.getOptionValue("options.coreTrace.cortexM3coreTrace.Cortex_M3_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            self.setTraceSourceEnabled(self.ETMs[i], enableSource)

        ptmStartIndex = 0
        ptmEndIndex = 0

        ptmEndIndex += NUM_CORES_CORTEX_A9
        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A9_TRACE_OPTIONS], TraceRangeOptions("cortexA9coreTrace", self), self.PTMs[ptmStartIndex:ptmEndIndex])
        ptmStartIndex += NUM_CORES_CORTEX_A9

        dstream_opts = "options.trace.traceCapture.dstream."
        traceBufferSizeOpt = self.getOptions().getOption(dstream_opts + "traceBufferSize")
        if traceBufferSizeOpt:
            traceBufferSize = self.getOptionValue(dstream_opts + "traceBufferSize")
            self.setTraceBufferSize(traceBufferSize)


    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setETBTraceEnabled(False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "ETB":
            self.setETBTraceEnabled(True)
            self.setDSTREAMTraceEnabled(False)
        elif method == "DSTREAM":
            self.setETBTraceEnabled(False)
            self.setDSTREAMTraceEnabled(True)

    def getPTMs(self):
        '''Get the PTMs'''
        return self.PTMs

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def setCoreTraceEnabled(self, enabled):
        '''Enable/disable the core trace sources'''
        for t in self.PTMs:
            self.setTraceSourceEnabled(t, enabled)

        for t in self.ETMs:
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

    def registerA9Filters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB_A9, "A9 AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB_A9, "A9 APB bus accessed via AP_1")])

    def registerM3Filters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AHBCortexMMemAPAccessor("AHB", self.AHB_M3, "M3 AHB bus accessed via AP_0")])

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
        # A9 is on port 3, M3 is on port 1
        if (core == 0):
            return 3
        return 1

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


class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_RVI.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCoreTraceTabPage()
                ]),
            ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB", "On Chip Trace Buffer (ETB)")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''

        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        self.setPortWidth(portWidth)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.funnel1, self.funnel0, self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.funnel1, self.funnel0, self.outCTI, self.tpiu, self.DSTREAM ])

        # register trace sources
        self.registerTraceSources(self.DSTREAM)

class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_ST.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCoreTraceTabPage()
                ]),
            ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"),
                                  ("ETB", "On Chip Trace Buffer (ETB)"),
                                  DtslScript_DSTREAM_ST.getDSTREAMOptions()],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

    @staticmethod
    def getDSTREAMOptions():
        return (
            "DSTREAM", "Streaming Trace",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('traceBufferSize', 'Trace buffer size', defaultValue="4GB",
                        values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"),
                                  ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"),
                                  ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                ]
            )
        )

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
                DtslScript_DSTREAM_PT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCoreTraceTabPage()
                ]),
            ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"),
                                  ("ETB", "On Chip Trace Buffer (ETB)"),
                                  ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")
