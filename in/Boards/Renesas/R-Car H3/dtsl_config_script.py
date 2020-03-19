# Copyright (C) 2016-2019 Arm Limited (or its affiliates). All rights reserved.
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
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMHTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import DeviceCluster
from com.arm.debug.dtsl.components import DeviceInfo
from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
import hsstp_usecase

tmDevs_cortexA53 = ["A53MP-ETM_0", "A53MP-ETM_1", "A53MP-ETM_2", "A53MP-ETM_3"]
tmDevs_cortexR7 = ["R7MP-ETM"]
tmDevs_cortexA57 = ["A57MP-ETM_0", "A57MP-ETM_1", "A57MP-ETM_2", "A57MP-ETM_3"]
ctiDevs_cortexA53 = ["A53MP-CTI_0", "A53MP-CTI_1", "A53MP-CTI_2", "A53MP-CTI_3"]
ctiDevs_cortexR7 = ["R7MP-CTI"]
ctiDevs_cortexA57 = ["A57MP-CTI_0", "A57MP-CTI_1", "A57MP-CTI_2", "A57MP-CTI_3"]
coreDevs_cortexA53 = ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
coreDevs_cortexR7 = ["Cortex-R7"]
coreDevs_cortexA57 = ["Cortex-A57_0", "Cortex-A57_1", "Cortex-A57_2", "Cortex-A57_3"]
NUM_CORES_CORTEX_A57 = 4
NUM_CORES_CORTEX_R7 = 1
NUM_CORES_CORTEX_A53 = 4
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
coresDap0 = ["Cortex-A57_0", "Cortex-A57_1", "Cortex-A57_2", "Cortex-A57_3", "Cortex-R7", "Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
DSTREAM_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 2  # Use channel 2 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 3  # Use channel 3 for trace triggers

# Import core specific functions
import a57_rams
import a53_rams

class ResetHookedA57Core(a57_rams.A57CoreDevice):
    def __init__(self, config, id, name):
        a57_rams.A57CoreDevice.__init__(self, config, id, name)
        self.parent = config

    def systemReset(self, resetType):
        # reset via reset controller
        self.parent.reset(self)

class ResetHookedA53Core(a53_rams.A53CoreDevice):
    def __init__(self, config, id, name):
        a53_rams.A53CoreDevice.__init__(self, config, id, name)
        self.parent = config

    def systemReset(self, resetType):
        # reset via reset controller
        self.parent.reset(self)

class ResetHookedCore(Device):
    def __init__(self, config, id, name):
        Device.__init__(self, config, id, name)
        self.parent = config

    def systemReset(self, resetType):
        # reset via reset controller
        self.parent.reset(self)

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


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA57TabPage(),
                DtslScript.getOptionCortexR7TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
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
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency.")
                ])

    @staticmethod
    def getOptionCortexA57TabPage():
        return DTSLv1.tabPage("cortexA57", "Cortex-A57", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A57 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A57_%d' % core, "Enable " + coreDevs_cortexA57[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_A57) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ ETMv4TraceSource.cycleAccurateOption(DtslScript.getTraceMacrocellsForCoreType("cortexA57"))]
                        ),
                ])

    @staticmethod
    def getOptionCortexR7TabPage():
        return DTSLv1.tabPage("cortexR7", "Cortex-R7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R7 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_R7_%d' % core, "Enable " + coreDevs_cortexR7[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_R7) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ ETMv4TraceSource.cycleAccurateOption(DtslScript.getTraceMacrocellsForCoreType("cortexR7"))] +
                            [ ETMv4TraceSource.dataOption(DtslScript.getTraceMacrocellsForCoreType("cortexR7"))] +
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

    @staticmethod
    def getOptionCortexA53TabPage():
        return DTSLv1.tabPage("cortexA53", "Cortex-A53", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A53 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A53_%d' % core, "Enable " + coreDevs_cortexA53[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_A53) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ ETMv4TraceSource.cycleAccurateOption(DtslScript.getTraceMacrocellsForCoreType("cortexA53"))] +
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

        traceComponentOrder = [ self.Funnel1, self.ETF1, self.Funnel2, self.ETF2, self.Funnel3, self.ETF3, self.Funnel0 ]
        managedDevices = [ self.Funnel1, self.ETF1, self.Funnel2, self.ETF2, self.Funnel3, self.ETF3, self.Funnel0, self.OutCTI0, self.csdTPIU, self.a57TPIU, self.r7TPIU, self.a53TPIU, self.ETF0Trace ]
        self.setupETFTrace(self.ETF0Trace, "CSD-ETF", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel1 ]
        managedDevices = [ self.Funnel1, self.OutCTI1, self.csdTPIU, self.a57TPIU, self.r7TPIU, self.a53TPIU, self.ETF1Trace ]
        self.setupETFTrace(self.ETF1Trace, "A57CA-ETF", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel2 ]
        managedDevices = [ self.Funnel2, self.OutCTI2, self.csdTPIU, self.a57TPIU, self.r7TPIU, self.a53TPIU, self.ETF2Trace ]
        self.setupETFTrace(self.ETF2Trace, "R7CA-ETF", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel3 ]
        managedDevices = [ self.Funnel3, self.OutCTI3, self.csdTPIU, self.a57TPIU, self.r7TPIU, self.a53TPIU, self.ETF3Trace ]
        self.setupETFTrace(self.ETF3Trace, "A53CA-ETF", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel1, self.ETF1, self.Funnel2, self.ETF2, self.Funnel3, self.ETF3, self.Funnel0, self.ETF0, self.csdTPIU, self.a57TPIU, self.r7TPIU, self.a53TPIU ]
        managedDevices = [ self.Funnel1, self.ETF1, self.Funnel2, self.ETF2, self.Funnel3, self.ETF3, self.Funnel0, self.ETF0, self.OutCTI0, self.csdTPIU, self.a57TPIU, self.r7TPIU, self.a53TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH, traceComponentOrder, managedDevices)

        self.setupCTISyncSMP()

        self.setupBigLittle()

        self.setManagedDeviceList(self.mgdPlatformDevs)

        self.setETFTraceEnabled(self.ETF0Trace, False)
        self.setETFTraceEnabled(self.ETF1Trace, False)
        self.setETFTraceEnabled(self.ETF2Trace, False)
        self.setETFTraceEnabled(self.ETF3Trace, False)
        self.setDSTREAMTraceEnabled(False)

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

        self.cortexA57cores = []

        self.cortexR7cores = []

        self.cortexA53cores = []

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, self.findDevice("CSD-CTI_0"), "CSD-CTI_0")

        # Trace start/stop CTI 1
        self.OutCTI1 = CSCTI(self, self.findDevice("A57CA-CTI"), "A57CA-CTI")

        # Trace start/stop CTI 2
        self.OutCTI2 = CSCTI(self, self.findDevice("R7CA-CTI"), "R7CA-CTI")

        # Trace start/stop CTI 3
        self.OutCTI3 = CSCTI(self, self.findDevice("A53CA-CTI"), "A53CA-CTI")

        self.CoreCTIs = []

        self.macrocells = {}
        self.macrocells["cortexA57"] = []
        self.macrocells["cortexR7"] = []
        self.macrocells["cortexA53"] = []

        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        # STM -- CSD-STM
        self.STM0 = self.createSTM("CSD-STM", streamID, "CSD-STM")
        streamID += 1

        #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for core in range(NUM_CORES_CORTEX_R7):
            # Create core
            coreDevice = ResetHookedCore(self, self.findDevice(coreDevs_cortexR7[core]), coreDevs_cortexR7[core])
            deviceInfo = DeviceInfo("core", "Cortex-R7")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexR7cores.append(coreDevice)

            # Create CTI (if a CTI exists for this core)
            if not ctiDevs_cortexR7[core] == None:
                coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexR7[core]), ctiDevs_cortexR7[core])
                self.CoreCTIs.append(coreCTI)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            if not tmDevs_cortexR7[core] == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmDevs_cortexR7[core]), streamID, tmDevs_cortexR7[core])
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["cortexR7"].append(tm)

        #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for core in range(NUM_CORES_CORTEX_A57):
            # Create core
            coreDevice = ResetHookedA57Core(self, self.findDevice(coreDevs_cortexA57[core]), coreDevs_cortexA57[core])
            deviceInfo = DeviceInfo("core", "Cortex-A57")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexA57cores.append(coreDevice)

            # Create CTI (if a CTI exists for this core)
            if not ctiDevs_cortexA57[core] == None:
                coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexA57[core]), ctiDevs_cortexA57[core])
                self.CoreCTIs.append(coreCTI)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            if not tmDevs_cortexA57[core] == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmDevs_cortexA57[core]), streamID, tmDevs_cortexA57[core])
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["cortexA57"].append(tm)

        #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for core in range(NUM_CORES_CORTEX_A53):
            # Create core
            coreDevice = ResetHookedA53Core(self, self.findDevice(coreDevs_cortexA53[core]), coreDevs_cortexA53[core])
            deviceInfo = DeviceInfo("core", "Cortex-A53")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexA53cores.append(coreDevice)

            # Create CTI (if a CTI exists for this core)
            if not ctiDevs_cortexA53[core] == None:
                coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexA53[core]), ctiDevs_cortexA53[core])
                self.CoreCTIs.append(coreCTI)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            if not tmDevs_cortexA53[core] == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmDevs_cortexA53[core]), streamID, tmDevs_cortexA53[core])
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["cortexA53"].append(tm)

        # ETF 0
        self.ETF0 = CSTMC(self, self.findDevice("CSD-ETF"), "CSD-ETF")

        # ETF 0 trace capture
        self.ETF0Trace = TMCETBTraceCapture(self, self.ETF0, "CSD-ETF")

        # ETF 1
        self.ETF1 = CSTMC(self, self.findDevice("A57CA-ETF"), "A57CA-ETF")

        # ETF 1 trace capture
        self.ETF1Trace = TMCETBTraceCapture(self, self.ETF1, "A57CA-ETF")

        # ETF 2
        self.ETF2 = CSTMC(self, self.findDevice("R7CA-ETF"), "R7CA-ETF")

        # ETF 2 trace capture
        self.ETF2Trace = TMCETBTraceCapture(self, self.ETF2, "R7CA-ETF")

        # ETF 3
        self.ETF3 = CSTMC(self, self.findDevice("A53CA-ETF"), "A53CA-ETF")

        # ETF 3 trace capture
        self.ETF3Trace = TMCETBTraceCapture(self, self.ETF3, "A53CA-ETF")

        # DSTREAM
        self.createDSTREAM()

        # 'CSD-TPIU' is the main TPIU that we want to use for off-chip trace
        self.csdTPIU = self.createTPIU("CSD-TPIU", "CSD-TPIU")
        # We don't care about these other TPIUs, but we need to have them as managed devices
        # to ensure they get turned off during connection.
        self.a57TPIU = self.createTPIU("A57CA-TPI", "A57CA-TPI")
        self.r7TPIU = self.createTPIU("R7CA-TPIU", "R7CA-TPIU")
        self.a53TPIU = self.createTPIU("A53CA-TPIU", "A53CA-TPIU")

        # Funnel 0
        self.Funnel0 = self.createFunnel("CSD-FUNNEL", "CSD-FUNNEL")
        # A57CA-ETF is connected to CSD-FUNNEL port 0
        self.Funnel0.setPortEnabled(0)
        # R7CA-ETF is connected to CSD-FUNNEL port 1
        self.Funnel0.setPortEnabled(1)
        # A53CA-ETF is connected to CSD-FUNNEL port 2
        self.Funnel0.setPortEnabled(2)

        # Funnel 1
        self.Funnel1 = self.createFunnel("A57CA-FUNNEL", "A57CA-FUNNEL")

        # Funnel 2
        self.Funnel2 = self.createFunnel("R7CA-FUNNEL", "R7CA-FUNNEL")

        # Funnel 3
        self.Funnel3 = self.createFunnel("A53CA-FUNNEL", "A53CA-FUNNEL")

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
        for core in self.cortexA57cores:
            a57_rams.registerInternalRAMs(core)
        for core in self.cortexA53cores:
            a53_rams.registerInternalRAMs(core)

    def setupETFTrace(self, etfTrace, name, traceComponentOrder, managedDevices):
        '''Setup ETF trace capture'''
        # Use continuous mode
        etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)

        # Register other trace components with ETF and register ETF with configuration
        etfTrace.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etfTrace)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.csdTPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # Configure the DSTREAM for trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.setPortWidth(portWidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def setPortWidth(self, portWidth):
        self.csdTPIU.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        macrocellNames = ["CSD-STM", "A57MP-ETM_0", "A57MP-ETM_1", "A57MP-ETM_2", "A57MP-ETM_3", "R7MP-ETM", "A53MP-ETM_0", "A53MP-ETM_1", "A53MP-ETM_2", "A53MP-ETM_3"]
        funnelNames = ["CSD-FUNNEL", "A57CA-FUNNEL", "A57CA-FUNNEL", "A57CA-FUNNEL", "A57CA-FUNNEL", "R7CA-FUNNEL", "A53CA-FUNNEL", "A53CA-FUNNEL", "A53CA-FUNNEL", "A53CA-FUNNEL"]
        funnelPorts = [3, 0, 1, 2, 3, 0, 0, 1, 2, 3]

        sourceName = source.getName()
        for i in range(len(macrocellNames)):
            if sourceName == macrocellNames[i]:
                return(self.getDeviceInterface(funnelNames[i]), funnelPorts[i])

        return (None, None)

    def getCTIInfoForCore(self, core):
        '''Get the funnel port number for a trace source'''

        coreNames = ["Cortex-A57_0", "Cortex-A57_1", "Cortex-A57_2", "Cortex-A57_3", "Cortex-R7", "Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
        ctiNames = ["A57MP-CTI_0", "A57MP-CTI_1", "A57MP-CTI_2", "A57MP-CTI_3", "R7MP-CTI", "A53MP-CTI_0", "A53MP-CTI_1", "A53MP-CTI_2", "A53MP-CTI_3"]
        ctiTriggers = [1, 1, 1, 1, 7, 1, 1, 1, 1]

        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return CTISyncSMPDevice.DeviceCTIInfo(self.getDeviceInterface(ctiNames[i]), CTISyncSMPDevice.DeviceCTIInfo.NONE, ctiTriggers[i], 0, 0)

        return None

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''
        macrocellNames = ["A57MP-ETM_0", "A57MP-ETM_1", "A57MP-ETM_2", "A57MP-ETM_3", "R7MP-ETM", "A53MP-ETM_0", "A53MP-ETM_1", "A53MP-ETM_2", "A53MP-ETM_3"]
        ctiNames = ["A57MP-CTI_0", "A57MP-CTI_1", "A57MP-CTI_2", "A57MP-CTI_3", "R7MP-CTI", "A53MP-CTI_0", "A53MP-CTI_1", "A53MP-CTI_2", "A53MP-CTI_3"]
        ctiTriggers = [6, 6, 6, 6, 6, 6, 6, 6, 6]

        sourceName = source.getName()
        for i in range(len(macrocellNames)):
            if sourceName == macrocellNames[i]:
                return (self.getDeviceInterface(ctiNames[i]), ctiTriggers[i], CTM_CHANNEL_TRACE_TRIGGER)

        return (None, None, None)

    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        sinkNames = ["CSD-ETF", "CSD-TPIU", "A57CA-ETF", "A57CA-TPI", "R7CA-ETF", "R7CA-TPIU", "A53CA-ETF", "A53CA-TPIU"]
        ctiNames = ["CSD-CTI_0", "CSD-CTI_0", "A57CA-CTI", "A57CA-CTI", "R7CA-CTI", "R7CA-CTI", "A53CA-CTI", "A53CA-CTI"]
        ctiTriggers = [1, 3, 1, 3, 1, 3, 1, 3]

        sinkName = sink.getName()
        for i in range(len(sinkNames)):
            if sinkName == sinkNames[i]:
                return (self.getDeviceInterface(ctiNames[i]), ctiTriggers[i], CTM_CHANNEL_TRACE_TRIGGER)

        return (None, None, None)

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''
        coreNames = ["Cortex-A57_0", "Cortex-A57_1", "Cortex-A57_2", "Cortex-A57_3", "Cortex-R7", "Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
        macrocellNames = ["A57MP-ETM_0", "A57MP-ETM_1", "A57MP-ETM_2", "A57MP-ETM_3", "R7MP-ETM", "A53MP-ETM_0", "A53MP-ETM_1", "A53MP-ETM_2", "A53MP-ETM_3"]

        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return self.getDeviceInterface(macrocellNames[i])

        return None

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
        # Cortex-A57x4 CTI SMP
        ctiInfo = {}
        for c in self.cortexA57cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)

        smp = CTISyncSMPDevice(self, "Cortex-A57x4 SMP", self.cortexA57cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp, 0)
        self.addDeviceInterface(smp)

        # Cortex-A53x4 CTI SMP
        ctiInfo = {}
        for c in self.cortexA53cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)

        smp = CTISyncSMPDevice(self, "Cortex-A53x4 SMP", self.cortexA53cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp, 0)
        self.addDeviceInterface(smp)

        # Automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CoreCTIs)

    def setupBigLittle(self):
        '''Create big.LITTLE device using CTI synchronization'''

        ctiInfo = {}
        for c in self.cortexA57cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)
        for c in self.cortexA53cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)
        cores = [ DeviceCluster("big", self.cortexA57cores), DeviceCluster("LITTLE", self.cortexA53cores) ]
        bigLITTLE = CTISyncSMPDevice(self, "big.LITTLE", cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)

        self.registerFilters(bigLITTLE, 0)
        self.addDeviceInterface(bigLITTLE)

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

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.csdTPIU.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for core in self.cortexA57cores:
            coreTM = self.getTMForCore(core)
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, core, coreTM)

        for core in self.cortexR7cores:
            coreTM = self.getTMForCore(core)
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, core, coreTM)

        for core in self.cortexA53cores:
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

        coreTraceEnabled = self.getOptionValue("options.cortexA57.coreTrace")
        for core in range(NUM_CORES_CORTEX_A57):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA57.coreTrace.Cortex_A57_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexA57cores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setTimestampingEnabled(coreTM, self.getOptionValue("options.cortexA57.coreTrace.timestamp"))
            self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexA57.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexA57.coreTrace.contextIDs.contextIDsSize"))

        coreTraceEnabled = self.getOptionValue("options.cortexR7.coreTrace")
        for core in range(NUM_CORES_CORTEX_R7):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexR7.coreTrace.Cortex_R7_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexR7cores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "cortexR7")
            self.setTimestampingEnabled(coreTM, self.getOptionValue("options.cortexR7.coreTrace.timestamp"))
            self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexR7.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexR7.coreTrace.contextIDs.contextIDsSize"))

        coreTraceEnabled = self.getOptionValue("options.cortexA53.coreTrace")
        for core in range(NUM_CORES_CORTEX_A53):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA53.coreTrace.Cortex_A53_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexA53cores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "cortexA53")
            self.setTimestampingEnabled(coreTM, self.getOptionValue("options.cortexA53.coreTrace.timestamp"))
            self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexA53.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexA53.coreTrace.contextIDs.contextIDsSize"))

        stmEnabled = self.getOptionValue("options.stm.CSD-STM")
        self.setTraceSourceEnabled(self.STM0, stmEnabled)

        # Register trace sources for each trace sink
        self.registerTraceSources(self.ETF0Trace)
        self.registerTraceSources(self.ETF1Trace)
        self.registerTraceSources(self.ETF2Trace)
        self.registerTraceSources(self.ETF3Trace)
        self.registerTraceSources(self.DSTREAM)

        self.setManagedDeviceList(self.getManagedDevices(traceMode))

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

        for core in range(0, len(self.cortexA57cores)):
            a57_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA57cores[core])
            a57_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA57cores[core])

        for core in range(0, len(self.cortexA53cores)):
            a53_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA53cores[core])
            a53_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA53cores[core])

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def setTraceCaptureMethod(self, method):
        if method == "CSD-ETF":
            self.setETFTraceEnabled(self.ETF0Trace, True)
        if method == "A57CA-ETF":
            self.setETFTraceEnabled(self.ETF1Trace, True)
        if method == "R7CA-ETF":
            self.setETFTraceEnabled(self.ETF2Trace, True)
        if method == "A53CA-ETF":
            self.setETFTraceEnabled(self.ETF3Trace, True)
        if method == "DSTREAM":
            self.setDSTREAMTraceEnabled(True)

    @staticmethod
    def getTraceMacrocellsForCoreType(coreType):
        '''Get the Trace Macrocells for a given coreType
           Use parameter-binding to ensure that the correct Macrocells
           are returned for the core type passed only'''
        def getMacrocells(self):
            return self.macrocells[coreType]
        return getMacrocells

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

    def reset(self, device):
        Device.systemReset(device, 0);
        self.powerUpClusters()
        DTSLv1.postConnect(self)

    def postDebugConnect(self):
        self.powerUpClusters()
        DTSLv1.postDebugConnect(self)

    def postConnect(self):
        DTSLv1.postConnect(self)

        try:
            freq = self.getOptionValue("options.trace.timestampFrequency")
        except:
            return

        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)

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

class DtslScript_HSSTP(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_HSSTP.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA57TabPage(),
                DtslScript.getOptionCortexR7TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
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
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency.")
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMHSSTPTraceCapture(self, "DSTREAM", self.AXIs[0])

class DtslScript_DSTREAM_HT(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_HT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA57TabPage(),
                DtslScript.getOptionCortexR7TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
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
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMHTTraceCapture(self, "DSTREAM", self.AXIs[0])

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.csdTPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        self.setPortWidth(portWidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def setPortWidth(self, portWidth):
        # DSTREAM-HT doesn't need to know the port width
        self.csdTPIU.setPortSize(portWidth)

