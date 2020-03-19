# Copyright (C) 2016-2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import ConnectableDevice
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
from com.arm.debug.dtsl.components import CSATBReplicator
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import CTISynchronizer
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource

from struct import pack, unpack
from jarray import array, zeros
from java.lang import Byte
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE

tmDevs_cortexM4 = ["CSETM_2"]
tmDevs_cortexA7 = ["CSETM_0", "CSETM_1"]
ctiDevs_cortexM4 = ["CSCTI_4"]
ctiDevs_cortexA7 = ["CSCTI_0", "CSCTI_1"]
coreDevs_cortexM4 = ["Cortex-M4"]
coreDevs_cortexA7 = ["Cortex-A7_0", "Cortex-A7_1"]
NUM_CORES_CORTEX_A7 = 2
NUM_CORES_CORTEX_M4 = 1
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
coresDap0 = ["Cortex-A7_0", "Cortex-A7_1", "Cortex-M4"]
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers

class M_Class_ETMv3_5(ETMv3_5TraceSource):
    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False

class CacheMaintCore(Device):
    def __init__(self, config, id, name):
        Device.__init__(self, config, id, name)

    def to_s8(self, val):
        return val > 127 and val - 256 or val

    def memRead(self, page, address, size, rule, count, pDataOut):
        Device.memRead(self, page, address, size, rule, count, pDataOut)
        self.__clean_invalidate_caches(page)

    def __clean_invalidate_caches(self, page):
        buf = zeros(4,'b')
        # Clean/Inv for I cache
        Device.memRead(self, page, 0xE0082800, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)
        if buf[0] & 0x1:
            buf = array(map(self.to_s8, [buf[0] & 0xFF, 0x0, 0x0, 0x8F]), 'b')
            Device.memWrite(self, page,  0xE0082800, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)
        # Clean/Inv for D cache
        Device.memRead(self, page, 0xE0082000, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)
        if buf[0] & 0x1:
            buf = array(map(self.to_s8, [buf[0] & 0xFF, 0x0, 0x0, 0x8F]), 'b')
            Device.memWrite(self, page,  0xE0082000, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)

    def setSWBreak(self, page, addr, flags):
        brkID = Device.setSWBreak(self, page, addr, flags)
        self.__clean_invalidate_caches(page)
        return brkID

    def memWrite(self, page, addr, size, rule, check, count, data):
        Device.memWrite(self, page, addr, size, rule, check, count, data)
        self.__clean_invalidate_caches(page)


# Import core specific functions
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a7_rams

