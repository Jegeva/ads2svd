# Copyright (C) 2018-2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
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
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import ITMTraceSource

from com.arm.rddi import RDDI_ACC_SIZE
from jarray import zeros
from java.lang import StringBuilder

coreNames_cortexA9 = ["Cortex-A9"]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''

class DtslScript(ConfigurationBaseSDF):

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False),
                    ]),
                ])

    @staticmethod
    def getOptionCortexA9TabPage():
        return DTSLv1.tabPage("cortexA9", "Cortex-A9", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_A9_0', 'Enable Cortex-A9 trace', defaultValue=True),
                            DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", defaultValue=False),
                            DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the output of context ID values into the PTM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            PTMTraceSource.cycleAccurateOption(DtslScript.getSourcesForCoreType("cortexA9")),
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
    def getOptionITMTabPage():
        return DTSLv1.tabPage("itm", "ITM", childOptions=[
                    DTSLv1.booleanOption('CSITM', 'Enable CSITM trace', defaultValue=False),
                ])

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionITMTabPage()
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
        AHBAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        APBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        
        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSCTI_1"), "CSCTI_1")
        
        
        
        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        itm = ITMTraceSource(self, self.findDevice("CSITM"), streamID, "CSITM")
        itm.setEnabled(False)
        streamID += 1
        
        self.cortexA9cores = []
        for coreName in (coreNames_cortexA9):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-A9")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexA9cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            
            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
            
            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = PTMTraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)
            
        tmc = CSTMC(self, self.findDevice("CSTMC"), "CSTMC")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tpiu = CSTPIU(self, self.findDevice("CSTPIU"), "CSTPIU")
        tpiu.setEnabled(False)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        
        # Create and Configure Funnels
        self.createFunnel("CSTFunnel")
        
    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB", self.getDeviceInterface("CSMEMAP_0"), "AHB bus accessed via AP 0 (CSMEMAP_0)"),
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_1"), "APB bus accessed via AP 1 (CSMEMAP_1)"),
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

    def postConnect(self):
        DTSLv1.postConnect(self)
        
        self.setupTrace()
        self.setupTracePins()

    def setupTrace(self):
        APB = self.getDeviceInterface("CSMEMAP_1")
        
        # Lock Access Register (writeonly)
        # Write 0xC5ACCE55 to 0xFC00FFB0 or 0x8000FFB0
        APB.writeMem(0x8000FFB0, 0xC5ACCE55)
        
        # Address 0x8000F004 or 0xFC00F004
        # Bit 20 TRCMUX_SEL - set to 1 to enable trace output
        APB.writeMem(0x8000F004, 0x00100000)

    def setupTracePins(self):
        AHB = self.getDeviceInterface("CSMEMAP_0")
        
        # enable writing to PFS register
        # set $Peripherals::$GPIO::$GPIO_PWPR.B0WI = 0x0
        # set $Peripherals::$GPIO::$GPIO_PWPR.PFSWE = 0x1
        # #0xFCFFE2FF = $Peripherals::$GPIO::$GPIO_PWPR
        AHB.writeMem(0xFCFFE2FF, RDDI_ACC_SIZE.RDDI_ACC_BYTE, False, 0x40)
        
        # set pins to output trace
        # set $Peripherals::$GPIO::$GPIO_PJ0PFS.PSEL = 0x1
        AHB.writeMem(0xFCFFE290, RDDI_ACC_SIZE.RDDI_ACC_BYTE, False, 0x01)
        
        # set $Peripherals::$GPIO::$GPIO_PJ1PFS.PSEL = 0x1
        AHB.writeMem(0xFCFFE291, RDDI_ACC_SIZE.RDDI_ACC_BYTE, False, 0x01)
        
        # set $Peripherals::$GPIO::$GPIO_PJ2PFS.PSEL = 0x1
        AHB.writeMem(0xFCFFE292, RDDI_ACC_SIZE.RDDI_ACC_BYTE, False, 0x01)
        
        # set $Peripherals::$GPIO::$GPIO_PJ3PFS.PSEL = 0x1
        AHB.writeMem(0xFCFFE293, RDDI_ACC_SIZE.RDDI_ACC_BYTE, False, 0x01)
        
        # set $Peripherals::$GPIO::$GPIO_PJ4PFS.PSEL = 0x1
        AHB.writeMem(0xFCFFE294, RDDI_ACC_SIZE.RDDI_ACC_BYTE, False, 0x01)
        
        # set $Peripherals::$GPIO::$GPIO_PJ5PFS.PSEL = 0x1
        AHB.writeMem(0xFCFFE295, RDDI_ACC_SIZE.RDDI_ACC_BYTE, False, 0x01)
        
        # set $Peripherals::$GPIO::$GPIO_PJ6PFS.PSEL = 0x6
        AHB.writeMem(0xFCFFE296, RDDI_ACC_SIZE.RDDI_ACC_BYTE, False, 0x06)
        
        # set $Peripherals::$GPIO::$GPIO_PJ7PFS.PSEL = 0x6
        AHB.writeMem(0xFCFFE297, RDDI_ACC_SIZE.RDDI_ACC_BYTE, False, 0x06)
    
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
        
        coreTraceEnabled = self.getOptionValue("options.cortexA9.coreTrace")
        for core in range(len(coreNames_cortexA9)):
            tmName = self.getTraceSourceNameForCore(coreNames_cortexA9[core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.cortexA9.coreTrace.Cortex_A9_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                if(self.getOptionValue("options.cortexA9.coreTrace.traceRange")):
                    coreTM.clearAllTraceRanges()
                    coreTM.addTraceRange(self.getOptionValue("options.cortexA9.coreTrace.traceRange.start"),
                                         self.getOptionValue("options.cortexA9.coreTrace.traceRange.end"))
                coreTM.setTriggerGeneratesDBGRQ(self.getOptionValue("options.cortexA9.coreTrace.triggerhalt"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexA9.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexA9.coreTrace.contextIDs.contextIDsSize"))
        
        if self.getOptions().getOption("options.trace.offChip.tpiuPortWidth"):
            self.setPortWidth(int(self.getOptionValue("options.trace.offChip.tpiuPortWidth")))
        
        if self.getOptions().getOption("options.trace.offChip.traceBufferSize"):
            self.setTraceBufferSize(self.getOptionValue("options.trace.offChip.traceBufferSize"))
        
        itmEnabled = self.getOptionValue("options.itm.CSITM")
        self.setTraceSourceEnabled("CSITM", itmEnabled)
        
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
    def getSourcesForCoreType(coreType):
        '''Get the Trace Sources for a given coreType
           Use parameter-binding to ensure that the correct Sources
           are returned for the core type passed only'''
        def getSources(self):
            return self.getTraceSourcesForCoreType(coreType)
        return getSources

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def createTraceCapture(self):
        DtslScript.createTraceCapture(self)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_ST.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)")],
                        setter=DtslScript_DSTREAM_ST.setTraceCaptureMethod)
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMSTStoredTraceCapture(self, "DSTREAM")

class DtslScript_DSTREAM_PT(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_PT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)"), ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer")],
                        setter=DtslScript_DSTREAM_PT.setTraceCaptureMethod),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False)
                    ])
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")

class DtslScript_DebugAndOnChipTrace(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DebugAndOnChipTrace.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC", "On Chip Trace Buffer (CSTMC/ETF)")],
                        setter=DtslScript_DebugAndOnChipTrace.setTraceCaptureMethod),
                ])
