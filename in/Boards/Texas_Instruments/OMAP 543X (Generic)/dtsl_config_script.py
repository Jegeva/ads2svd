from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource

from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE
from struct import pack, unpack
from jarray import array, zeros
from java.lang import StringBuilder
from java.lang import Long


NUM_CORES_CORTEX_A15 = 2
NUM_CORES_CORTEX_M4 = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
ATB_ID_BASE = 2
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
CORTEX_A15_TRACE_OPTIONS = 0

def writeMem(dev, addr, value):
    dev.writeMem(addr, value)

def readMem(dev, addr):
    buffer = zeros(4, 'b')
    return dev.readMem(addr)

def doM4Writes(dev):
    """ The magic writes to wake the M4s """
    PM_IPU_RSTCTRL = 0x4AE06910
    CORTEXM4_RTOS_IN_RESET   = 0x01
    CORTEXM4_SIMCOP_IN_RESET = 0x02
    CACHE_IN_RESET = 0x04
    CORTEXM4_RESET_MASK      = CORTEXM4_SIMCOP_IN_RESET | CORTEXM4_RTOS_IN_RESET
    RESET_MASK      = CACHE_IN_RESET | CORTEXM4_SIMCOP_IN_RESET | CORTEXM4_RTOS_IN_RESET

    PM_IPU_RSTST = 0x4AE06914
    RST_IPU_MMU_CACHE = 0x00000004
    RST_CPU1 = 0x00000002
    RST_CPU0 = 0x00000001

    PM_CORE_PWRSTST = 0x4AE06704
    PM_CORE_PWRSTCTRL = 0x4AE06700

    CM_IPU_CLKSTCTRL = 0x4A008900
    SW_WKUP = 0x00000002
    CLKTRCTRL = 0x00000003

    CM_IPU_IPU_CLKCTRL = 0x4A008920
    MODULEMODE_AUTO = 0x00000001
    MEMMODE_MASK = 0x00000003


    cortexResetRegister = readMem(dev, PM_IPU_RSTCTRL)
    cortexResetStatus = cortexResetRegister & CORTEXM4_RESET_MASK;

    # both devices in reset
    if cortexResetStatus == (CORTEXM4_RTOS_IN_RESET | CORTEXM4_SIMCOP_IN_RESET):
        # Configure Ipu mode into Auto mode
        # CORE_CM2:CM_DUCATI_DUCATI_CLKCTRL
        value = readMem(dev, CM_IPU_IPU_CLKCTRL)
        value = value & ~MEMMODE_MASK
        value = value | MODULEMODE_AUTO
        writeMem(dev, CM_IPU_IPU_CLKCTRL, value)

        # Set force-wakeup domain transition
        # CORE_CM2:CM_DUCATI_CLKSTCTRL = SW_WKUP
        value = readMem(dev, CM_IPU_CLKSTCTRL)
        value = value & ~CLKTRCTRL
        value = value | SW_WKUP
        writeMem(dev, CM_IPU_CLKSTCTRL, value)

        # Reading 1 : clock is running ir gating/ungating transition is on-going.
        value = readMem(dev, CM_IPU_CLKSTCTRL)


    # CORTEXM4_0 in reset
    if (cortexResetStatus & CORTEXM4_RTOS_IN_RESET):

        # Release Ipu MMU and Cache interface reset
        value = readMem(dev, PM_IPU_RSTCTRL)
        value = value & ~RESET_MASK
        value = value | (CORTEXM4_RTOS_IN_RESET | CORTEXM4_SIMCOP_IN_RESET)
        writeMem(dev, PM_IPU_RSTCTRL, value)

        # read 4 Ipu MMU and Cache interface reset applied
        state = 0
        while not state & RST_IPU_MMU_CACHE:
            state = readMem(dev, PM_IPU_RSTST)

        # Reset status cleared
        writeMem(dev, PM_IPU_RSTST, RST_IPU_MMU_CACHE)

        # Release Ipu CortexM4 RTOS (CortexM4 SIMCOP must be released by CortexM4 RTOS)
        value = value & ~CORTEXM4_RTOS_IN_RESET
        writeMem(dev, PM_IPU_RSTCTRL, value)

        # wait ipu CortexM4 RTOS reset applied
        state = 0
        while not state & RST_CPU0:
            state = readMem(dev, PM_IPU_RSTST)

        # Clear reset status
        writeMem(dev, PM_IPU_RSTST, RST_CPU0)

    # CORTEXM4_1 in reset
    if (cortexResetStatus & CORTEXM4_SIMCOP_IN_RESET):

        # Release Ipu CortexM4 SIMCOP
        value = readMem(dev, PM_IPU_RSTCTRL)
        value = value & ~RESET_MASK
        writeMem(dev, PM_IPU_RSTCTRL, value)

        # wait ipu CortexM4 RTOS reset applied
        while not state & RST_CPU1:
            state = readMem(dev, PM_IPU_RSTST)

        # Clear reset status
        writeMem(dev, PM_IPU_RSTST, RST_CPU1)


