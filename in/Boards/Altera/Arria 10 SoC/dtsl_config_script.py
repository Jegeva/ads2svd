# Copyright (C) 2015-2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTLiveStoredStreamingTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
from com.arm.debug.dtsl.nativelayer import NativeException
from com.arm.debug.dtsl import DTSLException
from com.arm.rddi import RDDI_ACC_SIZE

from struct import pack, unpack
from jarray import array, zeros

NUM_CORES_CORTEX_A9 = 2
ATB_ID_BASE = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
# The DSTREAM port width may vary with customer board configuration
DSTREAM_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
STM_FUNNEL_PORT = 3
CORTEX_A9_TRACE_OPTIONS = 0
TRIG_STOP = 0
TRIG_ACK = 0
FPGA_CTI_ADDR = 0x80007000
SMP_DEVICE_NAME = "Cortex-A9 SMP"

CTICTRL   = 0x00
CTIINTACK = 0x04
CTIINEN   = 0x08
CTIOUTEN  = 0x28


# Cross-triggering with a CTI in the FPGA
# Override of the Device class for Cortex-A9 that also knows how to configure CTIs for sync start and stop
# Controls two CTIs - the one bound to the core and the one in the FPGA
# Only touches the CTI if cross-triggering has been enabled
# De-configures CTI on disconnect

class CTICore(Device):
    def __init__(self, config, id, name, cti1, cti2):
        Device.__init__(self, config, id, name)
        self.myCTI = cti1
        self.fpgaCTI = cti2
        self.xTrigFPGA = False
        self.xTrigHPS = False
        self.connected = False

    def setCrossTrigFPGA(self, enabled):
        self.enableTrigFPGA(enabled)

    def setCrossTrigHPS(self, enabled):
        self.enableTrigHPS(enabled)

    def openConn(self, id, version, name):
        Device.openConn(self, id, version, name)
        self.connected = True
        self.configureCTIs()

    def closeConn(self):
        self.unconfigureCTIs()
        self.connected = False
        Device.closeConn(self)

    def configureCTIs(self):
        if self.xTrigFPGA or self.xTrigHPS:
            self.ensureCTIsConnected()
            self.enableCTIs()

        self.enableTrigFPGA(self.xTrigFPGA)
        self.enableTrigHPS(self.xTrigHPS)

    def unconfigureCTIs(self):
        self.enableTrigFPGA(False)
        self.enableTrigHPS(False)

    def enableTrigFPGA(self, enabled):
        if self.connected:
            if enabled:
                self.ensureCTIsConnected()
                self.enableCTIs()
                self.enableCTIStopChannel(self.myCTI, self.fpgaCTI, True)
            else:
                if self.xTrigFPGA:
                    self.clearTriggers()
                    self.enableCTIStopChannel(self.myCTI, self.fpgaCTI, False)

        self.xTrigFPGA = enabled

    def enableTrigHPS(self, enabled):
        if self.connected:
            if enabled:
                self.ensureCTIsConnected()
                self.enableCTIs()
                self.enableCTIStopChannel(self.fpgaCTI, self.myCTI, True)
            else:
                if self.xTrigHPS:
                    self.enableCTIStopChannel(self.fpgaCTI, self.myCTI, False)

        self.xTrigHPS = enabled


    def ensureCTIsConnected(self):
        # if enable the trigger sometime after connection then need to connect to CTI
        if not self.myCTI.isConnected():
            self.myCTI.connect()
        if not self.fpgaCTI.isConnected():
            self.fpgaCTI.connect()

    def enableCTIs(self):
        self.myCTI.writeRegister(CTICTRL, 0x00000001)
        self.fpgaCTI.writeRegister(CTICTRL, 0x00000001)

    def enableCTIStopChannel(self, outCTI, inCTI, enable):
        if enable:
            val = (0x01 << CTM_CHANNEL_SYNC_STOP)
        else:
            val = 0
        inCTI.writeRegister(CTIINEN + TRIG_STOP, val)
        outCTI.writeRegister(CTIOUTEN + TRIG_STOP, val)

    def clearTriggers(self):
        if self.xTrigFPGA and self.myCTI.isConnected():
            self.myCTI.writeRegister(CTIINTACK, 0x01 << TRIG_STOP)
            self.myCTI.writeRegister(CTIINTACK, 0x00)

    def go(self):
        self.clearTriggers()
        Device.go(self)

    def step(self, count, flags):
        self.clearTriggers()
        return Device.step(self, count, flags)


