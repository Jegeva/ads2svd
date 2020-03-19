from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import CSTPIU

NUM_CORES_CORTEX_A8 = 1
ATB_ID_BASE = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
CORTEX_A8_TRACE_OPTIONS = 0

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
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB", "On Chip Trace Buffer (ETB)")],
                        setter=DtslScript.setTraceCaptureMethod),
                ]),
                DTSLv1.tabPage("coreTrace", "Core Trace", childOptions=[
                    DTSLv1.booleanOption('cortexA8coreTrace', 'Enable Cortex-A8 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A8_%d' % c, "Enable Cortex-A8 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_A8) ] +
                            # Pull in common options for ETMs
                            ETMv3_3TraceSource.defaultOptions(DtslScript.getETMs) +
                            [ DTSLv1.booleanOption('addresses', 'Enable data address trace',
                                description='Enable trace of data access addresses in addition to instruction trace', defaultValue=False ) ] +
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
                ]),
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

        self.setupETBTrace()

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-A8 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        cortexA8coreDev = 0
        self.cortexA8cores = []

        streamID = ATB_ID_BASE

        self.CTIs = []

        # Trace start/stop CTI
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")

        coreCTIDev = self.findDevice("Cortex-A8")#look for core CTI devices after the first core..

        etmDev = 1
        self.ETMs  = []

        for i in range(0, NUM_CORES_CORTEX_A8):
            # create core
            cortexA8coreDev = self.findDevice("Cortex-A8", cortexA8coreDev+1)
            dev = Device(self, cortexA8coreDev, "Cortex-A8")
            self.cortexA8cores.append(dev)

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev+1)
            etm = ETMv3_3TraceSource(self, etmDev, streamID, "ETM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)

        # ETB
        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

    def exposeCores(self):
        for core in self.cortexA8cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def setupETBTrace(self):
        '''Setup ETB trace capture'''

        # use continuous mode
        self.ETB.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETB and register ETB with configuration
        self.addTraceCaptureInterface(self.ETB)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETB", [ self.tpiu, self.outCTI, self.ETB ])

        # register trace sources
        self.registerTraceSources(self.ETB)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == self.ETB:
            # ETB trigger input is CTI out 1
            return (self.outCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)
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
        self.enableCTIsForSource(source, enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # disable the TPIU by default to allow ETB to work at full rate
        tpiu.setEnabled(False)
        return tpiu

    def setETBTraceEnabled(self, enabled):
        '''Enable/disable ETB trace capture'''
        self.enableCTIsForSink(self.ETB, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A8):
            self.registerCoreTraceSource(traceCapture, self.cortexA8cores[c], self.ETMs[c])


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
        for i in range(0, NUM_CORES_CORTEX_A8):
            portMap[self.ETMs[i]] = self.getFunnelPortForCore(i)


        return portMap.get(source, None)

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()
        traceMode = optionValues.get("options.trace.traceCapture")
        self.setManagedDevices(self.getManagedDevices(traceMode))

        coreTraceEnabled = self.getOptionValue("options.coreTrace.cortexA8coreTrace")
        for i in range(0, NUM_CORES_CORTEX_A8):
            thisCoreTraceEnabled = self.getOptionValue("options.coreTrace.cortexA8coreTrace.Cortex_A8_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            self.setTraceSourceEnabled(self.ETMs[i], enableSource)
            self.setDataAddressTraceEnabled(self.getOptionValue("options.coreTrace.cortexA8coreTrace.addresses"))

        etmStartIndex = 0
        etmEndIndex = 0

        etmEndIndex += NUM_CORES_CORTEX_A8
        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A8_TRACE_OPTIONS], TraceRangeOptions("cortexA8coreTrace", self), self.ETMs[etmStartIndex:etmEndIndex])
        etmStartIndex += NUM_CORES_CORTEX_A8

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setETBTraceEnabled(False)
        elif method == "ETB":
            self.setETBTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def setCoreTraceEnabled(self, enabled):
        '''Enable/disable the core trace sources'''
        for t in self.ETMs:
            self.setTraceSourceEnabled(t, enabled)

    def setDataAddressTraceEnabled(self, enable):
        for ETM in self.ETMs:
            ETM.setDataTraceEnabled(enable)
            ETM.setDataAddressTraceEnabled(enable)

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