class WakingSyncSMPDevice(CTISyncSMPDevice):
    def __init__(self, configuration, name, id, devs, startChannel, stopChannel):
        self.parent = configuration
        CTISyncSMPDevice.__init__(self, configuration, name, id, devs, startChannel, stopChannel)

    def systemReset(self, flags):
        CTISyncSMPDevice.systemReset(self, flags)
        self.parent.releaseResets()


class WakingA15(Device):
    def __init__(self, config, id, name):
        self.parent = config
        Device.__init__(self, config, id, name)

    def systemReset(self, flags):
        Device.systemReset(self, flags)
        self.parent.releaseResets()

class WakingM4(Device):
    def __init__(self, config, id, name, memap):
        self.parent = config
        self.dev = memap
        self.wake = False
        Device.__init__(self, config, id, name)
        self.connected = False

    def isConnected(self):
        return self.connected

    def setWake(self, enabled):
        self.wake = enabled

    def releaseReset(self):
        if self.wake:
            devOpen = False
            try:
                self.dev.openConn(zeros(1, 'i'), zeros(1, 'i'), StringBuilder(1024))
                devOpen = True
            except:
                pass

            try:
               doM4Writes(self.dev)
            finally:
                if devOpen:
                    self.dev.closeConn()

    def openConn(self, id, version, name):
        self.releaseReset()

        Device.openConn(self, id, version, name)
        self.connected = True

    def closeConn(self):
        self.connected = False
        Device.closeConn(self)

    def systemReset(self, flags):
        Device.systemReset(self, flags)
        self.parent.releaseResets()


RSZ = 0x001
STS = 0x003
RAMRDAT = 0x004
RAMRPTR = 0x005
RAMWPTR = 0x006
CTL = 0x008
MODE = 0x00A
AXICTL = 0x044
FFSR = 0xC0
FFCR = 0xC1
DEVID = 0x3F2

