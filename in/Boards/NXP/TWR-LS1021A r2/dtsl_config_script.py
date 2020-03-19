# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
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
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import CSATBReplicator

clusterNames = ["Cortex-A7_SMP_0"]
clusterCores = [["Cortex-A7_0", "Cortex-A7_1"]]
coreNames_cortexA7 = ["Cortex-A7_0", "Cortex-A7_1"]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''

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
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)")],
                        setter=DtslScript.setTraceCaptureMethod),
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
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer0', 'Configure the system memory trace buffer to be used by the CSTMC_2/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the CSTMC_2/ETR device',
                            defaultValue=0x90000000,
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
        AHBAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        APBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        
        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSCTI_3"), "CSCTI_3")
        
        CSCTI(self, self.findDevice("CSCTI_4"), "CSCTI_4")
        
        
        
        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        self.cortexA7cores = []
        # Ensure that macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
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
            
            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv3_5TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)
            
        tmc = CSTMC(self, self.findDevice("CSTMC_0"), "CSTMC_0")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("CSTMC_1"), "CSTMC_1")
        tmc.setMode(CSTMC.Mode.ETF)
        
        # Create and Configure Funnels
        self.createFunnel("CSTFunnel_0")
        self.createFunnel("CSTFunnel_1")
        
        # Replicators
        CSATBReplicator(self, self.findDevice("CSATBReplicator"), "CSATBReplicator")
        
        
        self.setupCTISyncSMP()
        
    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB", self.getDeviceInterface("CSMEMAP_0"), "AHB bus accessed via AP 0 (CSMEMAP_0)"),
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_1"), "APB bus accessed via AP 1 (CSMEMAP_1)"),
        ])
    
    def createTraceCapture(self):
        # ETF Devices
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_0"), "CSTMC_0")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_1"), "CSTMC_1")
        self.addTraceCaptureInterface(etfTrace)
        # ETR Capture
        self.createETRCapture()
    
    def createETRCapture(self):
        etr = ETRTraceCapture(self, self.findDevice("CSTMC_2"), "CSTMC_2")
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
            
        for core in range(len(self.cortexA7cores)):
            a7_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA7cores[core])
            a7_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA7cores[core])
        
    def addDeviceInterface(self, device):
        '''Add the device to the configuration and register its address filters'''
        ConfigurationBase.addDeviceInterface(self, device)
        self.registerFilters(device)
    
    def setTraceCaptureMethod(self, method):
        '''Simply call into the configuration to enable the trace capture device.
        CTI devices associated with the capture will also be configured'''
        self.enableTraceCapture(method)
    
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
    
class DtslScript_DSTREAM_ST(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)")],
                        setter=DtslScript_DSTREAM_ST.setTraceCaptureMethod),
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
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
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

class DtslScript_DSTREAM_PT(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)")],
                        setter=DtslScript_DSTREAM_PT.setTraceCaptureMethod),
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
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
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

class DtslScript_DebugAndOnChipTrace(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "System Memory Trace Buffer (CSTMC_2/ETR)")],
                        setter=DtslScript_DebugAndOnChipTrace.setTraceCaptureMethod),
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
                +[DTSLv1.tabPage("ETR", "ETR", childOptions=[
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

