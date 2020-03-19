# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceInfo
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSATBReplicator
from com.arm.debug.dtsl.components import STMTraceSource

clusterNames = ["Cortex-A57_SMP_0"]
clusterCores = [["Cortex-A57_0", "Cortex-A57_1", "Cortex-A57_2", "Cortex-A57_3"]]
coreNames_cortexR5 = ["Cortex-R5_0", "Cortex-R5_1", "Cortex-R5_2"]
coreNames_v8Generic = ["Denver 2_0", "Denver 2_1"]
coreNames_cortexA57 = ["Cortex-A57_0", "Cortex-A57_1", "Cortex-A57_2", "Cortex-A57_3"]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''

# Import core specific functions
import a57_rams


class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_ETF", "On Chip Trace Buffer (CSTMC_ETF/ETF)"), ("CSTMC_ETR", "System Memory Trace Buffer (CSTMC_ETR/ETR)")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])]
                +[DTSLv1.tabPage("cortexR5", "Cortex-R5", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R5 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_R5_0', 'Enable Cortex-R5_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex_R5_1', 'Enable Cortex-R5_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex_R5_2', 'Enable Cortex-R5_2 trace', defaultValue=True),
                            DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ETMv3_3TraceSource.cycleAccurateOption(DtslScript.getSourcesForCoreType("Cortex-R5")),
                            ETMv3_3TraceSource.dataOption(DtslScript.getSourcesForCoreType("Cortex-R5")),
                            # Trace range selection (e.g. for linux kernel)
                            DTSLv1.booleanOption('traceRange', 'Trace capture range', description=TRACE_RANGE_DESCRIPTION, defaultValue = False,
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
                +[DTSLv1.tabPage("Cortex-A57_SMP_0", "Cortex-A57", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A57 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-A57_SMP_0_0', 'Enable Cortex-A57_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A57_SMP_0_1', 'Enable Cortex-A57_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A57_SMP_0_2', 'Enable Cortex-A57_2 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A57_SMP_0_3', 'Enable Cortex-A57_3 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-A57_SMP_0")),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer0', 'Configure the system memory trace buffer to be used by the CSTMC_ETR/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the CSTMC_ETR/ETR device',
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
                +[DTSLv1.tabPage("sync", "CTI Synchronization", childOptions=[
                    DTSLv1.infoElement("Select the cores to be cross-triggered (not needed for SMP connections)"),
                    DTSLv1.booleanOption(coreNames_cortexR5[0], coreNames_cortexR5[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexR5[1], coreNames_cortexR5[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexR5[2], coreNames_cortexR5[2], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA57[0], coreNames_cortexA57[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA57[1], coreNames_cortexA57[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA57[2], coreNames_cortexA57[2], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA57[3], coreNames_cortexA57[3], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]

    def __init__(self, root):
        ConfigurationBaseSDF.__init__(self, root)

        self.discoverDevices()
        self.createTraceCapture()

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        #MemAp devices
        APBAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        AXIAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")

        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSCTI_TraceSinks"), "CSCTI_TraceSinks")



        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        stm = STMTraceSource(self, self.findDevice("CSSTM"), streamID, "CSSTM")
        stm.setEnabled(False)
        streamID += 1

        self.cortexR5cores = []
        # Ensure that macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for coreName in (coreNames_cortexR5):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-R5")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexR5cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)

            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
                self.registerCoreForCrossSync(coreDevice)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv3_3TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)

        self.v8Genericcores = []
        # Ensure that macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for coreName in (coreNames_v8Generic):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "V8-Generic")
            coreDevice.setDeviceInfo(deviceInfo)
            self.v8Genericcores.append(coreDevice)
            self.addDeviceInterface(coreDevice)

            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
                self.registerCoreForCrossSync(coreDevice)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)

        self.cortexA57cores = []
        # Ensure that macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for coreName in (coreNames_cortexA57):
            # Create core
            coreDevice = a57_rams.A57CoreDevice(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-A57")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexA57cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            a57_rams.registerInternalRAMs(coreDevice)

            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
                self.registerCoreForCrossSync(coreDevice)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)

        tmc = CSTMC(self, self.findDevice("CSTMC_ETF"), "CSTMC_ETF")
        tmc.setMode(CSTMC.Mode.ETF)

        # Create and Configure Funnels
        self.createFunnel("CSTFunnel_0")
        self.createFunnel("CSTFunnel_1")
        self.createFunnel("CSTFunnel_2")

        # Replicators
        CSATBReplicator(self, self.findDevice("CSATBReplicator"), "CSATBReplicator")


        self.setupCTISyncSMP()

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_0"), "APB bus accessed via AP 0 (CSMEMAP_0)"),
            AXIMemAPAccessor("AXI", self.getDeviceInterface("CSMEMAP_1"), "AXI bus accessed via AP 1 (CSMEMAP_1)", 64),
        ])

    def createTraceCapture(self):
        # ETF Devices
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_ETF"), "CSTMC_ETF")
        self.addTraceCaptureInterface(etfTrace)
        # ETR Capture
        self.createETRCapture()

    def createETRCapture(self):
        etr = ETRTraceCapture(self, self.findDevice("CSTMC_ETR"), "CSTMC_ETR")
        self.addTraceCaptureInterface(etr)

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

        coreTraceEnabled = self.getOptionValue("options.cortexR5.coreTrace")
        for core in range(len(coreNames_cortexR5)):
            tmName = self.getTraceSourceNameForCore(coreNames_cortexR5[core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.cortexR5.coreTrace.Cortex_R5_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                if(self.getOptionValue("options.cortexR5.coreTrace.traceRange")):
                    coreTM.clearAllTraceRanges()
                    coreTM.addTraceRange(self.getOptionValue("options.cortexR5.coreTrace.traceRange.start"),
                                         self.getOptionValue("options.cortexR5.coreTrace.traceRange.end"))
                coreTM.setTriggerGeneratesDBGRQ(self.getOptionValue("options.cortexR5.coreTrace.triggerhalt"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexR5.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexR5.coreTrace.contextIDs.contextIDsSize"))

        coreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace")
        for core in range(len(clusterCores[0])):
            tmName = self.getTraceSourceNameForCore(clusterCores[0][core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace.Cortex-A57_SMP_0_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace.contextIDs"),
                                     "32")

        stmEnabled = self.getOptionValue("options.stm.CSSTM")
        self.setTraceSourceEnabled("CSSTM", stmEnabled)

        self.configureTraceCapture(traceMode)

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

        # Set up the ETR 0 buffer
        configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer0")
        if configureETRBuffer:
            etr = self.getTraceCaptureInterfaces()["CSTMC_ETR"]
            etr.setBaseAddress(self.getOptionValue("options.ETR.etrBuffer0.start"))
            etr.setTraceBufferSize(self.getOptionValue("options.ETR.etrBuffer0.size"))
            etr.setScatterGatherModeEnabled(self.getOptionValue("options.ETR.etrBuffer0.scatterGather"))

        for core in range(len(self.cortexA57cores)):
            a57_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA57cores[core])
            a57_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA57cores[core])

        for cluster in range(len(clusterNames)):
            if not self.getDeviceInterface(clusterNames[cluster]).isConnected():
                for core in range(len(clusterCores[cluster])):
                    if self.getCTINameForCore(clusterCores[cluster][core]):
                        enable = self.getOptionValue('options.sync.%s' % clusterCores[cluster][core])
                        self.setCrossSyncEnabled(self.getDeviceInterface(clusterCores[cluster][core]), enable)

        for core in range(len(self.cortexR5cores)):
            enable = self.getOptionValue('options.sync.%s' % coreNames_cortexR5[core])
            self.setCrossSyncEnabled(self.cortexR5cores[core], enable)

    def addDeviceInterface(self, device):
        '''Add the device to the configuration and register its address filters'''
        ConfigurationBase.addDeviceInterface(self, device)
        self.registerFilters(device)

    def setTraceCaptureMethod(self, method):
        '''Simply call into the configuration to enable the trace capture device.
        CTI devices associated with the capture will also be configured'''
        self.enableTraceCapture(method)

    @staticmethod
    def getSourcesForCoreType(coreType):
        '''Get the Trace Sources for a given coreType
           Use parameter-binding to ensure that the correct Sources
           are returned for the core type passed only'''
        def getSources(self):
            return self.getTraceSourcesForCoreType(coreType)
        return getSources

    @staticmethod
    def getSourcesForCluster(cluster):
        '''Get the Trace Sources for a given coreType
           Use parameter-binding to ensure that the correct Sources
           are returned for the core type and cluster passed only'''
        def getClusterSources(self):
            return self.getTraceSourcesForCluster(cluster)
        return getClusterSources

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def postConnect(self):
        ConfigurationBaseSDF.postConnect(self)

        try:
            freq = self.getOptionValue("options.trace.timestampFrequency")
        except:
            return

        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)
