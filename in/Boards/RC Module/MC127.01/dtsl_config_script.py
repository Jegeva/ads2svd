from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import ETMv3_1TraceSource
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource

tmDevs_aRM1176JZFS = ["ETM"]
coreDevs_aRM1176JZFS = ["ARM1176JZF-S"]
NUM_CORES_ARM1176JZF_S = 1
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 16


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB", "On Chip Trace Buffer (ETB)")],
                        setter=DtslScript.setTraceCaptureMethod),
                ])]
                +[DTSLv1.tabPage("aRM1176JZFS", "ARM1176JZF-S", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable ARM1176JZF-S core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('ARM1176JZF_S_%d' % core, "Enable " + coreDevs_aRM1176JZFS[core] + " trace", defaultValue=True)
                            for core in range(0, NUM_CORES_ARM1176JZF_S) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=False,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                            ] +
                            [ ETMv3_1TraceSource.cycleAccurateOption(DtslScript.getTraceMacrocellsForCoreType("aRM1176JZFS"))] +
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
                ])]
            )
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.exposeCores()

        self.traceRangeIDs = {}

        traceComponentOrder = []
        managedDevices = [ self.ETB0 ]
        self.setupETBTrace(self.ETB0, "ETB", traceComponentOrder, managedDevices)

        traceComponentOrder = []
        managedDevices = [ self.DSTREAM ]
        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH, traceComponentOrder, managedDevices)

        self.setManagedDeviceList(self.mgdPlatformDevs)

        self.setETBTraceEnabled(self.ETB0, False)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        self.aRM1176JZFScores = []

        self.macrocells = {}
        self.macrocells["aRM1176JZFS"] = []

        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for core in range(NUM_CORES_ARM1176JZF_S):
            # Create core
            coreDevice = Device(self, self.findDevice(coreDevs_aRM1176JZFS[core]), coreDevs_aRM1176JZFS[core])
            self.aRM1176JZFScores.append(coreDevice)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            if not tmDevs_aRM1176JZFS[core] == None:
                tm = ETMv3_1TraceSource(self, self.findDevice(tmDevs_aRM1176JZFS[core]), tmDevs_aRM1176JZFS[core])
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["aRM1176JZFS"].append(tm)

        # ETB 0
        self.ETB0 = ETBTraceCapture(self, self.findDevice("ETB"), "ETB")

        # DSTREAM
        self.createDSTREAM()

    def exposeCores(self):
        for core in self.aRM1176JZFScores:
            self.addDeviceInterface(core)

    def setupETBTrace(self, etb, name, traceComponentOrder, managedDevices):
        '''Setup ETB trace capture'''
        # Use bypass mode
        etb.setFormatterMode(FormatterMode.BYPASS)

        # Register other trace components with ETB and register ETB with configuration
        etb.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etb)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)

    def setupDSTREAMTrace(self, portwidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the DSTREAM for trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Raw)
        self.DSTREAM.setPortWidth(portwidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)


    def getTMForCore(self, core):
        '''Get trace macrocell for core'''
        coreNames = ["ARM1176JZF-S"]
        macrocellNames = ["ETM"]

        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return self.getDeviceInterface(macrocellNames[i])

        return None

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)

    def setETBTraceEnabled(self, etb, enabled):
        '''Enable/disable ETB trace capture'''

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for core in self.aRM1176JZFScores:
            coreTM = self.getTMForCore(core)
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, core, coreTM)

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

        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.aRM1176JZFS.coreTrace")
        for core in range(NUM_CORES_ARM1176JZF_S):
            thisCoreTraceEnabled = self.getOptionValue("options.aRM1176JZFS.coreTrace.ARM1176JZF_S_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.aRM1176JZFScores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "aRM1176JZFS")
            self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.aRM1176JZFS.coreTrace.contextIDs"),
                                     self.getOptionValue("options.aRM1176JZFS.coreTrace.contextIDs.contextIDsSize"))

            if ("DSTREAM" in traceMode):
                # We are using a Core TM directly with the DSTREAM unit so it is essential that the TM/DSTREAM port widths match
                coreTM.setPortWidth(DSTREAM_PORTWIDTH)
            else:
                # We are using other trace capture devices, so use the default TM port width
                coreTM.setPortWidthDefault()

        # Register trace sources for each trace sink
        self.registerTraceSources(self.ETB0)

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
        if method == "ETB":
            self.setETBTraceEnabled(self.ETB0, True)
        if method == "DSTREAM":
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

    def setContextIDEnabled(self, xtm, state, size):
        if state == False:
            xtm.setContextIDs(False, IARMCoreTraceSource.ContextIDSize.NONE)
        else:
            contextIDSizeMap = {
                 "8":IARMCoreTraceSource.ContextIDSize.BITS_7_0,
                "16":IARMCoreTraceSource.ContextIDSize.BITS_15_0,
                "32":IARMCoreTraceSource.ContextIDSize.BITS_31_0 }
            xtm.setContextIDs(True, contextIDSizeMap[size])

