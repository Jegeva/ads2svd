# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
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
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import STMTraceSource
from struct import pack, unpack
from jarray import array, zeros
from com.arm.rddi import RDDI_ACC_SIZE


clusterNames = ["Cortex-A7_SMP_0"]
clusterCores = [["Cortex-A7_0", "Cortex-A7_1"]]
coreNames_cortexA7 = ["Cortex-A7_0", "Cortex-A7_1"]
coreNames_cortexM4 = ["Cortex-M4"]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''

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
        buffer = zeros(4, 'b')
        # set DEMCR.TRCENA via RMW in case it is not already set
        DWT_CTRL_addr = 0xE0001000
        DEMCR_addr = 0xE000EDFC
        value = 0x01000000
        self.memAccessWrapper.readMem(DWT_CTRL_addr, 4, buffer)
        value = unpack('<I', buffer)[0]
        value |= (0x1 << 24)
        self.memAccessWrapper.memWrite(0, DEMCR_addr,
                       RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, 4, pack('<I', value))
        # DWT_CTRL enable CYCCNTENA, SYNCTAP at CYCCNT[24]
        # Read-modify-write
        mask = 0x00000C01
        self.memAccessWrapper.readMem(DWT_CTRL_addr, 4, buffer)
        value = unpack('<I', buffer)[0]
        value &= ~mask
        value |= 0x00000401
        self.memAccessWrapper.memWrite(0, DWT_CTRL_addr,
                       RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, 4, pack('<I', value))


# Import core specific functions
import a7_rams

