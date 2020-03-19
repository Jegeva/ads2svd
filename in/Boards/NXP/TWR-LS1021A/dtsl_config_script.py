from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import DeviceCluster
from com.arm.debug.dtsl.components import RDDISyncSMPDevice
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
from com.arm.rddi import RDDI_ACC_SIZE

# import core specific functions from Cores folder
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a7_rams

from struct import pack, unpack
from jarray import array, zeros

NUM_CORES_CORTEX_A7 = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
ATB_ID_BASE = 2
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
CORTEX_A7_TRACE_OPTIONS = 0

class TraceRangeOptions:
    def __init__(self, coreTraceName = None, dtsl = None):
        if coreTraceName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("%s.traceRange" % coreTraceName)
            self.traceRangeStart = dtsl.getOptionValue("%s.traceRange.start" % coreTraceName)
            self.traceRangeEnd = dtsl.getOptionValue("%s.traceRange.end" % coreTraceName)
            self.traceRangeIDs = None

    def defaultSetup(self):
        self.traceRangeEnable = False
        self.traceRangeStart = None
        self.traceRangeEnd = None
        self.traceRangeIDs = None

class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList(): # Trace disabled for this initial demo release
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/TMC)"), ("ETR", "System Memory Trace Buffer (ETR/TMC)")],
                        setter=DtslScript.setTraceCaptureMethod),
                ]),
                DTSLv1.tabPage("cortexA7", "Cortex-A7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A7 core trace', defaultValue=False, childOptions =
                        # Allow each source to be enabled/disabled individually
                        [ DTSLv1.booleanOption('Cortex_A7_%d' % c, "Enable Cortex-A7 %d trace" % c, defaultValue=True)
                        for c in range(0, NUM_CORES_CORTEX_A7) ] +
                        [ DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False) ] +
                        [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                        [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                            childOptions = [
                                DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                    values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                ])
                        ] +
                        # Pull in common options for ETMs
                        ETMv3_5TraceSource.defaultOptions(DtslScript.getETMs) +
                        [  # Data trace
                        ETMv3_5TraceSource.dataOption(DtslScript.getETMs),
                        # Trace range selection (e.g. for linux kernel)
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
                                    display=IIntegerOption.DisplayFormat.HEX)
                            ])
                        ]
                    )
                ]),
                DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer', 'Configure the system memory trace buffer to be used by the ETR/TMC device',defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the ETR/TMC device',
                            defaultValue=0x90000000,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('size', 'Size in bytes',
                            description='Size of the system memory trace buffer in bytes',
                            defaultValue=0x8000,
                            isDynamic=True,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.booleanOption('scatterGather','Enable scatter-gather mode',
                            defaultValue=False,
                            description='When enabling scatter-gather mode, the start address of the on-chip trace buffer must point to a configured scatter-gather table')
                        ]
                    )
                ]),
                DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ]),
            ]

        )]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # only AHB/APB are managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB)
        self.mgdPlatformDevs.add(self.APB)

        self.exposeCores()

        self.setupETFTrace()

        self.setupETRTrace()

        self.setupCTISyncSMP()

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
             TraceRangeOptions() # Cortex-A7 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = APBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = AHBAP(self, apbDev, "CSMEMAP")

        cortexA7coreDev = 0
        self.cortexA7cores = []

        streamID = ATB_ID_BASE

        coreCTIDev = 0
        self.CTIs  = []
        self.cortexA7ctiMap = {} # map cores to associated CTIs

        ptmDev = 1
        self.PTMs  = []

        etmDev = 1
        self.ETMs  = []

        for i in range(0, NUM_CORES_CORTEX_A7):
            # create core
            cortexA7coreDev = self.findDevice("Cortex-A7", cortexA7coreDev+1)
            dev = a7_rams.A7CoreDevice(self, cortexA7coreDev, "Cortex-A7_%d" % i)
            self.cortexA7cores.append(dev)

            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)
            self.cortexA7ctiMap[dev] = coreCTI

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev+1)
            etm = ETMv3_5TraceSource(self, etmDev, streamID, "ETM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)

        tmcDev = 1


        # TMC - ETF/ETB device
        tmcDev = self.findDevice("CSTMC", tmcDev + 1)
        self.ETF = CSTMC(self, tmcDev, "ETF")
        self.etfTrace = TMCETBTraceCapture(self, self.ETF, "ETF")

        # TMC - ETF between funnel 1 and ETR
        tmcDev = self.findDevice("CSTMC", tmcDev + 1)
        self.ETF1 = CSTMC(self, tmcDev, "ETF")
        self.ETF1.setMode(CSTMC.Mode.ETF)

        # TMC - ETR FIFO
        tmcDev = self.findDevice("CSTMC", tmcDev + 1)
        self.ETR = ETRTraceCapture(self, tmcDev, "ETR")

        # Funnel 0
        funnelDev0 = self.findDevice("CSTFunnel")
        self.funnel0 = self.createFunnel(funnelDev0, "Funnel_0")
        self.funnel0.setAllPortsDisabled()
        self.funnel0.setPortEnabled(0)
        self.funnel0.setPortEnabled(1)

        # Funnel 1
        funnelDev1 = self.findDevice("CSTFunnel", funnelDev0+1)
        self.funnel1 = self.createFunnel(funnelDev1, "Funnel_1")
        self.funnel1.setAllPortsDisabled()
        self.funnel1.setPortEnabled(0)
        #self.funnel1.setPortEnabled(1)

    def exposeCores(self):
        for core in self.cortexA7cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)
            a7_rams.registerInternalRAMs(core)

    def setupETRTrace(self):
        '''Setup ETR trace capture'''
        # use continuous mode
        self.ETR.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETR and register ETR with configuration
        self.ETR.setTraceComponentOrder([ self.ETF, self.ETF1, self.funnel1, self.funnel0 ])
        self.addTraceCaptureInterface(self.ETR)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETR", [ self.funnel1, self.funnel0, self.ETF, self.ETF1, self.ETR ])

    def setupETFTrace(self):
        '''Setup ETF trace capture'''
        # use continuous mode
        self.etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETF and register ETF with configuration
        self.etfTrace.setTraceComponentOrder([ self.funnel1, self.funnel0 ])
        self.addTraceCaptureInterface(self.etfTrace)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETF", [ self.funnel1, self.funnel0, self.etfTrace ])

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Cortex-A7 CTI SMP setup
        ctiInfo = {}
        for c in self.cortexA7cores:
            # use standard Cortex event mapping : in/out on trigger 0 for stop, out on trigger 7 for start
            ctiInfo[c] = CTISyncSMPDevice.DeviceCTIInfo(self.cortexA7ctiMap[c], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        smp = CTISyncSMPDevice(self, "Cortex-A7 SMP", self.cortexA7cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp)
        self.addDeviceInterface(smp)

        # automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CTIs)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        #if sink == self.TMC:
            # ETB trigger input is CTI out 1
            #return (self.outCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)

        # no associated CTI
        return (None, None, None)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a source
        return (None, None, None) if no associated CTI
        '''
        #if source in self.ETMs:
            #coreNum = self.ETMs.index(source)
            # ETM trigger is on input 6
            #if coreNum < len(self.CTIs):
                #return (self.CTIs[coreNum], 6, CTM_CHANNEL_TRACE_TRIGGER)

        # no associated CTI
        return (None, None, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def setETFTraceEnabled(self, enabled):
        '''Enable/disable ETF trace capture'''
        if enabled:
            # put the ETF in ETB mode
            self.ETF.setMode(CSTMC.Mode.ETB)
        else:
            # Put the ETF in FIFO mode
            self.ETF.setMode(CSTMC.Mode.ETF)

        self.enableCTIsForSink(self.etfTrace, enabled)

    def setETRTraceEnabled(self, enabled):
        '''Enable/disable ETR trace capture'''
        self.enableCTIsForSink(self.ETR, enabled)


    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A7):
            if self.ETMs[c].isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexA7cores[c], self.ETMs[c])

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

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnel ports
        portMap = {}
        for i in range(0, NUM_CORES_CORTEX_A7):
            portMap[self.ETMs[i]] = self.getFunnelPortForCore(NUM_CORES_CORTEX_A7+i)


        return portMap.get(source, None)

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

    def setTimestampingEnabled(self, xtm, state):
        xtm.setTimestampingEnabled(state)

    def setContextIDEnabled(self, xtm, state, size):
        if state == False:
            xtm.setContextIDs(False, IARMCoreTraceSource.ContextIDSize.NONE)
        else:
            contextIDSizeMap = {
                 "8":IARMCoreTraceSource.ContextIDSize.BITS_7_0,
                "16":IARMCoreTraceSource.ContextIDSize.BITS_15_0,
                "32":IARMCoreTraceSource.ContextIDSize.BITS_31_0 }
            xtm.setContextIDs(True, contextIDSizeMap[size])

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        if not self.isConnected():
            self.setInitialOptions()
        self.updateDynamicOptions()

    def setInitialOptions(self):
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()
        traceMode = optionValues.get("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.cortexA7.coreTrace")
        for i in range(0, NUM_CORES_CORTEX_A7):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA7.coreTrace.Cortex_A7_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            self.setTraceSourceEnabled(self.ETMs[i], enableSource)
            self.setTriggerGeneratesDBGRQ(self.ETMs[i], self.getOptionValue("options.cortexA7.coreTrace.triggerhalt"))
            self.setTimestampingEnabled(self.ETMs[i], self.getOptionValue("options.cortexA7.coreTrace.timestamp"))
            self.setContextIDEnabled(self.ETMs[i],
                                     self.getOptionValue("options.cortexA7.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexA7.coreTrace.contextIDs.contextIDsSize"))

        ptmStartIndex = 0
        ptmEndIndex = 0

        etmStartIndex = 0
        etmEndIndex = 0

        etmEndIndex += NUM_CORES_CORTEX_A7

        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A7_TRACE_OPTIONS], TraceRangeOptions("options.cortexA7.coreTrace", self), self.ETMs[etmStartIndex:etmEndIndex])
        etmStartIndex += NUM_CORES_CORTEX_A7

        # register trace sources for each trace sink
        self.registerTraceSources(self.etfTrace)
        self.registerTraceSources(self.ETR)

        self.setManagedDevices(self.getManagedDevices(traceMode))

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

        # Set up the ETR buffer
        configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer")
        if configureETRBuffer:
            scatterGatherMode = self.getOptionValue("options.ETR.etrBuffer.scatterGather")
            bufferStart = self.getOptionValue("options.ETR.etrBuffer.start")
            bufferSize = self.getOptionValue("options.ETR.etrBuffer.size")
            self.ETR.setBaseAddress(bufferStart)
            self.ETR.setTraceBufferSize(bufferSize)
            self.ETR.setScatterGatherModeEnabled(scatterGatherMode)
        for core in range(0, len(self.cortexA7cores)):
            a7_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA7cores[core])
            a7_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA7cores[core])

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = list(self.mgdPlatformDevs)
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList


    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setETFTraceEnabled(False)
            self.setETRTraceEnabled(False)
        elif method == "ETF":
            self.setETFTraceEnabled(True)
            self.setETRTraceEnabled(False)
        elif method == "ETR":
            self.setETFTraceEnabled(False)
            self.setETRTraceEnabled(True)

    def getPTMs(self):
        '''Get the PTMs'''
        return self.PTMs

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def setCoreTraceEnabled(self, enabled):
        '''Enable/disable the core trace sources'''
        for t in self.PTMs:
            self.setTraceSourceEnabled(t, enabled)

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
            traceDevs = []
            self.mgdTraceDevs[traceKey] = traceDevs
        for d in devs:
            if d not in traceDevs:
                traceDevs.append(d)


    #def addManagedTraceDevices(self, traceKey, devs):
    #    '''Add devices to the set of devices managed by the configuration for this trace mode'''
    #    traceDevs = self.mgdTraceDevs.get(traceKey)
    #    if not traceDevs:
    #        traceDevs = set()
    #        self.mgdTraceDevs[traceKey] = traceDevs
    #    for d in devs:
    #        traceDevs.add(d)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP_1")])

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

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.enableCTIInput(cti, input, channel, enabled)

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

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        port = self.getFunnelPortForSource(source)
        if enabled:
            self.funnel0.setPortEnabled(port)
        else:
            self.funnel0.setPortDisabled(port)

    def getFunnelPortForCore(self, core):
        ''' Funnel port-to-core mapping can be customized here'''
        port = core
        if (port > 2):
            port = port + 1
        return port

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


    def postConnect(self):
        DTSLv1.postConnect(self)

class DtslScript_CMSIS(DtslScript):
    @staticmethod
    def getOptionList():
        return DtslScript.getOptionList()

class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETF", "On Chip Trace Buffer (ETF/TMC)"), ("ETR", "System Memory Trace Buffer (ETR/TMC)")],
                        setter=DtslScript_RVI.setTraceCaptureMethod),
                ]),
                DTSLv1.tabPage("cortexA7", "Cortex-A7", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A7 core trace', defaultValue=False, childOptions =
                        # Allow each source to be enabled/disabled individually
                        [ DTSLv1.booleanOption('Cortex_A7_%d' % c, "Enable Cortex-A7 %d trace" % c, defaultValue=True)
                        for c in range(0, NUM_CORES_CORTEX_A7) ] +
                        [ DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False) ] +
                        [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                        [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                            childOptions = [
                                DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                    values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                ])
                        ] +
                        # Pull in common options for ETMs
                        ETMv3_5TraceSource.defaultOptions(DtslScript.getETMs) +
                        [  # Data trace
                        ETMv3_5TraceSource.dataOption(DtslScript.getETMs),
                        # Trace range selection (e.g. for linux kernel)
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
                                    display=IIntegerOption.DisplayFormat.HEX)
                            ])
                        ]
                    )
                ]),
                DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer', 'Configure the system memory trace buffer to be used by the ETR/TMC device',defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the ETR/TMC device',
                            defaultValue=0x90000000,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('size', 'Size in bytes',
                            description='Size of the system memory trace buffer in bytes',
                            defaultValue=0x8000,
                            isDynamic=True,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.booleanOption('scatterGather','Enable scatter-gather mode',
                            defaultValue=False,
                            description='When enabling scatter-gather mode, the start address of the on-chip trace buffer must point to a configured scatter-gather table')
                        ]
                    )
                ]),
                DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ]),
            ])]
