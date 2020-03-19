# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceInfo
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import V7M_ITMTraceSource

from struct import pack, unpack
from jarray import array, zeros
from com.arm.rddi import RDDI_ACC_SIZE

clusterNames = ["SMP_Cluster0"]
clusterCores = [["Cortex-A35_0", "Cortex-A35_1", "Cortex-A35_2", "Cortex-A35_3"]]
coreNames_cortexM4 = ["Cortex-M4_0_SCU", "Cortex-M4_1"]
coreNames_cortexA35 = ["Cortex-A35_0", "Cortex-A35_1", "Cortex-A35_2", "Cortex-A35_3"]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''

class CacheMaintCore(Device):
    def __init__(self, config, id, name):
        Device.__init__(self, config, id, name)

    def to_s8(self, val):
        return val > 127 and val - 256 or val

    def __clean_invalidate_caches(self):
        buf = zeros(4,'b')
        # If D cache is enabled, execute clean/invalidate operation
        Device.memRead(self, 0x0, 0xE0082800, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)
        if buf[0] & 0x1:
            buf = array(map(self.to_s8, [buf[0] & 0xFF, 0x0, 0x0, 0x8F]), 'b')
            Device.memWrite(self, 0x0, 0xE0082800, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)
        # If I cache is enabled, execute clean/invalidate operation
        Device.memRead(self, 0x0, 0xE0082000, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)
        if buf[0] & 0x1:
            buf = array(map(self.to_s8, [buf[0] & 0xFF, 0x0, 0x0, 0x8F]), 'b')
            Device.memWrite(self, 0x0, 0xE0082000, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)

    def setSWBreak(self, page, addr, flags):
        self.__clean_invalidate_caches()
        return Device.setSWBreak(self, page, addr, flags)

    def memWrite(self, page, addr, size, rule, check, count, data):
        self.__clean_invalidate_caches()
        Device.memWrite(self, page, addr, size, rule, check, count, data)

    def memRead(self, page, addr, size, rule, count, pDataOut):
        self.__clean_invalidate_caches()
        Device.memRead(self, page, addr, size, rule, count, pDataOut)

class M_Class_ETMv3_5(ETMv3_5TraceSource):
    def hasTriggers(self):
        return False
    
    def hasTraceStartPoints(self):
        return False
    
    def hasTraceStopPoints(self):
        return False
    
    def hasTraceRanges(self):
        return False
    
class M_Class_ITMTraceSource(V7M_ITMTraceSource):
    def __init__(self, config, id, streamID, name, memAccessWrapper):
        V7M_ITMTraceSource.__init__(self, config, id, streamID, name)
        self.memAccessWrapper = memAccessWrapper

    def postConnect(self):
        V7M_ITMTraceSource.postConnect(self)
        self.enableDwtSyncPackets()

    def enableDwtSyncPackets(self):
        # DWT_CTRL enable CYCCNTENA, SYNCTAP at CYCCNT[24]
        # Normally this is handled by MProfile_CSTPIU, but as only ETF
        # trace capture is available, we have to do this here
        buffer = zeros(4, 'b')
        DWT_CTRL_address = 0xE0001000
        mask = 0x00000C01
        # Read-modify-write
        self.memAccessWrapper.readMem(DWT_CTRL_address, 4, buffer)
        value = unpack('<I', buffer)[0]
        value &= ~mask
        value |= 0x00000401
        self.memAccessWrapper.memWrite(0, DWT_CTRL_address,
                       RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, 4, pack('<I', value))

# Import core specific functions
import a35_rams


