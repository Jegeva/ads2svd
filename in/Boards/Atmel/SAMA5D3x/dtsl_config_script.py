from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.nativelayer import NativeException
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE
from struct import pack
from jarray import array, zeros

ATB_ID_BASE = 2

def get_core_state(core):
    state = zeros(1, 'i')
    core.getExecStatus(state, zeros(1, 'i'), zeros(1, 'l'), zeros(1, 'l'),
                       zeros(1, 'l'))
    return state[0]


def is_stopped(core):
    return get_core_state(core) == RDDI_EVENT_TYPE.RDDI_PROC_STATE_STOPPED


class ResetDevice(Device):
    def __init__(self, root, devNo, name):
        Device.__init__(self, root, devNo, name)
        self.parent = root

    def systemReset(self, resetType):
        # reset via reset controller
        self.parent.reset()


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace", childOptions=[
                ])
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # only APB is managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.APB)

        self.exposeCores()

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        apbDev = self.findDevice("CSMEMAP")
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        # create core
        cortexA5coreDev = self.findDevice("Cortex-A5")
        dev = ResetDevice(self, cortexA5coreDev, "Cortex-A5")
        self.core = dev

    def exposeCores(self):
        self.registerFilters(self.core)
        self.addDeviceInterface(self.core)

    def reset(self):
        # System is reset via reset controller

        # Stop core to allow access to memory mapped registers
        if not is_stopped(self.core):
            try:
                self.core.stop()
            except:
                pass

        # Reset control register is at 0xFFFFFE00
        #  Turn off the MMU
        self.core.regWriteBlock(0xF801, 1, [ 0x00C50878 ])
        # Request PROCRST + PERRST (assert bits 0 & 2), with a key of 0xA5 in bits 31:24
        try:
            self.core.memWrite(0, 0xFFFFFE00, RDDI_ACC_SIZE.RDDI_ACC_DEF, RDDI.RDDI_MRUL_NORMAL, False, 4, pack('<I', 0xA5000005))
        except NativeException, e:
            if e.getRDDIErrorCode() == RDDI.RDDI_RWFAIL:
                # error is expected as a result of reset: ignore
                pass
            else:
                raise


    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the set of devices managed by the configuration'''
        for d in devs:
            self.mgdPlatformDevs.add(d)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APB for the device'''
        core.registerAddressFilters(
             [AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP_0")])