''' Because of slow connection with USB-Blaster, replace download with simple memWrites '''
class CTICoreNoDownload(CTICore):
    def __init__(self, config, id, name, cti1, cti2):
        CTICore.__init__(self, config, id, name, cti1, cti2)
        self.downloading = False
        self.dlStart = 0
        #self.dlError = null
        self.dlErrorEncountered = False

    def memDownload(self, page, address, size, rule, check, count, data):
        try:
            if (self.downloading == False):
                self.dlStart = address
                self.downloading = True
            self.memWrite( page, address, size, rule, check, count, data)
        except NativeException, e:
            if (self.dlErrorEncountered == False):
                self.dlError = e
                self.dlErrorEncountered = True



    def memDownloadEnd(self, values, pages, addresses, offsets):
        self.downloading = False
        if (self.dlErrorEncountered == True):
            self.dlErrorEncountered = False
            values[0] = self.dlError.getRDDIErrorCode()
            #pages[0] = self.dlPage
            #addresses[0] = self.dlAddress
            #offsets[0] = self.dlOffset
            raise self.dlError
        else:
            values[0] = 0


class AlteraAHB(AHBAP):
    def __init__(self, config, devno, name):
        AHBAP.__init__(self, config, devno, name)

    def makeRule(self):
        return AHBAP.makeRule(self) | 0x8000


# A very simple implementation of a CTI
# This knows about just one input and one output trigger
# It makes no access to the CTI device outside of the flushConfig() method
# To ensure this, access to the CTI registers is via MemAP memory writes - we don't use the CTI template

class RegisterDevice:
    def __init__(self, dev, address):
        self.inputEnabled = False
        self.device = dev
        self.baseAddr = address

    def flushConfig(self):
        if self.inputEnabled:
            self.writeRegister(CTICTRL, 1)

            register = CTIINEN + FPGA_TRIG_STOP
            value = 1 << CTM_CHANNEL_SYNC_STOP
            self.writeRegister(register, value)

            register = CTIOUTEN + FPGA_TRIG_ACK
            value = 1 << CTM_CHANNEL_SYNC_STOP
            self.writeRegister(register, value)
        else:
            register = CTIINEN + FPGA_TRIG_STOP
            self.writeRegister(register, 0)
            register = CTIOUTEN + FPGA_TRIG_STOP
            self.writeRegister(register, 0)

    def enableInputTrigger(self):
        self.inputEnabled = True

    def disableAllInputs(self):
        self.inputEnabled = False

    def disableAllOutputs(self):
        pass

    def writeRegister(self, register, value):
        # Access via AP 1
        address = self.baseAddr + register * 4
        self.device.memWrite(APB_AP, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, self.apToRule(APB_AP), False, 4, pack('<I', value))


# CTI Sync handler that can optionally deal with an additional CTI
# No access is made to the CTI unless cross-trigger for that CTI has been enabled
# To simplify other scripting and DTSL options dialog, only one method call is needed to enable/disable cross trigger
class AlteraCTISyncSMPDevice(CTISyncSMPDevice):

    def __init__(self, configuration, name, id, devs, startChannel, stopChannel):
        self.cti = RegisterDevice(self, FPGA_CTI_ADDR)
        self.xTrig = False
        CTISyncSMPDevice.__init__(self, configuration, name, id, devs, startChannel, stopChannel)

    def setCrossTrig(self, enabled):
        if enabled:
            # Wire up the STOP triggers on the FPGA
            self.cti.enableInputTrigger()
            # If we are connected, flush the config through to the CTI
            # Otherwise this must be done at connect time
            if self.isConnected():
                self.cti.flushConfig()
        else:
            # Only touch the CTI if we have previously enabled it
            if self.xTrig == True:
                self.cti.disableAllInputs()
                self.cti.disableAllOutputs()
                if self.isConnected():
                    self.cti.flushConfig()

        self.xTrig = enabled

    def startCores(self, stoppedCores):
        if self.xTrig:
            # Clear the trigger acks
            self.cti.writeRegister(CTIINTACK, 0x01 << FPGA_TRIG_STOP)
            self.cti.writeRegister(CTIINTACK, 0x00)
        self.super__startCores(stoppedCores)

    def openConn(self, id, version, message):
        CTISyncSMPDevice.openConn(self, id, version, message)
        if self.xTrig:
            self.cti.flushConfig()


