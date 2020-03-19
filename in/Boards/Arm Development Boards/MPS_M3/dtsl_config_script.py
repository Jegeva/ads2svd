# Copyright (C) 2013-2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTLiveStoredStreamingTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import ETMv3_4TraceSource
from com.arm.debug.dtsl.components import V7M_CSTPIU
from com.arm.debug.dtsl.components import ITMTraceSource

NUM_CORES_CORTEX_M3 = 1
ATB_ID_BASE = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 4
ITM_ATB_ID = 1
ITM_FUNNEL_PORT = 3
CORTEX_M3_TRACE_OPTIONS = 0

class TraceRangeOptions:
    def __init__(self, coreTraceName = None, dtsl = None):
        self.defaultSetup()

        # ''' Trace triggers and ranges unsupported. '''
        # if coreTraceName == None:
            # self.defaultSetup()
        # else:
            # self.traceRangeEnable = dtsl.getOptionValue("options.coreTrace.%s.traceRange" % coreTraceName)
            # self.traceRangeStart = dtsl.getOptionValue("options.coreTrace.%s.traceRange.start" % coreTraceName)
            # self.traceRangeEnd = dtsl.getOptionValue("options.coreTrace.%s.traceRange.end" % coreTraceName)
            # self.traceRangeIDs = None

    def defaultSetup(self):
        self.traceRangeEnable = False
        self.traceRangeStart = None
        self.traceRangeEnd = None
        self.traceRangeIDs = None

