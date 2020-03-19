# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import Device, ConnectableDevice
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import STMTraceSource

from com.arm.rddi import RDDI
from com.arm.rddi import RDDI_JTAGS_STATE
from com.arm.rddi import RDDI_JTAGS_IR_DR
from jarray import zeros

clusterNames = ["Cortex-A72_SMP_0"]
clusterCores = [["Cortex-A72_0", "Cortex-A72_1", "Cortex-A72_2", "Cortex-A72_3"]]
coreNames_cortexM3 = ["SB0_Cortex-M3", "SB1_Cortex-M3"]
coreNames_cortexA72 = ["Cortex-A72_0", "Cortex-A72_1", "Cortex-A72_2", "Cortex-A72_3"]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''

# Import core specific functions
import a72_rams

            
    
class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("SB0_ETF", "On Chip Trace Buffer (SB0_ETF/ETF)"), ("SB0_ETR", "System Memory Trace Buffer (SB0_ETR/ETR)"), ("AP806_ETF_0", "On Chip Trace Buffer (AP806_ETF_0/ETF)"), ("AP806_ETF_1", "On Chip Trace Buffer (AP806_ETF_1/ETF)"), ("AP806_ETF_2", "On Chip Trace Buffer (AP806_ETF_2/ETF)"), ("AP806_ETF_3", "On Chip Trace Buffer (AP806_ETF_3/ETF)"), ("AP806_ETF_4", "On Chip Trace Buffer (AP806_ETF_4/ETF)"), ("AP806_ETR", "System Memory Trace Buffer (AP806_ETR/ETR)"), ("SB1_ETF", "On Chip Trace Buffer (SB1_ETF/ETF)"), ("SB1_ETR", "System Memory Trace Buffer (SB1_ETR/ETR)")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                ])]
                +[DTSLv1.tabPage("Cortex-A72_SMP_0", "Cortex-A72", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A72 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-A72_SMP_0_0', 'Enable Cortex-A72_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A72_SMP_0_1', 'Enable Cortex-A72_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A72_SMP_0_2', 'Enable Cortex-A72_2 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A72_SMP_0_3', 'Enable Cortex-A72_3 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-A72_SMP_0")),
                        ]
                    ),
                ])]
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer0', 'Configure the system memory trace buffer to be used by the SB0_ETR/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the SB0_ETR/ETR device',
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
                    DTSLv1.booleanOption('etrBuffer1', 'Configure the system memory trace buffer to be used by the AP806_ETR/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the AP806_ETR/ETR device',
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
                    DTSLv1.booleanOption('etrBuffer2', 'Configure the system memory trace buffer to be used by the SB1_ETR/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the SB1_ETR/ETR device',
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
                    DTSLv1.booleanOption('SB0_STM', 'Enable SB0_STM trace', defaultValue=False),
                    DTSLv1.booleanOption('AP806_STM', 'Enable AP806_STM trace', defaultValue=False),
                    DTSLv1.booleanOption('SB1_STM', 'Enable SB1_STM trace', defaultValue=False),
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
        ConfigurationBaseSDF.__init__(self, root)
        
        self.discoverDevices()
        self.createTraceCapture()
    
    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+
    
    def discoverDevices(self):
        '''Find and create devices'''
        
        #MemAp devices
        AXIAP(self, self.findDevice("AXI_SB0"), "AXI_SB0")
        APBAP(self, self.findDevice("APB_SB0"), "APB_SB0")
        CortexM_AHBAP(self, self.findDevice("AHB_SB0"), "AHB_SB0")
        AXIAP(self, self.findDevice("AXI_AP806"), "AXI_AP806")
        APBAP(self, self.findDevice("APB_AP806"), "APB_AP806")
        AHBAP(self, self.findDevice("AHB_AP806"), "AHB_AP806")
        AXIAP(self, self.findDevice("AXI_SB1"), "AXI_SB1")
        APBAP(self, self.findDevice("APB_SB1"), "APB_SB1")
        CortexM_AHBAP(self, self.findDevice("AHB_SB1"), "AHB_SB1")
        
        gpr = []
        gpr.append(ConnectableDevice(self, self.findDevice("SB0_GPR"), "SB0_GPR"))
        gpr.append(ConnectableDevice(self, self.findDevice("SB1_GPR"), "SB1_GPR"))
        gpr.append(ConnectableDevice(self, self.findDevice("AP806_GPR"), "AP806_GPR"))
        
        self.gpr = gpr
        
        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("SB0_ETF_ETR_CTI"), "SB0_ETF_ETR_CTI")
        
        CSCTI(self, self.findDevice("AP806_ETF0123_CTI"), "AP806_ETF0123_CTI")
        
        CSCTI(self, self.findDevice("AP806_ETF_ETR_CTI"), "AP806_ETF_ETR_CTI")
        
        CSCTI(self, self.findDevice("SB1_ETF_ETR_CTI"), "SB1_ETF_ETR_CTI")
        
        
        
        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        stm = STMTraceSource(self, self.findDevice("SB0_STM"), streamID, "SB0_STM")
        stm.setEnabled(False)
        streamID += 1
        
        stm = STMTraceSource(self, self.findDevice("AP806_STM"), streamID, "AP806_STM")
        stm.setEnabled(False)
        streamID += 1
        
        stm = STMTraceSource(self, self.findDevice("SB1_STM"), streamID, "SB1_STM")
        stm.setEnabled(False)
        streamID += 1
        
        self.cortexM3cores = []
        for coreName in (coreNames_cortexM3):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
            self.cortexM3cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            
            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
            
        self.cortexA72cores = []
        for coreName in (coreNames_cortexA72):
            # Create core
            coreDevice = a72_rams.A72CoreDevice(self, self.findDevice(coreName), coreName)
            self.cortexA72cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            a72_rams.registerInternalRAMs(coreDevice)
            
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
            
        tmc = CSTMC(self, self.findDevice("SB0_ETF"), "SB0_ETF")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("AP806_ETF_0"), "AP806_ETF_0")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("AP806_ETF_1"), "AP806_ETF_1")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("AP806_ETF_2"), "AP806_ETF_2")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("AP806_ETF_3"), "AP806_ETF_3")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("AP806_ETF_4"), "AP806_ETF_4")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("SB1_ETF"), "SB1_ETF")
        tmc.setMode(CSTMC.Mode.ETF)
        
        # Create and Configure Funnels
        self.createFunnel("AP806_Funnel")
        
        self.setupCTISyncSMP()
        
    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB_AP806", self.getDeviceInterface("AHB_AP806"), "AHB bus accessed via AP 2 (AHB_AP806)"),
            AxBMemAPAccessor("APB_SB0", self.getDeviceInterface("APB_SB0"), "APB bus accessed via AP 1 (APB_SB0)"),
            AxBMemAPAccessor("APB_AP806", self.getDeviceInterface("APB_AP806"), "APB bus accessed via AP 1 (APB_AP806)"),
            AxBMemAPAccessor("APB_SB1", self.getDeviceInterface("APB_SB1"), "APB bus accessed via AP 1 (APB_SB1)"),
            AXIMemAPAccessor("AXI_SB0", self.getDeviceInterface("AXI_SB0"), "AXI bus accessed via AP 0 (AXI_SB0)", 64),
            AXIMemAPAccessor("AXI_AP806", self.getDeviceInterface("AXI_AP806"), "AXI bus accessed via AP 0 (AXI_AP806)", 64),
            AXIMemAPAccessor("AXI_SB1", self.getDeviceInterface("AXI_SB1"), "AXI bus accessed via AP 0 (AXI_SB1)", 64),
            AHBCortexMMemAPAccessor("AHB_SB0", self.getDeviceInterface("AHB_SB0"), "AHB-M bus accessed via AP 2 (AHB_SB0)"),
            AHBCortexMMemAPAccessor("AHB_SB1", self.getDeviceInterface("AHB_SB1"), "AHB-M bus accessed via AP 2 (AHB_SB1)"),
        ])
    
    def createTraceCapture(self):
        # ETF Devices
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("SB0_ETF"), "SB0_ETF")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("AP806_ETF_0"), "AP806_ETF_0")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("AP806_ETF_1"), "AP806_ETF_1")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("AP806_ETF_2"), "AP806_ETF_2")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("AP806_ETF_3"), "AP806_ETF_3")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("AP806_ETF_4"), "AP806_ETF_4")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("SB1_ETF"), "SB1_ETF")
        self.addTraceCaptureInterface(etfTrace)
        # ETR Devices
        etr = ETRTraceCapture(self, self.findDevice("SB0_ETR"), "SB0_ETR")
        self.addTraceCaptureInterface(etr)
        etr = ETRTraceCapture(self, self.findDevice("AP806_ETR"), "AP806_ETR")
        self.addTraceCaptureInterface(etr)
        etr = ETRTraceCapture(self, self.findDevice("SB1_ETR"), "SB1_ETR")
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
        
        coreTraceEnabled = self.getOptionValue("options.Cortex-A72_SMP_0.coreTrace")
        for core in range(len(clusterCores[0])):
            tmName = self.getTraceSourceNameForCore(clusterCores[0][core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A72_SMP_0.coreTrace.Cortex-A72_SMP_0_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A72_SMP_0.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.Cortex-A72_SMP_0.coreTrace.contextIDs"),
                                     "32")
        
        stmEnabled = self.getOptionValue("options.stm.SB0_STM")
        self.setTraceSourceEnabled("SB0_STM", stmEnabled)
        
        stmEnabled = self.getOptionValue("options.stm.AP806_STM")
        self.setTraceSourceEnabled("AP806_STM", stmEnabled)
        
        stmEnabled = self.getOptionValue("options.stm.SB1_STM")
        self.setTraceSourceEnabled("SB1_STM", stmEnabled)
        
        self.configureTraceCapture(traceMode)
        
    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        
        # Set up the ETR 0 buffer
        configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer0")
        if configureETRBuffer:
            etr = self.getTraceCaptureInterfaces()["SB0_ETR"]
            etr.setBaseAddress(self.getOptionValue("options.ETR.etrBuffer0.start"))
            etr.setTraceBufferSize(self.getOptionValue("options.ETR.etrBuffer0.size"))
            etr.setScatterGatherModeEnabled(self.getOptionValue("options.ETR.etrBuffer0.scatterGather"))
            
        # Set up the ETR 1 buffer
        configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer1")
        if configureETRBuffer:
            etr = self.getTraceCaptureInterfaces()["AP806_ETR"]
            etr.setBaseAddress(self.getOptionValue("options.ETR.etrBuffer1.start"))
            etr.setTraceBufferSize(self.getOptionValue("options.ETR.etrBuffer1.size"))
            etr.setScatterGatherModeEnabled(self.getOptionValue("options.ETR.etrBuffer1.scatterGather"))
            
        # Set up the ETR 2 buffer
        configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer2")
        if configureETRBuffer:
            etr = self.getTraceCaptureInterfaces()["SB1_ETR"]
            etr.setBaseAddress(self.getOptionValue("options.ETR.etrBuffer2.start"))
            etr.setTraceBufferSize(self.getOptionValue("options.ETR.etrBuffer2.size"))
            etr.setScatterGatherModeEnabled(self.getOptionValue("options.ETR.etrBuffer2.scatterGather"))
            
        for core in range(len(self.cortexA72cores)):
            a72_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA72cores[core])
            a72_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA72cores[core])
        
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
    
    def makebyte(self, val):
        return val > 127 and val - 256 or val
    
    def postRDDIConnect(self):
        try:
            STATE_RTI = RDDI_JTAGS_STATE.RDDI_JTAGS_RTI.ordinal()
            STATE_PIR = RDDI_JTAGS_STATE.RDDI_JTAGS_PIR.ordinal()
            STATE_PDR = RDDI_JTAGS_STATE.RDDI_JTAGS_PDR.ordinal()
            CHAIN_IR = RDDI_JTAGS_IR_DR.RDDI_JTAGS_IR.ordinal()
            CHAIN_DR = RDDI_JTAGS_IR_DR.RDDI_JTAGS_DR.ordinal()
            
            jtag = self.getJTAG()
            pVer = zeros (1,'i')
            jtag.connect(pVer)
            jtag.setUseRTCLK(0)
            jtag.setJTAGClock(25000000)
            jtag.TMS(8, [0x1f])
            jtag.stateJump(STATE_RTI)
            
            IRin = zeros(8, 'b')
            DRin = zeros(32, 'b')
            IRout = zeros(8, 'b')
            DRout = zeros(32, 'b')
            
            IRin[0] = self.makebyte(0xff)
            IRin[1] = self.makebyte(0xff)
            IRin[2] = self.makebyte(0x5f)
            
            DRin[0] = self.makebyte(0xff)
            
            jtag.scanIO(CHAIN_IR, 24, IRin, IRout, STATE_PIR, 0)
            jtag.scanIO(CHAIN_DR, 44, DRin, DRout, STATE_PDR, 0)

            IRin[0] = self.makebyte(0xcb)
            IRin[1] = self.makebyte(0xb2)
            IRin[2] = self.makebyte(0x8c)
            
            DRin[0] = self.makebyte(0x07)
            DRin[4] = self.makebyte(0x0c)
            DRin[8] = self.makebyte(0x18)
            DRin[12] = self.makebyte(0x10)

            jtag.scanIO(CHAIN_IR, 24, IRin, IRout, STATE_PIR, 0)
            jtag.scanIO(CHAIN_DR, 101, DRin, DRout, STATE_RTI, 1)

            #IRin[0] = self.makebyte(0xbb)
            #IRin[1] = self.makebyte(0xe8)
            #IRin[2] = self.makebyte(0xa2)
            #IRin[3] = self.makebyte(0x8b)
            #IRin[4] = self.makebyte(0x08)
            #
            #for i in range(len(DRin)):
            #    DRin[i] = self.makebyte(0xaa)
            #
            #jtag.scanIO(CHAIN_IR, 36, IRin, IRout, STATE_PIR, 0)
            #jtag.scanIO(CHAIN_DR, 228, DRin, DRout, STATE_PDR, 0)

        finally:
            if jtag:
                jtag.disconnect()

        # then call base implementation
        DTSLv1.postRDDIConnect(self)

    def postConnect(self):
        for req in self.gpr: # MORE POWER!!!!
            if not req.isConnected():
                 req.connect()
            req.writeRegister(0, 0xFFFFFFFF)
            if req.isConnected():
                req.disconnect()
        
        ConfigurationBaseSDF.postConnect(self)
        
        try:
            freq = self.getOptionValue("options.trace.traceOpts.timestampFrequency")
        except:
            return
        
        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)

class DtslScript_DSTREAM_ST(DtslScript):

    @staticmethod
    def getOptionList():
        return DtslScript.getOptionList()

class DtslScript_DSTREAM_PT(DtslScript):

    @staticmethod
    def getOptionList():
        return DtslScript.getOptionList()
