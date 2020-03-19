from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CadiSyncSMPDevice

NUM_CORES_CORTEX_A9 = 2
CORTEX_A9_START_ID = 1
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

        self.exposeCores()

        self.setupCadiSyncSMP()
        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        cortexA9coreDev = 0
        self.cortexA9cores = []

        streamID = ATB_ID_BASE

        for i in range(0, NUM_CORES_CORTEX_A9):
            # create core
            dev = Device(self, i+CORTEX_A9_START_ID, "Cortex-A9_%d" % i)
            self.cortexA9cores.append(dev)

    def exposeCores(self):
        for core in self.cortexA9cores:
            self.addDeviceInterface(core)

    def setupCadiSyncSMP(self):
        '''Create SMP device using RDDI synchronization'''

        # create SMP device and expose from configuration
        # Cortex-A9x2 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A9 SMP", self.cortexA9cores)
        self.addDeviceInterface(smp)

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