''' Overload CSTPIU with version that confirms setup has been completed before enabling trace
'''
class CheckedTPIU(CSTPIU):
    def __init__(self, config, dev, name):
        CSTPIU.__init__(self, config, dev, name)
        self.ignore = False

    def setMemAccessor(self, memAccessor):
        self.memAccessor = memAccessor

    def enforceCheck(self, e):
        self.ignore = not e

    def traceStart(self, capture):
        if (self.ignore or self.confirmTraceSetupDone()):
            self.super__traceStart(capture)
            self.supported = True
        else:
            self.supported = False

    def traceStop(self, capture):
        if (self.ignore or self.supported):
            self.super__traceStop(capture)

    def confirmTraceSetupDone(self):
        if self.getPortSize() == 4:
            # Using shared I/O directly from HPS, rather than routing through FPGA:
            trace_clk_pinmux = map(lambda addr: self.confirmValue(addr, 0xC),
                                   [0xFFD0709C,  # shared_3v_io_grp.pinmux_shared_io_q4_4
                                    0xFFD070AC]) # shared_3v_io_grp.pinmux_shared_io_q4_8

            trace_data_pinmux = map(lambda addr: self.confirmValue(addr, 0xC),
                                    [0xFFD070B0,  # shared_3v_io_grp.pinmux_shared_io_q4_9
                                     0xFFD070B4,  # shared_3v_io_grp.pinmux_shared_io_q4_10
                                     0xFFD070B8,  # shared_3v_io_grp.pinmux_shared_io_q4_11
                                     0xFFD070BC]) # shared_3v_io_grp.pinmux_shared_io_q4_12

            if any(trace_clk_pinmux) and all(trace_data_pinmux):
                return True
            else:
                return False

        elif self.getPortSize() == 16:
            # TODO: Detect if FPGA image is configured, and that it includes HPS trace component
            return True
        else:
            return False

    def confirmValue(self, addr, expected):
        try:
            actual = self.memAccessor.readMem(addr)
            if expected == actual:
                return True
            else:
                #print "Expected %08x but read %08x" % (expected, actual)
                return False
        except DTSLException:
            return False


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


