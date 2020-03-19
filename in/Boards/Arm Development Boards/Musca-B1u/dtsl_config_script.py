# Copyright (C) 2018-2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceInfo
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTLiveStoredStreamingTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import ITMTraceSource

from struct import pack, unpack
from jarray import array, zeros
from java.lang import Byte
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE

coreNames_cortexM33 = ["Cortex-M33_0", "Cortex-M33_1"]

class CacheMaintCore(Device):

    def __init__(self, config, id, name, clearCPUWAITRegOnConnect=False):
        Device.__init__(self, config, id, name)
        self.clearCPUWAITRegOnConnect = clearCPUWAITRegOnConnect

    def to_s8(self, val):
        return val > 127 and val - 256 or val

    def openConn(self, pId, pVersion, pMessage):
        Device.openConn(self, pId, pVersion, pMessage)
        if self.clearCPUWAITRegOnConnect:
            buf = zeros(4,'b')
            self.memWrite(0x0, 0x50021118, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)

    def memRead(self, page, address, size, rule, count, pDataOut):
        Device.memRead(self, page, address, size, rule, count, pDataOut)

    def __invalidate_Icache(self):
        buf = zeros(4,'b')
        # Read I cache control register
        Device.memRead(self, 0x0, 0x50010004, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)

        # If I cache is enabled, invalidate all
        if buf[0] & 0x1:
            buf[0] = buf[0] | 0x4
            self.memWrite(0x0,  0x50010004, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)

    def setSWBreak(self, page, addr, flags):
        brkID = Device.setSWBreak(self, page, addr, flags)
        self.__invalidate_Icache()
        return brkID

    def memWrite(self, page, addr, size, rule, check, count, data):
        Device.memWrite(self, page, addr, size, rule, check, count, data)

class M_Class_ETMv4(ETMv4TraceSource):

    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False

class DtslScript(ConfigurationBaseSDF):

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), DtslScript.getOffChipTraceOption()])
                ])

    @staticmethod
    def getOffChipTraceOption():
        return ("DSTREAM", "DSTREAM 4GB Trace Buffer",
            DTSLv1.infoElement("dstream", "Off-Chip Trace", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False),
                ]
            )
        )

    @staticmethod
    def getOptionCortexM33TabPage():
        return DTSLv1.tabPage("cortexM33", "Cortex-M33", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M33 core trace', defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex_M33_0', 'Enable Cortex-M33_0 trace', defaultValue=True),
                            DTSLv1.booleanOption('Cortex_M33_1', 'Enable Cortex-M33_1 trace', defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCoreType("cortexM33")),
                        ]
                    ),
                ])

    @staticmethod
    def getOptionITMTabPage():
        return DTSLv1.tabPage("itm", "ITM", childOptions=[
                    DTSLv1.booleanOption('CSITM_0', 'Enable CSITM_0 trace', defaultValue=False),
                    DTSLv1.booleanOption('CSITM_1', 'Enable CSITM_1 trace', defaultValue=False),
                ])

    @staticmethod
    def getOptionCTISyncPage():
        return DTSLv1.tabPage("sync", "CTI Synchronization", childOptions=[
                    DTSLv1.booleanOption(coreNames_cortexM33[0], coreNames_cortexM33[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM33[1], coreNames_cortexM33[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexM33TabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionCTISyncPage()
            ])
        ]

    def __init__(self, root):
        ConfigurationBaseSDF.__init__(self, root)

        self.discoverDevices()

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        #MemAp devices
        APBAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        CortexM_AHBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        AHBAP(self, self.findDevice("CSMEMAP_2"), "CSMEMAP_2")
        CortexM_AHBAP(self, self.findDevice("CSMEMAP_3"), "CSMEMAP_3")
        AHBAP(self, self.findDevice("CSMEMAP_4"), "CSMEMAP_4")

        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSCTI_1"), "CSCTI_1")

        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        itm = ITMTraceSource(self, self.findDevice("CSITM_0"), streamID, "CSITM_0")
        itm.setEnabled(False)
        streamID += 1

        itm = ITMTraceSource(self, self.findDevice("CSITM_1"), streamID, "CSITM_1")
        itm.setEnabled(False)
        streamID += 1

        self.cortexM33cores = []
        for coreName in (coreNames_cortexM33):
            # Create core
            coreDevice = CacheMaintCore(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-M33")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexM33cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)

            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
                self.registerCoreForCrossSync(coreDevice)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = M_Class_ETMv4(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)

        tpiu = CSTPIU(self, self.findDevice("CSTPIU"), "CSTPIU")
        tpiu.setEnabled(False)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)

        # Create and Configure Funnels
        self.createFunnel("CSTFunnel_0")
        self.createFunnel("CSTFunnel_1")

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB_0", self.getDeviceInterface("CSMEMAP_2"), "AHB bus accessed via AP 2 (CSMEMAP_2)"),
            AHBMemAPAccessor("AHB_1", self.getDeviceInterface("CSMEMAP_4"), "AHB bus accessed via AP 17 (CSMEMAP_4)"),
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_0"), "APB bus accessed via AP 0 (CSMEMAP_0)"),
            AHBCortexMMemAPAccessor("AHB_M_0", self.getDeviceInterface("CSMEMAP_1"), "AHB-M bus accessed via AP 1 (CSMEMAP_1)"),
            AHBCortexMMemAPAccessor("AHB_M_1", self.getDeviceInterface("CSMEMAP_3"), "AHB-M bus accessed via AP 16 (CSMEMAP_3)"),
        ])

    def createTraceCapture(self):
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

        coreTraceEnabled = self.getOptionValue("options.cortexM33.coreTrace")
        for core in range(len(coreNames_cortexM33)):
            tmName = self.getTraceSourceNameForCore(coreNames_cortexM33[core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.cortexM33.coreTrace.Cortex_M33_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                coreTM.setTimestampingEnabled(self.getOptionValue("options.cortexM33.coreTrace.timestamp"))

        itmEnabled = self.getOptionValue("options.itm.CSITM_0")
        self.setTraceSourceEnabled("CSITM_0", itmEnabled)

        itmEnabled = self.getOptionValue("options.itm.CSITM_1")
        self.setTraceSourceEnabled("CSITM_1", itmEnabled)

        traceMode = self.getOptionValue("options.trace.traceCapture")
        if traceMode != "none":
            self.createTraceCapture()
            self.enableTraceCapture(traceMode)

            if self.getOptions().getOption("options.trace.traceCapture." + self.getDstreamOptionString() + ".tpiuPortWidth"):
                self.setPortWidth(int(self.getOptionValue("options.trace.traceCapture." + self.getDstreamOptionString() + ".tpiuPortWidth")))

            if self.getOptions().getOption("options.trace.traceCapture." + self.getDstreamOptionString() + ".traceBufferSize"):
                self.setTraceBufferSize(self.getOptionValue("options.trace.traceCapture." + self.getDstreamOptionString() + ".traceBufferSize"))

            self.configureTraceCapture(traceMode)

    def getDstreamOptionString(self):
        return "dstream"

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

        for core in range(len(self.cortexM33cores)):
            enable = self.getOptionValue('options.sync.%s' % coreNames_cortexM33[core])
            self.setCrossSyncEnabled(self.cortexM33cores[core], enable)

    def addDeviceInterface(self, device):
        '''Add the device to the configuration and register its address filters'''
        ConfigurationBase.addDeviceInterface(self, device)
        self.registerFilters(device)

    @staticmethod
    def getSourcesForCoreType(coreType):
        '''Get the Trace Sources for a given coreType
           Use parameter-binding to ensure that the correct Sources
           are returned for the core type passed only'''
        def getSources(self):
            return self.getTraceSourcesForCoreType(coreType)
        return getSources

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def postConnect(self):
        ConfigurationBaseSDF.postConnect(self)

        debugAP = self.getDeviceInterface("CSMEMAP_3")
        debugAP.writeMem(0x4000B02C, 0x00000001)
        debugAP.writeMem(0x4000B004, 0x00000D00)
        debugAP.writeMem(0x4000C018, 0x00000002)

        try:
            freq = self.getOptionValue("options.trace.traceOpts.timestampFrequency")
        except:
            return

        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)

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
                DtslScript.getOptionCortexM33TabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionCTISyncPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), DtslScript_DSTREAM_ST.getOffChipTraceOption()]),
                ])

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

