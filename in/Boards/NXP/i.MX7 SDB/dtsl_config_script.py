# Copyright (C) 2015-2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.configurations import TimestampInfo

etmDevs_cortexM4 = ["CSETM_1"]
etmDevs_cortexA7 = ["CSETM_0"]
ctiDevs_cortexM4 = ["CSCTI_2"]
ctiDevs_cortexA7 = ["CSCTI_0"]
coreDevs_cortexM4 = ["Cortex-M4"]
coreDevs_cortexA7 = ["Cortex-A7"]
NUM_CORES_CORTEX_A7 = 1
NUM_CORES_CORTEX_M4 = 1
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers

# Import core specific functions
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a7_rams

class M_Class_ETMv3_5(ETMv3_5TraceSource):
    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False

class DtslScript(DTSLv1):

    @staticmethod
    def getOptionSJCTabPage():
        return DTSLv1.tabPage("sjc", "SJC", childOptions=[
                    DTSLv1.booleanOption('sjcUnlock', 'Configure the SJC',
                                         defaultValue = False,
                                         childOptions = [
                                            DTSLv1.integerOption('key', 'SJC key',
                                                                 description='56-bit SJC unlock code',
                                                                 defaultValue=0x123456789ABCDE,
                                                                 display=IIntegerOption.DisplayFormat.HEX)
                                            ]
                                         )
                        ])

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "System Memory Trace Buffer (CSTMC_1/ETR)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                            DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                                values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False)
                ])

    @staticmethod
    def getOptionCortexA7TabPage():
        return DTSLv1.tabPage("cortexA7", "Cortex-A7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A7 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A7_%d' % core, "Enable " + coreDevs_cortexA7[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_A7) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False) ]
                        ),
                ])

    @staticmethod
    def getOptionCortexM4TabPage():
        return DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_M4_%d' % core, "Enable " + coreDevs_cortexM4[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_M4) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ]
                        ),
                    DTSLv1.booleanOption('cortexM4WakeUp', 'Release Cortex-M4 from reset', defaultValue=False,
                              description="Brings the Cortex-M4 core out of reset. Note this should be set when connecting to the Cortex-M4 for the first time after the board has been powered up.\nCaution: enabling this option on subsequent connection attempts may lead to unpredictable behaviour."),
                ])

    @staticmethod
    def getOptionETRTabPage():
        return DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer0', 'Configure the system memory trace buffer to be used by the CSTMC_1/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the CSTMC_1/ETR device',
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
                ])

    @staticmethod
    def getOptionITMTabPage():
        return DTSLv1.tabPage("itm", "ITM", childOptions=[
                    DTSLv1.booleanOption('CSITM', 'Enable CSITM trace', defaultValue=False),
                ])

    @staticmethod
    def getOptionRAMTabPage():
        return DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ])

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionSJCTabPage(),
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA7TabPage(),
                DtslScript.getOptionCortexM4TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionRAMTabPage()
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        self.unlockSJC = False
        self.keySJC = 0x00000000000000

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # Only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
        for i in range(len(self.AHBs)):
            if self.AHBs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.AHBs[i])

        for i in range(len(self.APBs)):
            if self.APBs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.APBs[i])

        for i in range(len(self.AHB_Ms)):
            if self.AHB_Ms[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.AHB_Ms[i])

        self.exposeCores()

        traceComponentOrder = [ self.Funnel0, self.Funnel2, self.Funnel1 ]
        managedDevices = [ self.Funnel0, self.Funnel2, self.Funnel1, self.OutCTI0, self.TPIU, self.ETF0Trace ]
        self.setupETFTrace(self.ETF0Trace, "CSTMC_0", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel0, self.Funnel2, self.Funnel1, self.ETF0 ]
        managedDevices = [ self.Funnel0, self.Funnel2, self.Funnel1, self.ETF0, self.TPIU, self.ETR0 ]
        self.setupETRTrace(self.ETR0, "CSTMC_1", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel0, self.Funnel2, self.Funnel1, self.ETF0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.Funnel2, self.Funnel1, self.ETF0, self.OutCTI0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(traceComponentOrder, managedDevices)

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        apDevs_AHBs = ["CSMEMAP_0"]
        self.AHBs = []

        apDevs_APBs = ["CSMEMAP_1"]
        self.APBs = []

        apDevs_AHB_Ms = ["CSMEMAP_4"]
        self.AHB_Ms = []

        for i in range(len(apDevs_AHBs)):
            apDevice = AHBAP(self, self.findDevice(apDevs_AHBs[i]), "AHB_%d" % i)
            self.AHBs.append(apDevice)

        for i in range(len(apDevs_APBs)):
            apDevice = APBAP(self, self.findDevice(apDevs_APBs[i]), "APB_%d" % i)
            self.APBs.append(apDevice)

        for i in range(len(apDevs_AHB_Ms)):
            apDevice = CortexM_AHBAP(self, self.findDevice(apDevs_AHB_Ms[i]), "AHB_M_%d" % i)
            self.AHB_Ms.append(apDevice)

        self.cortexA7cores = []

        self.cortexM4cores = []

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, self.findDevice("CSCTI_3"), "CSCTI_3")

        self.CoreCTIs = []

        self.ETMs = []

        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        # ITM 0
        self.ITM0 = self.createITM("CSITM", streamID, "CSITM")
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

        #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for core in range(NUM_CORES_CORTEX_M4):
            # Create core
            coreDevice = Device(self, self.findDevice(coreDevs_cortexM4[core]), coreDevs_cortexM4[core])
            self.cortexM4cores.append(coreDevice)

            # Create CTI (if a CTI exists for this core)
            if not ctiDevs_cortexM4[core] == None:
                coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexM4[core]), ctiDevs_cortexM4[core])
                self.CoreCTIs.append(coreCTI)

            # Create ETM (if an ETM exists for this core - disabled by default - will enable with option)
            if not etmDevs_cortexM4[core] == None:
                etm = M_Class_ETMv3_5(self, self.findDevice(etmDevs_cortexM4[core]), streamID, etmDevs_cortexM4[core])
                streamID += 2
                etm.setEnabled(False)
                self.ETMs.append(etm)

        # ETF 0
        self.ETF0 = CSTMC(self, self.findDevice("CSTMC_0"), "CSTMC_0")

        # ETF 0 trace capture
        self.ETF0Trace = TMCETBTraceCapture(self, self.ETF0, "CSTMC_0")

        # ETR 0
        self.ETR0 = ETRTraceCapture(self, self.findDevice("CSTMC_1"), "CSTMC_1")

        # DSTREAM
        self.createDSTREAM()

        # TPIU
        self.TPIU = self.createTPIU("CSTPIU_0", "TPIU")

        # Funnel 0
        self.Funnel0 = self.createFunnel("CSTFunnel_0", "CSTFunnel_0")

        # Funnel 1
        self.Funnel1 = self.createFunnel("CSTFunnel_1", "CSTFunnel_1")
        # CSTFunnel_0 is connected to CSTFunnel_1 port 0
        self.Funnel1.setPortEnabled(0)
        # CSTFunnel_2 is connected to CSTFunnel_1 port 1
        self.Funnel1.setPortEnabled(1)

        # Funnel 2
        self.Funnel2 = self.createFunnel("CSTFunnel_2", "CSTFunnel_2")

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB_0", self.AHBs[0], "AHB bus accessed via AP 0 (CSMEMAP_0)"),
            AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 1 (CSMEMAP_1)"),
        ])

    def registerMClassFilters(self, core):
        '''Register MemAP filters to allow access to the AHB_Ms for the device'''
        core.registerAddressFilters([
            AHBCortexMMemAPAccessor("AHB_M_0", self.AHB_Ms[0], "M Class AHB bus accessed via AP 4 (CSMEMAP_4)"),
        ])

    def exposeCores(self):
        for core in self.cortexA7cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)
            a7_rams.registerInternalRAMs(core)
        for core in self.cortexM4cores:
            self.registerMClassFilters(core)
            self.addDeviceInterface(core)

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

    def setupDSTREAMTrace(self, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # Configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def setPortWidth(self, portWidth):
        self.TPIU.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

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
        sinkCTIMap[self.DSTREAM] = (self.OutCTI0, 3, CTM_CHANNEL_TRACE_TRIGGER)

        return sinkCTIMap.get(sink, (None, None, None))

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''

        # Build map of cores to trace macrocells
        coreTMMap = {}
        coreTMMap[self.cortexA7cores[0]] = self.ETMs[0]
        coreTMMap[self.cortexM4cores[0]] = self.ETMs[1]

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
        for c in range(len(self.cortexA7cores)):
            coreTM = self.getTMForCore(self.cortexA7cores[c])
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexA7cores[c], coreTM)

        for c in range(len(self.cortexM4cores)):
            coreTM = self.getTMForCore(self.cortexM4cores[c])
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexM4cores[c], coreTM)

        self.registerTraceSource(traceCapture, self.ITM0)

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
        funnelMap[self.ETMs[1]] = (self.Funnel2, 0)
        funnelMap[self.ITM0] = (self.Funnel2, 1)

        return funnelMap.get(source, (None, None))

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        if not self.isConnected():
            self.setInitialOptions()

        self.updateDynamicOptions()

        self.unlockSJC = self.getOptionValue("options.sjc.sjcUnlock")
        self.keySJC = self.getOptionValue("options.sjc.sjcUnlock.key")

    def setInitialOptions(self):
        '''Set the initial options'''

        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.cortexA7.coreTrace")
        for core in range(NUM_CORES_CORTEX_A7):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA7.coreTrace.Cortex_A7_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexA7cores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setTriggerGeneratesDBGRQ(coreTM, self.getOptionValue("options.cortexA7.coreTrace.triggerhalt"))

        coreTraceEnabled = self.getOptionValue("options.cortexM4.coreTrace")
        for core in range(NUM_CORES_CORTEX_M4):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexM4.coreTrace.Cortex_M4_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexM4cores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setTimestampingEnabled(coreTM, self.getOptionValue("options.cortexM4.coreTrace.timestamp"))

        itmEnabled = self.getOptionValue("options.itm.CSITM")
        self.setTraceSourceEnabled(self.ITM0, itmEnabled)

        portWidthOpt1 = self.getOptions().getOption("options.trace.tpiuPortWidth")
        portWidthOpt2 = self.getOptions().getOption("options.trace.traceCapture.dstream.tpiuPortWidth")
        if portWidthOpt1:
            portWidth = self.getOptionValue("options.trace.tpiuPortWidth")
            self.setPortWidth(int(portWidth))
        if portWidthOpt2:
            portWidth = self.getOptionValue("options.trace.traceCapture.dstream.tpiuPortWidth")
            self.setPortWidth(int(portWidth))

        traceBufferSizeOpt = self.getOptions().getOption("options.trace.traceCapture.dstream.traceBufferSize")
        if traceBufferSizeOpt:
            traceBufferSize = self.getOptionValue("options.trace.traceCapture.dstream.traceBufferSize")
            self.setTraceBufferSize(traceBufferSize)

        # Register trace sources for each trace sink
        self.registerTraceSources(self.ETF0Trace)
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
            self.setETRTraceEnabled(self.ETR0, False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "CSTMC_0":
            self.setETFTraceEnabled(self.ETF0Trace, True)
            self.setETRTraceEnabled(self.ETR0, False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "CSTMC_1":
            self.setETFTraceEnabled(self.ETF0Trace, False)
            self.setETRTraceEnabled(self.ETR0, True)
            self.setDSTREAMTraceEnabled(False)
        elif method == "DSTREAM":
            self.setETFTraceEnabled(self.ETF0Trace, False)
            self.setETRTraceEnabled(self.ETR0, False)
            self.setDSTREAMTraceEnabled(True)

    def getETMsForCortex_A7(self):
        '''Get the ETMs for Cortex-A7 cores only'''
        return [self.getTMForCore(core) for core in self.cortexA7cores]

    def getETMsForCortex_M4(self):
        '''Get the ETMs for Cortex-M4 cores only'''
        return [self.getTMForCore(core) for core in self.cortexM4cores]

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def connectManagedDevices(self):
        if self.unlockSJC:
            code = "from LDDI import *\nfrom rvi import *\nsjcConfigured = False\ndef unlockSJC():\n    global sjcConfigured\n    if sjcConfigured:\n        return\n    JTAG_Connect()\n    JTAG_nTRST(1)\n    sleep(100)\n    JTAG_nTRST(0)\n    JTAG_ConfigScanChain(4, 0, 1, 0)\n    DAP_ID_CMD = [ 0x01 ]\n    SJC_CFG_CMD = [ 0x0D ]\n    JTAG_ScanIO(RDDI_JTAGS_IR, 5, SJC_CFG_CMD , None, RDDI_JTAGS_PIR, 1)\n    response = [ "
            for i in range(7):
                segment = "0x%02X" % (self.keySJC & 0xFF)
                code = code + segment + ", "
                self.keySJC = self.keySJC >> 8

            code = code + "0x00 ]\n    JTAG_ScanIO(RDDI_JTAGS_DR, 56, response, None, RDDI_JTAGS_RTI, 1)\n    JTAG_ConfigScanChain(0, 9, 0, 2)\n    JTAG_ScanIO(RDDI_JTAGS_IR, 4, DAP_ID_CMD, None, RDDI_JTAGS_PIR, 1)\n    rData = [ 0x00 ]\n    JTAG_ScanIO(RDDI_JTAGS_DR, 32, None, rData, RDDI_JTAGS_RTI, 1)\n    JTAG_ConfigScanChain(0, 0, 0, 0)\n    JTAG_Disconnect()\n    sjcConfigured = True\ndef HandleOpenConn(DevID,type,state):\n    if type==1:\n        unlockSJC()\n    return handleOpenConn(DevID,type,state)\n"
            self.getDebug().setConfig(0, "PythonScript", code)

        DTSLv1.connectManagedDevices(self)

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

    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, self.findDevice(itmDev), streamID, name)
        # Disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

    def postConnect(self):

        if self.getOptionValue("options.cortexM4.cortexM4WakeUp"):
            #setup CM4 code
            self.AHBs[0].writeMem(0x00180000, 0x20000000)
            self.AHBs[0].writeMem(0x00180004, 0x00000009)
            self.AHBs[0].writeMem(0x00180008, 0xe7fee7fe)

            # Release the M4
            self.AHBs[0].writeMem(0x3039000C, 0xAB)
            self.AHBs[0].writeMem(0x3039000C, 0xAA)

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

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionSJCTabPage(),
                DtslScript_DSTREAM_ST.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA7TabPage(),
                DtslScript.getOptionCortexM4TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionRAMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption(
                        'traceCapture',
                        'Trace capture method',
                        defaultValue="none",
                        values=[("none", "None"),
                                ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"),
                                ("CSTMC_1", "System Memory Trace Buffer (CSTMC_1/ETR)"),
                                (DtslScript_DSTREAM_ST.getDSTREAMOptions())],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
        ])

    @staticmethod
    def getDSTREAMOptions():
        return (
            "DSTREAM", "DSTREAM-ST Streaming Trace",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")], isDynamic=False),
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
                DtslScript.getOptionSJCTabPage(),
                DtslScript_DSTREAM_PT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA7TabPage(),
                DtslScript.getOptionCortexM4TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionRAMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption(
                        'traceCapture',
                        'Trace capture method',
                        defaultValue="none",
                        values=[("none", "None"),
                                ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"),
                                ("CSTMC_1", "System Memory Trace Buffer (CSTMC_1/ETR)"),
                                (DtslScript_DSTREAM_PT.getStoreAndForwardOptions())],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
        ])

    @staticmethod
    def getStoreAndForwardOptions():
        return (
            "DSTREAM", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="4",
                        values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False)
                ]
            )
        )

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")

class DtslScript_RVI(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionSJCTabPage(),
                DtslScript_RVI.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA7TabPage(),
                DtslScript.getOptionCortexM4TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionRAMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "System Memory Trace Buffer (CSTMC_1/ETR)")],
                        setter=DtslScript_RVI.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                ])

class DtslScript_ULINKpro(DtslScript_RVI):
    pass

class DtslScript_ULINKpro_D(DtslScript_RVI):
    pass
