# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceInfo
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMHTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl.components import CSDAP
from jarray import zeros
from struct import unpack
import hsstp_usecase

clusterNames = ["Cortex-A53_SMP_0", "Cortex-A57_SMP_0"]
clusterCores = [["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"], ["Cortex-A57_0", "Cortex-A57_1"]]
coreNames_cortexA57 = ["Cortex-A57_0", "Cortex-A57_1"]
coreNames_cortexR7 = ["Cortex-R7"]
coreNames_cortexA53 = ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
blCores = [["Cortex-A57_0", "Cortex-A57_1"], ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''

# Import core specific functions
import a57_rams
import a53_rams

class DSTREAMHTTraceCapture(DSTREAMHTStoreAndForwardTraceCapture):

    def __init__(self, configuration, name, memAccessDevice):
        DSTREAMHTStoreAndForwardTraceCapture.__init__(self, configuration, name)
        self.memAccessDevice = memAccessDevice
        self.configuration = configuration

    def postConnect(self):
        # Do target setup and wait for HSSTP link to train
        DSTREAMHTStoreAndForwardTraceCapture.postConnect(self)
        hsstp_usecase.configureLink(self)


class DSTREAMHSSTPTraceCapture(DSTREAMTraceCapture):

    def __init__(self, configuration, name, memAccessDevice):
        DSTREAMTraceCapture.__init__(self, configuration, name)
        self.memAccessDevice = memAccessDevice
        self.configuration = configuration
        self.traceConn = None
        self.trace = None

    def postConnect(self):
        # Do target setup and wait for HSSTP link to train polling extended probe status
        # using trace transaction call
        DSTREAMTraceCapture.postConnect(self)
        hsstp_usecase.configureLink(self)

    def isProbeLinkUp(self):
        # No way to query the HSSTP so assume not up
        if not self.traceConn:
            return False
        # Do GetExtendedStatus command
        transactionCommand = zeros(1, 'b')
        transactionCommand[0] = 1 # 1 - TRACE_EXTENDED_STATUS_TRANSACTION
        dataOut = zeros(4, 'b')
        dataOutLen = zeros(1, 'i')
        self.trace.transaction(self.traceConn, transactionCommand, dataOut, dataOutLen)
        value = unpack('I', dataOut)[0]
        if value & 0x30000000 != 0x30000000:
            return False
        return True

class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexR7TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCortexA57TabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionCacheRAMsTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSD-ETF", "On Chip Trace Buffer (CSD-ETF/ETF)"), ("A57CA-ETF", "On Chip Trace Buffer (A57CA-ETF/ETF)"), ("R7CA-ETF", "On Chip Trace Buffer (R7CA-ETF/ETF)"), ("A53CA-ETF", "On Chip Trace Buffer (A53CA-ETF/ETF)")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ])
                ])

    @staticmethod
    def getOptionCortexR7TabPage():
        return DTSLv1.tabPage("cortexR7", "Cortex-R7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R7 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_R7_0', 'Enable Cortex-R7 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCoreType("cortexR7")),
                            ETMv4TraceSource.dataOption(DtslScript.getSourcesForCoreType("cortexR7")),
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
                ])

    @staticmethod
    def getOptionCortexA53TabPage():
        return DTSLv1.tabPage("Cortex-A53_SMP_0", "Cortex-A53", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A53 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-A53_SMP_0_0', 'Enable Cortex-A53_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A53_SMP_0_1', 'Enable Cortex-A53_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A53_SMP_0_2', 'Enable Cortex-A53_2 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A53_SMP_0_3', 'Enable Cortex-A53_3 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-A53_SMP_0")),
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
                ])

    @staticmethod
    def getOptionCortexA57TabPage():
        return DTSLv1.tabPage("Cortex-A57_SMP_0", "Cortex-A57", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A57 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-A57_SMP_0_0', 'Enable Cortex-A57_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A57_SMP_0_1', 'Enable Cortex-A57_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-A57_SMP_0")),
                        ]
                    ),
                ])

    @staticmethod
    def getOptionSTMTabPage():
        return DTSLv1.tabPage("stm", "STM", childOptions=[
                    DTSLv1.booleanOption('CSD-STM', 'Enable CSD-STM trace', defaultValue=False),
                ])

    @staticmethod
    def getOptionCacheRAMsTabPage():
        return DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ])

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
        self.AXIAP = AXIAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        APBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")

        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSD-CTI_0"), "CSD-CTI_0")

        CSCTI(self, self.findDevice("A57CA-CTI"), "A57CA-CTI")

        CSCTI(self, self.findDevice("R7CA-CTI"), "R7CA-CTI")

        CSCTI(self, self.findDevice("A53CA-CTI"), "A53CA-CTI")



        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        stm = STMTraceSource(self, self.findDevice("CSD-STM"), streamID, "CSD-STM")
        stm.setEnabled(False)
        streamID += 1

        self.cortexR7cores = []
        for coreName in (coreNames_cortexR7):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-R7")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexR7cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)

            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)

        self.cortexA57cores = []
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

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)

        self.cortexA53cores = []
        for coreName in (coreNames_cortexA53):
            # Create core
            coreDevice = a53_rams.A53CoreDevice(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-A53")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexA53cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            a53_rams.registerInternalRAMs(coreDevice)

            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)

        tmc = CSTMC(self, self.findDevice("CSD-ETF"), "CSD-ETF")
        tmc.setMode(CSTMC.Mode.ETF)

        tmc = CSTMC(self, self.findDevice("A57CA-ETF"), "A57CA-ETF")
        tmc.setMode(CSTMC.Mode.ETF)

        tmc = CSTMC(self, self.findDevice("R7CA-ETF"), "R7CA-ETF")
        tmc.setMode(CSTMC.Mode.ETF)

        tmc = CSTMC(self, self.findDevice("A53CA-ETF"), "A53CA-ETF")
        tmc.setMode(CSTMC.Mode.ETF)

        # 'CSD-TPIU' is the main TPIU that we want to use for off-chip trace
        csdTPIU = CSTPIU(self, self.findDevice("CSD-TPIU"), "CSD-TPIU")
        csdTPIU.setEnabled(False)
        csdTPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # We don't care about these other TPIUs, but we need to have them as managed devices
        # to ensure they get turned off during connection.
        a57TPIU = CSTPIU(self, self.findDevice("A57CA-TPI"), "A57CA-TPI")
        a57TPIU.setEnabled(False)
        self.addManagedDevice(a57TPIU)

        r7TPIU = CSTPIU(self, self.findDevice("R7CA-TPIU"), "R7CA-TPIU")
        r7TPIU.setEnabled(False)
        self.addManagedDevice(r7TPIU)

        a53TPIU = CSTPIU(self, self.findDevice("A53CA-TPIU"), "A53CA-TPIU")
        a53TPIU.setEnabled(False)
        self.addManagedDevice(a53TPIU)


        # Create and Configure Funnels
        self.createFunnel("CSD-FUNNEL")
        self.createFunnel("A57CA-FUNNEL")
        self.createFunnel("R7CA-FUNNEL")
        self.createFunnel("A53CA-FUNNEL")

        self.setupCTISyncSMP()
        self.setupCTISyncBigLittle(blCores)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_1"), "APB bus accessed via AP 1 (CSMEMAP_1)"),
            AXIMemAPAccessor("AXI", self.getDeviceInterface("CSMEMAP_0"), "AXI bus accessed via AP 0 (CSMEMAP_0)", 64),
        ])

    def createTraceCapture(self):
        # ETF Devices
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSD-ETF"), "CSD-ETF")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("A57CA-ETF"), "A57CA-ETF")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("R7CA-ETF"), "R7CA-ETF")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("A53CA-ETF"), "A53CA-ETF")
        self.addTraceCaptureInterface(etfTrace)
        # DSTREAM
        self.createDSTREAM()
        self.addTraceCaptureInterface(self.DSTREAM)

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

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

        coreTraceEnabled = self.getOptionValue("options.cortexR7.coreTrace")
        for core in range(len(coreNames_cortexR7)):
            tmName = self.getTraceSourceNameForCore(coreNames_cortexR7[core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.cortexR7.coreTrace.Cortex_R7_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                if(self.getOptionValue("options.cortexR7.coreTrace.traceRange")):
                    coreTM.clearAllTraceRanges()
                    coreTM.addTraceRange(self.getOptionValue("options.cortexR7.coreTrace.traceRange.start"),
                                         self.getOptionValue("options.cortexR7.coreTrace.traceRange.end"))
                coreTM.setTimestampingEnabled(self.getOptionValue("options.cortexR7.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexR7.coreTrace.contextIDs"),
                                     "32")

        coreTraceEnabled = self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace")
        for core in range(len(clusterCores[0])):
            tmName = self.getTraceSourceNameForCore(clusterCores[0][core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.Cortex-A53_SMP_0_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                if(self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.traceRange")):
                    coreTM.clearAllTraceRanges()
                    coreTM.addTraceRange(self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.traceRange.start"),
                                         self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.traceRange.end"))
                coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.contextIDs"),
                                     "32")

        coreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace")
        for core in range(len(clusterCores[1])):
            tmName = self.getTraceSourceNameForCore(clusterCores[1][core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace.Cortex-A57_SMP_0_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace.contextIDs"),
                                     "32")

        if self.getOptions().getOption("options.trace.offChip.tpiuPortWidth"):
            self.setPortWidth(int(self.getOptionValue("options.trace.offChip.tpiuPortWidth")))

        if self.getOptions().getOption("options.trace.offChip.traceBufferSize"):
            self.setTraceBufferSize(self.getOptionValue("options.trace.offChip.traceBufferSize"))

        stmEnabled = self.getOptionValue("options.stm.CSD-STM")
        self.setTraceSourceEnabled("CSD-STM", stmEnabled)

        traceMode = self.getOptionValue("options.trace.traceCapture")
        self.configureTraceCapture(traceMode)

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

        for core in range(len(self.cortexA57cores)):
            a57_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA57cores[core])
            a57_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA57cores[core])

        for core in range(len(self.cortexA53cores)):
            a53_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA53cores[core])
            a53_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA53cores[core])

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

    def reset(self, device):
        Device.systemReset(device, 0);
        self.powerUpClusters()
        ConfigurationBaseSDF.postConnect(self)

    def postDebugConnect(self):
        self.powerUpClusters()
        ConfigurationBaseSDF.postDebugConnect(self)


    def powerUpClusters(self):
        dapDev  = self.findDevice("ARMCS-DP", 1)

        dap = CSDAP(self, dapDev, "DAP")
        self.powerUpDap(dap)

        # CPG Write Protect Register
        CPGWPR = 0xE6150900
        # CPG Write Protect Control Register
        CPGWPCR = 0xE6150904

        # Cortex-A57 Reset Control Register
        CA57RESCNT  = 0xE6160040
        # Bring A57 cores out of reset
        CA57ENABLE = 0xA5A50000
        # A57 wake up control register
        CA57WUPCR = 0xE6152010
        # A57 power on
        CA57PWRON = 0xE61801CC

        #Cortex-A53 Reset Control Register
        CA53RESCNT = 0xE6160044
        # Bring A53 cores out of reset
        CA53ENABLE = 0x5A5A0000
        # A53 wake up control register
        CA53WUPCR = 0xE6151010
        # A53 power on
        CA53PWRON = 0xE618014C

        #Power and wake up R7 devices
        dap.writeMem(0, CPGWPR, 0x5A5AFFFF)
        dap.writeMem(0, CPGWPCR, 0xA5A50000)
        dap.writeMem(0, 0xE618024C, 0x1)

        # Power and wake up A57 devices
        dap.writeMem(0, CPGWPR, 0x5A5AFFFF)
        dap.writeMem(0, CPGWPCR, 0xA5A50000)
        dap.writeMem(0, CA57PWRON, 0x1)
        dap.writeMem(0, CA57WUPCR, 0xF)
        dap.writeMem(0, CA57RESCNT, CA57ENABLE)

        #Power and wake up A53 devices
        dap.writeMem(0, CPGWPR, 0x5A5AFFFF)
        dap.writeMem(0, CPGWPCR, 0xA5A50000)
        dap.writeMem(0, CA53PWRON, 0x1)
        dap.writeMem(0, CA53WUPCR, 0xF)
        dap.writeMem(0, CA53RESCNT, CA53ENABLE)

        self.fixA57ETMSync(dap)
        dap.closeConn()

    def powerUpDap(self, dap):
        DP_OFFSET = 0x2080;
        DP_CTRL_STAT   = DP_OFFSET + 1

        if not dap.isConnected():
            dap.openConn(None,None,None)

        value = dap.readRegister(DP_CTRL_STAT)

        if not (value & 0x20000000):
            value |= 0x50000000
            dap.writeRegister(DP_CTRL_STAT, value)

            for i in range(100):
                value = dap.readRegister(DP_CTRL_STAT)
                if (value & 0x20000000):
                    break
                # DAP powered

    def fixA57ETMSync(self, dap):
        ' Assume DAP powered up'
        dap.writeMem(0, 0xEA0F0FB0, 0xC5ACCE55)
        dap.writeMem(0, 0xEA0F0100, 0x00000200)
        dap.writeMem(0, 0xEA0F0100, 0x00000201)


    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def postConnect(self):
        ConfigurationBaseSDF.postConnect(self)

        try:
            freq = self.getOptionValue("options.trace.traceOpts.timestampFrequency")
        except:
            return

        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)


class DtslScript_HSSTP(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_HSSTP.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexR7TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCortexA57TabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionCacheRAMsTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSD-ETF", "On Chip Trace Buffer (CSD-ETF/ETF)"), ("A57CA-ETF", "On Chip Trace Buffer (A57CA-ETF/ETF)"), ("R7CA-ETF", "On Chip Trace Buffer (R7CA-ETF/ETF)"), ("A53CA-ETF", "On Chip Trace Buffer (A53CA-ETF/ETF)"), ("DSTREAM", "DSTREAM HSSTP 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                            values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False),
                    ]),
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMHSSTPTraceCapture(self, "DSTREAM", self.AXIAP)


class DtslScript_DSTREAM_HT(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_HT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexR7TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCortexA57TabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionCacheRAMsTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSD-ETF", "On Chip Trace Buffer (CSD-ETF/ETF)"), ("A57CA-ETF", "On Chip Trace Buffer (A57CA-ETF/ETF)"), ("R7CA-ETF", "On Chip Trace Buffer (R7CA-ETF/ETF)"), ("A53CA-ETF", "On Chip Trace Buffer (A53CA-ETF/ETF)"), ("DSTREAM", "DSTREAM-HT 8GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                            values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False),
                    ]),
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMHTTraceCapture(self, "DSTREAM", self.AXIAP)

    def createTraceCapture(self):
        DtslScript.createTraceCapture(self)
        self.addStreamTraceCaptureInterface(self.DSTREAM)


