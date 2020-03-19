from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.rddi import RDDI_ACC_SIZE
from struct import pack

NUM_CORES_CORTEX_R4 = 1
ATB_ID_BASE = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 16
CORTEX_R4_TRACE_OPTIONS = 0

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


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.booleanOption('cortexR4coreTrace', 'Enable Cortex-R4 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_R4_%d' % c, "Enable Cortex-R4 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_R4) ] +
                            # Pull in common options for ETMs
                            ETMv3_3TraceSource.defaultOptions(DtslScript.getETMs) +
                            [ ETMv3_3TraceSource.dataOption(DtslScript.getETMs) ] +
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

        # only AHB/APB devices are managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB)
        self.mgdPlatformDevs.add(self.APB)

        self.exposeCores()

        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-R4 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def doTRACECLKsetup(self):
        ap = 0

        # unlock TPIU config register: 0xFFa03FB0 = 0xC5acce55
        self.AHB.writeMem(0xFFa03FB0, 0xC5acce55)

        # set TRACECLK source = HCLK: 0xFFa03404 = 0x00000001
        self.AHB.writeMem(0xFFa03404, 0x00000001)

        # enable TRACECLK: 0xFFA04404 = 0x00000001
        self.AHB.writeMem(0xFFA04404, 0x00000001)

    def postConnect(self):
        if self.tpiu.getEnabled():
            self.doTRACECLKsetup()

        DTSLv1.postConnect(self)

    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        cortexR4coreDev = 0
        self.cortexR4cores = []

        streamID = ATB_ID_BASE

        etmDev = 1
        self.ETMs  = []

        for i in range(0, NUM_CORES_CORTEX_R4):
            # create core
            cortexR4coreDev = self.findDevice("Cortex-R4", cortexR4coreDev+1)
            dev = Device(self, cortexR4coreDev, "Cortex-R4")
            self.cortexR4cores.append(dev)

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev+1)
            etm = ETMv3_3TraceSource(self, etmDev, streamID, "ETM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)

        # DSTREAM
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

    def exposeCores(self):
        for core in self.cortexR4cores:
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
        self.DSTREAM.setTraceComponentOrder([ self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.tpiu, self.DSTREAM ])

        # register trace sources
        self.registerTraceSources(self.DSTREAM)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # disable the TPIU by default to allow ETB to work at full rate
        tpiu.setEnabled(False)
        return tpiu

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.tpiu.setEnabled(enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_R4):
            self.registerCoreTraceSource(traceCapture, self.cortexR4cores[c], self.ETMs[c])


    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnel ports
        portMap = {}
        for i in range(0, NUM_CORES_CORTEX_R4):
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

        coreTraceEnabled = self.getOptionValue("options.trace.cortexR4coreTrace")
        for i in range(0, NUM_CORES_CORTEX_R4):
            thisCoreTraceEnabled = self.getOptionValue("options.trace.cortexR4coreTrace.Cortex_R4_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            self.setTraceSourceEnabled(self.ETMs[i], enableSource)

        etmStartIndex = 0
        etmEndIndex = 0

        etmEndIndex += NUM_CORES_CORTEX_R4
        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_R4_TRACE_OPTIONS], TraceRangeOptions("cortexR4coreTrace", self), self.ETMs[etmStartIndex:etmEndIndex])
        etmStartIndex += NUM_CORES_CORTEX_R4

    def setDataTraceEnabled(enabled):
        for i in range(0, NUM_CORES_CORTEX_R4):
            self.ETMs[i].setDataTraceEnabled(dataTraceEnabled)

    def setDataAddressTraceEnabled(enabled):
        for i in range(0, NUM_CORES_CORTEX_R4):
            self.ETMs[i].setDataAddressTraceEnabled(dataTraceAddressEnabled)

    def setDataValueTraceEnabled(enabled):
        for i in range(0, NUM_CORES_CORTEX_R4):
            self.ETMs[i].setDataValueTraceEnabled(dataTraceValuesEnabled)

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setDSTREAMTraceEnabled(False)
        elif method == "DSTREAM":
            self.setDSTREAMTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def setCoreTraceEnabled(self, enabled):
        '''Enable/disable the core trace sources'''
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

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP_1")])

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
        return []
