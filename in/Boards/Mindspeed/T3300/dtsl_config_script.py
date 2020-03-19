from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import RDDISyncSMPDevice
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource

NUM_CLUSTERS = 2
NUM_CORES_CORTEX_A9 = 2
ATB_ID_BASE = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
ITM_ATB_ID = 1
ATB_ID_BASE = ITM_ATB_ID + NUM_CLUSTERS
ITM_FUNNEL_PORT = 3
CORTEX_A9_TRACE_OPTIONS = 0

class TraceRangeOptions:
    def __init__(self, coreTraceName = None, dtsl = None):
        if coreTraceName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("options.%s.cortexA9coreTrace.traceRange" % coreTraceName)
            self.traceRangeStart = dtsl.getOptionValue("options.%s.cortexA9coreTrace.traceRange.start" % coreTraceName)
            self.traceRangeEnd = dtsl.getOptionValue("options.%s.cortexA9coreTrace.traceRange.end" % coreTraceName)
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
                DTSLv1.tabPage("cluster_0", "Cluster 0", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB_0", "On Chip Trace Buffer (ETB)"), ("DSTREAM_0", "DSTREAM 4GB Trace Buffer")]),
                    DTSLv1.booleanOption('cortexA9coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A9_%d' % c, "Enable Cortex-A9 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_A9) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", defaultValue=False) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable PTM Timestamps", description="Controls the output of timestamps into the PTM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the output of context ID values into the PTM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ])
                            ] +
                            # Pull in common options for PTMs (cycle accurate etc)
                            PTMTraceSource.defaultOptions(DtslScript.getPTMs) +
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
                    DTSLv1.booleanOption('itm', 'Enable ITM trace', defaultValue=False),
                ]),
                DTSLv1.tabPage("cluster_1", "Cluster 1", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB_1", "On Chip Trace Buffer (ETB)"), ("DSTREAM_1", "DSTREAM 4GB Trace Buffer")]),
                    DTSLv1.booleanOption('cortexA9coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A9_%d' % c, "Enable Cortex-A9 %d trace" % (2+c), defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_A9) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", defaultValue=False) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable PTM Timestamps", description="Controls the output of timestamps into the PTM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the output of context ID values into the PTM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ])
                            ] +
                            # Pull in common options for PTMs (cycle accurate etc)
                            PTMTraceSource.defaultOptions(DtslScript.getPTMs) +
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
                    DTSLv1.booleanOption('itm', 'Enable ITM trace', defaultValue=False),
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
        for bus in self.AHBs + self.APBs:
            self.mgdPlatformDevs.add(bus)

        self.exposeCores()

        self.setupETBTrace()

        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)

        self.setupSimpleSyncSMP()
        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-A9 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        cortexA9coreDev = 0
        self.cortexA9cores = []

        streamID = ATB_ID_BASE

        coreCTIDev = 1
        self.CTIs  = []

        ahbDev = 1
        etbDev = 1
        tpiuDev = 1
        funnelDev = 1
        itmDev = 1
        ctiDev = 1

        self.AHBs = []
        self.APBs = []
        self.Funnels  = []
        self.ETBs  = []
        self.OutCTIs  = []
        self.TPIUs  = []
        self.ITMs  = []
        self.DSTREAMs  = []

        ptmDev = 1
        self.PTMs  = []

        # T3300 is 2 T2200 chips on a board
        # So each cluster is completely independant and has its own MEMAP/TF/ETB/TPIU
        for cluster in range(0, NUM_CLUSTERS):
            # MEMAP
            ahbDev = self.findDevice("CSMEMAP", ahbDev)
            self.AHBs.append(AHBAP(self, ahbDev, "CSMEMAP"))

            apbDev = self.findDevice("CSMEMAP", ahbDev+1)
            self.APBs.append(APBAP(self, apbDev, "CSMEMAP"))
            ahbDev = apbDev + 1

            # Funnel
            funnelDev = self.findDevice("CSTFunnel", funnelDev + 1)
            funnel = self.createFunnel(funnelDev, "Funnel_Cluster_%d" % cluster)
            self.Funnels.append(funnel)

            # ETB
            etbDev = self.findDevice("CSETB", etbDev + 1)
            etb = ETBTraceCapture(self, etbDev, "ETB_%d" % cluster)
            self.ETBs.append(etb)

            # Output CTI
            ctiDev = self.findDevice("CSCTI", ctiDev + 1)
            outCTI = CSCTI(self, ctiDev, "CTI_out_%d" % cluster)
            self.OutCTIs.append(outCTI)

            # TPIU
            tpiuDev = self.findDevice("CSTPIU", tpiuDev + 1)
            tpiu = self.createTPIU(tpiuDev, "TPIU_%d" % cluster)
            self.TPIUs.append(tpiu)

            # ITM
            itmDev = self.findDevice("CSITM", itmDev + 1)
            itm = self.createITM(itmDev, ITM_ATB_ID + cluster, "ITM_%d" % cluster)
            self.ITMs.append(itm)

            # DSTREAM
            dstream = DSTREAMTraceCapture(self, "DSTREAM_%d" % cluster)
            self.DSTREAMs.append(dstream)

            self.cortexA9cores.append([])
            for core in range(0, NUM_CORES_CORTEX_A9):
                # create core
                core_no = (cluster * NUM_CORES_CORTEX_A9) + core
                cortexA9coreDev = self.findDevice("Cortex-A9", cortexA9coreDev+1)
                dev = Device(self, cortexA9coreDev, "Cortex-A9_%d" % core_no)
                self.cortexA9cores[cluster].append(dev)

                # create the PTM for this core
                ptmDev = self.findDevice("CSPTM", ptmDev+1)
                ptm = PTMTraceSource(self, ptmDev, streamID, "PTM_%d_%d" % (core_no, streamID))
                streamID += 1
                # disabled by default - will enable with option
                ptm.setEnabled(False)
                self.PTMs.append(ptm)



    def exposeCores(self):
        for i in range(NUM_CLUSTERS):
            for core in self.cortexA9cores[i]:
                self.registerFilters(core, i)
                self.addDeviceInterface(core)

    def setupETBTrace(self):
        '''Setup ETB trace capture'''

        for i in range(0, NUM_CLUSTERS):
            # use continuous mode
            self.ETBs[i].setFormatterMode(FormatterMode.CONTINUOUS)

            # register other trace components with ETB and register ETB with configuration
            self.ETBs[i].setTraceComponentOrder([ self.Funnels[i] ])
            self.addTraceCaptureInterface(self.ETBs[i])

            # automatically handle connection/disconnection to trace components
            self.addManagedTraceDevices("ETB_%d" % i, [ self.Funnels[i], self.OutCTIs[i], self.TPIUs[i], self.ETBs[i] ])

            # register trace sources
            self.registerTraceSources(self.ETBs[i])

    def setupDSTREAMTrace(self, portwidth):
        '''Setup DSTREAM trace capture'''

        for i in range(0, NUM_CLUSTERS):
            # configure the TPIU for continuous mode
            self.TPIUs[i].setFormatterMode(FormatterMode.CONTINUOUS)
            self.TPIUs[i].setPortSize(portwidth)

            # configure the DSTREAM for continuous trace
            self.DSTREAMs[i].setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
            self.DSTREAMs[i].setPortWidth(portwidth)

            # register other trace components
            self.DSTREAMs[i].setTraceComponentOrder([ self.Funnels[i], self.TPIUs[i] ])

            # register the DSTREAM with the configuration
            self.addTraceCaptureInterface(self.DSTREAMs[i])

            # automatically handle connection/disconnection to trace components
            self.addManagedTraceDevices("DSTREAM_%d" % i, [ self.Funnels[i], self.OutCTIs[i], self.TPIUs[i], self.DSTREAMs[i] ])

            # register trace sources
            self.registerTraceSources(self.DSTREAMs[i])

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        for i in range(0, NUM_CLUSTERS):
            if sink == self.ETBs[i]:
                # ETB trigger input is CTI out 1
                return (self.OutCTIs[i], 1, CTM_CHANNEL_TRACE_TRIGGER)
            if sink == self.DSTREAMs[i]:
                # TPIU trigger input is CTI out 3
                return (self.OutCTIs[i], 3, CTM_CHANNEL_TRACE_TRIGGER)
            # no associated CTI
        return (None, None, None)

    def getCTIForSource(self, source):
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

    def setupSimpleSyncSMP(self):
        '''Create SMP device using RDDI synchronization'''

        # Cortex-A9x2 cluster 0 SMP
        smp = RDDISyncSMPDevice(self, "Cortex-A9 SMP 0", self.cortexA9cores[0])
        self.registerFilters(smp, 0)
        self.addDeviceInterface(smp)

        # Cortex-A9x2 cluster 1 SMP
        smp = RDDISyncSMPDevice(self, "Cortex-A9 SMP 1", self.cortexA9cores[1])
        self.registerFilters(smp, 1)
        self.addDeviceInterface(smp)

        # Cortex-A9x4 SMP
        smp = RDDISyncSMPDevice(self, "Cortex-A9 SMP ALL", self.cortexA9cores[0] + self.cortexA9cores[1])
        self.registerFilters(smp, 0)
        self.registerFilters(smp, 1)
        self.addDeviceInterface(smp)

    def setETBTraceEnabled(self, cluster, enabled):
        '''Enable/disable ETB trace capture'''
        self.enableCTIsForSink(self.ETBs[cluster], enabled)

    def setDSTREAMTraceEnabled(self, cluster, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIUs[cluster].setEnabled(enabled)
        self.enableCTIsForSink(self.ETBs[cluster], enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for i in range(0, NUM_CLUSTERS):
            for j in range(0, NUM_CORES_CORTEX_A9):
                c = (i * NUM_CLUSTERS) + j
                self.registerCoreTraceSource(traceCapture, self.cortexA9cores[i][j], self.PTMs[c])

            self.registerTraceSource(traceCapture, self.ITMs[i])

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

    def getFunnelForSource(self, source):
        '''Get the funnel for a trace source'''

        # Build map of sources to funnels
        funnelMap = {}
        for cluster in range(0, NUM_CLUSTERS):
            for core in range(0, NUM_CORES_CORTEX_A9):
                c = (cluster * NUM_CORES_CORTEX_A9) + core
                funnelMap[self.PTMs[c]] = self.Funnels[cluster]
            funnelMap[self.ITMs[cluster]] = self.Funnels[cluster]

        return funnelMap.get(source, None)

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnel ports
        portMap = {}
        for cluster in range(0, NUM_CLUSTERS):
            for core in range(0, NUM_CORES_CORTEX_A9):
                c = (cluster * NUM_CORES_CORTEX_A9) + core
                portMap[self.PTMs[c]] = self.getFunnelPortForCore(core)

            portMap[self.ITMs[cluster]] = ITM_FUNNEL_PORT

        return portMap.get(source, None)

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

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

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()

        ptmStartIndex = 0
        ptmEndIndex = 0
        for i in range(0, NUM_CLUSTERS):
            traceMode = optionValues.get("options.cluster_%d.traceCapture" % i)
            self.setManagedDevices(self.getManagedDevices(traceMode))

            coreTraceEnabled = self.getOptionValue("options.cluster_%d.cortexA9coreTrace" % i)
            for j in range(0, NUM_CORES_CORTEX_A9):
                c = (i * NUM_CORES_CORTEX_A9) + j
                thisCoreTraceEnabled = self.getOptionValue("options.cluster_%d.cortexA9coreTrace.Cortex_A9_%d" % (i, j))
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(self.PTMs[c], enableSource)
                self.setTriggerGeneratesDBGRQ(self.PTMs[c], self.getOptionValue("options.cluster_%d.cortexA9coreTrace.triggerhalt" % i))
                self.setTimestampingEnabled(self.PTMs[c], self.getOptionValue("options.cluster_%d.cortexA9coreTrace.timestamp" % i))
                self.setContextIDEnabled(self.PTMs[c],
                                     self.getOptionValue("options.cluster_%d.cortexA9coreTrace.contextIDs" % i),
                                     self.getOptionValue("options.cluster_%d.cortexA9coreTrace.contextIDs.contextIDsSize" % i))


            ptmEndIndex += NUM_CORES_CORTEX_A9
            self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A9_TRACE_OPTIONS], TraceRangeOptions("cluster_%d" % i, self), self.PTMs[ptmStartIndex:ptmEndIndex])
            ptmStartIndex += NUM_CORES_CORTEX_A9

            traceCaptureMethod = self.getOptionValue("options.cluster_%d.traceCapture" % i)
            if traceCaptureMethod == "none":
                self.setETBTraceEnabled(i, False)
                self.setDSTREAMTraceEnabled(i, False)
            elif traceCaptureMethod == "ETB_%d" % i:
                self.setETBTraceEnabled(i, True)
                self.setDSTREAMTraceEnabled(i, False)
            elif traceCaptureMethod == "DSTREAM_%d" % i:
                self.setETBTraceEnabled(i, False)
                self.setDSTREAMTraceEnabled(i, True)

            itmEnabled = self.getOptionValue("options.cluster_%d.itm" % i)
            self.setTraceSourceEnabled(self.ITMs[i], itmEnabled)


    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

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

    def registerFilters(self, core, cluster):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHBs[cluster], "AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APBs[cluster], "APB bus accessed via AP_1")])

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
        funnel = self.getFunnelForSource(source)
        port = self.getFunnelPortForSource(source)
        if enabled:
            funnel.setPortEnabled(port)
        else:
            funnel.setPortDisabled(port)

    def getFunnelPortForCore(self, core):
        ''' Funnel port-to-core mapping can be customized here'''
        # port = 5 to trace core 0
        # port = 6 to trace core 1
        port = core + 5
        return port

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


