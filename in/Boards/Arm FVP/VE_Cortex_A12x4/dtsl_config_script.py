from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CadiSyncSMPDevice

NUM_CORES_CORTEX_A12 = 4
CORTEX_A12_START_ID = 1


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

        self.exposeCores()

        self.setupCadiSyncSMP()
        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        cortexA12coreDev = 0
        self.cortexA12cores = []

        streamID = 0

        for i in range(0, NUM_CORES_CORTEX_A12):
            # create core
            dev = Device(self, i+CORTEX_A12_START_ID, "ARM_Cortex-A12_%d" % i)
            self.cortexA12cores.append(dev)

    def exposeCores(self):
        for core in self.cortexA12cores:
            self.addDeviceInterface(core)

    def setupCadiSyncSMP(self):
        '''Create SMP device using RDDI synchronization'''

        # create SMP device and expose from configuration
        # Cortex-A12x4 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A12 SMP", self.cortexA12cores)
        self.addDeviceInterface(smp)

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()

