# Copyright (C) 2017-2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.configurations import TimestampInfo

coreNames = ["V8M-Generic"]
dapIndices = [0]
ctiNames = [None]
ctiCoreTriggers = [None]
ctiMacrocellTriggers = [None]
macrocellNames = ["CSETM", "CSITM"]
funnelNames = ["CSTFunnel", "CSTFunnel"]
funnelPorts = [1, 0]
coreNames_v8MGeneric = ["V8M-Generic"]


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
                DtslScript.getTraceCaptureTabPage(),
                DtslScript.getCoreTabPage(),
                DtslScript.getItmTabPage(),
            ])
        ]

    @staticmethod
    def getTraceCaptureTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
            DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                values = [("none", "None"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                setter=DtslScript.setTraceCaptureMethod),
            DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
            ]),
            DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                    values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False),
            ]),
        ])

    @staticmethod
    def getCoreTabPage():
        return DTSLv1.tabPage("v8MGeneric", "V8M-Generic", childOptions=[
            DTSLv1.booleanOption('coreTrace', 'Enable V8M-Generic core trace', defaultValue=False,
                childOptions =
                    # Allow each source to be enabled/disabled individually
                    [ DTSLv1.booleanOption('V8M_Generic_%d' % core, "Enable " + coreNames_v8MGeneric[core] + " trace", defaultValue=True)
                    for core in range(len(coreNames_v8MGeneric)) ] +
                    [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ]
                ),
        ])

    @staticmethod
    def getItmTabPage():
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

        self.exposeCores()

        traceComponentOrder = [ self.Funnel0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(traceComponentOrder, managedDevices)

        self.setManagedDeviceList(self.mgdPlatformDevs)

        self.setDSTREAMTraceEnabled(False)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        self.APBs = []
        self.AHB_Ms = []

        ap = APBAP(self, self.findDevice("CSMEMAP_0"), "APB_0")
        self.mgdPlatformDevs.append(ap)
        self.APBs.append(ap)

        ap = CortexM_AHBAP(self, self.findDevice("CSMEMAP_1"), "AHB_M_0")
        self.mgdPlatformDevs.append(ap)
        self.AHB_Ms.append(ap)


        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1

        # ITM 0
        self.ITM0 = self.createITM("CSITM", streamID, "CSITM")
        streamID += 1

        # For future use, store a map of core types and cluster names against created devices
        self.macrocells = {}
        self.macrocells["v8MGeneric"] = []

        self.v8MGenericcores = []
        for core in range(len(coreNames_v8MGeneric)):
            # Create core
            coreDevice = Device(self, self.findDevice(coreNames_v8MGeneric[core]), coreNames_v8MGeneric[core])
            self.v8MGenericcores.append(coreDevice)

            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmDev = self.getMacrocellNameForCore(coreNames_v8MGeneric[core])
            if not tmDev == None:
                tm = M_Class_ETMv4(self, self.findDevice(tmDev), streamID, tmDev)
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["v8MGeneric"].append(tm)

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
                AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 0 (CSMEMAP_0)"),
                AHBCortexMMemAPAccessor("AHB_M_0", self.AHB_Ms[0], "AHB-M bus accessed via AP 1 (CSMEMAP_1)"),
            ])

    def exposeCores(self):
        '''Ensure that cores have access to memory'''
        for i in range(len(coreNames)):
            core = self.getDeviceInterface(coreNames[i])
            self.registerFilters(core, dapIndices[i])
            self.addDeviceInterface(core)

    def setupDSTREAMTrace(self, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

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

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/Disable all pertinent funnel ports for a trace source'''
        sourceName = source.getName()
        for i in range(len(macrocellNames)):
            if sourceName == macrocellNames[i]:
                '''We may have a list of funnels to which the source is connected.'''
                if isinstance(funnelNames[i], list):
                    for j in range(len(funnelNames[i])):
                        '''Enable/Disable multiple connected funnel ports for this trace source.'''
                        self.setFunnelPortEnabled(funnelNames[i][j], funnelPorts[i][j], enabled)
                else:
                    '''Enable/Disable a single connected funnel port for this trace source.'''
                    self.setFunnelPortEnabled(funnelNames[i], funnelPorts[i], enabled)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, self.findDevice(tpiuDev), name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for i in range(len(coreNames)):
            core = self.getDeviceInterface(coreNames[i])
            coreTM = self.getTMForCore(core)
            if coreTM is not None and coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, core, coreTM)

        i=len(coreNames)
        for macrocell in range(i, len(macrocellNames)):
            TM = self.getDeviceInterface(macrocellNames[macrocell])
            if TM is not None:
                self.registerTraceSource(traceCapture, TM)


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
            try:
                self.setInitialOptions()
            except:
                pass
        self.updateDynamicOptions()

    def setInitialOptions(self):
        '''Set the initial options'''

        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.v8MGeneric.coreTrace")
        for core in range(len(coreNames_v8MGeneric)):
            thisCoreTraceEnabled = self.getOptionValue("options.v8MGeneric.coreTrace.V8M_Generic_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.v8MGenericcores[core])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setTimestampingEnabled(coreTM, self.getOptionValue("options.v8MGeneric.coreTrace.timestamp"))

        portWidthOpt = self.getOptions().getOption("options.trace.offChip.tpiuPortWidth")
        if portWidthOpt:
            portWidth = self.getOptionValue("options.trace.offChip.tpiuPortWidth")
            self.setPortWidth(int(portWidth))

        traceBufferOpt = self.getOptions().getOption("options.trace.offChip.traceBufferSize")
        if traceBufferOpt:
            traceBufferSize = self.getOptionValue("options.trace.offChip.traceBufferSize")
            self.setTraceBufferSize(traceBufferSize)

        itmEnabled = self.getOptionValue("options.itm.CSITM")
        self.setTraceSourceEnabled(self.ITM0, itmEnabled)

        # Register trace sources for each trace sink
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

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''
        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return self.getDeviceInterface(macrocellNames[i])

        return None

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def getMacrocellNameForCore(self, coreName):
        '''Get the index of the dap with which this core is associated'''
        for index in range(len(coreNames)):
            if coreNames[index] == coreName:
                return macrocellNames[index]
        return None

    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, self.findDevice(funnelDev), name)
        funnel.setAllPortsDisabled() # Will enable for each source later
        return funnel

    def setFunnelPortEnabled(self, funnelName, port, enabled):
        '''Enable/disable a funnel port'''
        funnel = self.getDeviceInterface(funnelName)
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

        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)


class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_ST.getTraceCaptureTabPage(),
                DtslScript.getCoreTabPage(),
                DtslScript.getItmTabPage(),
            ])
        ]

    @staticmethod
    def getTraceCaptureTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
            DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                values = [("none", "None"), ("DSTREAM", "DSTREAM-ST Streaming Trace")],
                setter=DtslScript.setTraceCaptureMethod),
            DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
            ]),
            DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                    values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")], isDynamic=False),
                DTSLv1.enumOption('traceBufferSize', 'Trace Buffer Size', defaultValue="4GB",
                    values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"), ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"), ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
            ]),
        ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMSTStoredTraceCapture(self, "DSTREAM")

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


class DtslScript_DSTREAM_PT(DtslScript_DSTREAM_ST_Family):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_PT.getTraceCaptureTabPage(),
                DtslScript.getCoreTabPage(),
                DtslScript.getItmTabPage(),
            ])
        ]

    @staticmethod
    def getTraceCaptureTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
            DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                values = [("none", "None"), ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer")],
                setter=DtslScript.setTraceCaptureMethod),
            DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
            ]),
            DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                    values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False)
            ]),
        ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")
