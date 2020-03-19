# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl import DTSLException
from com.arm.rddi import RDDI
from com.arm.rddi import RDDI_JTAGS_STATE
from com.arm.rddi import RDDI_JTAGS_IR_DR
from jarray import zeros
import time

clusterNames = ["Cortex-A53_SMP_0"]
clusterCores = [["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]]
coreNames_cortexR5 = ["Cortex-R5_0", "Cortex-R5_1"]
coreNames_cortexA53 = ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''

# import core specific functions from Cores folder
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a53_rams

class DtslScript(ConfigurationBaseSDF):

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "Cortex-A Cluster On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "System On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                            values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False),
                    ]),
                ])

    @staticmethod
    def getOptionCortexR5TabPage():
        return DTSLv1.tabPage("cortexR5", "Cortex-R5", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R5 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_R5_0', 'Enable Cortex-R5_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex_R5_1', 'Enable Cortex-R5_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ETMv3_3TraceSource.cycleAccurateOption(DtslScript.getSourcesForCoreType("cortexR5")),
                            ETMv3_3TraceSource.dataOption(DtslScript.getSourcesForCoreType("cortexR5")),
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
                        ]
                    ),
                ])

    @staticmethod
    def getOptionETRTabPage():
        return DTSLv1.tabPage("ETR", "ETR", childOptions=[
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
                ])

    @staticmethod
    def getOptionSTMTabPage():
        return DTSLv1.tabPage("stm", "STM", childOptions=[
                    DTSLv1.booleanOption('CSSTM', 'Enable CSSTM trace', defaultValue=False),
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
    def getOptionCTISyncPage():
        return DTSLv1.tabPage("sync", "CTI Synchronization", childOptions=[
                    DTSLv1.booleanOption(coreNames_cortexR5[0], coreNames_cortexR5[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexR5[1], coreNames_cortexR5[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[0], coreNames_cortexA53[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[1], coreNames_cortexA53[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[2], coreNames_cortexA53[2], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexA53[3], coreNames_cortexA53[3], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexR5TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionRAMTabPage(),
                DtslScript.getOptionCTISyncPage()
            ])
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
        APBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        
        
        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        stm = STMTraceSource(self, self.findDevice("CSSTM"), streamID, "CSSTM")
        stm.setEnabled(False)
        streamID += 1
        
        self.cortexR5cores = []
        for coreName in (coreNames_cortexR5):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
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
            
        self.cortexA53cores = []
        for coreName in (coreNames_cortexA53):
            # Create core
            coreDevice = a53_rams.A53CoreDevice(self, self.findDevice(coreName), coreName)
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
            
        tmc = CSTMC(self, self.findDevice("CSTMC_0"), "CSTMC_0")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("CSTMC_1"), "CSTMC_1")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tpiu = CSTPIU(self, self.findDevice("CSTPIU"), "CSTPIU")
        tpiu.setEnabled(False)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        
        # Create and Configure Funnels
        self.createFunnel("CSTFunnel_0")
        self.createFunnel("CSTFunnel_1")
        self.createFunnel("CSTFunnel_2")
        
        self.setupCTISyncSMP()
        
    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AxBMemAPAccessor("APB_0", self.getDeviceInterface("CSMEMAP_1"), "APB bus accessed via AP 1 (CSMEMAP_1)"),
            AXIMemAPAccessor("AXI_0", self.getDeviceInterface("CSMEMAP_0"), "AXI bus accessed via AP 0 (CSMEMAP_0)", 64),
        ])
    
    def createTraceCapture(self):
        # ETF Devices
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_0"), "CSTMC_0")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_1"), "CSTMC_1")
        self.addTraceCaptureInterface(etfTrace)
        # ETR Devices
        etr = ETRTraceCapture(self, self.findDevice("CSTMC_2"), "CSTMC_2")
        self.addTraceCaptureInterface(etr)
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
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexR5.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexR5.coreTrace.contextIDs.contextIDsSize"))
        
        coreTraceEnabled = self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace")
        for core in range(len(clusterCores[0])):
            tmName = self.getTraceSourceNameForCore(clusterCores[0][core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.Cortex-A53_SMP_0_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.contextIDs"),
                                     "32")
        
        if self.getOptions().getOption("options.trace.offChip.tpiuPortWidth"):
            self.setPortWidth(int(self.getOptionValue("options.trace.offChip.tpiuPortWidth")))
        
        if self.getOptions().getOption("options.trace.offChip.traceBufferSize"):
            self.setTraceBufferSize(self.getOptionValue("options.trace.offChip.traceBufferSize"))
        
        stmEnabled = self.getOptionValue("options.stm.CSSTM")
        self.setTraceSourceEnabled("CSSTM", stmEnabled)
        
        self.configureTraceCapture(traceMode)
        
    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        
        # Set up the ETR 0 buffer
        configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer0")
        if configureETRBuffer:
            etr = self.getTraceCaptureInterfaces()["CSTMC_2"]
            etr.setBaseAddress(self.getOptionValue("options.ETR.etrBuffer0.start"))
            etr.setTraceBufferSize(self.getOptionValue("options.ETR.etrBuffer0.size"))
            etr.setScatterGatherModeEnabled(self.getOptionValue("options.ETR.etrBuffer0.scatterGather"))
            
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

    def resetTarget(self, resetType, targetDevice):
        # need to sort out properly what to do on Reset
        pass

    def connect(self):
        # do preconnect scans here
        pVer = zeros (1,'i')
        myOnes = [0x1F]

        try:
            myJTAG = self.getJTAG()
            myJTAG.connect(pVer)
            myJTAG.setJTAGClock(1000000)
            myJTAG.TMS(5, myOnes)
            TDIData = [0x24, 0x08]
            # now move from TLR -> Shift-IR
            TMSscans = [0x06]
            myJTAG.TMS(5, TMSscans)
            myJTAG.TDIO(12, TDIData, None, 1)
             
            #myJTAG.scanIO(RDDI_JTAGS_IR_DR.RDDI_JTAGS_IR.ordinal(), 12, TDOData, TDIData,RDDI_JTAGS_STATE.RDDI_JTAGS_RTI.ordinal(), 1)

            TMSScans = [0x05]
            myJTAG.TMS(5, TMSScans) # now round to Shift-DR
            TDIData = [0x02, 0x00, 0x00, 0x00]
            myJTAG.TDIO(32, TDIData, None, 1)
            TMSScans = [ 0x01 ]
            myJTAG.TMS(2, TMSScans) # to RTI
            #myJTAG.scanIO(RDDI_JTAGS_IR_DR.RDDI_JTAGS_DR.ordinal(), 32, TDOData, TDIData, RDDI_JTAGS_STATE.RDDI_JTAGS_RTI.ordinal(), 1)
            myJTAG.TMS(5, myOnes)
        finally:
            if myJTAG:
                myJTAG.disconnect()
                time.sleep(0.5)

        # then call base implementation
        ConfigurationBaseSDF.connect(self)
    
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
    
class DtslScript_DSTREAM_ST(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_ST.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexR5TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionRAMTabPage(),
                DtslScript.getOptionCTISyncPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)")],
                        setter=DtslScript_DSTREAM_ST.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ])
                ])

class DtslScript_DSTREAM_PT(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_PT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexR5TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionRAMTabPage(),
                DtslScript.getOptionCTISyncPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)"), ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer")],
                        setter=DtslScript_DSTREAM_PT.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                            values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False)]),
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")

class DtslScript_RVI(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_RVI.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexR5TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionRAMTabPage(),
                DtslScript.getOptionCTISyncPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "Cortex-A Cluster On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "System On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)")],
                        setter=DtslScript_RVI.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                ])
