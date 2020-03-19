# Copyright (C) 2017-2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import MTBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTLiveStoredStreamingTraceCapture
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import V8M_CSTPIU
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.configurations import TimestampInfo

tmDevs_cortexM33 = ["CSETM"]
coreDevs_cortexM33 = ["Cortex-M33"]
NUM_CORES_CORTEX_M33 = 1
coresDap0 = ["Cortex-M33"]
DSTREAM_PORTWIDTH = 4

class M_Class_ETMv4(ETMv4TraceSource):

    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False

class DtslScript(DTSLv1):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexM33TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency.")
                ])

    @staticmethod
    def getOptionCortexM33TabPage():
        return DTSLv1.tabPage("cortexM33", "Core Trace", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M33 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_M33_%d' % core, "Enable " + coreDevs_cortexM33[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_M33) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                            [ ETMv4TraceSource.cycleAccurateOption(DtslScript.getTraceMacrocellsForCoreType("cortexM33"))]
                        ),
                ])

    @staticmethod
    def getOptionITMTabPage():
        return DTSLv1.tabPage("itm", "ITM", childOptions=[
                    DTSLv1.booleanOption('CSITM', 'Enable CSITM trace', defaultValue=False),
                ])

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # Only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
        for i in range(len(self.AHB_Ms)):
            if self.AHB_Ms[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.AHB_Ms[i])

        self.exposeCores()

        self.setupMTBTrace()

        self.setManagedDeviceList(self.mgdPlatformDevs)

        self.setDSTREAMTraceEnabled(False)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        apDevs_AHB_Ms = ["CSMEMAP"]
        self.AHB_Ms = []

        for i in range(len(apDevs_AHB_Ms)):
            apDevice = CortexM_AHBAP(self, self.findDevice(apDevs_AHB_Ms[i]), "AHB_M_%d" % i)
            self.AHB_Ms.append(apDevice)

        self.cortexM33cores = []

        self.MTBs = []

        self.macrocells = {}
        self.macrocells["cortexM33"] = []

        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        # ITM 0
        self.ITM0 = self.createITM("CSITM", streamID, "CSITM")
        streamID += 1

        #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for core in range(NUM_CORES_CORTEX_M33):
            # Create core
            coreDevice = Device(self, self.findDevice(coreDevs_cortexM33[core]), coreDevs_cortexM33[core])
            self.cortexM33cores.append(coreDevice)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            if not tmDevs_cortexM33[core] == None:
                tm = M_Class_ETMv4(self, self.findDevice(tmDevs_cortexM33[core]), streamID, tmDevs_cortexM33[core])
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["cortexM33"].append(tm)


        # TPIU
        self.TPIU = self.createTPIU("CSTPIU", "TPIU")

    def registerFilters(self, core, dap):
        '''Register MemAP filters to allow access to the APs for the device'''
        if dap == 0:
            core.registerAddressFilters([
                AHBCortexMMemAPAccessor("AHB_M_0", self.AHB_Ms[0], "AHB-M bus accessed via AP 0 (CSMEMAP)"),
            ])

    def exposeCores(self):
        for coreName in coresDap0:
            core = self.getDeviceInterface(coreName)
            self.registerFilters(core, 0)
            self.addDeviceInterface(core)

    def setupDSTREAMTrace(self, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        self.setPortWidth(DSTREAM_PORTWIDTH)

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

    def setupMTBTrace(self):
        ''' Setup MTB trace capture'''
        for mtb in self.MTBs:
            mtb.setTraceBufferSize(4096)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("CSMTB", self.MTBs)

        for mtb in self.MTBs:
            self.addTraceCaptureInterface(mtb)

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''
        coreNames = ["Cortex-M33"]
        macrocellNames = ["CSETM"]

        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return self.getDeviceInterface(macrocellNames[i])

        return None

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = V8M_CSTPIU(self, self.findDevice(tpiuDev), name, self.AHB_Ms[0])
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.dstreamTraceEnabled = enabled
        self.TPIU.setEnabled(enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for core in self.cortexM33cores:
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
        if self.dstreamTraceEnabled:
            self.createDSTREAM()
            traceComponentOrder = [ self.TPIU ]
            managedDevices = [ self.TPIU, self.DSTREAM ]
            self.setupDSTREAMTrace(traceComponentOrder, managedDevices)


        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.cortexM33.coreTrace")
        for core in range(NUM_CORES_CORTEX_M33):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexM33.coreTrace.Cortex_M33_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexM33cores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setTimestampingEnabled(coreTM, self.getOptionValue("options.cortexM33.coreTrace.timestamp"))

        if self.dstreamTraceEnabled:
            dstream_opts = "options.trace.traceCapture." + self.getDstreamOptionString() + "."
            portWidthOpt = self.getOptions().getOption(dstream_opts + "tpiuPortWidth")
            if portWidthOpt:
                portWidth = self.getOptionValue(dstream_opts + "tpiuPortWidth")
                self.setPortWidth(int(portWidth))

            traceBufferSizeOpt = self.getOptions().getOption(dstream_opts + "traceBufferSize")
            if traceBufferSizeOpt:
                traceBufferSize = self.getOptionValue(dstream_opts + "traceBufferSize")
                self.setTraceBufferSize(traceBufferSize)

        itmEnabled = self.getOptionValue("options.itm.CSITM")
        self.setTraceSourceEnabled(self.ITM0, itmEnabled)

        # Register trace sources for each trace sink
        if self.dstreamTraceEnabled:
            self.registerTraceSources(self.DSTREAM)

        self.setManagedDeviceList(self.getManagedDevices(traceMode))

    def getDstreamOptionString(self):
        return "dstream"

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def setTraceCaptureMethod(self, method):
        if method in ["DSTREAM", "DSTREAM_PT_Store_and_Forward", "DSTREAM_PT_StreamingTrace"]:
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

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, self.findDevice(itmDev), streamID, name)
        # Disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

    def postConnect(self):
        DTSLv1.postConnect(self)

        try:
            freq = self.getOptionValue("options.trace.traceOpts.timestampFrequency")
        except:
            return

        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)

    def setTimestampingEnabled(self, xtm, state):
        xtm.setTimestampingEnabled(state)

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(self.getOptionValue("options.trace.traceCapture"), managedDevices)

    def setTraceBufferSize(self, mode):
        '''Configuration option setter method for the trace buffer size'''
        bufferSize = 64*1024*1024
        if (mode == "64MB"):
            bufferSize = 64*1024*1024
        if (mode == "128MB"):
            bufferSize = 128*1024*1024
        if (mode == "256MB"):
            bufferSize = 256*1024*1024
        if (mode == "512MB"):
            bufferSize = 512*1024*1024
        if (mode == "1GB"):
            bufferSize = 1*1024*1024*1024
        if (mode == "2GB"):
            bufferSize = 2*1024*1024*1024
        if (mode == "4GB"):
            bufferSize = 4*1024*1024*1024
        if (mode == "8GB"):
            bufferSize = 8*1024*1024*1024
        if (mode == "16GB"):
            bufferSize = 16*1024*1024*1024
        if (mode == "32GB"):
            bufferSize = 32*1024*1024*1024
        if (mode == "64GB"):
            bufferSize = 64*1024*1024*1024
        if (mode == "128GB"):
            bufferSize = 128*1024*1024*1024

        self.DSTREAM.setMaxCaptureSize(bufferSize)