''' Overload PTM Trace Source with a version that will report the ability to deliver timestamps.
    This version of PTM underreports its capabilities in the ETMCCER register.
'''
class PTMTimestampingTraceSource(PTMTraceSource):
    def hasTimestamping(self):
        return True

    def getTimestampEncoding(self):
        return IARMCoreTraceSource.TimestampEncoding.GRAY


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionCortexA9TabPage():
        return DTSLv1.tabPage("cortexA9", "Cortex-A9", childOptions=[
            DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A9 core trace', defaultValue=False, childOptions =
                # Allow each core to be enabled/disabled individually
                [ DTSLv1.booleanOption('Cortex_A9_%d' % c, "Enable Cortex-A9 %d trace" % c, defaultValue=True)
                for c in range(0, NUM_CORES_CORTEX_A9) ] +
                [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", defaultValue=False) ] +
                [ DTSLv1.booleanOption('timestamp', "Enable PTM Timestamps", description="Controls the ouptut of timestamps into the PTM output streams", defaultValue=True, isDynamic=True, childOptions =
                   [ DTSLv1.integerOption('tsPeriod', 'Timestamp period', defaultValue=4000, isDynamic=False, description="This value will be used to vary the period between timestamps appearing in the trace stream.\nIt represents the number of cycles, so a lower value gives more frequent timestamps."),
                    ])
                ] +
                [ DTSLv1.booleanOption('contextIDs', "Enable PTM Context IDs", description="Controls the ouptut of context ID values into the PTM output streams", defaultValue=True,
                    childOptions = [
                        DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                            values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                        ])
                ] +
                # Pull in common options for PTMs (cycle accurate etc)
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
    def getOptionCrossTriggerTabPage():
        INIT_INFO = '''The Cross Trigger interface can only be accessed if the system clocks
have been initialized.  If the Cross Trigger interface is accessed
prior to the clock initialization, then the target may lock up.
The folllowing option should only be set if you are sure that the system
clocks have been initialized prior to Arm DS connecting to the target system.
The system clocks are typically set up by running the Altera preloader script'''

        return DTSLv1.tabPage('xtrig', 'Cross Trigger', childOptions=[
            DTSLv1.booleanOption('xtrigFPGA', 'Enable FPGA -> HPS Cross Trigger', defaultValue=False, isDynamic=True,
                setter=DtslScript.setXTrigFPGAEnabled, description="Trigger events in the FPGA can halt the Cortex-A9 cores"),
            DTSLv1.booleanOption('xtrigHPS', 'Enable HPS -> FPGA Cross Trigger', defaultValue=False, isDynamic=True,
                setter=DtslScript.setXTrigHPSEnabled, description="Trigger events in the FPGA can be caused when Cortex-A9 cores halt")
        ])

    @staticmethod
    def getOptionSTMTabPage():
        return DTSLv1.tabPage("STM", "STM", childOptions=[
            DTSLv1.booleanOption('stm', 'Enable STM trace', defaultValue=False,
                setter=DtslScript.setSTMEnabled),
        ])

    @staticmethod
    def getOptionETRTabPage():
        return DTSLv1.tabPage("ETR", "ETR", childOptions=[
            DTSLv1.booleanOption('etrBuffer', 'Configure the system memory trace buffer',
                defaultValue = False,
                childOptions = [
                    DTSLv1.integerOption('start', 'Start address',
                        description='Start address of the system memory trace buffer',
                        defaultValue=0x00100000,
                        display=IIntegerOption.DisplayFormat.HEX),
                    DTSLv1.integerOption('size', 'Size in Words',
                        description='Size of the system memory trace buffer in Words',
                        defaultValue=0x8000,
                        display=IIntegerOption.DisplayFormat.HEX),
                    DTSLv1.booleanOption('scatterGather', 'Enable scatter-gather mode', defaultValue=False, description='When enabling scatter-gather mode, the start address of the on-chip trace buffer must point to a configured scatter-gather table')
                ]
            )
        ])

    @staticmethod
    def getOptionETFTabPage():
        return DTSLv1.tabPage("ETF", "ETF", childOptions=[
            DTSLv1.booleanOption('etfBuffer', 'Configure the on-chip trace buffer',
                defaultValue = False,
                childOptions = [
                    DTSLv1.integerOption('size', 'Size',
                        description='Size of the on-chip trace buffer in bytes',
                        isDynamic=True,
                        maximum=0x8000,
                        minimum=0x0,
                        defaultValue=0x8000,
                        display=IIntegerOption.DisplayFormat.HEX)
                    ]
            )
        ])

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # DAP/MEM-AP devices managed by default - others will be added when enabling trace, SMP etc
        self.addManagedPlatformDevices([self.dap, self.AHB, self.APB])

        self.exposeCores()

        self.setupCTISyncSMP()

        # Needs a way of checking if trace has been configured
        self.tpiu.setMemAccessor(self.AHB)

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-A9 trace options
            ]

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''
        dapDev = self.findDevice("ARMCS-DP")
        self.dap = CSDAP(self, dapDev, "DAP")

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AlteraAHB(self, ahbDev, "CSMEMAP")
        self.AHB.setHProt(0x03)

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        cortexA9coreDev = 0
        self.cortexA9cores = []

        streamID = ATB_ID_BASE

        # Trace start/stop CTI
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")

        self.CTIs  = []
        self.cortexA9ctiMap = {} # map cores to associated CTIs

        # FPGA CTI
        fpgaCTIDev = self.findDevice("CSCTI", outCTIDev+1)
        self.fpgaCTI = CSCTI(self, fpgaCTIDev, "CTI_FPGA")

        coreCTIDev = fpgaCTIDev
        ptmDev = 1
        self.PTMs  = []

        for i in range(0, NUM_CORES_CORTEX_A9):
            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)

            # create core
            cortexA9coreDev = self.findDevice("Cortex-A9", cortexA9coreDev+1)
            dev = self.ctiCoreFactory(cortexA9coreDev, "Cortex-A9_%d" % i, coreCTI, self.fpgaCTI)
            self.cortexA9cores.append(dev)
            self.cortexA9ctiMap[dev] = coreCTI

            # create the PTM for this core
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            ptm = PTMTimestampingTraceSource(self, ptmDev, streamID, "PTM_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            ptm.setEnabled(False)
            self.PTMs.append(ptm)

        tmcDev = 1

        # ETF device
        tmcDev = self.findDevice("CSTMC", tmcDev + 1)
        self.ETF = CSTMC(self, tmcDev, "ETF")

        # Reserve this TMC for use as an ETR
        self.etrTmcDev = self.findDevice("CSTMC", tmcDev + 1)

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

        # Funnel 0
        funnelDev0 = self.findDevice("CSTFunnel")
        self.funnel0 = self.createFunnel(funnelDev0, "Funnel_0")

        # STM
        stmDev = self.findDevice("CSSTM")
        self.STM = STMTraceSource(self, stmDev, streamID, "STM", True, True)
        streamID += 1

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def createETR(self):
        self.ETR = ETRTraceCapture(self, self.etrTmcDev, "ETR")

    def createETFTrace(self):
        self.etfTrace = TMCETBTraceCapture(self, self.ETF, "ETF")

    def exposeCores(self):
        for core in self.cortexA9cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def setupETRTrace(self):
        '''Setup ETR trace capture'''
        # use continuous mode
        self.ETR.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETR and register ETR with configuration
        self.ETR.setTraceComponentOrder([ self.ETF, self.funnel0 ])
        self.addTraceCaptureInterface(self.ETR)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETR", [ self.funnel0, self.tpiu, self.outCTI, self.ETF, self.ETR ])

    def setupETFTrace(self):
        '''Setup ETF trace capture'''
        # use continuous mode
        self.etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETF and register ETF with configuration
        self.etfTrace.setTraceComponentOrder([ self.funnel0 ])
        self.addTraceCaptureInterface(self.etfTrace)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETF", [ self.funnel0, self.tpiu, self.outCTI, self.etfTrace ])

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''

        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        self.setPortWidth(portWidth)

        # configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.ETF, self.funnel0, self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.funnel0, self.outCTI, self.tpiu, self.ETF, self.DSTREAM ])

    def setPortWidth(self, portWidth):
        self.tpiu.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for synch start/stop
        # Cortex-A9 CTI SMP setup
        ctiInfo = {}
        for c in self.cortexA9cores:
            # use standard Cortex event mapping : in/out on trigger 0 for stop, out on trigger 7 for start
            ctiInfo[c] = CTISyncSMPDevice.DeviceCTIInfo(self.cortexA9ctiMap[c], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)

        self.smp = AlteraCTISyncSMPDevice(self, SMP_DEVICE_NAME, self.cortexA9cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(self.smp)
        self.addDeviceInterface(self.smp)

        # automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CTIs)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == "TPIU":
            # TPIU trigger input is CTI out 3
            return (self.outCTI, 3, CTM_CHANNEL_TRACE_TRIGGER)
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

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = CheckedTPIU(self, tpiuDev, name)
        # disable the TPIU by default to allow ETB to work at full rate
        tpiu.setEnabled(False)
        return tpiu

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.dstreamTraceEnabled = enabled
        self.tpiu.setEnabled(enabled)
        self.enableCTIsForSink("TPIU", enabled)

    def setETRTraceEnabled(self, enabled):
        '''Enable/disable ETR trace capture'''
        self.etrTraceEnabled = enabled
        self.enableCTIsForSink("ETR", enabled)

    def setETFTraceEnabled(self, enabled):
        '''Enable/disable ETF trace capture'''
        self.etfTraceEnabled = enabled
        if enabled:
            # ensure TPIU is disabled and put the ETF in ETB mode
            self.tpiu.setEnabled(False)
            self.ETF.setMode(CSTMC.Mode.ETB)
        else:
            # Put the ETF in FIFO mode
            self.ETF.setMode(CSTMC.Mode.ETF)

        self.enableCTIsForSink("ETF", enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A9):
            if self.PTMs[c].isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexA9cores[c], self.PTMs[c])

        self.registerTraceSource(traceCapture, self.STM)

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
        portMap = {self.STM: STM_FUNNEL_PORT}
        for i in range(0, NUM_CORES_CORTEX_A9):
            portMap[self.PTMs[i]] = self.getFunnelPortForCore(i)

        return portMap.get(source, None)

    def setTriggerGeneratesDBGRQ(self, ptm, state):
        ptm.setTriggerGeneratesDBGRQ(state)

    def setTimestampingEnabled(self, ptm, state):
        ptm.setTimestampingEnabled(state)

    def setTimestampingPeriod(self, ptm, period):
        ptm.setTimestampPeriod(period)

    def setContextIDEnabled(self, ptm, state, size):
        ''' Set the context IDs up on the PTM '''
        if state == False:
            ptm.setContextIDs(False, IARMCoreTraceSource.ContextIDSize.NONE)
        else:
            contextIDSizeMap = {
                 "8":IARMCoreTraceSource.ContextIDSize.BITS_7_0,
                "16":IARMCoreTraceSource.ContextIDSize.BITS_15_0,
                "32":IARMCoreTraceSource.ContextIDSize.BITS_31_0 }
            ptm.setContextIDs(True, contextIDSizeMap[size])


    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        if not self.isConnected():
            self.setInitialOptions()
        self.updateDynamicOptions()

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
            self.setETRTraceEnabled(False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "ETF":
            self.setETFTraceEnabled(True)
            self.setETRTraceEnabled(False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "ETR":
            self.setETFTraceEnabled(False)
            self.setETRTraceEnabled(True)
            self.setDSTREAMTraceEnabled(False)
        elif method in ["DSTREAM", "DSTREAM_PT_Store_and_Forward", "DSTREAM_PT_StreamingTrace"]:
            self.setETFTraceEnabled(False)
            self.setETRTraceEnabled(False)
            self.setDSTREAMTraceEnabled(True)

    def setSTMEnabled(self, enabled):
        '''Enable/disable the STM trace source'''
        self.setTraceSourceEnabled(self.STM, enabled)

    def setXTrigFPGAEnabled(self, enabled):
        for core in self.cortexA9cores:
            core.setCrossTrigFPGA(enabled)

    def setXTrigHPSEnabled(self, enabled):
        for core in self.cortexA9cores:
            core.setCrossTrigHPS(enabled)

    def setCTIAccess(self, access):
        # check whether CTIs should be configured on connection
        for core in self.cortexA9cores:
            if self.isConnected():
                core.configureCTIs()

    def getPTMs(self):
        '''Get the PTMs'''
        return self.PTMs

    def setInitialOptions(self):
        '''Set the initial options'''

        ''' Setup whichever trace capture device was selected (if any) '''
        if self.dstreamTraceEnabled:
            self.createDSTREAM()
            self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)
        elif self.etrTraceEnabled:
            self.createETR()
            self.setupETRTrace()
        elif self.etfTraceEnabled:
            self.createETFTrace()
            self.setupETFTrace()

        coreTraceEnabled = self.getOptionValue("options.cortexA9.coreTrace")
        for i in range(0, NUM_CORES_CORTEX_A9):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA9.coreTrace.Cortex_A9_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            self.setTraceSourceEnabled(self.PTMs[i], enableSource)
            self.setTriggerGeneratesDBGRQ(self.PTMs[i], self.getOptionValue("options.cortexA9.coreTrace.triggerhalt"))
            self.setTimestampingEnabled(self.PTMs[i], self.getOptionValue("options.cortexA9.coreTrace.timestamp"))
            self.setTimestampingPeriod(self.PTMs[i], self.getOptionValue("options.cortexA9.coreTrace.timestamp.tsPeriod"))
            self.setContextIDEnabled(self.PTMs[i],
                         self.getOptionValue("options.cortexA9.coreTrace.contextIDs"),
                         self.getOptionValue("options.cortexA9.coreTrace.contextIDs.contextIDsSize"))

        ptmStartIndex = 0
        ptmEndIndex = 0

        ptmEndIndex += NUM_CORES_CORTEX_A9
        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A9_TRACE_OPTIONS], TraceRangeOptions("cortexA9", self), self.PTMs[ptmStartIndex:ptmEndIndex])
        ptmStartIndex += NUM_CORES_CORTEX_A9

        # register trace sources for each trace sink
        if self.etfTraceEnabled:
            self.registerTraceSources(self.etfTrace)
        elif self.etrTraceEnabled:
            self.registerTraceSources(self.ETR)
        elif self.dstreamTraceEnabled:
            self.registerTraceSources(self.DSTREAM)

        traceMode = self.getOptionValue("options.trace.traceCapture")
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

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

        # Set up the ETR buffer
        if self.etrTraceEnabled:
            configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer")
            if configureETRBuffer:
                scatterGatherMode = self.getOptionValue("options.ETR.etrBuffer.scatterGather")
                bufferStart = self.getOptionValue("options.ETR.etrBuffer.start")
                bufferSize = self.getOptionValue("options.ETR.etrBuffer.size")
                self.ETR.setBaseAddress(bufferStart)
                self.ETR.setTraceBufferSize(bufferSize)
                self.ETR.setScatterGatherModeEnabled(scatterGatherMode)

        # Set up the ETF buffer
        if self.etfTraceEnabled:
            configureETFBuffer = self.getOptionValue("options.ETF.etfBuffer")
            if configureETFBuffer:
                bufferSize = self.getOptionValue("options.ETF.etfBuffer.size")
                self.etfTrace.setMaxCaptureSize(bufferSize)

    def getDstreamOptionString(self):
        return "dstream"

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

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        ahbAccessor = AHBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0")
        ahbAccessor.setHProt(0x03)

        core.registerAddressFilters(
            [ahbAccessor,
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
        '''Funnel port-to-core mapping can be customized here'''
        port = core
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

    def verify(self):
        mask = [ 0xF, 0x0, 0x0, 0x0, 0xFF, 0xFF, 0xF, 0x0 ]
        expectedROMTable = [ 0L, 0L, 0L, 0L, 2L, 224L, 14L, 0L ]
        addrROMTable = 0x80000fd0
        return self.confirmValue(addrROMTable, expectedROMTable, mask)

    def confirmValue(self, addr, expected, mask):
        actual = zeros(len(expected), 'l')
        for i in range(0,len(expected)-1) :
            j = i*4
            buffer = zeros(4, 'b')
            try:
                self.APB.readMem(addr+j, 4, buffer)
            except DTSLException:
                return False
            value = unpack('<I', buffer)[0]
            actual[i] = value
            if ((actual[i] & mask[i]) != (expected[i] & mask[i])):
                return False
        return True

    def postConnect(self):
        DTSLv1.postConnect(self)

        freq = self.getOptionValue("options.trace.timestampFrequency")

        # update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)

        if self.etfTraceEnabled:
            bufferSize = self.getOptionValue("options.ETF.etfBuffer.size")
            self.etfTrace.setMaxCaptureSize(bufferSize)

    def ctiCoreFactory(self, dev, label, coreCTI, fpgaCTI):
        return CTICore(self, dev, label, coreCTI, fpgaCTI)


class DSTREAM_DtslScript(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DSTREAM_DtslScript.getOptionTraceCaptureTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionCrossTriggerTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionETFTabPage(),
                DtslScript.getOptionETRTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceCaptureTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
            # If you change the position or name of the traceCapture device option you MUST
            # modify the project_types.xml to tell the debugger about the new location/name
            DSTREAM_DtslScript.getTraceCaptureDeviceOptions(),
            DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
            DTSLv1.booleanOption('enforceCheck', "Check board is correctly configured before attempting to capture trace in DSTREAM buffer", description="Checks that the values of certain registers are set, indicating that the system has been setup correctly.\nDisabling this option may result in corrupt trace buffers being returned for an incorrectly configured system", isDynamic=True, defaultValue=True, setter=DSTREAM_DtslScript.enforceCheck)
        ])

    @staticmethod
    def getTraceCaptureDeviceOptions():
        return DTSLv1.radioEnumOption(
                    name='traceCapture',
                    displayName = 'Trace capture method',
                    description="Specify how trace data is to be collected",
                    defaultValue="none",
                    setter=DtslScript.setTraceCaptureMethod,
                    values = [("none", "None"),
                              ("ETR", "System Memory Trace Buffer (ETR)"),
                              ("ETF", "On Chip Trace Buffer (ETF)"),
                              DSTREAM_DtslScript.getDSTREAMOptions()])

    @staticmethod
    def getDSTREAMOptions():
        return (
            "DSTREAM", "DSTREAM 4GB Trace Buffer",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                        values = [("4", "4 bit"), ("16", "16 bit")], isDynamic=False)
                ]
            )
        )

    def enforceCheck(self, b):
        self.tpiu.enforceCheck(b)


