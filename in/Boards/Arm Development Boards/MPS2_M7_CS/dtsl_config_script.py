# Copyright (C) 2014-2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import DSTREAMPTLiveStoredStreamingTraceCapture
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import V7M_CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource

ATB_ID_BASE = 2
NUM_CORES_CORTEX_M7 = 1
DSTREAM_PORTWIDTH = 4
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
ITM_ATB_ID = 1
ITM_FUNNEL_PORT = 3
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''

class TraceRangeOptions:
    def __init__(self, coreTraceName = None, dtsl = None):
        if coreTraceName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("options.coreTrace.%s.traceRange" % coreTraceName)
            self.traceRangeStart = dtsl.getOptionValue("options.coreTrace.%s.traceRange.start" % coreTraceName)
            self.traceRangeEnd = dtsl.getOptionValue("options.coreTrace.%s.traceRange.end" % coreTraceName)
            self.traceRangeIDs = None

    def defaultSetup(self):
        self.traceRangeEnable = False
        self.traceRangeStart = None
        self.traceRangeEnd = None
        self.traceRangeIDs = None

class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexM7TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/TMC)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency',
                                         'Timestamp frequency',
                                         defaultValue=25000000,
                                         isDynamic=False,
                                         description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),

                ])

    @staticmethod
    def getOptionCortexM7TabPage():
        return DTSLv1.tabPage("coreTrace", "Core Trace", childOptions=[
                    DTSLv1.booleanOption('cortexM7coreTrace', 'Enable Cortex-M7 core trace',
                                        defaultValue=False,
                                        childOptions=[DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                                        ETMv4TraceSource.cycleAccurateOption(DtslScript.getETMs),
                                        ETMv4TraceSource.dataOption(DtslScript.getETMs),
                                        DTSLv1.booleanOption('traceRange', 'Trace capture range',
                                            description=TRACE_RANGE_DESCRIPTION,
                                            defaultValue = False,
                                            childOptions = [
                                                DTSLv1.integerOption('start', 'Start address',
                                                    description='Start address for trace capture',
                                                    defaultValue=0,
                                                    display=IIntegerOption.DisplayFormat.HEX),
                                                DTSLv1.integerOption('end', 'End address',
                                                    description='End address for trace capture',
                                                    defaultValue=0xFFFFFFFF,
                                                    display=IIntegerOption.DisplayFormat.HEX)]),

                    ])
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

        ''' Do not add directly to this list - first check if the item you are adding is already present.. '''
        self.mgdPlatformDevs = []

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
        if self.AHB_M not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.AHB_M)

        self.exposeCores()

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = TraceRangeOptions()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def postConnect(self):
        DTSLv1.postConnect(self)
        freq = self.getOptionValue("options.trace.timestampFrequency")
        # update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)

    def createETFTrace(self):
        self.etfTrace = TMCETBTraceCapture(self, self.ETF, "ETF")

    def discoverDevices(self):
        '''find and create devices'''

        memApDev = 0

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.AHB_M = CortexM_AHBAP(self, memApDev, "CSMEMAP")

        cortexM7coreDev = 0
        self.cortexM7cores = []

        streamID = ATB_ID_BASE

        # Trace start/stop CTI
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")

        coreCTIDev = self.findDevice("Cortex-M7") # look for core CTI devices after the first core
        self.CTIs  = []

        etmDev = 1
        self.ETMs  = []

        for i in range(0, NUM_CORES_CORTEX_M7):
            # create core
            cortexM7coreDev = self.findDevice("Cortex-M7", cortexM7coreDev+1)
            dev = Device(self, cortexM7coreDev, "Cortex-M7")
            self.cortexM7cores.append(dev)

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev+1)
            etm = ETMv4TraceSource(self, etmDev, streamID, "ETM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)

        tmcDev = 1

        # ETF device
        tmcDev = self.findDevice("CSTMC", tmcDev + 1)
        self.ETF = CSTMC(self, tmcDev, "ETF")
        self.ETF.setMode(CSTMC.Mode.ETB)

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

        # Funnel 0
        funnelDev0 = self.findDevice("CSTFunnel")
        self.funnel0 = self.createFunnel(funnelDev0, "Funnel_0")

        # Funnel 1
        funnelDev1 = self.findDevice("CSTFunnel", funnelDev0+1)
        self.funnel1 = self.createFunnel(funnelDev1, "Funnel_1")

        # ITM
        itmDev = self.findDevice("CSITM")
        self.ITM = self.createITM(itmDev, ITM_ATB_ID, "ITM")

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def exposeCores(self):
        for core in self.cortexM7cores:
            self.registerMClassFilters(core)
            self.addDeviceInterface(core)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a source
        return (None, None, None) if no associated CTI
        '''
        if source in self.ETMs:
            coreNum = self.ETMs.index(source)
            # ETM trigger is on input 6
            if coreNum < len(self.CTIs):
                return (self.CTIs[coreNum], 6, CTM_CHANNEL_TRACE_TRIGGER)

        # no associated CTI
        return (None, None, None)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == "TPIU":
            # TPIU trigger input is CTI out 3
            return (self.outCTI, 3, CTM_CHANNEL_TRACE_TRIGGER)

        if sink == "ETF":
            return (self.outCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)

        # no associated CTI
        return (None, None, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableCTIsForSource(source, enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # disable the TPIU by default to allow ETB to work at full rate
        tpiu.setEnabled(False)
        return tpiu

    def setupETFTrace(self):
        '''Setup ETF trace capture'''
        # use continuous mode
        self.etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETF and register ETF with configuration
        self.etfTrace.setTraceComponentOrder([ self.funnel1, self.ETF])
        self.addTraceCaptureInterface(self.etfTrace)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETF", [ self.funnel1,self.funnel0, self.tpiu, self.outCTI, self.etfTrace ])

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)

        # configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.setPortWidth(portWidth)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.funnel0, self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.funnel0, self.ETF, self.outCTI, self.tpiu, self.DSTREAM, self.funnel1])

    def setPortWidth(self, portWidth):
        self.tpiu.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.dstreamTraceEnabled = enabled
        self.tpiu.setEnabled(enabled)
        self.enableCTIsForSink("TPIU", enabled)

        if enabled:
            self.funnel0.setPortEnabled(0)
            self.funnel0.setPortEnabled(1)
            self.funnel0.setPortEnabled(2)
        else:
            self.funnel0.setAllPortsDisabled();

    def setETFTraceEnabled(self, enabled):
        '''Enable/disable ETF trace capture'''
        self.etfTraceEnabled = enabled
        self.enableCTIsForSink("ETF", enabled)
        #disable the funnel for TPIU

        if enabled:
            self.funnel1.setPortEnabled(0)
            self.funnel1.setPortEnabled(1)
            self.funnel1.setPortEnabled(2)
        else:
            self.funnel1.setAllPortsDisabled();

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_M7):
            if self.ETMs[c].isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexM7cores[c], self.ETMs[c])

        self.registerTraceSource(traceCapture, self.ITM)

    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

        # CTI (if present) is also managed by the configuration
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.addManagedTraceDevices(traceCapture.getName(), [ cti ])

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
            self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)
        elif self.etfTraceEnabled:
            self.createETFTrace()
            self.setupETFTrace()

        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.coreTrace.cortexM7coreTrace")
        self.setTraceSourceEnabled(self.ETMs[0], coreTraceEnabled)

        self.ETMs[0].setTimestampingEnabled(self.getOptionValue("options.coreTrace.cortexM7coreTrace.timestamp"))

        # register trace sources for each trace sink
        if self.etfTraceEnabled:
            self.registerTraceSources(self.etfTrace)

        if self.dstreamTraceEnabled:
            self.registerTraceSources(self.DSTREAM)

        self.setInternalTraceRange(self.traceRangeOptions, TraceRangeOptions("cortexm7coreTrace", self), self.ETMs)
        self.setManagedDeviceList(self.getManagedDevices(traceMode))

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
        if method == "none":
            self.setETFTraceEnabled(False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "ETF":
            self.setETFTraceEnabled(True)
            self.setDSTREAMTraceEnabled(False)
        elif method in ["DSTREAM", "DSTREAM_PT_Store_and_Forward", "DSTREAM_PT_StreamingTrace"]:
            self.setETFTraceEnabled(False)
            self.setDSTREAMTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def setITMEnabled(self, enabled):
        '''Enable/disable the ITM trace source'''
        self.setTraceSourceEnabled(self.ITM, enabled)


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

    def registerMClassFilters(self, core):
        '''Register MemAP filters to allow access to the AHB for the device'''
        core.registerAddressFilters(
            [AHBCortexMMemAPAccessor("AHB", self.AHB_M, "M Class AHB bus accessed via AP")])

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.enableCTIInput(cti, input, channel, enabled)

    def enableCTIInput(self, cti, input, channel, enabled):
        '''Enable/disable cross triggering between an input and a channel'''
        if enabled:
            cti.enableInputEvent(input, channel)
        else:
            cti.disableInputEvent(input, channel)

    def enableCTIsForSink(self, sink, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, output, channel = self.getCTIForSink(sink)
        if cti:
            self.enableCTIOutput(cti, output, channel, enabled)

    def enableCTIOutput(self, cti, output, channel, enabled):
        '''Enable/disable cross triggering between a channel and an output'''
        if enabled:
            cti.enableOutputEvent(output, channel)
        else:
            cti.disableOutputEvent(output, channel)

    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, funnelDev, name)
        funnel.setAllPortsDisabled() # Will enable for each source later
        return funnel

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

class NoDSTREAMTrace_DtslScript(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                NoDSTREAMTrace_DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexM7TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/TMC)")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency',
                                         'Timestamp frequency',
                                         defaultValue=25000000,
                                         isDynamic=False,
                                         description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),

                ])

    def setInitialOptions(self):
        '''Set the initial options'''
        if self.etfTraceEnabled:
            self.createETFTrace()
            self.setupETFTrace()
        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.coreTrace.cortexM7coreTrace")
        self.setTraceSourceEnabled(self.ETMs[0], coreTraceEnabled)

        self.ETMs[0].setTimestampingEnabled(self.getOptionValue("options.coreTrace.cortexM7coreTrace.timestamp"))

        # register trace sources for each trace sink
        if self.etfTraceEnabled:
            self.registerTraceSources(self.etfTrace)

        self.setInternalTraceRange(self.traceRangeOptions, TraceRangeOptions("cortexm7coreTrace", self), self.ETMs)
        self.setManagedDeviceList(self.getManagedDevices(traceMode))

    def postConnect(self):
        DTSLv1.postConnect(self)

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)

        # configure the DSTREAM for continuous trace
        self.setPortWidth(portWidth)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.funnel0, self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(self.getOptionValue("options.trace.traceCapture"), [ self.funnel0, self.ETF, self.outCTI, self.tpiu, self.DSTREAM, self.funnel1])

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
                DtslScript.getOptionCortexM7TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/TMC)"), DtslScript_DSTREAM_ST.getDSTREAMOptions()],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency',
                                         'Timestamp frequency',
                                         defaultValue=25000000,
                                         isDynamic=False,
                                         description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),

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
                DtslScript.getOptionCortexM7TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.radioEnumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/TMC)"), DtslScript_DSTREAM_PT.getStoreAndForwardOptions(), DtslScript_DSTREAM_PT.getStreamingTraceOptions()],
                        setter=DtslScript_DSTREAM_PT.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency',
                                         'Timestamp frequency',
                                         defaultValue=25000000,
                                         isDynamic=False,
                                         description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),

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