class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("cluster_0", "Cluster 0", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB_0", "On Chip Trace Buffer (ETB)")]),
                    DTSLv1.booleanOption('cortexA9coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A9_%d' % c, "Enable Cortex-A9 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_A9) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", defaultValue=False) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable PTM Timestamps", description="Controls the output of timestamps into the PTM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the output of context ID values into the PTM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ])
                            ] +
                            # Pull in common options for PTMs (cycle accurate etc)
                            PTMTraceSource.defaultOptions(DtslScript.getPTMs) +
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
                    DTSLv1.booleanOption('itm', 'Enable ITM trace', defaultValue=False),
                ]),
                DTSLv1.tabPage("cluster_1", "Cluster 1", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB_1", "On Chip Trace Buffer (ETB)")]),
                    DTSLv1.booleanOption('cortexA9coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A9_%d' % c, "Enable Cortex-A9 %d trace" % (2+c), defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_A9) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", defaultValue=False) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable PTM Timestamps", description="Controls the output of timestamps into the PTM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the output of context ID values into the PTM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ])
                            ] +
                            # Pull in common options for PTMs (cycle accurate etc)
                            PTMTraceSource.defaultOptions(DtslScript.getPTMs) +
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
                    DTSLv1.booleanOption('itm', 'Enable ITM trace', defaultValue=False),
                ])
            ])
        ]