class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "System Memory Trace Buffer (CSTMC/ETR)")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])]
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M4_0', 'Enable Cortex-M4_0_SCU trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex_M4_1', 'Enable Cortex-M4_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("SMP_Cluster0", "Cortex-A35", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A35 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('SMP_Cluster0_0', 'Enable Cortex-A35_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('SMP_Cluster0_1', 'Enable Cortex-A35_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('SMP_Cluster0_2', 'Enable Cortex-A35_2 trace', defaultValue=True),
                            DTSLv1.booleanOption('SMP_Cluster0_3', 'Enable Cortex-A35_3 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("SMP_Cluster0")),
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
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer0', 'Configure the system memory trace buffer to be used by the CSTMC/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the CSTMC/ETR device',
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
                    DTSLv1.booleanOption('CSITM_M4_0', 'Enable CSITM_M4_0_SCU trace', defaultValue=False),
                    DTSLv1.booleanOption('CSITM_M4_1', 'Enable CSITM_M4_1 trace', defaultValue=False),
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
                    DTSLv1.booleanOption(coreNames_cortexM4[0], coreNames_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM4[1], coreNames_cortexM4[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA35[0], coreNames_cortexA35[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA35[1], coreNames_cortexA35[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA35[2], coreNames_cortexA35[2], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA35[3], coreNames_cortexA35[3], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
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
        AXIAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        ahbm0 = CortexM_AHBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        ahbm1 = CortexM_AHBAP(self, self.findDevice("CSMEMAP_2"), "CSMEMAP_2")
        self.AHB_Ms = []
        self.AHB_Ms.append(ahbm0)
        self.AHB_Ms.append(ahbm1)
        AHBAP(self, self.findDevice("CSMEMAP_3"), "CSMEMAP_3")
        apb = APBAP(self, self.findDevice("CSMEMAP_4"), "CSMEMAP_4")
        self.APBs = []
        self.APBs.append(apb)
        AHBAP(self, self.findDevice("CSMEMAP_5"), "CSMEMAP_5")
        AHBAP(self, self.findDevice("CSMEMAP_6"), "CSMEMAP_6")
        
        
        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        itm = M_Class_ITMTraceSource(self, self.findDevice("CSITM_M4_0_SCU"), streamID, "CSITM_M4_0_SCU", ahbm0)
        itm.setPortPrivileges(True, True, True, True)
        itm.setIsSetupByTarget(False)
        itm.setEnabled(False)
        streamID += 1
        
        itm = M_Class_ITMTraceSource(self, self.findDevice("CSITM_M4_1"), streamID, "CSITM_M4_1", ahbm1)
        itm.setPortPrivileges(True, True, True, True)
        itm.setIsSetupByTarget(False)
        itm.setEnabled(False)
        streamID += 1
        
        self.cortexM4cores = []
        for coreName in (coreNames_cortexM4):
            # Create core
            coreDevice = CacheMaintCore(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-M4")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexM4cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            
            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
                self.registerCoreForCrossSync(coreDevice)
            
            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = M_Class_ETMv3_5(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)
            
        self.cortexA35cores = []
        for coreName in (coreNames_cortexA35):
            # Create core
            coreDevice = a35_rams.A35CoreDevice(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-A35")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexA35cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            a35_rams.registerInternalRAMs(coreDevice)
            
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
            
        # Create and Configure Funnels
        self.createFunnel("CSTFunnel_M4_0_SCU")
        self.createFunnel("CSTFunnel_M4_1")
        self.createFunnel("CSTFunnel_Main")
        
        self.setupCTISyncSMP()
        
    def postDebugConnect(self):
        # Power up subsystems with CoreSight using Granular Power Request.  The CoreSight components
        # must be powered to support successful discovery/instantiation when the tool attaches to the target
        #
        #        CoreSight_GPR.CPWRUPREQ[5]  = A53
        #        CoreSight_GPR.CPWRUPREQ[6]  = M4_0_SCU
        #
        self.APBs[0].connect()
        self.APBs[0].writeMem(0x80070000, 0x00000060)
        self.APBs[0].disconnect()


        # Configure LMEM Parity/ECC Control Register
        #
        #   Note: ECC Multi-bit IRQ should be disabled
        #   prior to list/dump of locations that
        #   have not been written to avoid vectoring
        #   to the NMI
        #
        #   31:22   RESERVED
        #      21   Enable Cache Parity IRQ
        #      20   Enable Cache Parity Report
        #   19:17   RESERVED
        #      16   Enable RAM Parity Reporting
        #   15:10   RESERVED
        #       9   Enable RAM ECC 1-bit IRQ
        #       8   Enable RAM ECC 1-bit Report
        #     7:2   RESERVED
        #       1   Enable RAM ECC Multi-bit IRQ
        #       0   Enable RAM ECC Multi-bit
        #
        # Configure LMEM of SCU, CM4_0_SCU
        #
        self.AHB_Ms[0].connect()
        self.AHB_Ms[0].writeMem(0xE0080480, 0x00300001)
        self.AHB_Ms[0].disconnect()
        self.AHB_Ms[1].connect()
        self.AHB_Ms[1].writeMem(0xE0080480, 0x00300001)
        self.AHB_Ms[1].disconnect()
        DTSLv1.postDebugConnect(self)
        
    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB_0", self.getDeviceInterface("CSMEMAP_3"), "AHB bus accessed via AP 3 (CSMEMAP_3)"),
            AHBMemAPAccessor("AHB_1", self.getDeviceInterface("CSMEMAP_5"), "AHB bus accessed via AP 5 (CSMEMAP_5)"),
            AHBMemAPAccessor("AHB_2", self.getDeviceInterface("CSMEMAP_6"), "AHB bus accessed via AP 6 (CSMEMAP_6)"),
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_4"), "APB bus accessed via AP 4 (CSMEMAP_4)"),
            AXIMemAPAccessor("AXI", self.getDeviceInterface("CSMEMAP_0"), "AXI bus accessed via AP 0 (CSMEMAP_0)", 64),
            AHBCortexMMemAPAccessor("AHB_M_0", self.getDeviceInterface("CSMEMAP_1"), "AHB-M bus accessed via AP 1 (CSMEMAP_1)"),
            AHBCortexMMemAPAccessor("AHB_M_1", self.getDeviceInterface("CSMEMAP_2"), "AHB-M bus accessed via AP 2 (CSMEMAP_2)"),
        ])
    
    def createTraceCapture(self):
        # ETR Capture
        self.createETRCapture()
    
    def createETRCapture(self):
        etr = ETRTraceCapture(self, self.findDevice("CSTMC"), "CSTMC")
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
        
        coreTraceEnabled = self.getOptionValue("options.cortexM4.coreTrace")
        for core in range(len(coreNames_cortexM4)):
            tmName = self.getTraceSourceNameForCore(coreNames_cortexM4[core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.cortexM4.coreTrace.Cortex_M4_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                coreTM.setTimestampingEnabled(self.getOptionValue("options.cortexM4.coreTrace.timestamp"))
        
        coreTraceEnabled = self.getOptionValue("options.SMP_Cluster0.coreTrace")
        for core in range(len(clusterCores[0])):
            tmName = self.getTraceSourceNameForCore(clusterCores[0][core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.SMP_Cluster0.coreTrace.SMP_Cluster0_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                if(self.getOptionValue("options.SMP_Cluster0.coreTrace.traceRange")):
                    coreTM.clearAllTraceRanges()
                    coreTM.addTraceRange(self.getOptionValue("options.SMP_Cluster0.coreTrace.traceRange.start"),
                                         self.getOptionValue("options.SMP_Cluster0.coreTrace.traceRange.end"))
                coreTM.setTimestampingEnabled(self.getOptionValue("options.SMP_Cluster0.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.SMP_Cluster0.coreTrace.contextIDs"),
                                     "32")
        
        itmEnabled = self.getOptionValue("options.itm.CSITM_M4_0")
        self.setTraceSourceEnabled("CSITM_M4_0_SCU", itmEnabled)
        
        itmEnabled = self.getOptionValue("options.itm.CSITM_M4_1")
        self.setTraceSourceEnabled("CSITM_M4_1", itmEnabled)
        
        self.configureTraceCapture(traceMode)
        
    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        
        # Set up the ETR 0 buffer
        configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer0")
        if configureETRBuffer:
            etr = self.getTraceCaptureInterfaces()["CSTMC"]
            etr.setBaseAddress(self.getOptionValue("options.ETR.etrBuffer0.start"))
            etr.setTraceBufferSize(self.getOptionValue("options.ETR.etrBuffer0.size"))
            etr.setScatterGatherModeEnabled(self.getOptionValue("options.ETR.etrBuffer0.scatterGather"))
            
        for core in range(len(self.cortexA35cores)):
            a35_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA35cores[core])
            a35_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA35cores[core])
        
        for cluster in range(len(clusterNames)):
            if not self.getDeviceInterface(clusterNames[cluster]).isConnected():
                for core in range(len(clusterCores[cluster])):
                    if self.getCTINameForCore(clusterCores[cluster][core]):
                        enable = self.getOptionValue('options.sync.%s' % clusterCores[cluster][core])
                        self.setCrossSyncEnabled(self.getDeviceInterface(clusterCores[cluster][core]), enable)
        
        for core in range(len(self.cortexM4cores)):
            enable = self.getOptionValue('options.sync.%s' % coreNames_cortexM4[core])
            self.setCrossSyncEnabled(self.cortexM4cores[core], enable)
        
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
    