class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_ST.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexM33TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption(
                        'traceCapture',
                        'Trace capture method',
                        defaultValue="none",
                        values = [("none", "None"),
                                  DtslScript_DSTREAM_ST.getDSTREAMOptions()],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency.")
                ])

    @staticmethod
    def getDSTREAMOptions():
        return (
            "DSTREAM", "Streaming Trace",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('traceBufferSize', 'Trace buffer size', defaultValue="4GB",
                        values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"),
                                  ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"),
                                  ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
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
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption(
                        'traceCapture',
                        'Trace capture method',
                        defaultValue="none",
                        values = [("none", "None"),
                                  DtslScript_DSTREAM_PT.getStoreAndForwardOptions(), DtslScript_DSTREAM_PT.getStreamingTraceOptions()],
                        setter=DtslScript_DSTREAM_PT.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency.")
                ])

    @staticmethod
    def getStoreAndForwardOptions():
        return (
            "DSTREAM_PT_Store_and_Forward", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement(
                "dpt_storeandforward", "", "",
                childOptions=[
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                                values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False)
                    ])
                ]
            )
        )

    @staticmethod
    def getStreamingTraceOptions():
        return (
            "DSTREAM_PT_StreamingTrace", "DSTREAM-PT Streaming Trace",
            DTSLv1.infoElement(
                "dpt_streamingtrace", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="4",
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

class NoDSTREAMTrace_DtslScript(DtslScript):

    @staticmethod
    def getOptionList():
        return []