class M3_ETM(ETMv3_4TraceSource):

    # Disable trace triggers and start stop points as currently unsupported
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
                DtslScript.getOptionCortexM3TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

    @staticmethod
    def getOptionCortexM3TabPage():
        return DTSLv1.tabPage("coreTrace", "Core Trace", childOptions=[
                    DTSLv1.booleanOption('cortexM3coreTrace', 'Enable Cortex-M3 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_M3_%d' % c, "Enable Cortex-M3 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_M3) ]
                            # Cycle-accurate trace unsupported.
                            # Trace triggers and ranges unsupported, so no trace range selection.
                        ),
                ])

    @staticmethod
    def getOptionITMTabPage():
        return DTSLv1.tabPage("itm", "ITM", childOptions=[
                    DTSLv1.booleanOption('itm', 'Enable ITM trace', defaultValue=False,
                        setter=DtslScript.setITMEnabled),
                ])

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

         # only AHB managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB)

        self.exposeCores()

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-M3 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        cortexM3coreDev = 0
        self.cortexM3cores = []

        streamID = ATB_ID_BASE

        etmDev = 1
        self.ETMs  = []

        for i in range(0, NUM_CORES_CORTEX_M3):
            # create core
            cortexM3coreDev = self.findDevice("Cortex-M3", cortexM3coreDev+1)
            dev = Device(self, cortexM3coreDev, "Cortex-M3")
            self.cortexM3cores.append(dev)

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev+1)
            etm = M3_ETM(self, etmDev, streamID, "ETM_%d_%d" % (i, streamID)) # use the M3_ETM subclass
            streamID += 1
            # disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)

        # MEMAP devices
        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = CortexM_AHBAP(self, ahbDev, "CSMEMAP")

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")
        # ITM
        itmDev = self.findDevice("CSITM")
        self.ITM = self.createITM(itmDev, ITM_ATB_ID, "ITM")

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def exposeCores(self):
        for core in self.cortexM3cores:
            self.registerAccessors(core)
            self.addDeviceInterface(core)

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''

        self.setPortWidth(portWidth)

        # configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.tpiu, self.DSTREAM ])

        # register trace sources
        self.registerTraceSources(self.DSTREAM)

    def setPortWidth(self, portWidth):
        self.tpiu.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = V7M_CSTPIU(self, tpiuDev, name, self.AHB)
        # disable the TPIU by default to allow ETB to work at full rate
        tpiu.setEnabled(False)
        return tpiu

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.dstreamTraceEnabled = enabled
        self.tpiu.setEnabled(enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_M3):
            self.registerCoreTraceSource(traceCapture, self.cortexM3cores[c], self.ETMs[c])

        self.registerTraceSource(traceCapture, self.ITM)

    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnel ports
        portMap = {self.ITM: ITM_FUNNEL_PORT}
        for i in range(0, NUM_CORES_CORTEX_M3):
            portMap[self.ETMs[i]] = self.getFunnelPortForCore(i)


        return portMap.get(source, None)

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''

        if self.dstreamTraceEnabled:
            self.createDSTREAM()
            self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)

        optionValues = self.getOptionValues()
        traceMode = optionValues.get("options.trace.traceCapture")
        self.setManagedDevices(self.getManagedDevices(traceMode))

        coreTraceEnabled = self.getOptionValue("options.coreTrace.cortexM3coreTrace")
        for i in range(0, NUM_CORES_CORTEX_M3):
            thisCoreTraceEnabled = self.getOptionValue("options.coreTrace.cortexM3coreTrace.Cortex_M3_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            self.setTraceSourceEnabled(self.ETMs[i], enableSource)

        etmStartIndex = 0
        etmEndIndex = 0

        etmEndIndex += NUM_CORES_CORTEX_M3
        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_M3_TRACE_OPTIONS], TraceRangeOptions("cortexM3coreTrace", self), self.ETMs[etmStartIndex:etmEndIndex])
        etmStartIndex += NUM_CORES_CORTEX_M3

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

    def getDstreamOptionString(self):
        return "dstream"

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setDSTREAMTraceEnabled(False)
        elif method in ["DSTREAM", "DSTREAM_PT_Store_and_Forward", "DSTREAM_PT_StreamingTrace"]:
            self.setDSTREAMTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def setITMEnabled(self, enabled):
        '''Enable/disable the ITM trace source'''
        self.setTraceSourceEnabled(self.ITM, enabled)

    def setCoreTraceEnabled(self, enabled):
        '''Enable/disable the core trace sources'''
        for t in self.ETMs:
            self.setTraceSourceEnabled(t, enabled)

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the set of devices managed by the configuration'''
        for d in devs:
            self.mgdPlatformDevs.add(d)

    def registerTraceSource(self, traceCapture, source):
        '''Register trace source with trace capture device'''
        traceCapture.addTraceSource(source)
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

    def addManagedTraceDevices(self, traceKey, devs):
        '''Add devices to the set of devices managed by the configuration for this trace mode'''
        traceDevs = self.mgdTraceDevs.get(traceKey)
        if not traceDevs:
            traceDevs = set()
            self.mgdTraceDevs[traceKey] = traceDevs
        for d in devs:
            traceDevs.add(d)

    def registerAccessors(self, core):
        '''Add a wrapper around a core to allow access to AHB and APB via the MEMAP template'''
        core.registerAddressFilter(
            AHBCortexMMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"))

    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, itmDev, streamID, name)
        # disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

    def setInternalTraceRange(self, currentTraceOptions, newTraceOptions, traceMacrocells):
        # values are different to current config
        if (newTraceOptions.traceRangeEnable != currentTraceOptions.traceRangeEnable) or \
            (newTraceOptions.traceRangeStart != currentTraceOptions.traceRangeStart) or \
            (newTraceOptions.traceRangeEnd != currentTraceOptions.traceRangeEnd):

            # clear existing ranges
            if currentTraceOptions.traceRangeIDs:
                for i in range(0, len(traceMacrocells)):
                    traceMacrocells[i].clearTraceRange(currentTraceOptions.traceRangeIDs[i])
                currentTraceOptions.traceRangeIDs = None

            # set new ranges
            if newTraceOptions.traceRangeEnable:
                currentTraceOptions.traceRangeIDs = [
                    traceMacrocells[i].addTraceRange(newTraceOptions.traceRangeStart, newTraceOptions.traceRangeEnd)
                    for i in range(0, len(traceMacrocells))
                    ]

            currentTraceOptions.traceRangeEnable = newTraceOptions.traceRangeEnable
            currentTraceOptions.traceRangeStart = newTraceOptions.traceRangeStart
            currentTraceOptions.traceRangeEnd = newTraceOptions.traceRangeEnd


class DtslScript_RVI(DTSLv1):
    @staticmethod
    def getOptionList():
        return []

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''

        self.setPortWidth(portWidth)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(self.getOptionValue("options.trace.traceCapture"), [ self.tpiu, self.DSTREAM ])

        # register trace sources
        self.registerTraceSources(self.DSTREAM)

    def setTraceBufferSize(self, mode):
        '''Configuration option setter method for the trace cache buffer size'''
        cacheSize = 64*1024*1024
        if (mode == "64MB"):
            cacheSize = 64*1024*1024
        if (mode == "128MB"):
            cacheSize = 128*1024*1024
        if (mode == "256MB"):
            cacheSize = 256*1024*1024
        if (mode == "512MB"):
            cacheSize = 512*1024*1024
        if (mode == "1GB"):
            cacheSize = 1*1024*1024*1024
        if (mode == "2GB"):
            cacheSize = 2*1024*1024*1024
        if (mode == "4GB"):
            cacheSize = 4*1024*1024*1024
        if (mode == "8GB"):
            cacheSize = 8*1024*1024*1024
        if (mode == "16GB"):
            cacheSize = 16*1024*1024*1024
        if (mode == "32GB"):
            cacheSize = 32*1024*1024*1024
        if (mode == "64GB"):
            cacheSize = 64*1024*1024*1024
        if (mode == "128GB"):
            cacheSize = 128*1024*1024*1024

        self.DSTREAM.setMaxCaptureSize(cacheSize)

class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_ST.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexM3TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), DtslScript_DSTREAM_ST.getDSTREAMOptions()],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

    @staticmethod
    def getDSTREAMOptions():
        return (
            "DSTREAM", "Streaming Trace",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")],isDynamic=False),
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
                DtslScript.getOptionCortexM3TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), DtslScript_DSTREAM_PT.getStoreAndForwardOptions(), DtslScript_DSTREAM_PT.getStreamingTraceOptions()],
                        setter=DtslScript_DSTREAM_PT.setTraceCaptureMethod),
                ])

    @staticmethod
    def getStoreAndForwardOptions():
        return (
            "DSTREAM_PT_Store_and_Forward", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement(
                "dpt_storeandforward", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False)
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

