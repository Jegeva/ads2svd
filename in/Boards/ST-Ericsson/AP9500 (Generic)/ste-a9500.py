# Copyright (C) 2009-2011 ARM Limited. All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import RDDISyncSMPDevice
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import CSDAP
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE
from struct import pack
from jarray import array, zeros
from java.lang import StringBuilder
from time import sleep

PTM_ATB_ID_BASE = 2

def getFunnelPort(core):
    # Core n is on port n
    return core



class STEU8500A9SingleCoreETB(DTSLv1):
    def __init__(self, root, coreNo):
        DTSLv1.__init__(self, root)

        self.core = coreNo

        # disable the TPIU to allow ETB to work at full rate
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(False)

        # enable port for self. core on the funnel
        funnelDev = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev, "Funnel")
        funnel.setAllPortsDisabled()
        funnel.setPortEnabled(getFunnelPort(self.core))

        # enable cross trigger using channel 2 for trace trigger
        outCTIDev = self.findDevice("CSCTI")
        outCTI = CSCTI(self, outCTIDev, "CTI_out")
        outCTI.enableOutputEvent(1, 2) # ETB trigger input is CTI out 1

        # find first core/PTM
        coreCTIDev = outCTIDev
        coreDev = self.findDevice("Cortex-A9")
        ptmDev = self.findDevice("CSPTM")

        # skip through list to desired core/PTM/CTI
        for i in range(0, coreNo):
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)

        self.PTM = PTMTraceSource(self, ptmDev, 1, "PTM")
        self.addDeviceInterface(Device(self, coreDev, "Cortex-A9_%d" % coreNo))

        coreCTI = CSCTI(self, coreCTIDev, "CTI_core")
        coreCTI.enableInputEvent(6, 2) # use channel 2 for PTM trigger

        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(FormatterMode.BYPASS)
        self.ETB.addTraceSource(self.PTM, coreDev)
        self.ETB.setTraceComponentOrder([ funnel ])
        self.addTraceCaptureInterface(self.ETB)

        self.setManagedDevices([ self.PTM, funnel, tpiu, self.ETB, coreCTI ])



class STEU8500A9_0_ETB(STEU8500A9SingleCoreETB):
    def __init__(self, root):
        STEU8500A9SingleCoreETB.__init__(self, root, 0)

class STEU8500A9_1_ETB(STEU8500A9SingleCoreETB):
    def __init__(self, root):
        STEU8500A9SingleCoreETB.__init__(self, root, 1)

class STEU8500A9_0_ETB_KernelOnly(STEU8500A9SingleCoreETB):
    def __init__(self, root):
        STEU8500A9SingleCoreETB.__init__(self, root, 0)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)

class STEU8500A9_1_ETB_KernelOnly(STEU8500A9SingleCoreETB):
    def __init__(self, root):
        STEU8500A9SingleCoreETB.__init__(self, root, 1)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)

DSCR = 0x088
BVR0 = 0x100
BCR0 = 0x140


def get_core_state(core):
    state = zeros(1, 'i')
    core.getExecStatus(state, zeros(1, 'i'), zeros(1, 'l'), zeros(1, 'l'),
                       zeros(1, 'l'))
    return state[0]


def is_stopped(core):
    return get_core_state(core) == RDDI_EVENT_TYPE.RDDI_PROC_STATE_STOPPED


# The device we need might be open already - don't bail out if so
def with_open_dap(dev, f):
    """ Call f with a DAP connection resource managed """

    devOpen = False

    try:
        dev.connect()
        devOpen = True
    except:
        pass

    try:
        f(dev)
    finally:
        if devOpen:
            dev.disconnect()


# The device we need might be open already - don't bail out if so
def with_open_dev(dev, f):
    """ Call f with a device connection resource managed """

    devOpen = False

    try:
        dev.openConn(zeros(1, 'i'), zeros(1, 'i'), StringBuilder(1024))
        devOpen = True
    except:
        pass

    try:
        f(dev)
    finally:
        if devOpen:
            dev.closeConn()


