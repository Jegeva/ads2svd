# Copyright (C) 2014-2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMHTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import RDDISyncSMPDevice
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
from com.arm.debug.dtsl.components import ConnectableTraceCaptureBase
import hsstp_usecase

NUM_CORES_CORTEX_R4 = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
TPIU_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers
CORTEX_R4_TRACE_OPTIONS = 0

class DSTREAMHTTraceCapture(DSTREAMHTStoreAndForwardTraceCapture):
    def __init__(self, configuration, name, ahb, apb, dtslConfigScript):
        DSTREAMHTStoreAndForwardTraceCapture.__init__(self, configuration, name)
        self.ahb = ahb
        self.apb = apb
        self.firstHalt=True
        self.firstStart=True
        self.configuration = configuration
        self.dtslConfigScript = dtslConfigScript

    def postConnect(self):
        DSTREAMHTStoreAndForwardTraceCapture.postConnect(self)
        hsstp_usecase.configureLink(self)

    def stop(self):
        # After initialisation the link can fail, so just reset the SCLK Domain Logic
        if self.firstHalt:
            self.firstHalt = False
            hsstp_usecase.resetSCLKDomain(self.apb, self.dtslConfigScript)
        DSTREAMHTStoreAndForwardTraceCapture.stop(self)

    def start(self):
        # After initialisation the link can fail, so just reset the SCLK Domain Logic
        DSTREAMHTStoreAndForwardTraceCapture.start(self)
        if self.firstHalt:
            self.firstHalt = False
            hsstp_usecase.resetSCLKDomain(self.apb, self.dtslConfigScript)

class DSTREAMHSSTPTraceCapture(DSTREAMTraceCapture):
    def __init__(self, configuration, name, ahb, apb, dtslConfigScript):
        DSTREAMTraceCapture.__init__(self, configuration, name)
        self.ahb = ahb
        self.apb = apb
        self.firstHalt=True
        self.firstStart=True
        self.configuration = configuration
        self.dtslConfigScript = dtslConfigScript
        self.trace = None
        self.traceConn = None

    def postConnect(self):
        # Do target setup and wait for HSSTP link to train polling extended probe status
        # using trace transaction call
        DSTREAMTraceCapture.postConnect(self)
        hsstp_usecase.configureLink(self)

    def stop(self):
        # After initialisation the link can fail, so just reset the SCLK Domain Logic
        if self.firstHalt:
            self.firstHalt = False
            hsstp_usecase.resetSCLKDomain(self.apb, self.dtslConfigScript)
        DSTREAMTraceCapture.stop(self)

    def start(self):
        # After initialisation the link can fail, so just reset the SCLK Domain Logic
        DSTREAMTraceCapture.start(self)
        if self.firstHalt:
            self.firstHalt = False
            hsstp_usecase.resetSCLKDomain(self.apb, self.dtslConfigScript)

    def isProbeLinkUp(self):
        # No way to query the HSSTP so assume not up
        if not self.traceConn:
            return False
        # Do GetExtendedStatus command
        transactionCommand = zeros(1, 'b')
        transactionCommand[0] = 1 # 1 - TRACE_EXTENDED_STATUS_TRANSACTION
        dataOut = zeros(4, 'b')
        dataOutLen = zeros(1, 'i')
        self.trace.transaction(self.traceConn, transactionCommand, dataOut, dataOutLen)
        value = unpack('I', dataOut)[0]
        if value & 0x30000000 != 0x30000000:
            return False
        return True

