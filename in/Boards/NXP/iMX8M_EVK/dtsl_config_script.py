# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceInfo
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import ITMTraceSource

from struct import pack, unpack
from jarray import array, zeros
from com.arm.rddi import RDDI_ACC_SIZE

clusterNames = ["Cortex-A53_SMP_0"]
clusterCores = [["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]]
coreNames_cortexA53 = ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
coreNames_cortexM4 = ["Cortex-M4"]

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

class M_Class_ITMTraceSource(ITMTraceSource):
    def __init__(self, config, id, streamID, name, memAccessWrapper):
        ITMTraceSource.__init__(self, config, id, streamID, name)
        self.memAccessWrapper = memAccessWrapper

    def postConnect(self):
        ITMTraceSource.postConnect(self)
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
import a53_rams

class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/ETF)")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                ])]
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M4_0', 'Enable Cortex-M4 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("Cortex-A53_SMP_0", "Cortex-A53", childOptions=[
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
                    DTSLv1.booleanOption(coreNames_cortexA53[0], coreNames_cortexA53[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[1], coreNames_cortexA53[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[2], coreNames_cortexA53[2], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[3], coreNames_cortexA53[3], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM4[0], coreNames_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
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
        AHBAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        APBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        memap4 = CortexM_AHBAP(self, self.findDevice("CSMEMAP_4"), "CSMEMAP_4")
        
        
        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        itm = M_Class_ITMTraceSource(self, self.findDevice("CSITM"), streamID, "CSITM", memap4)
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
                self.registerCoreForCrossSync(coreDevice)
            
            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)
            
        tmc = CSTMC(self, self.findDevice("ETF"), "ETF")
        tmc.setMode(CSTMC.Mode.ETF)
        
        # Create and Configure Funnels
        self.createFunnel("CSTFunnel_1")
        self.createFunnel("CSTFunnel_0")
        
        self.setupCTISyncSMP()
        
    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB", self.getDeviceInterface("CSMEMAP_0"), "AHB bus accessed via AP 0 (CSMEMAP_0)"),
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_1"), "APB bus accessed via AP 1 (CSMEMAP_1)"),
            AHBCortexMMemAPAccessor("AHB_M", self.getDeviceInterface("CSMEMAP_4"), "AHB-M bus accessed via AP 4 (CSMEMAP_4)"),
        ])
    
    def createTraceCapture(self):
        # ETF Devices
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("ETF"), "ETF")
        self.addTraceCaptureInterface(etfTrace)
    
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
        
        itmEnabled = self.getOptionValue("options.itm.CSITM")
        self.setTraceSourceEnabled("CSITM", itmEnabled)
        
        self.configureTraceCapture(traceMode)
        
    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        
        for core in range(len(self.cortexA53cores)):
            a53_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA53cores[core])
            a53_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA53cores[core])
        
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
            freq = self.getOptionValue("options.trace.traceOpts.timestampFrequency")
        except:
            return
        
        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)

class DtslScript_ULINKpro(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/ETF)")],
                        setter=DtslScript_ULINKpro.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                ])]
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M4_0', 'Enable Cortex-M4 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("Cortex-A53_SMP_0", "Cortex-A53", childOptions=[
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
                    DTSLv1.booleanOption(coreNames_cortexA53[0], coreNames_cortexA53[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[1], coreNames_cortexA53[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[2], coreNames_cortexA53[2], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[3], coreNames_cortexA53[3], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM4[0], coreNames_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]

class DtslScript_ULINKpro_D(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/ETF)")],
                        setter=DtslScript_ULINKpro_D.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                ])]
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M4_0', 'Enable Cortex-M4 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("Cortex-A53_SMP_0", "Cortex-A53", childOptions=[
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
                    DTSLv1.booleanOption(coreNames_cortexA53[0], coreNames_cortexA53[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[1], coreNames_cortexA53[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[2], coreNames_cortexA53[2], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[3], coreNames_cortexA53[3], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM4[0], coreNames_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]

class DtslScript_ULINK2(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/ETF)")],
                        setter=DtslScript_ULINK2.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                ])]
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M4_0', 'Enable Cortex-M4 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("Cortex-A53_SMP_0", "Cortex-A53", childOptions=[
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
                    DTSLv1.booleanOption(coreNames_cortexA53[0], coreNames_cortexA53[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[1], coreNames_cortexA53[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[2], coreNames_cortexA53[2], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[3], coreNames_cortexA53[3], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM4[0], coreNames_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]

class DtslScript_DSTREAM_ST(DtslScript):

    @staticmethod
    def getOptionList():
        return DtslScript.getOptionList()

class DtslScript_DSTREAM_PT(DtslScript):

    @staticmethod
    def getOptionList():
        return DtslScript.getOptionList()