def enable_halting_debug(dap, ap, base):
    """ Set HDBGen in DSCR for the core at this address """
    dscr_addr = base + DSCR
    val = dap.readMem(ap, dscr_addr)
    dap.writeMem(ap, dscr_addr, False, val | (1 << 14)) # HDBGen


def with_tmp_ap_memory_value(dap, ap, address, value, f):
    """ Call f with a word of memory temporarily set to a new value """
    oldval = dap.readMem(ap, address)
    dap.writeMem(ap, address, False, value)
    try:
        f()
    finally:
        dap.writeMem(ap, address, False, oldval)


def with_mismatch_all_break(dap, ap, base, f):
    """ Call f with a temporary global mismatch breakpoint set """
    with_tmp_ap_memory_value(dap, ap, base + BVR0, 0xffffffff,
      lambda: with_tmp_ap_memory_value(dap, ap, base + BCR0, 0x00400007, f))


def with_halted_core(core, f):
    """ Call f with core temporarily stopped """
    if not is_stopped(core):
        try:
            core.stop()
            f(core)
        finally:
            core.go()
    else:
        f(core)


def physical_mem_write(dev, address, value, check):
    """ write to physical address """
    dev.memWrite(0, address, RDDI_ACC_SIZE.RDDI_ACC_DEF,
                 RDDI.RDDI_MEM_MMU_PHYSICAL, check, 4, pack('<I', value))


def do_pokes(core0):
    """ The magic writes to wake core 1 """
    physical_mem_write(core0, 0x80151ff4, 0x00000000, True)
    physical_mem_write(core0, 0x80151ff0, 0xa1feed01, True)
    physical_mem_write(core0, 0xa0411f00, 0x00020001, False)


def wait_for_stop(dap, ap, base):
    for i in range(10):
        if dap.readMem(ap, base + DSCR) & 1:
            return
        sleep(0.1)
    raise Exception('Core failed to stop')


def poke_core1_with_core0_halted(core0):
    with_halted_core(core0, do_pokes)


def poke_it(dap, core1_ap, core1_base, core0):
    with_open_dev(core0, poke_core1_with_core0_halted)
    wait_for_stop(dap, core1_ap, core1_base)


def wake_core1(dap, core0):
    """
    Do the steps to get core 1 out of WFE:
    - Set a global mismatch breakpoint on core 1. This needs to be done
      through the AP, as the template interface doesn't support mismatch.
    - Do some magic memory writes through core 0. This needs to be done
      through the core because I can't find the locations on the AHB-AP.
    - Put everything back as we found it.  This is why we have all the
      annoying lambdas and with... functions.
    """
    CORE1_AP = 0x1
    CORE1_BASE = 0x801aa000
    dap.setHProt(0x43)
    enable_halting_debug(dap, CORE1_AP, CORE1_BASE)
    with_mismatch_all_break(dap, CORE1_AP, CORE1_BASE,
                            lambda: poke_it(dap, CORE1_AP, CORE1_BASE, core0))


