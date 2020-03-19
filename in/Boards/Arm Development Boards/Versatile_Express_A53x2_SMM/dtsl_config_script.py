# Copyright (C) 2013-2019 Arm Limited (or its affiliates). All rights reserved.
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
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTLiveStoredStreamingTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import CTISyncSMPDevice

NUM_CORES_CORTEX_A53 = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 2  # Use channel 2 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 3  # Use channel 3 for trace triggers

# import core specific functions from Cores folder
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a53_rams

class DtslScript(DTSLv1):

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("traceBuffer", "Trace Buffer", childOptions=[
            DTSLv1.enumOption(
              'traceCapture',
              'Trace capture method',
              defaultValue="none",
              values=[("none", "None"),
                      ("ETB0", "On Chip Trace Buffer (ETB0)"),
                      ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
              setter=DtslScript.setTraceCaptureMethod)
        ])

    @staticmethod
    def getOptionCortexA53TabPage():
        return DTSLv1.tabPage("cortexA53", "Cortex-A53", childOptions=[
            DTSLv1.booleanOption(
              'coreTrace',
              'Enable Cortex-A53 core trace',
              defaultValue=False,
              childOptions=[
                # Allow each source to be enabled/disabled individually
                DTSLv1.booleanOption(
                  'Cortex_A53_%d' % c,
                  "Enable Cortex-A53 %d trace" % c,
                  defaultValue=True)
                for c in range(0, NUM_CORES_CORTEX_A53)] + [
                ETMv4TraceSource.cycleAccurateOption(DtslScript.getETMsForCortexAR)] + [
                # Trace range selection (e.g. for linux kernel)
                DTSLv1.booleanOption(
                  'traceRange',
                  'Trace capture range',
                  description=TRACE_RANGE_DESCRIPTION,
                  defaultValue = False,
                  childOptions = [
                    DTSLv1.integerOption(
                      'start',
                      'Start address',
                      description='Start address for trace capture',
                      defaultValue=0,
                      display=IIntegerOption.DisplayFormat.HEX),
                    DTSLv1.integerOption(
                      'end',
                      'End address',
                      description='End address for trace capture',
                      defaultValue=0xFFFFFFFF,
                      display=IIntegerOption.DisplayFormat.HEX)])
              ]
            )
        ])

    @staticmethod
    def getOptionITMTabPage():
        return DTSLv1.tabPage("ITM", "ITM", childOptions=[
            DTSLv1.booleanOption(
              'ITM0',
              'Enable ITM 0 trace',
              defaultValue=False)])

    @staticmethod
    def getRAMOptions():
        return DTSLv1.tabPage("rams", "Cache RAMs", childOptions =[
            # Turn cache debug mode on/off
            DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                 description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                 defaultValue=False, isDynamic=True),
            DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                 description='Preserve the contents of caches while the core is stopped.',
                                 defaultValue=False, isDynamic=True),
            ])

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getRAMOptions()
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
        if self.AHB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.AHB)
        if self.APB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.APB)

        self.exposeCores()

        self.traceRangeIDs = {}

        self.setupCTISyncSMP()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        memApDev = 0

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.AHB = AHBAP(self, memApDev, "AHB")

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.APB = APBAP(self, memApDev, "APB")

        cortexA53coreDevs = [10, 14]
        self.cortexA53cores = []

        streamID = 1

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, 3, "OutCTI0")

        coreCTIDevs = [11, 15]
        self.CoreCTIs = []

        etmDevs = [13, 17]
        self.ETMs = []
        self.cortexARetms = []

        # ITM 0
        self.ITM0 = self.createITM(6, streamID, "ITM0")
        streamID += 1

        for i in range(0, NUM_CORES_CORTEX_A53):
            # Create core
            core = a53_rams.A53CoreDevice(self, cortexA53coreDevs[i], "Cortex-A53_%d" % i)
            self.cortexA53cores.append(core)

        for i in range(0, len(coreCTIDevs)):
            # Create CTI
            coreCTI = CSCTI(self, coreCTIDevs[i], "CoreCTIs[%d]" % i)
            self.CoreCTIs.append(coreCTI)

        for i in range(0, len(etmDevs)):
            # Create ETM
            etm = self.createETM(etmDevs[i], streamID, "ETMs[%d]" % i)
            streamID += 1

        # TPIU
        self.TPIU = self.createTPIU(4, "TPIU")

        # Funnel 0
        self.Funnel0 = self.createFunnel(5, "Funnel0")

        # Funnel 1
        self.Funnel1 = self.createFunnel(8, "Funnel1")
        # self.Funnel0 is connected to self.Funnel1 port 0
        self.Funnel1.setPortEnabled(0)

        # Funnel 2
        self.Funnel2 = self.createFunnel(9, "Funnel2")
        # self.Funnel1 is connected to self.Funnel2 port 0
        self.Funnel2.setPortEnabled(0)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP"),
            AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP"),
        ])

    def exposeCores(self):
        for core in self.cortexA53cores:
            a53_rams.registerInternalRAMs(core)
            self.registerFilters(core)
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

    def createETBTraceCapture(self):
        self.ETB0 = ETBTraceCapture(self, 2, "ETB0")

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def setPortWidth(self, portWidth):
        self.TPIU.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def setupDSTREAMTrace(self, portwidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # Set dstream and tpiu port width
        self.setPortWidth(portwidth)

        # Configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def getCTIInfoForCore(self, core):
        '''Get the CTI info associated with a core
        return None if no associated CTI info
        '''

        # Build map of cores to DeviceCTIInfo objects
        ctiInfoMap = {}
        ctiInfoMap[self.cortexA53cores[0]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[0], CTISyncSMPDevice.DeviceCTIInfo.NONE, 1, 0, 0)
        ctiInfoMap[self.cortexA53cores[1]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[1], CTISyncSMPDevice.DeviceCTIInfo.NONE, 1, 0, 0)

        return ctiInfoMap.get(core, None)

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
        sinkCTIMap["ETB0"] = (self.OutCTI0, 1, CTM_CHANNEL_TRACE_TRIGGER)
        sinkCTIMap["TPIU"] = (self.OutCTI0, 3, CTM_CHANNEL_TRACE_TRIGGER)

        return sinkCTIMap.get(sink, (None, None, None))

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''

        # Build map of cores to trace macrocells
        coreTMMap = {}
        coreTMMap[self.cortexA53cores[0]] = self.ETMs[0]
        coreTMMap[self.cortexA53cores[1]] = self.ETMs[1]

        return coreTMMap.get(core, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createETM(self, etmDev, streamID, name):
        '''Create ETM of correct version'''
        if etmDev == 13:
            etm = ETMv4TraceSource(self, etmDev, streamID, name)
            # Disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            self.cortexARetms.append(etm)
            return etm
        if etmDev == 17:
            etm = ETMv4TraceSource(self, etmDev, streamID, name)
            # Disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            self.cortexARetms.append(etm)
            return etm

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for sync start/stop
        # Cortex-A53 CTI SMP setup
        ctiInfo = {}
        for c in self.cortexA53cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)
        smp = CTISyncSMPDevice(self, "Cortex-A53 SMP", self.cortexA53cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp)
        self.addDeviceInterface(smp)

        # Automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CoreCTIs)

    def setETBTraceEnabled(self, enabled):
        '''Enable/disable ETB trace capture'''
        self.etbTraceEnabled = enabled
        self.enableCTIsForSink("ETB0", enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.dstreamTraceEnabled = enabled
        self.TPIU.setEnabled(enabled)
        self.enableCTIsForSink("TPIU", enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A53):
            coreTM = self.getTMForCore(self.cortexA53cores[c])
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexA53cores[c], coreTM)

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

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnels and funnel ports
        funnelMap = {}
        funnelMap[self.ITM0] = (self.Funnel0, 3)
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

        ''' Setup whichever trace capture device was selected (if any) '''
        if self.dstreamTraceEnabled:
            self.createDSTREAM()
            traceComponentOrder = [ self.Funnel0, self.Funnel1, self.Funnel2, self.TPIU ]
            managedDevices = [ self.Funnel0, self.Funnel1, self.Funnel2, self.OutCTI0, self.TPIU, self.DSTREAM ]
            self.setupDSTREAMTrace(DSTREAM_PORTWIDTH, traceComponentOrder, managedDevices)
        elif self.etbTraceEnabled:
            self.createETBTraceCapture()
            traceComponentOrder = [ self.Funnel0, self.Funnel1, self.Funnel2 ]
            managedDevices = [ self.Funnel0, self.Funnel1, self.Funnel2, self.OutCTI0, self.TPIU, self.ETB0 ]
            self.setupETBTrace(self.ETB0, "ETB0", traceComponentOrder, managedDevices)

        coreTraceEnabled = self.getOptionValue("options.cortexA53.coreTrace")
        for i in range(0, NUM_CORES_CORTEX_A53):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA53.coreTrace.Cortex_A53_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexA53cores[i])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "cortexA53")

        itmEnabled = self.getOptionValue("options.itm.ITM0")
        self.setTraceSourceEnabled(self.ITM0, itmEnabled)

        if self.dstreamTraceEnabled:
            dstream_opts = "options.traceBuffer.traceCapture." + self.getDstreamOptionString() + "."

            portWidthOpt = self.getOptions().getOption(dstream_opts + "tpiuPortWidth")
            if portWidthOpt:
               portWidth = self.getOptionValue(dstream_opts + "tpiuPortWidth")
               self.setPortWidth(int(portWidth))

            traceBufferSizeOpt = self.getOptions().getOption(dstream_opts + "traceBufferSize")
            if traceBufferSizeOpt:
                traceBufferSize = self.getOptionValue(dstream_opts + "traceBufferSize")
                self.setTraceBufferSize(traceBufferSize)

        # Register trace sources for each trace sink
        if self.dstreamTraceEnabled:
            self.registerTraceSources(self.DSTREAM)
        elif self.etbTraceEnabled:
            self.registerTraceSources(self.ETB0)

        traceMode = self.getOptionValue("options.traceBuffer.traceCapture")
        self.setManagedDeviceList(self.getManagedDevices(traceMode))

    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        for i in range(0, NUM_CORES_CORTEX_A53):
            a53_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA53cores[i])
            a53_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA53cores[i])

    def getDstreamOptionString(self):
        return "dstream"

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setETBTraceEnabled(False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "ETB0":
            self.setETBTraceEnabled(True)
            self.setDSTREAMTraceEnabled(False)
        elif method in ["DSTREAM", "DSTREAM_PT_Store_and_Forward", "DSTREAM_PT_StreamingTrace"]:
            self.setETBTraceEnabled(False)
            self.setDSTREAMTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def getETMsForCortexAR(self):
        '''Get the ETMs for Cortex-A and Cortex-R cores only'''
        return self.cortexARetms

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

    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, itmDev, streamID, name)
        # Disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, portwidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)

        # Set dstream and tpiu port width
        self.setPortWidth(portwidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(self.getOptionValue("options.traceBuffer.traceCapture"), managedDevices)

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
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getRAMOptions()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("traceBuffer", "Trace Buffer", childOptions=[
            DTSLv1.radioEnumOption(
              'traceCapture',
              'Trace capture method',
              defaultValue="none",
              values=[("none", "None"),
                      ("ETB0", "On Chip Trace Buffer (ETB0)"),
                      (DtslScript_DSTREAM_ST.getDSTREAMOptions())],
              setter=DtslScript.setTraceCaptureMethod)
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
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionITMTabPage(),
                DtslScript.getRAMOptions()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("traceBuffer", "Trace Buffer", childOptions=[
            DTSLv1.radioEnumOption(
              'traceCapture',
              'Trace capture method',
              defaultValue="none",
              values=[("none", "None"),
                      ("ETB0", "On Chip Trace Buffer (ETB0)"),
                      DtslScript_DSTREAM_PT.getStoreAndForwardOptions(),
                      DtslScript_DSTREAM_PT.getStreamingTraceOptions()],
              setter=DtslScript.setTraceCaptureMethod)
        ])

    @staticmethod
    def getStoreAndForwardOptions():
        return (
            "DSTREAM_PT_Store_and_Forward", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement(
                "dpt_storeandforward", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="16",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit"),
                                  ("5", "5 bit"), ("6", "6 bit"), ("7", "7 bit"), ("8", "8 bit"),
                                  ("9", "9 bit"), ("10", "10 bit"), ("11", "11 bit"), ("12", "12 bit"),
                                  ("13", "13 bit"), ("14", "14 bit"), ("15", "15 bit"), ("16", "16 bit"),
                                  ("18", "18 bit"), ("20", "20 bit"), ("22", "22 bit"), ("24", "24 bit"),
                                  ("26", "26 bit"), ("28", "28 bit"), ("30", "30 bit"), ("32", "32 bit")], isDynamic=False)
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
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="16",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit"),
                                  ("5", "5 bit"), ("6", "6 bit"), ("7", "7 bit"), ("8", "8 bit"),
                                  ("9", "9 bit"), ("10", "10 bit"), ("11", "11 bit"), ("12", "12 bit"),
                                  ("13", "13 bit"), ("14", "14 bit"), ("15", "15 bit"), ("16", "16 bit"),
                                  ("18", "18 bit"), ("20", "20 bit"), ("22", "22 bit"), ("24", "24 bit"),
                                  ("26", "26 bit"), ("28", "28 bit"), ("30", "30 bit"), ("32", "32 bit")], isDynamic=False),
                    DTSLv1.enumOption('traceBufferSize', 'Host trace buffer size', defaultValue="4GB",
                        values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"),
                                  ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"),
                                  ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                ]
            )
        )

    def getDstreamOptionString(self):
        if self.getOptionValue("options.traceBuffer.traceCapture") == "DSTREAM_PT_Store_and_Forward":
            return "dpt_storeandforward"
        if self.getOptionValue("options.traceBuffer.traceCapture") == "DSTREAM_PT_StreamingTrace":
            return "dpt_streamingtrace"

    def createDSTREAM(self):
        if self.getOptionValue("options.traceBuffer.traceCapture") == "DSTREAM_PT_Store_and_Forward":
            self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM_PT_Store_and_Forward")
        elif self.getOptionValue("options.traceBuffer.traceCapture") == "DSTREAM_PT_StreamingTrace":
            self.DSTREAM = DSTREAMPTLiveStoredStreamingTraceCapture(self, "DSTREAM_PT_StreamingTrace")