class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)"), DtslScript.getOffChipTraceOption()],
                        setter=DtslScript.setTraceCaptureMethod),
                ])]
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M4_0', 'Enable Cortex-M4 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("Cortex-A7_SMP_0", "Cortex-A7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A7 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-A7_SMP_0_0', 'Enable Cortex-A7_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A7_SMP_0_1', 'Enable Cortex-A7_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ETMv3_5TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-A7_SMP_0")),
                            ETMv3_5TraceSource.dataOption(DtslScript.getSourcesForCluster("Cortex-A7_SMP_0")),
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
                    DTSLv1.booleanOption(coreNames_cortexA7[0], coreNames_cortexA7[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA7[1], coreNames_cortexA7[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM4[0], coreNames_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]
    
    @staticmethod
    def getOffChipTraceOption():
        return ("DSTREAM", "DSTREAM 4GB Trace Buffer",
            DTSLv1.infoElement("dstream", "Off-Chip Trace", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit"), ("5", "5 bit"), ("6", "6 bit"), ("7", "7 bit"), ("8", "8 bit"), ("9", "9 bit"), ("10", "10 bit"), ("11", "11 bit"), ("12", "12 bit"), ("13", "13 bit"), ("14", "14 bit"), ("15", "15 bit"), ("16", "16 bit")], isDynamic=False),
                ]
            )
        )
    
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
        APBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        memap2 = CortexM_AHBAP(self, self.findDevice("CSMEMAP_2"), "CSMEMAP_2")
        
        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSCTI_0"), "CSCTI_0")
        
        
        
        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        itm = M_Class_ITMTraceSource(self, self.findDevice("CSITM"), streamID, "CSITM", memap2)
        itm.setEnabled(False)
        streamID += 1
        
        stm = STMTraceSource(self, self.findDevice("CSSTM"), streamID, "CSSTM")
        stm.setEnabled(False)
        streamID += 1
        
        self.cortexM4cores = []
        for coreName in (coreNames_cortexM4):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
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
            
        self.cortexA7cores = []
        for coreName in (coreNames_cortexA7):
            # Create core
            coreDevice = a7_rams.A7CoreDevice(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-A7")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexA7cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            a7_rams.registerInternalRAMs(coreDevice)
            
            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
                self.registerCoreForCrossSync(coreDevice)
            
            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv3_5TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)
            
        tmc = CSTMC(self, self.findDevice("CSTMC"), "CSTMC")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tpiu = CSTPIU(self, self.findDevice("CSTPIU"), "CSTPIU")
        tpiu.setEnabled(False)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        
        # Create and Configure Funnels
        self.createFunnel("CSTFunnel")
        
        self.setupCTISyncSMP()
        
    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_1"), "APB bus accessed via AP 1 (CSMEMAP_1)"),
            AXIMemAPAccessor("AXI", self.getDeviceInterface("CSMEMAP_0"), "AXI bus accessed via AP 0 (CSMEMAP_0)", 32),
            AHBCortexMMemAPAccessor("AHB_M", self.getDeviceInterface("CSMEMAP_2"), "AHB-M bus accessed via AP 2 (CSMEMAP_2)"),
        ])
    
    def createTraceCapture(self):
        # ETF Devices
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC"), "CSTMC")
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
        
        coreTraceEnabled = self.getOptionValue("options.Cortex-A7_SMP_0.coreTrace")
        for core in range(len(clusterCores[0])):
            tmName = self.getTraceSourceNameForCore(clusterCores[0][core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A7_SMP_0.coreTrace.Cortex-A7_SMP_0_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                if(self.getOptionValue("options.Cortex-A7_SMP_0.coreTrace.traceRange")):
                    coreTM.clearAllTraceRanges()
                    coreTM.addTraceRange(self.getOptionValue("options.Cortex-A7_SMP_0.coreTrace.traceRange.start"),
                                         self.getOptionValue("options.Cortex-A7_SMP_0.coreTrace.traceRange.end"))
                coreTM.setTriggerGeneratesDBGRQ(self.getOptionValue("options.Cortex-A7_SMP_0.coreTrace.triggerhalt"))
                coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A7_SMP_0.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.Cortex-A7_SMP_0.coreTrace.contextIDs"),
                                     self.getOptionValue("options.Cortex-A7_SMP_0.coreTrace.contextIDs.contextIDsSize"))
        
        if self.getOptions().getOption("options.trace.traceCapture.dstream.tpiuPortWidth"):
            self.setPortWidth(int(self.getOptionValue("options.trace.traceCapture.dstream.tpiuPortWidth")))
        
        if self.getOptions().getOption("options.trace.traceCapture.dstream.traceBufferSize"):
            self.setTraceBufferSize(self.getOptionValue("options.trace.traceCapture.dstream.traceBufferSize"))
        
        itmEnabled = self.getOptionValue("options.itm.CSITM")
        self.setTraceSourceEnabled("CSITM", itmEnabled)
        
        stmEnabled = self.getOptionValue("options.stm.CSSTM")
        self.setTraceSourceEnabled("CSSTM", stmEnabled)
        
        self.configureTraceCapture(traceMode)
        
    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        
        for core in range(len(self.cortexA7cores)):
            a7_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA7cores[core])
            a7_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA7cores[core])
        
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
    
    def setupPinMuxForTrace(self):
        
        AXIAP = self.getDeviceInterface("CSMEMAP_0");
               
        # set up GPIO for off-chip trace
        AXIAP.writeMem(0x50000A28,0x000007FF)
        AXIAP.writeMem(0x5000080C,0x00000301)
        AXIAP.writeMem(0x5000C000,0xAAAAAAAA)
        AXIAP.writeMem(0x5000C008,0xAAAAAAAA)
        AXIAP.writeMem(0x5000C020,0x00000000)
        AXIAP.writeMem(0x5000C024,0x00000000)
        AXIAP.writeMem(0x5000C004,0x00000000)

        #GPIOJ CFG
        AXIAP.writeMem(0x5000B000,0xAAAAAAAA)
        AXIAP.writeMem(0x5000B008,0xAAAAAAAA)
        AXIAP.writeMem(0x5000B020,0x00000000)
        AXIAP.writeMem(0x5000B024,0x00000000)
        AXIAP.writeMem(0x5000B004,0x00000000)

        #GPIOF CFG
        AXIAP.writeMem(0x50007000,0xAAAAAAAA)
        AXIAP.writeMem(0x50007008,0xAAAAAAAA)
        AXIAP.writeMem(0x50007020,0x00000000)
        AXIAP.writeMem(0x50007024,0x00000000)

        #GPIOG CFG
        AXIAP.writeMem(0x50008000,0xAAAAAAAA)
        AXIAP.writeMem(0x50008008,0xAAAAAAAA)
        AXIAP.writeMem(0x50008020,0x00000000)
        AXIAP.writeMem(0x50008024,0x00000000)

        #GPIOB CFG
        AXIAP.writeMem(0x50003000,0xAAAAAAAA)
        AXIAP.writeMem(0x50003008,0xAAAAAAAA)
        AXIAP.writeMem(0x50003020,0x00000000)
        AXIAP.writeMem(0x50003024,0x00000000)

        #GPIOI CFG
        AXIAP.writeMem(0x5000A000,0xAAAAAAAA)
        AXIAP.writeMem(0x5000A008,0xAAAAAAAA)
        AXIAP.writeMem(0x5000A020,0x00000000)
        AXIAP.writeMem(0x5000A024,0x00000000)

        #GPIOJ CFG
        AXIAP.writeMem(0x50004000,0xAAAAAAAA)
        AXIAP.writeMem(0x50004008,0xAAAAAAAA)
        AXIAP.writeMem(0x50004020,0x00000000)
        AXIAP.writeMem(0x50004004,0x00000000)


    def postConnect(self):
        ConfigurationBaseSDF.postConnect(self)
        if self.getOptionValue("options.trace.traceCapture") == "DSTREAM":
            self.setupPinMuxForTrace()

        if self.getOptionValue("options.trace.traceCapture") == "CSTMC":
            #enable DBGCKEN and TRACECKEN
            AXIAP = self.getDeviceInterface("CSMEMAP_0");
            AXIAP.writeMem(0x5000080C,0x00000301)

        try:
            freq = self.getOptionValue("options.trace.timestampFrequency")
        except:
            return
        
        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)
    