class STEU8500A9_SMP(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # find trace output cross trigger
        outCTIDev = self.findDevice("CSCTI")

        # find each core
        coreCTIDev = outCTIDev
        ctis = []
        ctiMap = {}
        coreDev = 1
        self.coreDevices= []
        for i in range(0, 2):
            # create Device representation for the core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)

            dev = Device(self, coreDev, "Cortex-A9_%d" % i)
            self.addDeviceInterface(dev)
            self.coreDevices.append(dev)

            # setup cross trigger to stop cores together
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            coreCTI.enableInputEvent(0, 0) # use channel 0 for sync stop
            coreCTI.enableOutputEvent(0, 0)
            coreCTI.enableOutputEvent(7, 1) # use channel 1 for sync start
            ctis.append(coreCTI)
            ctiMap[dev] = coreCTI

        # automatically handle connection/disconnection
        self.setManagedDevices(ctis)

        # create SMP device and expose from configuration
        self.addDeviceInterface(CTISyncSMPDevice(self, "U8500-A9 SMP",1,self.coreDevices, ctiMap, 1, 0))


class WakingDevice(Device):
    def __init__(self, root, devNo, name):
        Device.__init__(self, root, devNo, name)
        self.parent = root

    def systemReset(self, resetType):
        Device.systemReset(self, resetType)
        dap = CSDAP(self.parent, self.parent.findDevice('ARMCS-DP'), 'ARMCS_DP')
        with_open_dap(dap, lambda dap: wake_core1(dap, self))


class STEU8500A9_SMP_WAKE(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # find each core
        coreDev = 1
        ptmDev = 1
        self.coreDevices= []

        # Use override device for Cortex-A9_0 to bring Cortex-A9_1 out of reset
        coreDev = self.findDevice("Cortex-A9", coreDev+1)
        core = WakingDevice(self, coreDev, "Cortex-A9_0")
        self.coreDevices.append(core)

        # Use standard device for Cortex-A9_1
        coreDev = self.findDevice("Cortex-A9", coreDev+1)
        self.coreDevices.append(Device(self, coreDev, "Cortex-A9_1"))

        self.addDeviceInterface(RDDISyncSMPDevice(self, "U8500-A9 SMP wake",1,self.coreDevices))


    def postConnect(self):
        dap = CSDAP(self, self.findDevice('ARMCS-DP'), 'ARMCS_DP')
        with_open_dap(dap, lambda dap: wake_core1(dap, self.coreDevices[0]))
        DTSLv1.postConnect(self)


class STEU8500A9_SMP_ETB(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # disable the TPIU to allow ETB to work at full rate
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(False)

        # enable ports for each core on the funnel
        funnelDev = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev, "Funnel")
        funnel.setAllPortsDisabled()

        # Create ETB and put into CONTINUOUS mode
        etbDev = self.findDevice("CSETB")
        ETB = ETBTraceCapture(self, etbDev, "ETB")
        ETB.setFormatterMode(FormatterMode.CONTINUOUS)

        # enable cross trigger using channel 2 for trace trigger
        outCTIDev = self.findDevice("CSCTI")
        outCTI = CSCTI(self, outCTIDev, "CTI_out")
        outCTI.enableOutputEvent(1, 2) # ETB trigger input is CTI out 1

        # find each core/PTM and enable trace
        coreCTIDev = outCTIDev
        ctis = []
        self.PTMs = []
        ctiMap = {}
        coreDev = 1
        ptmDev = 1
        self.coreDevices= []
        for i in range(0, 2):
            # create Device representation for the core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)

            # create the PTM for this core
            streamID = PTM_ATB_ID_BASE + i
            PTM = PTMTraceSource(self, ptmDev, streamID, "PTM%d" % i)
            self.PTMs.append(PTM)

            # enable the funnel for this core
            funnel.setPortEnabled(getFunnelPort(i))

            # register trace source with ETB
            ETB.addTraceSource(PTM, coreDev)

            # create Device representation for the core
            dev = Device(self, coreDev, "Cortex-A9_%d" % i)
            self.addDeviceInterface(dev)
            self.coreDevices.append(dev)

            # setup cross trigger to stop cores together and forward trace trigger
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            coreCTI.enableInputEvent(0, 0) # use channel 0 for sync stop
            coreCTI.enableOutputEvent(0, 0)
            coreCTI.enableOutputEvent(7, 1) # use channel 1 for sync start
            coreCTI.enableInputEvent(6, 2) # use channel 2 for PTM trigger
            ctis.append(coreCTI)
            ctiMap[dev] = coreCTI

        # register other trace components with ETB and register ETB with configuration
        ETB.setTraceComponentOrder([ funnel ])
        self.addTraceCaptureInterface(ETB)

        # automatically handle connection/disconnection to trace components
        self.setManagedDevices(self.PTMs + ctis + [ funnel, tpiu, outCTI, ETB ])

        # create SMP device and expose from configuration
        self.addDeviceInterface(CTISyncSMPDevice(self, "U8500-A9 SMP ETB",1,self.coreDevices, ctiMap, 1, 0))

class STEU8500A9_SMP_ETB_KernelOnly(STEU8500A9_SMP_ETB):
    def __init__(self, root):
        STEU8500A9_SMP_ETB.__init__(self, root)
        for ptm in self.PTMs:
            ptm.addTraceRange(0x7F000000,0xFFFFFFFF)

