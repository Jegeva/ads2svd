# Copyright (C) 2018-2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMHTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
import hsstp_usecase

tmDevs_cortexA9 = ["CSPTM_0", "CSPTM_1"]
ctiDevs_cortexA9 = ["CSCTI_3", "CSCTI_4"]
coreDevs_cortexA9 = ["Cortex-A9_0", "Cortex-A9_1"]
NUM_CORES_CORTEX_A9 = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
coresDap0 = ["Cortex-A9_0", "Cortex-A9_1"]
DSTREAM_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers


class DSTREAMHTTraceCapture(DSTREAMHTStoreAndForwardTraceCapture):
    def __init__(self, configuration, name, memAccessDevice):
        DSTREAMHTStoreAndForwardTraceCapture.__init__(self, configuration, name)
        self.memAccessDevice = memAccessDevice
        self.configuration = configuration

    def postConnect(self):
        # Do target setup and wait for HSSTP link to train
        DSTREAMHTStoreAndForwardTraceCapture.postConnect(self)
        hsstp_usecase.configureLink(self)

class DSTREAMHSSTPTraceCapture(DSTREAMTraceCapture):
    def __init__(self, configuration, name, memAccessDevice):
        DSTREAMTraceCapture.__init__(self, configuration, name)
        self.memAccessDevice = memAccessDevice
        self.configuration = configuration

    def postConnect(self):
        # Do target setup and wait for HSSTP link to train polling extended probe status
        # using trace transaction call
        DSTREAMTraceCapture.postConnect(self)
        hsstp_usecase.configureLink(self)

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