class DtslScript_DSTREAM_PT(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_PT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexM33TabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getOptionCTISyncPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), DtslScript_DSTREAM_PT.getStoreAndForwardOptions(),
                                  DtslScript_DSTREAM_PT.getStreamingTraceOptions()]),
                ])

    @staticmethod
    def getStoreAndForwardOptions():
        return ("DSTREAM_PT_Store_and_Forward", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement("dpt_storeandforward", "Off-Chip Trace", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False),
                ]
            )
        )

    @staticmethod
    def getStreamingTraceOptions():
        return (
            "DSTREAM_PT_StreamingTrace", "DSTREAM-PT Streaming Trace",
            DTSLv1.infoElement(
                "dpt_streamingtrace", "Off-Chip Trace", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")],isDynamic=False),
                    DTSLv1.enumOption('traceBufferSize', 'Host trace buffer size', defaultValue="4GB",
                        values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"),
                                  ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"),
                                  ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                ]
            )
        )

    def getDstreamOptionString(self):
        if self.getOptionValue("options.trace.traceCapture") == "DSTREAM_PT_Store_and_Forward":
            return "dpt_storeandforward"
        if self.getOptionValue("options.trace.traceCapture") == "DSTREAM_PT_StreamingTrace":
            return "dpt_streamingtrace"

    def createDSTREAM(self):
        if self.getOptionValue("options.trace.traceCapture") == "DSTREAM_PT_Store_and_Forward":
            self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM_PT_Store_and_Forward")
        elif self.getOptionValue("options.trace.traceCapture") == "DSTREAM_PT_StreamingTrace":
            self.DSTREAM = DSTREAMPTLiveStoredStreamingTraceCapture(self, "DSTREAM_PT_StreamingTrace")

class DtslScript_ULINK(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("sync", "CTI Synchronization", childOptions=[
                    DTSLv1.booleanOption(coreNames_cortexM33[0], coreNames_cortexM33[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM33[1], coreNames_cortexM33[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])]
            )
        ]

    def setInitialOptions(self):
        '''Set the initial options'''