class DtslScript_DSTREAM_ST(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)"), DtslScript_DSTREAM_ST.getOffChipTraceOption()],
                        setter=DtslScript_DSTREAM_ST.setTraceCaptureMethod),
                ])]
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M4_0', 'Enable Cortex-M4 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("Cortex-A7_SMP_0", "Cortex-A7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A7 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-A7_SMP_0_0', 'Enable Cortex-A7_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A7_SMP_0_1', 'Enable Cortex-A7_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ETMv3_5TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-A7_SMP_0")),
                            ETMv3_5TraceSource.dataOption(DtslScript.getSourcesForCluster("Cortex-A7_SMP_0")),
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
                    DTSLv1.booleanOption(coreNames_cortexA7[0], coreNames_cortexA7[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA7[1], coreNames_cortexA7[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM4[0], coreNames_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]
    
    @staticmethod
    def getOffChipTraceOption():
        return ("DSTREAM", "DSTREAM-ST Streaming Trace",
            DTSLv1.infoElement("dstream", "Off-Chip Trace", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")], isDynamic=False),
                    DTSLv1.enumOption('traceBufferSize', 'Trace Buffer Size', defaultValue="4GB",
                        values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"), ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"), ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                ]
            )
        )
    
    def createDSTREAM(self):
        self.DSTREAM = DSTREAMSTStoredTraceCapture(self, "DSTREAM")
    
    def createTraceCapture(self):
        DtslScript.createTraceCapture(self)
        self.addStreamTraceCaptureInterface(self.DSTREAM)
    

class DtslScript_DSTREAM_PT(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)"), DtslScript_DSTREAM_PT.getOffChipTraceOption()],
                        setter=DtslScript_DSTREAM_PT.setTraceCaptureMethod),
                ])]
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M4_0', 'Enable Cortex-M4 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("Cortex-A7_SMP_0", "Cortex-A7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A7 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-A7_SMP_0_0', 'Enable Cortex-A7_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A7_SMP_0_1', 'Enable Cortex-A7_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ETMv3_5TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-A7_SMP_0")),
                            ETMv3_5TraceSource.dataOption(DtslScript.getSourcesForCluster("Cortex-A7_SMP_0")),
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
                    DTSLv1.booleanOption(coreNames_cortexA7[0], coreNames_cortexA7[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA7[1], coreNames_cortexA7[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM4[0], coreNames_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]
    
    @staticmethod
    def getOffChipTraceOption():
        return ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement("dstream", "Off-Chip Trace", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit"), ("5", "5 bit"), ("6", "6 bit"), ("7", "7 bit"), ("8", "8 bit"), ("9", "9 bit"), ("10", "10 bit"), ("11", "11 bit"), ("12", "12 bit"), ("13", "13 bit"), ("14", "14 bit"), ("15", "15 bit"), ("16", "16 bit")], isDynamic=False),
                ]
            )
        )
    
    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")
    
    def createTraceCapture(self):
        DtslScript.createTraceCapture(self)
        self.addStreamTraceCaptureInterface(self.DSTREAM)
    

class DtslScript_DebugAndOnChipTrace(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)")],
                        setter=DtslScript_DebugAndOnChipTrace.setTraceCaptureMethod),
                ])]
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M4_0', 'Enable Cortex-M4 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("Cortex-A7_SMP_0", "Cortex-A7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A7 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-A7_SMP_0_0', 'Enable Cortex-A7_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A7_SMP_0_1', 'Enable Cortex-A7_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ETMv3_5TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-A7_SMP_0")),
                            ETMv3_5TraceSource.dataOption(DtslScript.getSourcesForCluster("Cortex-A7_SMP_0")),
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
                    DTSLv1.booleanOption(coreNames_cortexA7[0], coreNames_cortexA7[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA7[1], coreNames_cortexA7[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM4[0], coreNames_cortexM4[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]

