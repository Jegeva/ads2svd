from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
from com.arm.rddi import RDDI_ACC_SIZE;
from java.lang import StringBuilder
from jarray import zeros

NUM_CORES_CORTEX_R5 = 1
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers

CHIP_ID__S6J311EJ = "S6J311EJ"
CHIP_ID__S6J311AH = "S6J311AH"

# Choose the CHIP ID
CHIP_ID = CHIP_ID__S6J311EJ

APB_SCCFG_UNLCK        = 0x000C01A4
APB_SCSCU_CNTL         = 0x000C01B4
SCCFG_UNLOCK           = 0x5ECACCE5
SCCFG_LOCK             = 0xA135331A
WDGRST_MASK           = 0x00000100


SYSTEM_RAM_START_ADDRESS       =     0x02000000
SYSTEM_RAM_SIZE_BYTES          =     {
                                    CHIP_ID__S6J311EJ    :     256*1024,
                                    CHIP_ID__S6J311AH    :     16*1024,
                                }

# TCMRAM related definitions
TCMRAM_START_ADDRESS           =     0x00000000
TCMRAM_SIZE_BYTES              =     {
                                    CHIP_ID__S6J311EJ    :    64*1024,
                                    CHIP_ID__S6J311AH    :    64*1024,
                                }


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB0", "On Chip Trace Buffer (ETB0)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                ]),
                DTSLv1.tabPage("cortexR5", "Cortex-R5", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R5 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_R5_%d' % c, "Enable Cortex-R5 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_R5) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ ETMv3_3TraceSource.cycleAccurateOption(DtslScript.getETMsForCortex_R5) ] +
                            [ ETMv3_3TraceSource.dataOption(DtslScript.getETMsForCortex_R5) ] +
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
                DTSLv1.tabPage("RAMWatchdogInit", "Watchdog disable", childOptions=[
                    DTSLv1.booleanOption('disableHWWatchdog', 'Disable HW Watchdog', defaultValue=True)
                ]),
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # Only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
        if self.AHB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.AHB)
        if self.APB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.APB)

        self.exposeCores()

        self.traceRangeIDs = {}

        traceComponentOrder = [ self.Funnel0 ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.ETB0 ]
        self.setupETBTrace(self.ETB0, "ETB0", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH, traceComponentOrder, managedDevices)

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        memApDev = 0

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.AHB = AHBAP(self, memApDev, "AHB")

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.APB = APBAP(self, memApDev, "APB")

        cortexR5coreDevs = [9]
        self.cortexR5cores = []

        streamID = 1

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, 6, "OutCTI0")

        coreCTIDevs = []
        self.CoreCTIs = []

        etmDevs = [10]
        self.ETMs = []

        for i in range(0, NUM_CORES_CORTEX_R5):
            # Create core
            core = Device(self, cortexR5coreDevs[i], "Cortex-R5")
            self.cortexR5cores.append(core)

        for i in range(0, len(coreCTIDevs)):
            # Create CTI
            coreCTI = CSCTI(self, coreCTIDevs[i], "CoreCTIs[%d]" % i)
            self.CoreCTIs.append(coreCTI)

        for i in range(0, len(etmDevs)):
            # Create ETM
            etm = self.createETM(etmDevs[i], streamID, "ETMs[%d]" % i)
            streamID += 1

        # ETB 0
        self.ETB0 = ETBTraceCapture(self, 5, "ETB0")

        # DSTREAM
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

        # TPIU
        self.TPIU = self.createTPIU(7, "TPIU")

        # Funnel 0
        self.Funnel0 = self.createFunnel(8, "Funnel0")

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP"),
            AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP"),
        ])

    def exposeCores(self):
        for core in self.cortexR5cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def setupETBTrace(self, etb, name, traceComponentOrder, managedDevices):
        '''Setup ETB trace capture'''
        # Use continuous mode
        etb.setFormatterMode(FormatterMode.CONTINUOUS)

        # Register other trace components with ETB and register ETB with configuration
        etb.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etb)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)

    def setupDSTREAMTrace(self, portwidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        self.TPIU.setPortSize(portwidth)

        # Configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.DSTREAM.setPortWidth(portwidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sources to CTIs
        sourceCTIMap = {}

        return sourceCTIMap.get(source, (None, None, None))

    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sinks to CTIs
        sinkCTIMap = {}
        sinkCTIMap[self.ETB0] = (self.OutCTI0, 1, CTM_CHANNEL_TRACE_TRIGGER)
        sinkCTIMap[self.DSTREAM] = (self.OutCTI0, 3, CTM_CHANNEL_TRACE_TRIGGER)

        return sinkCTIMap.get(sink, (None, None, None))

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''

        # Build map of cores to trace macrocells
        coreTMMap = {}
        coreTMMap[self.cortexR5cores[0]] = self.ETMs[0]

        return coreTMMap.get(core, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createETM(self, etmDev, streamID, name):
        '''Create ETM of correct version'''
        if etmDev == 10:
            etm = ETMv3_3TraceSource(self, etmDev, streamID, name)
            # Disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            return etm

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setETBTraceEnabled(self, etb, enabled):
        '''Enable/disable ETB trace capture'''
        self.enableCTIsForSink(etb, enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_R5):
            coreTM = self.getTMForCore(self.cortexR5cores[c])
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexR5cores[c], coreTM)


    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # Source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

        # CTI (if present) is also managed by the configuration
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.addManagedTraceDevices(traceCapture.getName(), [ cti ])

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnels and funnel ports
        funnelMap = {}
        funnelMap[self.ETMs[0]] = (self.Funnel0, 0)

        return funnelMap.get(source, (None, None))

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def disableHWWatchdog(self):
        self.APB.writeMem(APB_SCCFG_UNLCK, SCCFG_UNLOCK)   # Unlock
        self.APB.writeMem(APB_SCSCU_CNTL,  WDGRST_MASK)    # Set watchdog mask
        self.APB.writeMem(APB_SCCFG_UNLCK, SCCFG_LOCK)     # Lock again


    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        if not self.isConnected():
            self.setInitialOptions()
        self.updateDynamicOptions()

    def setInitialOptions(self):
        '''Set the initial options'''

        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.cortexR5.coreTrace")
        for i in range(0, NUM_CORES_CORTEX_R5):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexR5.coreTrace.Cortex_R5_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexR5cores[i])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "cortexR5")
            self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexR5.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexR5.coreTrace.contextIDs.contextIDsSize"))

        # Register trace sources for each trace sink
        self.registerTraceSources(self.ETB0)
        self.registerTraceSources(self.DSTREAM)

        self.setManagedDeviceList(self.getManagedDevices(traceMode))

    def connectManagedDevices(self):
        # Stop Cortex-R5 as soon as possible to allow connection
        # of trace devices else the connection will fail due to a watchdog reset
        # taking place during the connection process
        if (self.getOptionValue("options.RAMWatchdogInit.disableHWWatchdog")):
            # Force stop, otherwise the part has the potential to reset continually
            # removing any initialisation performed
            sb = StringBuilder()
            self.APB.openConn(zeros(1, 'i'), zeros(1, 'i'), StringBuilder(1024))
            self.APB.writeMem(0x80090090, 1) # Cortex-R5 DSCTRL
            self.disableHWWatchdog()
            self.APB.closeConn()

        DTSLv1.connectManagedDevices(self)


    def postConnect(self):
        DTSLv1.postConnect(self)

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setETBTraceEnabled(self.ETB0, False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "ETB0":
            self.setETBTraceEnabled(self.ETB0, True)
            self.setDSTREAMTraceEnabled(False)
        elif method == "DSTREAM":
            self.setETBTraceEnabled(self.ETB0, False)
            self.setDSTREAMTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def getETMsForCortex_R5(self):
        '''Get the ETMs for Cortex-R5 cores only'''
        return [self.getTMForCore(core) for core in self.cortexR5cores]

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def registerTraceSource(self, traceCapture, source):
        '''Register trace source with trace capture device'''
        traceCapture.addTraceSource(source)
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

    def addManagedTraceDevices(self, traceKey, devs):
        '''Add devices to the set of devices managed by the configuration for this trace mode'''
        traceDevs = self.mgdTraceDevs.get(traceKey)
        if not traceDevs:
            traceDevs = []
            self.mgdTraceDevs[traceKey] = traceDevs
        for d in devs:
            if d not in traceDevs:
                traceDevs.append(d)

    def setInternalTraceRange(self, coreTM, coreName):

        traceRangeEnable = self.getOptionValue("options.%s.coreTrace.traceRange" % coreName)
        traceRangeStart = self.getOptionValue("options.%s.coreTrace.traceRange.start" % coreName)
        traceRangeEnd = self.getOptionValue("options.%s.coreTrace.traceRange.end" % coreName)

        if coreTM in self.traceRangeIDs:
            coreTM.clearTraceRange(self.traceRangeIDs[coreTM])
            del self.traceRangeIDs[coreTM]

        if traceRangeEnable:
            self.traceRangeIDs[coreTM] = coreTM.addTraceRange(traceRangeStart, traceRangeEnd)

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.enableCTIInput(cti, input, channel, enabled)

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
        funnel, port = self.getFunnelPortForSource(source)
        if funnel:
            if enabled:
                funnel.setPortEnabled(port)
            else:
                funnel.setPortDisabled(port)

    def setContextIDEnabled(self, xtm, state, size):
        if state == False:
            xtm.setContextIDs(False, IARMCoreTraceSource.ContextIDSize.NONE)
        else:
            contextIDSizeMap = {
                 "8":IARMCoreTraceSource.ContextIDSize.BITS_7_0,
                "16":IARMCoreTraceSource.ContextIDSize.BITS_15_0,
                "32":IARMCoreTraceSource.ContextIDSize.BITS_31_0 }
            xtm.setContextIDs(True, contextIDSizeMap[size])

class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB0", "On Chip Trace Buffer (ETB0)")],
                        setter=DtslScript_RVI.setTraceCaptureMethod),
                ]),
                DTSLv1.tabPage("cortexR5", "Cortex-R5", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R5 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_R5_%d' % c, "Enable Cortex-R5 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_R5) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ ETMv3_3TraceSource.cycleAccurateOption(DtslScript.getETMsForCortex_R5) ] +
                            [ ETMv3_3TraceSource.dataOption(DtslScript.getETMsForCortex_R5) ] +
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


