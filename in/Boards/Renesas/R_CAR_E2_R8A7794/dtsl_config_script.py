from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource

etmDevs_cortexA7 = ["CSETM_0", "CSETM_1"]
ctiDevs_cortexA7 = ["CSCTI_4", "CSCTI_5"]
coreDevs_cortexA7 = ["Cortex-A7_0", "Cortex-A7_1"]
NUM_CORES_CORTEX_A7 = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
coresDap0 = ["Cortex-A7_0", "Cortex-A7_1"]
DSTREAM_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers

# Import core specific functions
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a7_rams

class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                            DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                                values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False)
                ])]
                +[DTSLv1.tabPage("cortexA7", "Cortex-A7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A7 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A7_%d' % core, "Enable " + coreDevs_cortexA7[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_A7) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ ETMv3_5TraceSource.cycleAccurateOption(DtslScript.getETMsForCortex_A7) ] +
                            [ ETMv3_5TraceSource.dataOption(DtslScript.getETMsForCortex_A7) ] +
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
                ])]
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer0', 'Configure the system memory trace buffer to be used by the CSTMC_2/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the CSTMC_2/ETR device',
                            defaultValue=0x00100000,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('size', 'Size in bytes',
                            description='Size of the system memory trace buffer in bytes',
                            defaultValue=0x8000,
                            isDynamic=True,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.booleanOption('scatterGather', 'Enable scatter-gather mode',
                            defaultValue=False,
                            description='When enabling scatter-gather mode, the start address of the on-chip trace buffer must point to a configured scatter-gather table')
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("stm", "STM", childOptions=[
                    DTSLv1.booleanOption('CSSTM', 'Enable CSSTM trace', defaultValue=False),
                ])]
                +[DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ])]
            )
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
        for i in range(len(self.APBs)):
            if self.APBs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.APBs[i])

        for i in range(len(self.AXIs)):
            if self.AXIs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.AXIs[i])

        self.exposeCores()

        self.traceRangeIDs = {}

        traceComponentOrder = [ self.Funnel1, self.Funnel2, self.ETF1, self.Funnel0 ]
        managedDevices = [ self.Funnel1, self.Funnel2, self.ETF1, self.Funnel0, self.OutCTI0, self.TPIU, self.ETF0Trace ]
        self.setupETFTrace(self.ETF0Trace, "CSTMC_0", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel2 ]
        managedDevices = [ self.Funnel2, self.OutCTI2, self.TPIU, self.ETF1Trace ]
        self.setupETFTrace(self.ETF1Trace, "CSTMC_1", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel2, self.ETF1 ]
        managedDevices = [ self.Funnel2, self.ETF1, self.OutCTI2, self.TPIU, self.ETR0 ]
        self.setupETRTrace(self.ETR0, "CSTMC_2", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel1, self.Funnel2, self.ETF1, self.Funnel0, self.ETF0, self.TPIU ]
        managedDevices = [ self.Funnel1, self.Funnel2, self.ETF1, self.Funnel0, self.ETF0, self.OutCTI0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH, traceComponentOrder, managedDevices)

        self.setupCTISyncSMP()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        apDevs_APBs = ["CSMEMAP_1"]
        self.APBs = []

        apDevs_AXIs = ["CSMEMAP_0"]
        self.AXIs = []

        for i in range(len(apDevs_APBs)):
            apDevice = APBAP(self, self.findDevice(apDevs_APBs[i]), "APB_%d" % i)
            self.APBs.append(apDevice)

        for i in range(len(apDevs_AXIs)):
            apDevice = AXIAP(self, self.findDevice(apDevs_AXIs[i]), "AXI_%d" % i)
            self.AXIs.append(apDevice)

        self.cortexA7cores = []

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, self.findDevice("CSCTI_0"), "CSCTI_0")

        # Trace start/stop CTI 1
        self.OutCTI1 = CSCTI(self, self.findDevice("CSCTI_2"), "CSCTI_2")

        # Trace start/stop CTI 2
        self.OutCTI2 = CSCTI(self, self.findDevice("CSCTI_3"), "CSCTI_3")

        self.CoreCTIs = []

        self.ETMs = []

        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        # STM -- CSSTM
        self.STM0 = self.createSTM("CSSTM", streamID, "CSSTM")
        streamID += 1

        #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for core in range(NUM_CORES_CORTEX_A7):
            # Create core
            coreDevice = a7_rams.A7CoreDevice(self, self.findDevice(coreDevs_cortexA7[core]), coreDevs_cortexA7[core])
            self.cortexA7cores.append(coreDevice)

            # Create CTI (if a CTI exists for this core)
            if not ctiDevs_cortexA7[core] == None:
                coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexA7[core]), ctiDevs_cortexA7[core])
                self.CoreCTIs.append(coreCTI)

            # Create ETM (if an ETM exists for this core - disabled by default - will enable with option)
            if not etmDevs_cortexA7[core] == None:
                etm = ETMv3_5TraceSource(self, self.findDevice(etmDevs_cortexA7[core]), streamID, etmDevs_cortexA7[core])
                streamID += 2
                etm.setEnabled(False)
                self.ETMs.append(etm)

        # ETF 0
        self.ETF0 = CSTMC(self, self.findDevice("CSTMC_0"), "CSTMC_0")

        # ETF 0 trace capture
        self.ETF0Trace = TMCETBTraceCapture(self, self.ETF0, "CSTMC_0")

        # ETF 1
        self.ETF1 = CSTMC(self, self.findDevice("CSTMC_1"), "CSTMC_1")

        # ETF 1 trace capture
        self.ETF1Trace = TMCETBTraceCapture(self, self.ETF1, "CSTMC_1")

        # ETR 0
        self.ETR0 = ETRTraceCapture(self, self.findDevice("CSTMC_2"), "CSTMC_2")

        # DSTREAM
        self.createDSTREAM()

        # TPIU
        self.TPIU = self.createTPIU("CSTPIU_0", "TPIU")

        # Funnel 0
        self.Funnel0 = self.createFunnel("CSTFunnel_0", "CSTFunnel_0")
        # CSTFunnel_1 is connected to CSTFunnel_0 port 2
        self.Funnel0.setPortEnabled(2)
        # CSTMC_1 is connected to CSTFunnel_0 port 5
        self.Funnel0.setPortEnabled(5)

        # Funnel 1
        self.Funnel1 = self.createFunnel("CSTFunnel_1", "CSTFunnel_1")

        # Funnel 2
        self.Funnel2 = self.createFunnel("CSTFunnel_2", "CSTFunnel_2")

    def registerFilters(self, core, dap):
        '''Register MemAP filters to allow access to the APs for the device'''
        if dap == 0:
            core.registerAddressFilters([
                AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 1 (CSMEMAP_1)"),
                AXIMemAPAccessor("AXI_0", self.AXIs[0], "AXI bus accessed via AP 0 (CSMEMAP_0)", 64),
            ])

    def exposeCores(self):
        for coreName in coresDap0:
            core = self.getDeviceInterface(coreName)
            self.registerFilters(core, 0)
            self.addDeviceInterface(core)
        for core in self.cortexA7cores:
            a7_rams.registerInternalRAMs(core)

    def setupETFTrace(self, etfTrace, name, traceComponentOrder, managedDevices):
        '''Setup ETF trace capture'''
        # Use continuous mode
        etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)

        # Register other trace components with ETF and register ETF with configuration
        etfTrace.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etfTrace)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)

    def setupETRTrace(self, etr, name, traceComponentOrder, managedDevices):
        '''Setup ETR trace capture'''
        # Use continuous mode
        etr.setFormatterMode(FormatterMode.CONTINUOUS)

        # Register other trace components with ETR and register ETR with configuration
        etr.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etr)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)

    def setupDSTREAMTrace(self, portwidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        self.TPIU.setPortSize(portwidth)

        # Configure the DSTREAM for trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.DSTREAM.setPortWidth(portwidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)


    def getCTIInfoForCore(self, core):
        '''Get the CTI info associated with a core
        return None if no associated CTI info
        '''

        # Build map of cores to DeviceCTIInfo objects
        ctiInfoMap = {}
        ctiInfoMap[self.cortexA7cores[0]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[0], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        ctiInfoMap[self.cortexA7cores[1]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[1], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)

        return ctiInfoMap.get(core, None)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sources to CTIs
        sourceCTIMap = {}
        sourceCTIMap[self.ETMs[0]] = (self.CoreCTIs[0], 6, CTM_CHANNEL_TRACE_TRIGGER)
        sourceCTIMap[self.ETMs[1]] = (self.CoreCTIs[1], 6, CTM_CHANNEL_TRACE_TRIGGER)

        return sourceCTIMap.get(source, (None, None, None))

    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sinks to CTIs
        sinkCTIMap = {}
        sinkCTIMap[self.ETF0] = (self.OutCTI0, 1, CTM_CHANNEL_TRACE_TRIGGER)
        sinkCTIMap[self.ETF1] = (self.OutCTI2, 1, CTM_CHANNEL_TRACE_TRIGGER)
        sinkCTIMap[self.ETR0] = (self.OutCTI2, 1, CTM_CHANNEL_TRACE_TRIGGER)
        sinkCTIMap[self.DSTREAM] = (self.OutCTI0, 3, CTM_CHANNEL_TRACE_TRIGGER)

        return sinkCTIMap.get(sink, (None, None, None))

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''

        # Build map of cores to trace macrocells
        coreTMMap = {}
        coreTMMap[self.cortexA7cores[0]] = self.ETMs[0]
        coreTMMap[self.cortexA7cores[1]] = self.ETMs[1]

        return coreTMMap.get(core, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, self.findDevice(tpiuDev), name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for sync start/stop
        # Cortex-A7x2 CTI SMP
        ctiInfo = {}
        for c in self.cortexA7cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)

        smp = CTISyncSMPDevice(self, "Cortex-A7x2 SMP", self.cortexA7cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp, 0)
        self.addDeviceInterface(smp)

        # Automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CoreCTIs)

    def setETFTraceEnabled(self, etfTrace, enabled):
        '''Enable/disable ETF trace capture'''
        if enabled:
            # Put the ETF in ETB mode
            etfTrace.getTMC().setMode(CSTMC.Mode.ETB)
        else:
            # Put the ETF in FIFO mode
            etfTrace.getTMC().setMode(CSTMC.Mode.ETF)

        self.enableCTIsForSink(etfTrace, enabled)

    def setETRTraceEnabled(self, etr, enabled):
        '''Enable/disable ETR trace capture'''
        if enabled:
            # Ensure TPIU is disabled
            self.TPIU.setEnabled(False)
        self.enableCTIsForSink(etr, enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for core in self.cortexA7cores:
            coreTM = self.getTMForCore(core)
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, core, coreTM)

        self.registerTraceSource(traceCapture, self.STM0)

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
        funnelMap[self.STM0] = (self.Funnel1, 0)
        funnelMap[self.ETMs[0]] = (self.Funnel2, 0)
        funnelMap[self.ETMs[1]] = (self.Funnel2, 1)

        return funnelMap.get(source, (None, None))

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        if not self.isConnected():
            self.setInitialOptions()

        self.updateDynamicOptions()

    def setInitialOptions(self):
        '''Set the initial options'''

        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.cortexA7.coreTrace")
        for core in range(NUM_CORES_CORTEX_A7):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA7.coreTrace.Cortex_A7_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexA7cores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "cortexA7")
            self.setTriggerGeneratesDBGRQ(coreTM, self.getOptionValue("options.cortexA7.coreTrace.triggerhalt"))
            self.setTimestampingEnabled(coreTM, self.getOptionValue("options.cortexA7.coreTrace.timestamp"))
            self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexA7.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexA7.coreTrace.contextIDs.contextIDsSize"))

        opt = self.getOptions().getOption("options.trace.tpiuPortWidth")
        if not opt is None:
            portWidth = self.getOptionValue("options.trace.tpiuPortWidth")
            self.TPIU.setPortSize(int(portWidth))
            self.DSTREAM.setPortWidth(int(portWidth))

        stmEnabled = self.getOptionValue("options.stm.CSSTM")
        self.setTraceSourceEnabled(self.STM0, stmEnabled)

        # Register trace sources for each trace sink
        self.registerTraceSources(self.ETF0Trace)
        self.registerTraceSources(self.ETF1Trace)
        self.registerTraceSources(self.ETR0)
        self.registerTraceSources(self.DSTREAM)

        self.setManagedDeviceList(self.getManagedDevices(traceMode))

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

        # Set up the ETR 0 buffer
        configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer0")
        if configureETRBuffer:
            scatterGatherMode = self.getOptionValue("options.ETR.etrBuffer0.scatterGather")
            bufferStart = self.getOptionValue("options.ETR.etrBuffer0.start")
            bufferSize = self.getOptionValue("options.ETR.etrBuffer0.size")
            self.ETR0.setBaseAddress(bufferStart)
            self.ETR0.setTraceBufferSize(bufferSize)
            self.ETR0.setScatterGatherModeEnabled(scatterGatherMode)

        for core in range(0, len(self.cortexA7cores)):
            a7_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA7cores[core])
            a7_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA7cores[core])

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setETFTraceEnabled(self.ETF0Trace, False)
            self.setETFTraceEnabled(self.ETF1Trace, False)
            self.setETRTraceEnabled(self.ETR0, False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "CSTMC_0":
            self.setETFTraceEnabled(self.ETF0Trace, True)
            self.setETFTraceEnabled(self.ETF1Trace, False)
            self.setETRTraceEnabled(self.ETR0, False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "CSTMC_1":
            self.setETFTraceEnabled(self.ETF0Trace, False)
            self.setETFTraceEnabled(self.ETF1Trace, True)
            self.setETRTraceEnabled(self.ETR0, False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "CSTMC_2":
            self.setETFTraceEnabled(self.ETF0Trace, False)
            self.setETFTraceEnabled(self.ETF1Trace, False)
            self.setETRTraceEnabled(self.ETR0, True)
            self.setDSTREAMTraceEnabled(False)
        elif method == "DSTREAM":
            self.setETFTraceEnabled(self.ETF0Trace, False)
            self.setETFTraceEnabled(self.ETF1Trace, False)
            self.setETRTraceEnabled(self.ETR0, False)
            self.setDSTREAMTraceEnabled(True)

    def getETMsForCortex_A7(self):
        '''Get the ETMs for Cortex-A7 cores only'''
        return [self.getTMForCore(core) for core in self.cortexA7cores]

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the list of devices managed by the configuration, as long as they are not already present'''
        for d in devs:
            if d not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(d)

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

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

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
        funnel = CSFunnel(self, self.findDevice(funnelDev), name)
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

    def createSTM(self, stmDev, streamID, name):
        stm = STMTraceSource(self, self.findDevice(stmDev), streamID, name)
        # Disabled by default - will enable with option
        stm.setEnabled(False)
        return stm

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

    def postConnect(self):
        DTSLv1.postConnect(self)

        try:
            freq = self.getOptionValue("options.trace.timestampFrequency")
        except:
            return

        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)

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

class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)")],
                        setter=DtslScript_RVI.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                ])]
                +[DTSLv1.tabPage("cortexA7", "Cortex-A7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A7 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A7_%d' % core, "Enable " + coreDevs_cortexA7[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_A7) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ ETMv3_5TraceSource.cycleAccurateOption(DtslScript.getETMsForCortex_A7) ] +
                            [ ETMv3_5TraceSource.dataOption(DtslScript.getETMsForCortex_A7) ] +
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
                ])]
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer0', 'Configure the system memory trace buffer to be used by the CSTMC_2/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the CSTMC_2/ETR device',
                            defaultValue=0x00100000,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('size', 'Size in bytes',
                            description='Size of the system memory trace buffer in bytes',
                            defaultValue=0x8000,
                            isDynamic=True,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.booleanOption('scatterGather', 'Enable scatter-gather mode',
                            defaultValue=False,
                            description='When enabling scatter-gather mode, the start address of the on-chip trace buffer must point to a configured scatter-gather table')
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("stm", "STM", childOptions=[
                    DTSLv1.booleanOption('CSSTM', 'Enable CSSTM trace', defaultValue=False),
                ])]
                +[DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ])]
            )
        ]

