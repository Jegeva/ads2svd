from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl.components import MemoryRouter
from com.arm.debug.dtsl.components import DapMemoryAccessor
from com.arm.debug.dtsl.components import Device

NUM_CORES_CORTEX_M0 = 1
ATB_ID_BASE = 2


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # only DAP device is managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.dap)

        self.exposeCores()

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        dapDev = self.findDevice("ARMCS-DP")
        self.dap = CSDAP(self, dapDev, "DAP")

        cortexM0coreDev = 0
        self.cortexM0cores = []

        streamID = ATB_ID_BASE

        for i in range(0, NUM_CORES_CORTEX_M0):
            # create core
            cortexM0coreDev = self.findDevice("Cortex-M0", cortexM0coreDev+1)
            dev = Device(self, cortexM0coreDev, "Cortex-M0")
            self.cortexM0cores.append(dev)

    def exposeCores(self):
        for core in self.cortexM0cores:
            self.addDeviceInterface(self.createDAPWrapper(core))

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

    def createDAPWrapper(self, core):
        '''Add a wrapper around a core to allow access to AHB and APB via the DAP'''
        return MemoryRouter(
            [DapMemoryAccessor("AHB", self.dap, 0, "AHB bus accessed via AP_0 on DAP_0"),
             DapMemoryAccessor("APB", self.dap, 1, "APB bus accessed via AP_1 on DAP_0")],
            core)

class DtslScript_CMSIS(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]

class DtslScript_ULINK2(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]

class DtslScript_ULINKpro(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]

class DtslScript_ULINKpro_D(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]