class DtslScript(DTSLv1):

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
                            [ DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ ETMv3_5TraceSource.cycleAccurateOption(DtslScript.getTraceMacrocellsForCoreType("cortexA7"))] +
                            [ ETMv3_5TraceSource.dataOption(DtslScript.getTraceMacrocellsForCoreType("cortexA7"))] +
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
                        )
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
                        )
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
                    )
                ])

    @staticmethod
    def getOptionITMTabPage():
        return DTSLv1.tabPage("itm", "ITM", childOptions=[
                    DTSLv1.booleanOption('CSITM', 'Enable CSITM trace', defaultValue=False)
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
                                         defaultValue=False, isDynamic=True)
                ])

    @staticmethod
    def getOptionCTISyncPage():
        return DTSLv1.tabPage("sync", "CTI Synchronization", childOptions=[
                    DTSLv1.booleanOption('Cortex_A7_0', coreDevs_cortexA7[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('Cortex_A7_1', coreDevs_cortexA7[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('Cortex_M4_0', coreDevs_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True)
                ])

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA7TabPage(),
                DtslScript.getOptionCortexM4TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionRAMTabPage(),
                DtslScript.getOptionCTISyncPage()
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

        self.mgdPlatformDevs.append(self.sysCtrl0)

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

        self.traceRangeIDs = {}

        traceComponentOrder = [ self.Funnel0, self.Funnel2, self.Funnel1 ]
        managedDevices = [ self.Funnel0, self.Funnel2, self.Funnel1, self.OutCTI1, self.TPIU, self.ETF0Trace ]
        self.setupETFTrace(self.ETF0Trace, "CSTMC_0", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel0, self.Funnel2, self.Funnel1, self.ETF0 ]
        managedDevices = [ self.Funnel0, self.Funnel2, self.Funnel1, self.ETF0, self.OutCTI0, self.TPIU, self.ETR0 ]
        self.setupETRTrace(self.ETR0, "CSTMC_1", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel0, self.Funnel2, self.Funnel1, self.ETF0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.Funnel2, self.Funnel1, self.ETF0, self.OutCTI1, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(traceComponentOrder, managedDevices)

        self.setupCTISyncSMP()

        self.setManagedDeviceList(self.mgdPlatformDevs)

        self.setETFTraceEnabled(self.ETF0Trace, False)
        self.setETRTraceEnabled(self.ETR0, False)
        self.setDSTREAMTraceEnabled(False)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        self.sysCtrl0 = ConnectableDevice(self, self.findDevice("iMX7SystemControl"), "iMX7SystemControl")

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
        self.OutCTI0 = CSCTI(self, self.findDevice("CSCTI_2"), "CSCTI_2")

        # Trace start/stop CTI 1
        self.OutCTI1 = CSCTI(self, self.findDevice("CSCTI_3"), "CSCTI_3")

        self.CoreCTIs = []

        self.macrocells = {}
        self.macrocells["cortexA7"] = []
        self.macrocells["cortexM4"] = []

        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        # ITM 0
        self.ITM0 = self.createITM("CSITM", streamID, "CSITM")
        streamID += 1

        self.synchronizer = CTISynchronizer(self, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)

        #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for core in range(NUM_CORES_CORTEX_M4):
            # Create core
            coreDevice = CacheMaintCore(self, self.findDevice(coreDevs_cortexM4[core]), coreDevs_cortexM4[core])
            self.cortexM4cores.append(coreDevice)

            # Create CTI (if a CTI exists for this core)
            if not ctiDevs_cortexM4[core] == None:
                coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexM4[core]), ctiDevs_cortexM4[core])
                self.CoreCTIs.append(coreCTI)

                self.synchronizer.registerDevice(coreDevice, coreCTI,
                                                 CTISynchronizer.CTIInfo(CTISynchronizer.CTIInfo.NONE, 7, 0, 0))

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            if not tmDevs_cortexM4[core] == None:
                tm = M_Class_ETMv3_5(self, self.findDevice(tmDevs_cortexM4[core]), streamID, tmDevs_cortexM4[core])
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["cortexM4"].append(tm)

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

                self.synchronizer.registerDevice(coreDevice, coreCTI,
                                                 CTISynchronizer.CTIInfo(CTISynchronizer.CTIInfo.NONE, 7, 0, 0))

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            if not tmDevs_cortexA7[core] == None:
                tm = ETMv3_5TraceSource(self, self.findDevice(tmDevs_cortexA7[core]), streamID, tmDevs_cortexA7[core])
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["cortexA7"].append(tm)

        # ETF 0
        self.ETF0 = CSTMC(self, self.findDevice("CSTMC_0"), "CSTMC_0")

        # ETF 0 trace capture
        self.ETF0Trace = TMCETBTraceCapture(self, self.ETF0, "CSTMC_0")

        # ETR 0
        self.ETR0 = ETRTraceCapture(self, self.findDevice("CSTMC_1"), "CSTMC_1")

        # DSTREAM
        self.createDSTREAM()

        # TPIU
        self.TPIU = self.createTPIU("CSTPIU", "TPIU")

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

        # Replicator 0
        self.Replicator0 = CSATBReplicator(self, self.findDevice("CSATBReplicator"), "CSATBReplicator")

    def registerFilters(self, core, dap):
        '''Register MemAP filters to allow access to the APs for the device'''
        if dap == 0:
            core.registerAddressFilters([
                AHBMemAPAccessor("AHB_0", self.AHBs[0], "AHB bus accessed via AP 0 (CSMEMAP_0)"),
                AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 1 (CSMEMAP_1)"),
                AHBCortexMMemAPAccessor("AHB_M_0", self.AHB_Ms[0], "AHB-M bus accessed via AP 4 (CSMEMAP_4)"),
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

    def setupDSTREAMTrace(self, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # Configure the DSTREAM for trace
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

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        macrocellNames = ["CSETM_0", "CSETM_1", "CSITM", "CSETM_2"]
        funnelNames = ["CSTFunnel_0", "CSTFunnel_0", "CSTFunnel_2", "CSTFunnel_2"]
        funnelPorts = [0, 1, 1, 0]

        sourceName = source.getName()
        for i in range(len(macrocellNames)):
            if sourceName == macrocellNames[i]:
                return(self.getDeviceInterface(funnelNames[i]), funnelPorts[i])

        return (None, None)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''
        macrocellNames = ["CSETM_0", "CSETM_1", "CSETM_2"]
        ctiNames = ["CSCTI_0", "CSCTI_1", "CSCTI_4"]
        ctiTriggers = [6, 6, 6]

        sourceName = source.getName()
        for i in range(len(macrocellNames)):
            if sourceName == macrocellNames[i]:
                return (self.getDeviceInterface(ctiNames[i]), ctiTriggers[i], CTM_CHANNEL_TRACE_TRIGGER)

        return (None, None, None)

    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        sinkNames = ["CSTMC_0", "CSTMC_1", "CSTPIU"]
        ctiNames = ["CSCTI_3", "CSCTI_2", "CSCTI_3"]
        ctiTriggers = [1, 1, 3]

        sinkName = sink.getName()
        for i in range(len(sinkNames)):
            if sinkName == sinkNames[i]:
                return (self.getDeviceInterface(ctiNames[i]), ctiTriggers[i], CTM_CHANNEL_TRACE_TRIGGER)

        return (None, None, None)

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''
        coreNames = ["Cortex-A7_0", "Cortex-A7_1", "Cortex-M4"]
        macrocellNames = ["CSETM_0", "CSETM_1", "CSETM_2"]

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
        # Cortex-A7x2 CTI SMP
        self.cortexA7smp = CTISyncSMPDevice(self, "Cortex-A7x2 SMP", self.cortexA7cores, self.synchronizer)
        self.registerFilters(self.cortexA7smp, 0)
        self.addDeviceInterface(self.cortexA7smp)

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

        for core in self.cortexM4cores:
            coreTM = self.getTMForCore(core)
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, core, coreTM)

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

        coreTraceEnabled = self.getOptionValue("options.cortexM4.coreTrace")
        for core in range(NUM_CORES_CORTEX_M4):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexM4.coreTrace.Cortex_M4_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexM4cores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setTimestampingEnabled(coreTM, self.getOptionValue("options.cortexM4.coreTrace.timestamp"))

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

        itmEnabled = self.getOptionValue("options.itm.CSITM")
        self.setTraceSourceEnabled(self.ITM0, itmEnabled)

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

        if not self.cortexA7smp.isConnected():
            for core in range(0, NUM_CORES_CORTEX_A7):
                enable = self.getOptionValue('options.sync.Cortex_A7_%d' % core)
                self.synchronizer.setSynchEnabled(self.cortexA7cores[core], enable, enable)

        for core in range(0, NUM_CORES_CORTEX_M4):
            enable = self.getOptionValue('options.sync.Cortex_M4_%d' % core)
            self.synchronizer.setSynchEnabled(self.cortexM4cores[core], enable, enable)

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def setTraceCaptureMethod(self, method):
        if method == "CSTMC_0":
            self.setETFTraceEnabled(self.ETF0Trace, True)
        if method == "CSTMC_1":
            self.setETRTraceEnabled(self.ETR0, True)
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

    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, self.findDevice(itmDev), streamID, name)
        # Disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

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
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "System Memory Trace Buffer (CSTMC_1/ETR)")],
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
                            [ ETMv3_5TraceSource.cycleAccurateOption(DtslScript.getTraceMacrocellsForCoreType("cortexA7"))] +
                            [ ETMv3_5TraceSource.dataOption(DtslScript.getTraceMacrocellsForCoreType("cortexA7"))] +
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
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_M4_%d' % core, "Enable " + coreDevs_cortexM4[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_M4) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ]
                        ),
                ])]
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
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
                ])]
                +[DTSLv1.tabPage("itm", "ITM", childOptions=[
                    DTSLv1.booleanOption('CSITM', 'Enable CSITM trace', defaultValue=False),
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
                    DTSLv1.booleanOption('Cortex_A7_0', coreDevs_cortexA7[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('Cortex_A7_1', coreDevs_cortexA7[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('Cortex_M4_0', coreDevs_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
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
                DtslScript_DSTREAM_ST.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA7TabPage(),
                DtslScript.getOptionCortexM4TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionRAMTabPage(),
                DtslScript.getOptionCTISyncPage()
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
            "DSTREAM", "Streaming Trace",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")],isDynamic=False),
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
                DtslScript.getOptionCortexA7TabPage(),
                DtslScript.getOptionCortexM4TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionRAMTabPage(),
                DtslScript.getOptionCTISyncPage()
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
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="16",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit"),
                                  ("5", "5 bit"), ("6", "6 bit"), ("7", "7 bit"), ("8", "8 bit"),
                                  ("9", "9 bit"), ("10", "10 bit"), ("11", "11 bit"), ("12", "12 bit"),
                                  ("13", "13 bit"), ("14", "14 bit"), ("15", "15 bit"), ("16", "16 bit")], isDynamic=False)
                ]
            )
        )

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")

class DtslScript_ULINKpro(DtslScript_RVI):
    pass

class DtslScript_ULINKpro_D(DtslScript_RVI):
    pass
