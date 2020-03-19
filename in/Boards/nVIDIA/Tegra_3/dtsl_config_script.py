from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import V7M_CSTPIU
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE
from struct import pack, unpack
from jarray import array, zeros
from java.lang import StringBuilder
import time

ALL_CORES = -1
DEFAULT_PORT_SIZE = 8
KERNEL_RANGE_END = 0xFFFFFFFF
KERNEL_RANGE_START = 0x7F000000


def get_core_state(core):
    state = zeros(1, 'i')
    core.getExecStatus(state, zeros(1, 'i'), zeros(1, 'l'), zeros(1, 'l'),
                       zeros(1, 'l'))
    return state[0]


def is_stopped(core):
    return get_core_state(core) == RDDI_EVENT_TYPE.RDDI_PROC_STATE_STOPPED

def with_halted_core(core, f):
    """ Call f with core temporarily stopped """
    if not is_stopped(core):
        try:
            core.stop()
            f(core)
        finally:
            pass
            core.go()
    else:
        f(core)

def do_pokes(dev):
    """ The magic writes to correctly pinmux the TPIU output """
    read_modify_write(dev, 0x700032FC, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_COL0_0
    read_modify_write(dev, 0x70003300, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_COL1_0
    read_modify_write(dev, 0x70003304, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_COL2_0
    read_modify_write(dev, 0x70003308, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_COL3_0
    read_modify_write(dev, 0x7000330C, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_COL4_0
    read_modify_write(dev, 0x70003310, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_COL5_0
    read_modify_write(dev, 0x70003314, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_COL6_0
    read_modify_write(dev, 0x70003318, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_COL7_0
    read_modify_write(dev, 0x700032CC, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_ROW4_0
    read_modify_write(dev, 0x700032D0, 0xFFFFFFEF, 0x00000000)   # PINMUX_AUX_KB_ROW5_0
    read_modify_write(dev, 0x700032FC, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_COL0_0
    read_modify_write(dev, 0x70003300, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_COL1_0
    read_modify_write(dev, 0x70003304, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_COL2_0
    read_modify_write(dev, 0x70003308, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_COL3_0
    read_modify_write(dev, 0x7000330C, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_COL4_0
    read_modify_write(dev, 0x70003310, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_COL5_0
    read_modify_write(dev, 0x70003314, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_COL6_0
    read_modify_write(dev, 0x70003318, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_COL7_0
    read_modify_write(dev, 0x700032CC, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_ROW4_0
    read_modify_write(dev, 0x700032D0, 0xFFFFFFFC, 0x00000002)   # PINMUX_AUX_KB_ROW5_0

    write16(dev, 0x6000D484, 0x00001000)    # GPIO_MSK_CNF_1_4
    write16(dev, 0x6000D484, 0x00002000)    # GPIO_MSK_CNF_1_4
    write16(dev, 0x6000D480, 0x00000100)    # GPIO_MSK_CNF_4
    write16(dev, 0x6000D480, 0x00000200)    # GPIO_MSK_CNF_4
    write16(dev, 0x6000D480, 0x00000400)    # GPIO_MSK_CNF_4
    write16(dev, 0x6000D480, 0x00000800)    # GPIO_MSK_CNF_4
    write16(dev, 0x6000D480, 0x00001000)    # GPIO_MSK_CNF_4
    write16(dev, 0x6000D480, 0x00002000)    # GPIO_MSK_CNF_4
    write16(dev, 0x6000D480, 0x00004000)    # GPIO_MSK_CNF_4
    write16(dev, 0x6000D480, 0x00008000)    # GPIO_MSK_CNF_4

    write32(dev, 0x700032B4,0x00000028)    # PINMUX_AUX_PWR_I2C_SCL_0
    write32(dev, 0x700032B8,0x00000028)    # PINMUX_AUX_PWR_I2C_SDA_0
    write16(dev, 0x6000D684,0x00004000)    # GPIO_MSK_CNF_1_6
    write16(dev, 0x6000D684,0x00008000)    # GPIO_MSK_CNF_1_6
    read_modify_write(dev, 0x60006008,0xFFFF7FFF,0x00008000)    # CLK_RST_CONTROLLER_RST_DEVICES_H_0
    read_modify_write(dev, 0x60006008,0xFFFF7FFF,0x00000000)    # CLK_RST_CONTROLLER_RST_DEVICES_H_0
    write32(dev, 0x60006128,0xC000001D)    # CLK_RST_CONTROLLER_CLK_SOURCE_DVC_I2C_0
    read_modify_write(dev, 0x60006014,0xFFFF7FFF,0x00008000)    # CLK_RST_CONTROLLER_CLK_OUT_ENB_H_0
    read_modify_write(dev, 0x70000868,0xFFFFFFF7,0x00000008)    # APB_MISC_GP_AOCFG1PADCTRL_0

    write32(dev, 0x7000D010,0x00000000)    # I2C_I2C_CMD_DATA2_4
    write32(dev, 0x7000D004,0x000000D2)    # I2C_I2C_CMD_ADDR0_4
    write32(dev, 0x7000D008,0x000000D3)    # I2C_I2C_CMD_ADDR1_4
    write32(dev, 0x7000D000,0x00000000)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D00C,0x00000002)    # I2C_I2C_CMD_DATA1_4
    write32(dev, 0x7000D000,0x00000090)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D000,0x00000290)    # I2C_I2C_CNFG_4
    time.sleep(1)
    write32(dev, 0x7000D004,0x000000D2)    # I2C_I2C_CMD_ADDR0_4
    write32(dev, 0x7000D000,0x00000002)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D00C,0x00001402)    # I2C_I2C_CMD_DATA1_4
    write32(dev, 0x7000D010,0xCCCCCCCC)    # I2C_I2C_CMD_DATA2_4
    write32(dev, 0x7000D000,0x00000A02)    # I2C_I2C_CNFG_4
    time.sleep(1)
    write32(dev, 0x7000D010,0x00000000)    # I2C_I2C_CMD_DATA2_4
    write32(dev, 0x7000D004,0x000000D2)    # I2C_I2C_CMD_ADDR0_4
    write32(dev, 0x7000D008,0x000000D3)    # I2C_I2C_CMD_ADDR1_4
    write32(dev, 0x7000D000,0x00000000)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D00C,0x00000002)    # I2C_I2C_CMD_DATA1_4
    write32(dev, 0x7000D000,0x00000090)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D000,0x00000290)    # I2C_I2C_CNFG_4
    time.sleep(1)
    write32(dev, 0x7000D004,0x000000D2)    # I2C_I2C_CMD_ADDR0_4
    write32(dev, 0x7000D000,0x00000002)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D00C,0x00001402)    # I2C_I2C_CMD_DATA1_4
    write32(dev, 0x7000D010,0xCCCCCCCC)    # I2C_I2C_CMD_DATA2_4
    write32(dev, 0x7000D000,0x00000A02)    # I2C_I2C_CNFG_4
    time.sleep(1)
    write32(dev, 0x7000D010,0x00000000)    # I2C_I2C_CMD_DATA2_4
    write32(dev, 0x7000D004,0x000000D2)    # I2C_I2C_CMD_ADDR0_4
    write32(dev, 0x7000D008,0x000000D3)    # I2C_I2C_CMD_ADDR1_4
    write32(dev, 0x7000D000,0x00000000)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D00C,0x00000003)    # I2C_I2C_CMD_DATA1_4
    write32(dev, 0x7000D000,0x00000090)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D000,0x00000290)    # I2C_I2C_CNFG_4
    time.sleep(1)
    write32(dev, 0x7000D004,0x000000D2)    # I2C_I2C_CMD_ADDR0_4
    write32(dev, 0x7000D000,0x00000002)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D00C,0x00000203)    # I2C_I2C_CMD_DATA1_4
    write32(dev, 0x7000D010,0xCCCCCCCC)    # I2C_I2C_CMD_DATA2_4
    write32(dev, 0x7000D000,0x00000A02)    # I2C_I2C_CNFG_4
    time.sleep(1)
    write32(dev, 0x7000D010,0x00000000)    # I2C_I2C_CMD_DATA2_4
    write32(dev, 0x7000D004,0x000000D2)    # I2C_I2C_CMD_ADDR0_4
    write32(dev, 0x7000D008,0x000000D3)    # I2C_I2C_CMD_ADDR1_4
    write32(dev, 0x7000D000,0x00000000)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D00C,0x00000003)    # I2C_I2C_CMD_DATA1_4
    write32(dev, 0x7000D000,0x00000090)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D000,0x00000290)    # I2C_I2C_CNFG_4
    time.sleep(1)
    write32(dev, 0x7000D004,0x000000D2)    # I2C_I2C_CMD_ADDR0_4
    write32(dev, 0x7000D000,0x00000002)    # I2C_I2C_CNFG_4
    write32(dev, 0x7000D00C,0x00000203)    # I2C_I2C_CMD_DATA1_4
    write32(dev, 0x7000D010,0xCCCCCCCC)    # I2C_I2C_CMD_DATA2_4
    write32(dev, 0x7000D000,0x00000A02)    # I2C_I2C_CNFG_4
    time.sleep(1)


def read_modify_write(dev, address, mask, data):
    """ write to physical address """
    buffer = zeros(4, 'b')
    dev.memRead(0, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, RDDI.RDDI_MEM_MMU_PHYSICAL, 4, buffer)
    value = unpack('<I', buffer)[0]       # buffer[0] | (buffer[1] << 8) | (buffer[2] << 16) | (buffer[3] << 24)
    new_value = (value & mask) | data
    dev.memWrite(0, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, RDDI.RDDI_MEM_MMU_PHYSICAL, False, 4, pack('<I', new_value))

def write16(dev, address, value):
    """ write to physical address """
    dev.memWrite(0, address, RDDI_ACC_SIZE.RDDI_ACC_HALF, RDDI.RDDI_MEM_MMU_PHYSICAL, False, 2, pack('<I', value))

def write32(dev, address, value):
    """ write to physical address """
    dev.memWrite(0, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, RDDI.RDDI_MEM_MMU_PHYSICAL, False, 4, pack('<I', value))

def pinmux_tpiu_with_core0_halted(dev):
    with_halted_core(dev, do_pokes)


def pinmux_tpiu(dev):
    with_open_dev(dev, pinmux_tpiu_with_core0_halted)


# The device we need might be open already - don't bail out if so
def with_open_dev(dev, f):
    """ Call f with a device connection resource managed """

    devOpen = False

    try:
        print "Hello world"
        dev.openConn(zeros(1, 'i'), zeros(1, 'i'), StringBuilder(1024))
        devOpen = True
    except:
        raise

    try:
        f(dev)
    finally:
        if devOpen:
            dev.closeConn()

class DTSLConfigurationFunctions(DTSLv1):
    def createCTIsWithSeparateTraceCTI(self):
        """
        This function creates all CTIs, including a CTI for ETB/TPIU.
        The first CTI is assumed to be used for ETB/TPIU, the rest are assumed to be associated with
        the cores in a linear fassion. This function might need adjustments
        in order to better match the hardware setup.
        """
        self.ctis = []
        self.ctiMap = {}
        outCTIDev = self.createOutCTI()
        coreCTIDev = outCTIDev
        for i in range(0, len(self.coreDevices)):
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev + 1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            coreCTI.enableInputEvent(0, 0) # use channel 0 for sync stop
            coreCTI.enableInputEvent(6, 2) # use channel 2 for ETM/PTM trigger
            coreCTI.enableOutputEvent(0, 0)
            coreCTI.enableOutputEvent(7, 1) # use channel 1 for sync start
            self.ctis.append(coreCTI)
            coreDev = self.coreDevices[i]
            self.ctiMap[coreDev] = coreCTI

    def createCores(self, coreType, numberOfCores):
        """
        Creates two lists: one containing the core indexes, the other - the core Device objects.
        Those will be used by other functions that set up the current activity.
        """
        self.coreIndexList = []
        self.coreDevices = []
        coreDev = 0
        for i in range (0, numberOfCores):
            coreDev = self.findDevice(coreType, coreDev + 1)
            self.coreIndexList.append(coreDev)
            self.coreDevices.append(Device(self, coreDev, "%s_%d" % (coreType, i)))

    def createDSTREAM(self, pw):
        """
        Creates and sets up the DSTREAM for DSTREAM trace.
        """
        if (hasattr(self, 'mgdDevices')) != True:
            self.mgdDevices = []
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        self.DSTREAM.setTraceMode(self.dstreamMode)
        self.DSTREAM.setPortWidth(pw)
        self.mgdDevices.append(self.DSTREAM)
        self.addTraceCaptureInterface(self.DSTREAM)
        self.DSTREAM.setTraceComponentOrder(self.traceComponentOrder)

    def createDisabledTPIU(self):
        """
        Disables the TPIU to allow ETB to run at full rate.
        """
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = CSTPIU(self, tpiuDev, "TPIU")
        self.tpiu.setEnabled(False)
        self.mgdDevices = [ self.tpiu ]


    def createETMsv3_3(self, sink, etmToUse):
        """
        This function creates all the ETMs or a
        specific ETM. It assumes linear mapping
        between the cores and the ETMs. This function might need adjustments
        in order to better match the hardware setup.
        """
        self.traceSources = []
        if etmToUse >= len(self.coreIndexList):
            etms = etmToUse + 1
        else:
            etms = len(self.coreIndexList)

        etmDev = 1
        for i in range(0, etms):
            etmDev = self.findDevice("ETM", etmDev + 1)
            if (etmToUse == ALL_CORES) or (i == etmToUse):
                ETM = ETMv3_3TraceSource(self, etmDev, i + 1,"ETM%d" % i)
                self.traceSources.append(ETM)
                if etmToUse == ALL_CORES:
                    sink.addTraceSource(ETM, self.coreIndexList[i])
                else:
                    sink.addTraceSource(ETM, self.coreIndexList[0])

        self.mgdDevices = self.traceSources + self.mgdDevices


    def createEnabledTPIU(self, pw):
        """
        Creates a TPIU and configures it for DSTREAM trace.
        """
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = CSTPIU(self, tpiuDev, "TPIU")
        self.tpiu.setEnabled(True)
        self.tpiu.setFormatterMode(self.formatterMode)
        self.tpiu.setPortSize(pw)
        self.mgdDevices = [ self.tpiu ]
        self.traceComponentOrder = [ self.tpiu ]

    def createEtb(self):
        """
        Creates and sets up the ETB for ETB trace.
        """
        if (hasattr(self, 'mgdDevices')) != True:
            self.mgdDevices = []
        if (hasattr(self, 'traceComponentOrder')) != True:
            self.traceComponentOrder = []
        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(self.formatterMode)
        self.mgdDevices.append(self.ETB)
        self.addTraceCaptureInterface(self.ETB)
        self.ETB.setTraceComponentOrder(self.traceComponentOrder)

    def createOutCTI(self):
        """
        This function creates the cross trigger CTI for ETB/TPIU.
        This function might need adjustments
        in order to better match the hardware setup.
        """
        outCTIDev = self.findDevice("CSCTI")
        outCTI = CSCTI(self, outCTIDev, "CTI_out")
        if (hasattr(self, 'ETB')) == True:
            outCTI.enableOutputEvent(1, 2) # ETB trigger input is CTI out 1
        else:
            if (hasattr(self, 'DSTREAM')) == True:
                outCTI.enableOutputEvent(3, 2) # TPIU trigger input is CTI out 3
        self.ctis = [ outCTI ]
        return outCTIDev

    def createPTMs(self, sink, ptmToUse):
        """
        This function creates all the PTMs or a
        specific PTM. It assumes linear mapping
        between the cores and the PTMs. This function might need adjustments
        in order to better match the hardware setup.
        """
        self.traceSources = []
        if ptmToUse >= len(self.coreIndexList):
            ptms = ptmToUse + 1
        else:
            ptms = len(self.coreIndexList)

        ptmDev = 1
        for i in range(0, ptms):
            ptmDev = self.findDevice("CSPTM", ptmDev + 1)
            if (ptmToUse == ALL_CORES) or (i == ptmToUse):
                PTM = PTMTraceSource(self, ptmDev, i + 1,"PTM%d" % i)
                self.traceSources.append(PTM)
                if ptmToUse == ALL_CORES:
                    sink.addTraceSource(PTM, self.coreIndexList[i])
                else:
                    sink.addTraceSource(PTM, self.coreIndexList[0])

        self.mgdDevices = self.traceSources + self.mgdDevices


    def createSingleCore(self, coreType, desiredCoreIndex):
        """
        Creates two lists: one containing the core index, the other - the core Device object.
        Those will be used by other functions that set up the current activity.
        """
        coreDev = 0
        for i in range (0, desiredCoreIndex + 1):
            coreDev = self.findDevice(coreType, coreDev + 1)
            if i == desiredCoreIndex:
                self.coreIndexList = [ coreDev ]
                self.coreDevices = [ Device(self, coreDev,"%s_%d" % (coreType, i)) ]

    def createSingleFunnel(self, portToOpen):
        """
        Creates and sets up a single funnel, assuming linear mapping between
        the ETMs/PTMs and the funnel ports. This function might need adjustments
        in order to better match the hardware setup.
        """
        if (hasattr(self, 'traceComponentOrder')) != True:
            self.traceComponentOrder = []
        funnelDev = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev, "Funnel")
        funnel.setAllPortsDisabled()
        if (portToOpen == -1):
            for i in range(0, len(self.coreDevices)): # opens all ports
                funnel.setPortEnabled(self.getFunnelPort(i))
        else:
            funnel.setPortEnabled(self.getFunnelPort(portToOpen))  # opens a specific port

        self.mgdDevices.append(funnel)
        self.traceComponentOrder = [ funnel ] + self.traceComponentOrder

    def createV7MTPIU(self, pw, enabled):
        """
        Creates a Cortex-M*-specific TPIU and configures it for DSTREAM trace.
        """
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = V7M_CSTPIU(self, tpiuDev, "TPIU", self.coreDevices[0])
        if enabled == True:
            self.tpiu.setEnabled(True)
            self.tpiu.setPortSize(pw)
            self.traceComponentOrder = [ self.tpiu ]
        else:
            self.tpiu.setEnabled(False)
        self.mgdDevices = [ self.tpiu ]

    def determineFormatterMode(self):
        # Configures the TPIU for continuous mode.
        self.formatterMode = FormatterMode.CONTINUOUS

        # Configures the DSTREAM for continuous trace
        self.dstreamMode = DSTREAMTraceCapture.TraceMode.Continuous

    def getFunnelPort(self, core):
        # select port for desired core
        port = -1
        if core == 3:
            # core 3 isn't on port 3, but on port 4!
            port = 4
        else:
            # otherwise core n is on port n
            port = core
        return port

    def postConnect(self):
        DTSLv1.postConnect(self)

class Cortex_A9_0_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 0
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTMs(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

class TPIU_Pinmux(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)

    def postConnect(self):
        dev = self.coreDevices[0]
        pinmux_tpiu(dev)
        DTSLConfigurationFunctions.postConnect(self)

class Cortex_A9_0_PINMUX(TPIU_Pinmux):
    def __init__(self, root):
        TPIU_Pinmux.__init__(self, root)
        coreIndex = 0
        self.createSingleCore("Cortex-A9", coreIndex)

class Cortex_A9_0_DSTREAM(TPIU_Pinmux):
    def __init__(self, root):
        TPIU_Pinmux.__init__(self, root)
        coreIndex = 0
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(coreIndex)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTMs(self.DSTREAM, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

class Cortex_A9_1_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 1
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTMs(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

class Cortex_A9_1_DSTREAM(TPIU_Pinmux):
    def __init__(self, root):
        TPIU_Pinmux.__init__(self, root)
        coreIndex = 1
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(coreIndex)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTMs(self.DSTREAM, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

class Cortex_A9_2_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 2
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTMs(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

class Cortex_A9_2_DSTREAM(TPIU_Pinmux):
    def __init__(self, root):
        TPIU_Pinmux.__init__(self, root)
        coreIndex = 2
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(coreIndex)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTMs(self.DSTREAM, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

class Cortex_A9_3_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 3
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTMs(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

class Cortex_A9_3_DSTREAM(TPIU_Pinmux):
    def __init__(self, root):
        TPIU_Pinmux.__init__(self, root)
        coreIndex = 3
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(coreIndex)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTMs(self.DSTREAM, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

class Cortex_A9_CTI_SYNC_SMP(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 4)
        self.createCTIsWithSeparateTraceCTI()
        self.setManagedDevices(self.ctis)
        self.addDeviceInterface(CTISyncSMPDevice(self, "Cortex-A9_CTI_SYNC_SMP", 1, self.coreDevices, self.ctiMap, 1, 0))

class Cortex_A9_CTI_SYNC_SMP_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 4)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(ALL_CORES)
        self.createEtb()
        self.createPTMs(self.ETB, ALL_CORES)
        self.createCTIsWithSeparateTraceCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)
        self.addDeviceInterface(CTISyncSMPDevice(self, "Cortex-A9_CTI_SYNC_SMP_ETB", 1, self.coreDevices, self.ctiMap, 1, 0))

class Cortex_A9_CTI_SYNC_SMP_DSTREAM(TPIU_Pinmux):
    def __init__(self, root):
        TPIU_Pinmux.__init__(self, root)
        self.createCores("Cortex-A9", 4)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(ALL_CORES)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTMs(self.DSTREAM, ALL_CORES)
        self.createCTIsWithSeparateTraceCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)
        self.addDeviceInterface(CTISyncSMPDevice(self, "Cortex-A9_CTI_SYNC_SMP_DSTREAM", 1, self.coreDevices, self.ctiMap, 1, 0))

class Cortex_A9_0_ETB_KernelOnly(Cortex_A9_0_ETB):
    def __init__(self, root):
        Cortex_A9_0_ETB.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_0_DSTREAM_KernelOnly(Cortex_A9_0_DSTREAM):
    def __init__(self, root):
        Cortex_A9_0_DSTREAM.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_1_ETB_KernelOnly(Cortex_A9_1_ETB):
    def __init__(self, root):
        Cortex_A9_1_ETB.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_1_DSTREAM_KernelOnly(Cortex_A9_1_DSTREAM):
    def __init__(self, root):
        Cortex_A9_1_DSTREAM.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_2_ETB_KernelOnly(Cortex_A9_2_ETB):
    def __init__(self, root):
        Cortex_A9_2_ETB.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_2_DSTREAM_KernelOnly(Cortex_A9_2_DSTREAM):
    def __init__(self, root):
        Cortex_A9_2_DSTREAM.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_3_ETB_KernelOnly(Cortex_A9_3_ETB):
    def __init__(self, root):
        Cortex_A9_3_ETB.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_3_DSTREAM_KernelOnly(Cortex_A9_3_DSTREAM):
    def __init__(self, root):
        Cortex_A9_3_DSTREAM.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_CTI_SYNC_SMP_ETB_KernelOnly(Cortex_A9_CTI_SYNC_SMP_ETB):
    def __init__(self, root):
        Cortex_A9_CTI_SYNC_SMP_ETB.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_CTI_SYNC_SMP_DSTREAM_KernelOnly(Cortex_A9_CTI_SYNC_SMP_DSTREAM):
    def __init__(self, root):
        Cortex_A9_CTI_SYNC_SMP_DSTREAM.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

