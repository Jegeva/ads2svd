# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceInfo
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSTPIU

clusterNames = ["Cortex-R52_SMP_0"]
clusterCores = [["Cortex-R52_0", "Cortex-R52_1"]]
coreNames_cortexR52 = ["Cortex-R52_0", "Cortex-R52_1"]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''


class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                            values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit"), ("5", "5 bit"), ("6", "6 bit"), ("7", "7 bit"), ("8", "8 bit"), ("9", "9 bit"), ("10", "10 bit"), ("11", "11 bit"), ("12", "12 bit"), ("13", "13 bit"), ("14", "14 bit"), ("15", "15 bit"), ("16", "16 bit")], isDynamic=False),
                    ]),
                ])]
                +[DTSLv1.tabPage("Cortex-R52_SMP_0", "Cortex-R52", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R52 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-R52_SMP_0_0', 'Enable Cortex-R52_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-R52_SMP_0_1', 'Enable Cortex-R52_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-R52_SMP_0")),
                            ETMv4TraceSource.dataOption(DtslScript.getSourcesForCluster("Cortex-R52_SMP_0")),
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
        APBAP(self, self.findDevice("CSMEMAP"), "CSMEMAP")
        
        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSCTI_2"), "CSCTI_2")
        
        
        
        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        self.cortexR52cores = []
        for coreName in (coreNames_cortexR52):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-R52")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexR52cores.append(coreDevice)
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
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP"), "APB bus accessed via AP 0 (CSMEMAP)"),
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
        
        coreTraceEnabled = self.getOptionValue("options.Cortex-R52_SMP_0.coreTrace")
        for core in range(len(clusterCores[0])):
            tmName = self.getTraceSourceNameForCore(clusterCores[0][core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.Cortex-R52_SMP_0.coreTrace.Cortex-R52_SMP_0_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                if(self.getOptionValue("options.Cortex-R52_SMP_0.coreTrace.traceRange")):
                    coreTM.clearAllTraceRanges()
                    coreTM.addTraceRange(self.getOptionValue("options.Cortex-R52_SMP_0.coreTrace.traceRange.start"),
                                         self.getOptionValue("options.Cortex-R52_SMP_0.coreTrace.traceRange.end"))
                coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-R52_SMP_0.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.Cortex-R52_SMP_0.coreTrace.contextIDs"),
                                     "32")
        
        if self.getOptions().getOption("options.trace.offChip.tpiuPortWidth"):
            self.setPortWidth(int(self.getOptionValue("options.trace.offChip.tpiuPortWidth")))
        
        if self.getOptions().getOption("options.trace.offChip.traceBufferSize"):
            self.setTraceBufferSize(self.getOptionValue("options.trace.offChip.traceBufferSize"))
        
        self.configureTraceCapture(traceMode)
        
    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        
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
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)"), ("DSTREAM", "DSTREAM-ST Streaming Trace")],
                        setter=DtslScript_DSTREAM_ST.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False),
                        DTSLv1.enumOption('traceBufferSize', 'Trace Buffer Size', defaultValue="4GB",
                            values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"), ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"), ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                    ]),
                ])]
                +[DTSLv1.tabPage("Cortex-R52_SMP_0", "Cortex-R52", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R52 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-R52_SMP_0_0', 'Enable Cortex-R52_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-R52_SMP_0_1', 'Enable Cortex-R52_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-R52_SMP_0")),
                            ETMv4TraceSource.dataOption(DtslScript.getSourcesForCluster("Cortex-R52_SMP_0")),
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
            )
        ]
    def createDSTREAM(self):
        self.DSTREAM = DSTREAMSTStoredTraceCapture(self, "DSTREAM")
    
    def createTraceCapture(self):
        DtslScript.createTraceCapture(self)
        self.addStreamTraceCaptureInterface(self.DSTREAM)
    

class DtslScript_DebugAndOnChipTrace(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)")],
                        setter=DtslScript_DebugAndOnChipTrace.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                ])]
                +[DTSLv1.tabPage("Cortex-R52_SMP_0", "Cortex-R52", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R52 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-R52_SMP_0_0', 'Enable Cortex-R52_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex-R52_SMP_0_1', 'Enable Cortex-R52_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-R52_SMP_0")),
                            ETMv4TraceSource.dataOption(DtslScript.getSourcesForCluster("Cortex-R52_SMP_0")),
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
            )
        ]

