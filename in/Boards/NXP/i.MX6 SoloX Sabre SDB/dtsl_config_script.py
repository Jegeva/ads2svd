from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETMv3_4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource

from struct import pack, unpack
from jarray import array, zeros
from java.lang import Byte
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE

NUM_CORES_CORTEX_A9 = 1
NUM_CORES_CORTEX_M4 = 1
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers
# Set to True if access required to M4 bus
# This can cause connection failures for A9 if Linux running
ADD_M4_BUS_ACCESSOR = False

class M_Class_ETMv3_4(ETMv3_4TraceSource):
    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False


class CacheMaintCore(Device):
    def __init__(self, config, id, name):
        Device.__init__(self, config, id, name)

    def to_s8(self, val):
        return val > 127 and val - 256 or val

    def memRead(self, page, address, size, rule, count, pDataOut):
        Device.memRead(self, page, address, size, rule, count, pDataOut)

    def __clean_invalidate_caches(self, page):
        buf = zeros(4,'b')
        # Clean/Inv for I cache
        Device.memRead(self, page, 0xE0082800, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)
        if buf[0] & 0x1:
            buf = array(map(self.to_s8, [buf[0] & 0xFF, 0x0, 0x0, 0x8F]), 'b')
            Device.memWrite(self, page,  0xE0082800, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)
        # Clean/Inv for D cache
        Device.memRead(self, page, 0xE0082000, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)
        if buf[0] & 0x1:
            buf = array(map(self.to_s8, [buf[0] & 0xFF, 0x0, 0x0, 0x8F]), 'b')
            Device.memWrite(self, page,  0xE0082000, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)

    def setSWBreak(self, page, addr, flags):
        brkID = Device.setSWBreak(self, page, addr, flags)
        self.__clean_invalidate_caches(page)
        return brkID

    def memWrite(self, page, addr, size, rule, check, count, data):
        Device.memWrite(self, page, addr, size, rule, check, count, data)
        self.__clean_invalidate_caches(page)