class CT_TBR(CSTMC):
    def postConnect(self):
        CSTMC.postConnect(self)

        self.writeRegister(0x42, 0x0000000F)
        self.writeRegister(0x43, 0x006F00FF)

    def memRead(self, page, address, size, rule, count, data):
        CSTMC.memRead(self, page, address / 4, size, rule, count, data)

    def decodeRAMSize(self, value):
        result = 0
        if value == 1:
            result = 0x400
        if value == 2:
            result = 0x800
        if value == 3:
            result = 0x1000
        if value == 4:
            result = 0x2000
        if value == 5:
            result = 0x4000
        if value == 6:
            result = 0x8000

        return result

    def regWriteBlock(self, start, count, data):
        for i in range(count):
            self.writeRegister(start + i, data[i])

    def regReadBlock(self, start, count, data):
        for i in range(count):
            data[i] = self.readRegister(start + i)

    def regWriteList(self, regList, data):
        for i in range(len(regList)):
            self.writeRegister(regList[i], data[i])

    def regReadList(self, regList, data):
        for i in range(len(regList)):
            data[i] = self.readRegister(regList[i])

    def readRegister(self, reg):
        data = zeros(1, 'i')
        CSTMC.regReadBlock(self, reg, 1, data)
        value = data[0]

        orig = value
        if reg == RSZ:
            value = self.decodeRAMSize(value & 0x00000007)
        if reg == FFCR:
            value &= 0xFFFFFFBF
        if reg == DEVID:
            value = 0x300

        if reg == RAMRPTR or reg == RAMWPTR:
            value = value * 4


        return value

    def writeRegister(self, reg, value):
        orig_value = value
        if reg != MODE and reg != AXICTL:
            if reg == RAMRPTR or reg == RAMWPTR:
                value = value / 4
            if reg == CTL:
                orig = self.readRegister(CTL)
                value = (orig & 0xFFFFFFFE) | (value & 0x00000001)

            value = Long(value & 0xFFFFFFFFl).intValue()
            CSTMC.regWriteBlock(self, reg, 1, [ value ])


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
    def getOptionCortexM4TabPage():
        return DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
            DTSLv1.booleanOption('wakeM4', 'Bring Cortex-M4 cores out of reset', defaultValue=False),
        ])

    @staticmethod
    def getOptionCortexA15TabPage():
        return DTSLv1.tabPage("cortexA15", "Cortex-A15", childOptions=[
            DTSLv1.booleanOption('cortexA15coreTrace', 'Enable Cortex-A15 core trace', defaultValue=False, childOptions =
                # Allow each source to be enabled/disabled individually
                [ DTSLv1.booleanOption('Cortex_A15_%d' % c, "Enable Cortex-A15 %d trace" % c, defaultValue=True)
                for c in range(0, NUM_CORES_CORTEX_A15) ] +
                [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", defaultValue=False) ] +
                [ DTSLv1.booleanOption('timestamp', "Enable PTM Timestamps", description="Controls the output of timestamps into the PTM output streams", defaultValue=True) ] +
                [ DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the output of context ID values into the PTM output streams", defaultValue=True,
                    childOptions = [
                        DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                            values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                        ])
                ] +
                # Pull in common options for PTMs
                PTMTraceSource.defaultOptions(DtslScript.getPTMs) +
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
        )
    ])

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("traceBuffer", "Trace Buffer", childOptions=[
            # If you change the position or name of the traceCapture device option you MUST
            # modify the project_types.xml to tell the debugger about the new location/name
            DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                values = [("none", "None"), ("ETF", "System Memory Trace Buffer (CT_TBR)")],
                setter=DtslScript.setTraceCaptureMethod)
        ])



    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA15TabPage(),
                DtslScript.getOptionCortexM4TabPage()
            ])
        ]

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

        self.setupCTISyncSMP()

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-A15 trace options
            TraceRangeOptions(), # Cortex-A7 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    # Something has caused a system reset
    # If either of the M4s are connected and we want to bring them out of reset,
    # do this now
    def releaseResets(self):
        released = False
        for core in self.cortexM4cores:
            if not released:
                if core.isConnected():
                    core.releaseReset()
                    released = True

    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        cortexA15coreDev = 0
        self.cortexA15cores = []

        cortexM4coreDev = 0
        self.cortexM4cores = []

        ptmDev = 1
        self.PTMs  = []

        streamID = ATB_ID_BASE

        # Trace start/stop CTI
        coreCTIDev = 1
        self.CTIs  = []
        self.cortexA15ctiMap = {} # map cores to associated CTIs

        for i in range(0, NUM_CORES_CORTEX_A15):
            # create core
            cortexA15coreDev = self.findDevice("Cortex-A15", cortexA15coreDev+1)
            dev = WakingA15(self, cortexA15coreDev, "Cortex-A15_%d" % i)
            self.cortexA15cores.append(dev)

            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)
            self.cortexA15ctiMap[dev] = coreCTI

            # create the PTM for this core
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            ptm = PTMTraceSource(self, ptmDev, streamID, "PTM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            ptm.setEnabled(False)
            self.PTMs.append(ptm)

        for i in range(0, NUM_CORES_CORTEX_M4):
            # create core
            cortexM4coreDev = self.findDevice("Cortex-M4", cortexM4coreDev+1)
            dev = WakingM4(self, cortexM4coreDev, "Cortex-M4_%d" % i, self.AHB)
            self.cortexM4cores.append(dev)

        # output CTI
        outCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")

        # CT_TBR
        tmcDev = self.findDevice("CSTMC")
        self.ETF = CT_TBR(self, tmcDev, "ETF")
        self.etfTrace = TMCETBTraceCapture(self, self.ETF, "ETF")

        # Funnel
        funnelDev = self.findDevice("CSTFunnel")
        self.TF_A15 = self.createFunnel(funnelDev, "CSTF_A15")
        funnelDev = self.findDevice("CSTFunnel", funnelDev + 1)
        self.TF_SYS = self.createFunnel(funnelDev, "CSTF_SYS")
        self.TF_SYS.setPortEnabled(0)

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

    def exposeCores(self):
        for core in self.cortexA15cores + self.cortexM4cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def setupETFTrace(self):
        '''Setup ETF trace capture'''

        # use continuous mode
        self.etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)
        # self.etfTrace.setFormatterMode(FormatterMode.BYPASS)

        # register other trace components with ETF and register ETF with configuration
        self.etfTrace.setTraceComponentOrder([ self.TF_A15, self.TF_SYS ])
        self.addTraceCaptureInterface(self.etfTrace)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETF", [self.TF_A15, self.TF_SYS, self.outCTI, self.tpiu, self.etfTrace])

        # register trace sources
        self.registerTraceSources(self.etfTrace)

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for synch start/stop
        # Cortex-A15 CTI SMP setup
        ctiInfo = {}
        for c in self.cortexA15cores:
            # use standard Cortex event mapping : in/out on trigger 0 for stop, out on trigger 7 for start
            ctiInfo[c] = CTISyncSMPDevice.DeviceCTIInfo(self.cortexA15ctiMap[c], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        smp = WakingSyncSMPDevice(self, "Cortex-A15 SMP", self.cortexA15cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp)
        self.addDeviceInterface(smp)

        # automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CTIs)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A15):
            self.registerCoreTraceSource(traceCapture, self.cortexA15cores[c], self.PTMs[c])

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

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == self.ETF:
            # ETB trigger input is CTI out 1
            return (self.outCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)
        # no associated CTI
        return (None, None, None)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a source
        return (None, None, None) if no associated CTI
        '''
        if source in self.PTMs:
            coreNum = self.PTMs.index(source)
            # PTM trigger is on input 6
            if coreNum < len(self.CTIs):
                return (self.CTIs[coreNum], 6, CTM_CHANNEL_TRACE_TRIGGER)

        # no associated CTI
        return (None, None, None)

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
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()
        traceMode = optionValues.get("options.traceBuffer.traceCapture")
        self.setManagedDevices(self.getManagedDevices(traceMode))

        coreTraceEnabled = self.getOptionValue("options.cortexA15.cortexA15coreTrace")
        for i in range(0, NUM_CORES_CORTEX_A15):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA15.cortexA15coreTrace.Cortex_A15_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            self.setTraceSourceEnabled(self.PTMs[i], enableSource)
            self.setTriggerGeneratesDBGRQ(self.PTMs[i], self.getOptionValue("options.cortexA15.cortexA15coreTrace.triggerhalt"))
            self.setTimestampingEnabled(self.PTMs[i], self.getOptionValue("options.cortexA15.cortexA15coreTrace.timestamp"))
            self.setContextIDEnabled(self.PTMs[i],
                                     self.getOptionValue("options.cortexA15.cortexA15coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexA15.cortexA15coreTrace.contextIDs.contextIDsSize"))

        wake = self.getOptionValue("options.cortexM4.wakeM4")
        for i in range(0, NUM_CORES_CORTEX_M4):
            self.cortexM4cores[i].setWake(wake)

        ptmStartIndex = 0
        ptmEndIndex = 0

        ptmEndIndex += NUM_CORES_CORTEX_A15
        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A15_TRACE_OPTIONS], TraceRangeOptions("options.cortexA15.cortexA15coreTrace", self), self.PTMs[ptmStartIndex:ptmEndIndex])
        ptmStartIndex += NUM_CORES_CORTEX_A15


    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def setETFTraceEnabled(self, enabled):
        '''Enable/disable ETF trace capture'''
        if enabled:
            # ensure TPIU is disabled
            self.tpiu.setEnabled(False)
        self.enableCTIsForSink(self.etfTrace, enabled)

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setETFTraceEnabled(False)
        elif method == "ETF":
            self.ETF.setMode(CSTMC.Mode.ETB)
            self.setETFTraceEnabled(True)

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the set of devices managed by the configuration'''
        for d in devs:
            self.mgdPlatformDevs.add(d)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP_1")])

    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, funnelDev, name)
        funnel.setAllPortsDisabled()
        return funnel

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # disable the TPIU by default to allow ETB to work at full rate
        tpiu.setEnabled(False)
        return tpiu

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnel ports
        # Assume a linear mapping for all clusters (port - core index in the cluster)
        portMap = { }
        for i in range(0, NUM_CORES_CORTEX_A15):
            portMap[self.PTMs[i]] = i

        return portMap.get(source, None)

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        port = self.getFunnelPortForSource(source)
        if enabled:
            self.TF_A15.setPortEnabled(port)
        else:
            self.TF_A15.setPortDisabled(port)

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


    def addManagedTraceDevices(self, traceKey, devs):
        '''Add devices to the set of devices managed by the configuration for this trace mode'''
        traceDevs = self.mgdTraceDevs.get(traceKey)
        if not traceDevs:
            traceDevs = set()
            self.mgdTraceDevs[traceKey] = traceDevs
        for d in devs:
            traceDevs.add(d)

    def getPTMs(self):
        '''Get the PTMs'''
        return self.PTMs

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