class DtslScript(DTSLv1):

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSETB", "On Chip Trace Buffer (CSETB)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                        values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False)
                ])

    @staticmethod
    def getOptionCortexA9TabPage():
        return DTSLv1.tabPage("cortexA9", "Cortex-A9", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A9_%d' % core, "Enable " + coreDevs_cortexA9[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_A9) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", defaultValue=False) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the output of context ID values into the PTM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ PTMTraceSource.cycleAccurateOption(DtslScript.getTraceMacrocellsForCoreType("cortexA9"))] +
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
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # Only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
        for i in range(len(self.AHBs)):
            if self.AHBs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.AHBs[i])

        for i in range(len(self.APBs)):
            if self.APBs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.APBs[i])

        self.exposeCores()

        self.traceRangeIDs = {}

        traceComponentOrder = [ self.Funnel0 ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.ETB0 ]
        self.setupETBTrace(self.ETB0, "CSETB", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH, traceComponentOrder, managedDevices)

        self.setupCTISyncSMP()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        apDevs_AHBs = ["CSMEMAP_0"]
        self.AHBs = []

        apDevs_APBs = ["CSMEMAP_1"]
        self.APBs = []

        for i in range(len(apDevs_AHBs)):
            apDevice = AHBAP(self, self.findDevice(apDevs_AHBs[i]), "AHB_%d" % i)
            self.AHBs.append(apDevice)

        for i in range(len(apDevs_APBs)):
            apDevice = APBAP(self, self.findDevice(apDevs_APBs[i]), "APB_%d" % i)
            self.APBs.append(apDevice)

        self.cortexA9cores = []

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, self.findDevice("CSCTI_0"), "CSCTI_0")

        self.CoreCTIs = []

        self.macrocells = {}
        self.macrocells["cortexA9"] = []

        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        # ITM 0
        self.ITM0 = self.createITM("CSITM", streamID, "CSITM")
        streamID += 1

        #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for core in range(NUM_CORES_CORTEX_A9):
            # Create core
            coreDevice = Device(self, self.findDevice(coreDevs_cortexA9[core]), coreDevs_cortexA9[core])
            self.cortexA9cores.append(coreDevice)

            # Create CTI (if a CTI exists for this core)
            if not ctiDevs_cortexA9[core] == None:
                coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexA9[core]), ctiDevs_cortexA9[core])
                self.CoreCTIs.append(coreCTI)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            if not tmDevs_cortexA9[core] == None:
                tm = PTMTraceSource(self, self.findDevice(tmDevs_cortexA9[core]), streamID, tmDevs_cortexA9[core])
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["cortexA9"].append(tm)

        # ETB 0
        self.ETB0 = ETBTraceCapture(self, self.findDevice("CSETB"), "CSETB")

        # DSTREAM
        self.createDSTREAM()

        # TPIU
        self.TPIU = self.createTPIU("CSTPIU", "TPIU")

        # Funnel 0
        self.Funnel0 = self.createFunnel("CSTFunnel", "CSTFunnel")

    def registerFilters(self, core, dap):
        '''Register MemAP filters to allow access to the APs for the device'''
        if dap == 0:
            core.registerAddressFilters([
                AHBMemAPAccessor("AHB_0", self.AHBs[0], "AHB bus accessed via AP 0 (CSMEMAP_0)"),
                AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 1 (CSMEMAP_1)"),
            ])

    def exposeCores(self):
        for coreName in coresDap0:
            core = self.getDeviceInterface(coreName)
            self.registerFilters(core, 0)
            self.addDeviceInterface(core)

    def setupETBTrace(self, etb, name, traceComponentOrder, managedDevices):
        '''Setup ETB trace capture'''
        # Use continuous mode
        etb.setFormatterMode(FormatterMode.CONTINUOUS)

        # Register other trace components with ETB and register ETB with configuration
        etb.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etb)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        self.TPIU.setPortSize(portWidth)

        # Configure the DSTREAM for trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.DSTREAM.setPortWidth(portWidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def setPortWidth(self, portWidth):
        self.TPIU.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        macrocellNames = ["CSITM", "CSPTM_0", "CSPTM_1"]
        funnelNames = ["CSTFunnel", "CSTFunnel", "CSTFunnel"]
        funnelPorts = [3, 0, 1]

        sourceName = source.getName()
        for i in range(len(macrocellNames)):
            if sourceName == macrocellNames[i]:
                return(self.getDeviceInterface(funnelNames[i]), funnelPorts[i])

        return (None, None)

    def getCTIInfoForCore(self, core):
        '''Get the funnel port number for a trace source'''

        coreNames = ["Cortex-A9_0", "Cortex-A9_1"]
        ctiNames = ["CSCTI_3", "CSCTI_4"]
        ctiTriggers = [7, 7]

        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return CTISyncSMPDevice.DeviceCTIInfo(self.getDeviceInterface(ctiNames[i]), CTISyncSMPDevice.DeviceCTIInfo.NONE, ctiTriggers[i], 0, 0)

        return None

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''
        macrocellNames = ["CSPTM_0", "CSPTM_1"]
        ctiNames = ["CSCTI_3", "CSCTI_4"]
        ctiTriggers = [6, 6]

        sourceName = source.getName()
        for i in range(len(macrocellNames)):
            if sourceName == macrocellNames[i]:
                return (self.getDeviceInterface(ctiNames[i]), ctiTriggers[i], CTM_CHANNEL_TRACE_TRIGGER)

        return (None, None, None)

    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        sinkNames = ["CSETB", "CSTPIU"]
        ctiNames = ["CSCTI_0", "CSCTI_0"]
        ctiTriggers = [1, 3]

        sinkName = sink.getName()
        for i in range(len(sinkNames)):
            if sinkName == sinkNames[i]:
                return (self.getDeviceInterface(ctiNames[i]), ctiTriggers[i], CTM_CHANNEL_TRACE_TRIGGER)

        return (None, None, None)

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''
        coreNames = ["Cortex-A9_0", "Cortex-A9_1"]
        macrocellNames = ["CSPTM_0", "CSPTM_1"]

        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return self.getDeviceInterface(macrocellNames[i])

        return None

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, self.findDevice(tpiuDev), name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for sync start/stop
        # Cortex-A9x2 CTI SMP
        ctiInfo = {}
        for c in self.cortexA9cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)

        smp = CTISyncSMPDevice(self, "Cortex-A9x2 SMP", self.cortexA9cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp, 0)
        self.addDeviceInterface(smp)

        # Automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CoreCTIs)

    def setETBTraceEnabled(self, etb, enabled):
        '''Enable/disable ETB trace capture'''
        self.enableCTIsForSink(etb, enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for core in self.cortexA9cores:
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

        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.cortexA9.coreTrace")
        for core in range(NUM_CORES_CORTEX_A9):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA9.coreTrace.Cortex_A9_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexA9cores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "cortexA9")
            self.setTriggerGeneratesDBGRQ(coreTM, self.getOptionValue("options.cortexA9.coreTrace.triggerhalt"))
            self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.cortexA9.coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexA9.coreTrace.contextIDs.contextIDsSize"))

        opt = self.getOptions().getOption("options.trace.tpiuPortWidth")
        if not opt is None:
            portWidth = self.getOptionValue("options.trace.tpiuPortWidth")
            self.TPIU.setPortSize(int(portWidth))
            self.DSTREAM.setPortWidth(int(portWidth))

        itmEnabled = self.getOptionValue("options.itm.CSITM")
        self.setTraceSourceEnabled(self.ITM0, itmEnabled)

        # Register trace sources for each trace sink
        self.registerTraceSources(self.ETB0)
        self.registerTraceSources(self.DSTREAM)

        self.setManagedDeviceList(self.getManagedDevices(traceMode))

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
            self.setETBTraceEnabled(self.ETB0, False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "CSETB":
            self.setETBTraceEnabled(self.ETB0, True)
            self.setDSTREAMTraceEnabled(False)
        elif method == "DSTREAM":
            self.setETBTraceEnabled(self.ETB0, False)
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

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the list of devices managed by the configuration, as long as they are not already present'''
        for d in devs:
            if d not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(d)

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

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

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
        funnel = CSFunnel(self, self.findDevice(funnelDev), name)
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

    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, self.findDevice(itmDev), streamID, name)
        # Disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

    def setContextIDEnabled(self, xtm, state, size):
        if state == False:
            xtm.setContextIDs(False, IARMCoreTraceSource.ContextIDSize.NONE)
        else:
            contextIDSizeMap = {
                 "8":IARMCoreTraceSource.ContextIDSize.BITS_7_0,
                "16":IARMCoreTraceSource.ContextIDSize.BITS_15_0,
                "32":IARMCoreTraceSource.ContextIDSize.BITS_31_0 }
            xtm.setContextIDs(True, contextIDSizeMap[size])

class DtslScript_RVI(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSETB", "On Chip Trace Buffer (CSETB)")],
                        setter=DtslScript_RVI.setTraceCaptureMethod),
                ])

class DtslScript_HSSTP(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_HSSTP.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSETB", "On Chip Trace Buffer (CSETB)"), ("DSTREAM", "DSTREAM HSSTP 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMHSSTPTraceCapture(self, "DSTREAM", self.AHBs[0])

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        self.TPIU.setPortSize(32)

        # Configure the DSTREAM for trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.DSTREAM.setPortWidth(portWidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

class DtslScript_DSTREAM_HT(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_HT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionITMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSETB", "On Chip Trace Buffer (CSETB)"), ("DSTREAM", "DSTREAM-HT 8GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMHTTraceCapture(self, "DSTREAM", self.AHBs[0])

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        self.setPortWidth(32)

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

class DtslScript_DSTREAM_ST(DtslScript):

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
                        values = [("none", "None"), ("CSETB", "On Chip Trace Buffer (CSETB)")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])

class DtslScript_DSTREAM_PT(DtslScript):

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
                        values = [("none", "None"), ("CSETB", "On Chip Trace Buffer (CSETB)"), ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                        values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False)
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        self.setPortWidth(portWidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)