class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''

        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        self.setPortWidth(portWidth)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.ETF, self.funnel0, self.tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(self.getOptionValue("options.trace.traceCapture"), [ self.funnel0, self.outCTI, self.tpiu, self.ETF, self.DSTREAM ])

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
                DtslScript_DSTREAM_ST.getOptionTraceCaptureTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionCrossTriggerTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionETFTabPage(),
                DtslScript.getOptionETRTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceCaptureTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
            DtslScript_DSTREAM_ST.getTraceCaptureDeviceOptions(),
            DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
        ])

    @staticmethod
    def getTraceCaptureDeviceOptions():
        return DTSLv1.radioEnumOption(
                    name='traceCapture',
                    displayName = 'Trace capture method',
                    description="Specify how trace data is to be collected",
                    defaultValue="none",
                    setter=DtslScript.setTraceCaptureMethod,
                    values = [("none", "None"),
                              ("ETR", "System Memory Trace Buffer (ETR)"),
                              ("ETF", "On Chip Trace Buffer (ETF)"),
                              DtslScript_DSTREAM_ST.getDSTREAMOptions()])

    @staticmethod
    def getDSTREAMOptions():
        return (
            "DSTREAM", "DSTREAM-ST Streaming Trace",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                        values = [("4", "4 bit")], isDynamic=False),
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
                DtslScript_DSTREAM_PT.getOptionTraceCaptureTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionCrossTriggerTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionETFTabPage(),
                DtslScript.getOptionETRTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceCaptureTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
            DtslScript_DSTREAM_PT.getTraceCaptureDeviceOptions(),
            DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
        ])

    @staticmethod
    def getTraceCaptureDeviceOptions():
        return DTSLv1.radioEnumOption(
                    name='traceCapture',
                    displayName = 'Trace capture method',
                    description="Specify how trace data is to be collected",
                    defaultValue="none",
                    setter=DtslScript.setTraceCaptureMethod,
                    values = [("none", "None"),
                              ("ETR", "System Memory Trace Buffer (ETR)"),
                              ("ETF", "On Chip Trace Buffer (ETF)"),
                              DtslScript_DSTREAM_PT.getStoreAndForwardOptions(),
                              DtslScript_DSTREAM_PT.getStreamingTraceOptions()])

    @staticmethod
    def getStoreAndForwardOptions():
        return (
            "DSTREAM_PT_StreamingTrace", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement(
                "dpt_streamingtrace", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                        values = [("4", "4 bit"), ("16", "16 bit")], isDynamic=False)
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
                        values = [("4", "4 bit"), ("16", "16 bit")], isDynamic=False),
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