class TraceRangeOptions:
    def __init__(self, coreName = None, dtsl = None):
        if coreName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("options.%s.coreTrace.traceRange" % coreName)
            self.traceRangeStart = dtsl.getOptionValue("options.%s.coreTrace.traceRange.start" % coreName)
            self.traceRangeEnd = dtsl.getOptionValue("options.%s.coreTrace.traceRange.end" % coreName)
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
                DtslScript.getOptionCortexR4TabPage(),
                DtslScript.getOptionHSSTPTabPage()
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
    def getOptionCortexR4TabPage():
        return DTSLv1.tabPage("cortexR4", "Cortex-R4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R4 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_R4_%d' % c, "Enable Cortex-R4 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_R4) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False) ] +
                            [ DTSLv1.booleanOption('contextIDs',
                                                   "Enable ETM Context IDs",
                                                   description="Controls the output of context ID values into the ETM output streams",
                                                   defaultValue=True,
                                                   childOptions = [
                                                       DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                                           values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                                       ]),
                            ] +
                            [ ETMv3_3TraceSource.cycleAccurateOption(DtslScript.getETMsForCortex_R4) ] +
                            [ ETMv3_3TraceSource.dataOption(DtslScript.getETMsForCortex_R4) ] +
                            [ # Trace range selection (e.g. for linux kernel)
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
                        ),
                ])

    @staticmethod
    def getOptionHSSTPTabPage():
        return DTSLv1.tabPage("HSSTP_options", "HSSTP Options", childOptions=[
                    DTSLv1.booleanOption('targetClocks', "Configure Target Clocks", defaultValue=False, childOptions = [
                        DTSLv1.enumOption('FrefInput', 'Fref', defaultValue="0xF020",
                        values = [("0xF010", "25 MHz"), ("0xF020", "30 MHz"), ("0xF030", "40 MHz")])
                    ]),
                    DTSLv1.enumOption('portWidth', 'Port Width', defaultValue="16", description="Configure the Serial ETM Port Width",
                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
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
        if self.AHB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.AHB)
        if self.APB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.APB)

        self.exposeCores()

        self.traceRangeIDs = {}

        traceComponentOrder = [ self.Funnel0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(TPIU_PORTWIDTH, traceComponentOrder, managedDevices)

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-R4 trace options
            ]

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''
        memApDev = 0

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.AHB = AHBAP(self, memApDev, "AHB")

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.APB = APBAP(self, memApDev, "APB")

        cortexR4coreDevs = [5, 8]
        self.cortexR4cores = []

        streamID = 1

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, 2, "OutCTI0")

        coreCTIDevs = [6, 9]
        self.CoreCTIs = []

        etmDevs = [7, 10]
        self.ETMs = []

        for i in range(0, NUM_CORES_CORTEX_R4):
            # Create core
            core = Device(self, cortexR4coreDevs[i], "Cortex-R4_%d" % i)
            self.cortexR4cores.append(core)

        for i in range(0, len(coreCTIDevs)):
            # Create CTI
            coreCTI = CSCTI(self, coreCTIDevs[i], "CoreCTIs[%d]" % i)
            self.CoreCTIs.append(coreCTI)

        for i in range(0, len(etmDevs)):
            # Create ETM
            etm = self.createETM(etmDevs[i], streamID, "ETMs[%d]" % i)
            streamID += 1

        # DSTREAM
        self.createDSTREAM()

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.TPIU = CSTPIU(self, tpiuDev, "TPIU")

        # Funnel 0
        self.Funnel0 = self.createFunnel(4, "Funnel0")

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMHSSTPTraceCapture(self, "DSTREAM", self.AHB, self.APB, self)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP"),
            AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP"),
        ])

    def exposeCores(self):
        for core in self.cortexR4cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # Configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.setPortWidth(portWidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def setPortWidth(self, portWidth):
        self.TPIU.setPortSize(portWidth)
        # portWidth has no effect on the DSTREAM object for HSSTP
        # but we need to set it to something so that DSTREAMTraceCapture doesn't throw when connecting
        self.DSTREAM.setPortWidth(16)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sources to CTIs
        sourceCTIMap = {}
        sourceCTIMap[self.ETMs[0]] = (self.CoreCTIs[0], 6, CTM_CHANNEL_TRACE_TRIGGER)
        sourceCTIMap[self.ETMs[1]] = (self.CoreCTIs[1], 6, CTM_CHANNEL_TRACE_TRIGGER)

        return sourceCTIMap.get(source, (None, None, None))

    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sinks to CTIs
        sinkCTIMap = {}
        sinkCTIMap[self.DSTREAM] = (self.OutCTI0, 3, CTM_CHANNEL_TRACE_TRIGGER)

        return sinkCTIMap.get(sink, (None, None, None))

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''

        # Build map of cores to trace macrocells
        coreTMMap = {}
        coreTMMap[self.cortexR4cores[0]] = self.ETMs[0]
        coreTMMap[self.cortexR4cores[1]] = self.ETMs[1]

        return coreTMMap.get(core, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createETM(self, etmDev, streamID, name):
        '''Create ETM of correct version'''
        if etmDev == 7:
            etm = ETMv3_3TraceSource(self, etmDev, streamID, name)
            # Disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            return etm
        if etmDev == 10:
            etm = ETMv3_3TraceSource(self, etmDev, streamID, name)
            # Disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            return etm

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_R4):
            coreTM = self.getTMForCore(self.cortexR4cores[c])
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexR4cores[c], coreTM)


    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # Source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

        # CTI (if present) is also managed by the configuration
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.addManagedTraceDevices(traceCapture.getName(), [ cti ])

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnels and funnel ports
        funnelMap = {}
        funnelMap[self.ETMs[0]] = (self.Funnel0, 0)
        funnelMap[self.ETMs[1]] = (self.Funnel0, 1)

        return funnelMap.get(source, (None, None))

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

        coreTraceEnabled = self.getOptionValue("options.cortexR4.coreTrace")
        for i in range(0, NUM_CORES_CORTEX_R4):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexR4.coreTrace.Cortex_R4_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexR4cores[i])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setContextIDEnabled(self.ETMs[i],
                                         self.getOptionValue("options.cortexR4.coreTrace.contextIDs"),
                                         self.getOptionValue("options.cortexR4.coreTrace.contextIDs.contextIDsSize"))
            self.setInternalTraceRange(coreTM, "cortexR4")
            self.setTriggerGeneratesDBGRQ(coreTM, self.getOptionValue("options.cortexR4.coreTrace.triggerhalt"))

        # Register trace sources for each trace sink
        self.registerTraceSources(self.DSTREAM)

        traceMode = self.getOptionValue("options.trace.traceCapture")
        self.setManagedDeviceList(self.getManagedDevices(traceMode))

        portWidth = self.getOptionValue("options.HSSTP_options.portWidth")
        self.setPortWidth(int(portWidth))

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
            self.setDSTREAMTraceEnabled(False)
        elif method == "DSTREAM":
            self.setDSTREAMTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def getETMsForCortex_R4(self):
        '''Get the ETMs for Cortex-R4 cores only'''
        return [self.getTMForCore(core) for core in self.cortexR4cores]

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

    def setInternalTraceRange(self, coreTM, coreName):

        traceRangeEnable = self.getOptionValue("options.%s.coreTrace.traceRange" % coreName)
        traceRangeStart = self.getOptionValue("options.%s.coreTrace.traceRange.start" % coreName)
        traceRangeEnd = self.getOptionValue("options.%s.coreTrace.traceRange.end" % coreName)

        if coreTM in self.traceRangeIDs:
            coreTM.clearTraceRange(self.traceRangeIDs[coreTM])
            del self.traceRangeIDs[coreTM]

        if traceRangeEnable:
            self.traceRangeIDs[coreTM] = coreTM.addTraceRange(traceRangeStart, traceRangeEnd)

    def setContextIDEnabled(self, xtm, state, size):
        if state == False:
            xtm.setContextIDs(False, IARMCoreTraceSource.ContextIDSize.NONE)
        else:
            contextIDSizeMap = {
                 "8":IARMCoreTraceSource.ContextIDSize.BITS_7_0,
                "16":IARMCoreTraceSource.ContextIDSize.BITS_15_0,
                "32":IARMCoreTraceSource.ContextIDSize.BITS_31_0 }
            xtm.setContextIDs(True, contextIDSizeMap[size])

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

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        funnel, port = self.getFunnelPortForSource(source)
        if funnel:
            if enabled:
                funnel.setPortEnabled(port)
            else:
                funnel.setPortDisabled(port)

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]

class DtslScript_DSTREAM_HT(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_HT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexR4TabPage(),
                DtslScript.getOptionHSSTPTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("DSTREAM", "DSTREAM-HT 8GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMHTTraceCapture(self, "DSTREAM", self.AHB, self.APB, self)

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # Configure the DSTREAM for continuous trace
        self.setPortWidth(portWidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def setPortWidth(self, portWidth):
        # DSTREAM-HT doesn't need to know the port width
        self.TPIU.setPortSize(portWidth)