class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("cortexA9", "Cortex-A9", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB0", "On Chip Trace Buffer (ETB0)")],
                        setter=DtslScript.setTraceCaptureMethodA9),
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A9_%d' % core, "Enable Cortex-A9 %d trace" % core, defaultValue=True)
                            for core in range(0, NUM_CORES_CORTEX_A9) ] +
                            [ PTMTraceSource.cycleAccurateOption(DtslScript.getPTMs) ] +
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
                +[DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB1", "On Chip Trace Buffer (ETB1)")],
                        setter=DtslScript.setTraceCaptureMethodM4),
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-M4 core trace', defaultValue=False),
                    DTSLv1.booleanOption('itm', 'Enable CSITM trace', defaultValue=False),
                    DTSLv1.booleanOption('cortexM4WakeUp', 'Release Cortex-M4 from reset', defaultValue=True,
                        description="Brings the Cortex-M4 core out of reset. Note this should be set when connecting to the Cortex-M4 for the first time after the board has been powered up."),
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

        # Only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
        if self.AHB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.AHB)
        if self.APB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.APB)

        if ADD_M4_BUS_ACCESSOR != False:
            if self.AHB_M not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.AHB_M)

        self.exposeCores()

        self.traceRangeIDs = {}

        traceComponentOrder = [ self.Funnel0 ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.ETB0 ]
        self.setupETBTrace(self.ETB0, "ETB0", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH, traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel1 ]
        managedDevices = [ self.Funnel1, self.ETB1 ]
        self.setupETBTrace(self.ETB1, "ETB1", traceComponentOrder, managedDevices)

        self.setManagedDeviceList(self.mgdPlatformDevs)

        self.setETBTraceEnabled(self.ETB0, False)
        self.setETBTraceEnabled(self.ETB1, False)
        self.setDSTREAMTraceEnabled(False)

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

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.AHB_M = CortexM_AHBAP(self, memApDev, "AHB_M")

        cortexA9coreDevs = [11]
        self.cortexA9cores = []

        cortexM4coreDevs = [15]
        self.cortexM4cores = []

        streamID = 1

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, 8, "OutCTI0")

        coreCTIDevs = []
        self.CoreCTIs = []

        ptmDevs = [6]
        self.PTMs = []

        etmDevs = [18]
        self.ETMs = []

        # ITM 0
        self.ITM0 = self.createITM(16, streamID, "ITM0")
        streamID += 1

        for i in range(0, NUM_CORES_CORTEX_A9):
            # Create core
            core = Device(self, cortexA9coreDevs[i], "Cortex-A9")
            self.cortexA9cores.append(core)

        for i in range(0, NUM_CORES_CORTEX_M4):
            # Create core
            core = CacheMaintCore(self, cortexM4coreDevs[i], "Cortex-M4")
            self.cortexM4cores.append(core)

        for i in range(0, len(coreCTIDevs)):
            # Create CTI
            coreCTI = CSCTI(self, coreCTIDevs[i], "CoreCTIs[%d]" % i)
            self.CoreCTIs.append(coreCTI)

        for i in range(0, len(ptmDevs)):
            # Create PTM
            ptm = PTMTraceSource(self, ptmDevs[i], streamID, "PTMs[%d]" % i)
            streamID += 1
            # Disabled by default - will enable with option
            ptm.setEnabled(False)
            self.PTMs.append(ptm)

        for i in range(0, len(etmDevs)):
            # Create ETM
            etm = self.createETM(etmDevs[i], streamID, "ETMs[%d]" % i)
            streamID += 1

        # A9 ETB 0
        self.ETB0 = ETBTraceCapture(self, 7, "ETB0")

        # DSTREAM
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

        # TPIU
        self.TPIU = self.createTPIU(9, "TPIU")

        # A9 Funnel 0
        self.Funnel0 = self.createFunnel(10, "Funnel0")

        # M4 ETB 1
        self.ETB1 = ETBTraceCapture(self, 19, "ETB1")

        # M4 funnel 1
        self.Funnel1 = self.createFunnel(20, "Funnel1")

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP"),
            AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP"),
        ])

    def exposeCores(self):
        for core in self.cortexA9cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)
        for core in self.cortexM4cores:
            self.registerMClassFilters(core)
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

    def setupDSTREAMTrace(self, portwidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        self.TPIU.setPortSize(portwidth)

        # Configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.DSTREAM.setPortWidth(portwidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sources to CTIs
        sourceCTIMap = {}

        return sourceCTIMap.get(source, (None, None, None))

    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sinks to CTIs
        sinkCTIMap = {}
        sinkCTIMap[self.ETB0] = (self.OutCTI0, 1, CTM_CHANNEL_TRACE_TRIGGER)
        sinkCTIMap[self.DSTREAM] = (self.OutCTI0, 3, CTM_CHANNEL_TRACE_TRIGGER)

        return sinkCTIMap.get(sink, (None, None, None))

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''

        # Build map of cores to trace macrocells
        coreTMMap = {}
        coreTMMap[self.cortexA9cores[0]] = self.PTMs[0]
        coreTMMap[self.cortexM4cores[0]] = self.ETMs[0]

        return coreTMMap.get(core, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createETM(self, etmDev, streamID, name):
        '''Create ETM of correct version'''
        if etmDev == 18:
            etm = M_Class_ETMv3_4(self, etmDev, streamID, name)
            # Disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            return etm

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setETBTraceEnabled(self, etb, enabled):
        '''Enable/disable ETB trace capture'''
        self.enableCTIsForSink(etb, enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def registerETB0TraceSources(self):
        coreTM = self.getTMForCore(self.cortexA9cores[0])
        if coreTM.isEnabled():
            self.registerCoreTraceSource(self.ETB0, self.cortexA9cores[0], coreTM)

    def registerETB1TraceSources(self):
        coreTM = self.getTMForCore(self.cortexM4cores[0])
        if coreTM.isEnabled():
            self.registerCoreTraceSource(self.ETB1, self.cortexM4cores[0], coreTM)
        self.registerTraceSource(self.ETB1, self.ITM0)

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
        funnelMap[self.PTMs[0]] = (self.Funnel0, 0)
        funnelMap[self.ETMs[0]] = (self.Funnel1, 0)
        funnelMap[self.ITM0] = (self.Funnel1, 1)

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

        A9traceMode = self.getOptionValue("options.cortexA9.traceCapture")
        A9coreTraceEnabled = self.getOptionValue("options.cortexA9.coreTrace") and self.getOptionValue("options.cortexA9.coreTrace.Cortex_A9_0")
        coreTM = self.getTMForCore(self.cortexA9cores[0])
        self.setTraceSourceEnabled(coreTM, A9coreTraceEnabled)
        self.setInternalTraceRange(coreTM, "cortexA9")

        M4traceMode = self.getOptionValue("options.cortexM4.traceCapture")
        M4coretraceEnabled = self.getOptionValue("options.cortexM4.coreTrace")
        coreTM = self.getTMForCore(self.cortexM4cores[0])
        self.setTraceSourceEnabled(coreTM, M4coretraceEnabled)

        itmEnabled = self.getOptionValue("options.cortexM4.itm")
        self.setTraceSourceEnabled(self.ITM0, itmEnabled)

        # Register trace sources for each trace sink
        self.registerETB0TraceSources()
        self.registerETB1TraceSources()

        devList = []
        devList += self.getManagedDevices(A9traceMode)
        devList += self.getManagedDevices(M4traceMode)
        self.setManagedDeviceList(list(set(devList)))

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def setTraceCaptureMethodA9(self, method):
        if method == "ETB0":
            self.setETBTraceEnabled(self.ETB0, True)

    def setTraceCaptureMethodM4(self, method):
        if method == "ETB1":
            self.setETBTraceEnabled(self.ETB1, True)

    def getPTMs(self):
        '''Get the PTMs'''
        return self.PTMs

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

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
        if ADD_M4_BUS_ACCESSOR != False:
            core.registerAddressFilters([AHBCortexMMemAPAccessor("AHB", self.AHB_M, "M Class AHB bus accessed via AP")])
        pass

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

    def enableClocks(self):
        script = """from LDDI import *
import sys

DAP_DevID = 3
M4_DAP_DevID = 13

targetConfigured = False

def HandleOpenConn(DevID,type,state):
    if type==1:
        configureTarget()
    return handleOpenConn(DevID,type,state)

def isCoreConnected(id):
    err, configTest = getConfig(id,'CONFIG_ITEMS')
    return err == 0


def configureTarget(force=False):
    global targetConfigured
    if targetConfigured and not force:
        # already setup
        return 0
"""
        if self.getOptionValue("options.cortexM4.cortexM4WakeUp"):
            script += """
    print "Opening connection to the DAP"
    err, id, version, message = Debug_OpenConn(DAP_DevID)
    if err == 0x101: # already open
        dapOpened = False
    elif err != 0:
        print >> sys.stderr, "Failed to open DAP: %04x" % err
        return err
    else:
        dapOpened = True

    print "Powering up the DAP"
    # Assume either that the DAP is powered down and we know about it in which case
    # powering down again won't do anything, or DAP is thought to be powered but
    # a reset has powered it down, in which case powering down will sync the reference count with reality
    err = setConfig(DAP_DevID, 'DAP_POWER_UP', 0)
    err = setConfig(DAP_DevID, 'DAP_POWER_UP', 1)

    Debug_MemWrite(DAP_DevID,0x4300,0x0207c000,4,0x0320,0,[0x77, 0x77, 0x77, 0x77])
    Debug_MemWrite(DAP_DevID,0x4300,0x0217c000,4,0x0320,0,[0x77, 0x77, 0x77, 0x77])
    Debug_MemWrite(DAP_DevID,0x4300,0x0227c000,4,0x0320,0,[0x77, 0x77, 0x77, 0x77])

    #open all clocks
    Debug_MemWrite(DAP_DevID,0x4300,0x020c4068,4,0x0320,0,[0xFF, 0xFF, 0xFF, 0xFF])
    Debug_MemWrite(DAP_DevID,0x4300,0x020c406c,4,0x0320,0,[0xFF, 0xFF, 0xFF, 0xFF])
    Debug_MemWrite(DAP_DevID,0x4300,0x020c4070,4,0x0320,0,[0xFF, 0xFF, 0xFF, 0xFF])
    Debug_MemWrite(DAP_DevID,0x4300,0x020c4074,4,0x0320,0,[0xFF, 0xFF, 0xFF, 0xFF])
    Debug_MemWrite(DAP_DevID,0x4300,0x020c4078,4,0x0320,0,[0xFF, 0xFF, 0xFF, 0xFF])
    Debug_MemWrite(DAP_DevID,0x4300,0x020c407c,4,0x0320,0,[0xFF, 0xFF, 0xFF, 0xFF])
    Debug_MemWrite(DAP_DevID,0x4300,0x020c4080,4,0x0320,0,[0xFF, 0xFF, 0xFF, 0xFF])
    Debug_MemWrite(DAP_DevID,0x4300,0x020c4084,4,0x0320,0,[0xFF, 0xFF, 0xFF, 0xFF])
    #setup CM4 code
    Debug_MemWrite(DAP_DevID,0x4300,0x007f8000,4,0x0320,0,[0x00, 0x00, 0x00, 0x20])
    Debug_MemWrite(DAP_DevID,0x4300,0x007f8004,4,0x0320,0,[0x09, 0x00, 0x00, 0x00])
    Debug_MemWrite(DAP_DevID,0x4300,0x007f8008,4,0x0320,0,[0xFE, 0xE7, 0xFE, 0xE7])

    # Release the M4
    print "Releasing the M4"
    value = [ 0, 0, 0, 0 ]
    err = Debug_MemRead(DAP_DevID, 0x4300, 0x020d8000, 4, 0x320, 4, value)
    if err == 0:
        value[2] |= 0x40
        Debug_MemWrite(DAP_DevID,0x4300,0x020d8000,4,0x0320,0,value)
    value = [ 0, 0, 0, 0 ]
    err = Debug_MemRead(DAP_DevID, 0x4300, 0x020d8000, 4, 0x320, 4, value)
    if err == 0:
        value[0] &= ~0x10
        Debug_MemWrite(DAP_DevID,0x4300,0x020d8000,4,0x0320,0,value)

    print "Opening connection to the M4 DAP"
    err, id, version, message = Debug_OpenConn(M4_DAP_DevID)
    if err == 0x101: # already open
        dapOpened = False
    elif err != 0:
        print >> sys.stderr, "Failed to open M4_DAP: %04x" % err
        return err
    else:
        dapOpened = True

    print "Powering up the M4 DAP"
    # Assume either that the DAP is powered down and we know about it in which case
    # powering down again won't do anything, or DAP is thought to be powered but
    # a reset has powered it down, in which case powering down will sync the reference count with reality
    err = setConfig(M4_DAP_DevID, 'DAP_POWER_UP', 0)
    err = setConfig(M4_DAP_DevID, 'DAP_POWER_UP', 1)
    if err != 0:
        print >> sys.stderr, "Failed to powerup M4 DAP: %04x" % err

    if dapOpened:
        print "Closing DAP using Debug_CloseConn(DAP_DevID)"
        Debug_CloseConn(DAP_DevID)

    if dapOpened:
        Debug_CloseConn(M4_DAP_DevID)
"""
            script += """
    targetConfigured = True
    return 0

def UnknownStateRecovery():
    configureTarget(force=True)

def HandleExeReset(flags):
    JTAG_Connect()
    JTAG_nSRST(True)
    sleep(500)
    JTAG_nSRST(False)
    sleep(100)
    JTAG_Disconnect()
    configureTarget(force=True)
    return False
"""
        self.getDebug().setConfig(0, "PythonScript", script)

    def connectManagedDevices(self):
        self.enableClocks()
        DTSLv1.connectManagedDevices(self)

class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return DtslScript.getOptionList() # RVI is the same as DSTREAM as no TPIU trace port on SABRE board