class NoDSTREAMTrace_DtslScript(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                NoDSTREAMTrace_DtslScript.getOptionTraceCaptureTabPage(),
                DtslScript.getOptionCortexA9TabPage(),
                DtslScript.getOptionCrossTriggerTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionETFTabPage(),
                DtslScript.getOptionETRTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceCaptureTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
            NoDSTREAMTrace_DtslScript.getTraceCaptureDeviceOptions(),
            DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
        ])

    @staticmethod
    def getTraceCaptureDeviceOptions():
        return DTSLv1.radioEnumOption(
                    name='traceCapture',
                    displayName = 'Trace capture method',
                    description="Specify how trace data is to be collected",
                    defaultValue="none",
                    setter=DtslScript.setTraceCaptureMethod,
                    values = [("none", "None"),
                              ("ETR", "System Memory Trace Buffer (ETR)"),
                              ("ETF", "On Chip Trace Buffer (ETF)")])

    def ctiCoreFactory(self, dev, label, coreCTI, fpgaCTI):
        return CTICoreNoDownload(self, dev, label, coreCTI, fpgaCTI)


class USBBlaster_DtslScript(NoDSTREAMTrace_DtslScript):
    @staticmethod
    def dummy():
        #dummy function to prevent error
        return

class RVI_DtslScript(NoDSTREAMTrace_DtslScript):
    @staticmethod
    def dummy():
        #dummy function to prevent error
        return

class ULINKpro_DtslScript(NoDSTREAMTrace_DtslScript):
    @staticmethod
    def dummy():
        #dummy function to prevent error
        return

class ULINKproD_DtslScript(NoDSTREAMTrace_DtslScript):
    @staticmethod
    def dummy():
        #dummy function to prevent error
        return

