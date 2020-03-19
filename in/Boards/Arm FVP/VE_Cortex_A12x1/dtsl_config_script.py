from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device

NUM_CORES_CORTEX_A12 = 1
CORTEX_A12_START_ID = 1
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

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        cortexA12coreDev = 0
        self.cortexA12cores = []

        streamID = ATB_ID_BASE

        for i in range(0, NUM_CORES_CORTEX_A12):
            # create core
            dev = Device(self, i+CORTEX_A12_START_ID, "Cortex-A12_%d" % i)
            self.cortexA12cores.append(dev)

    def exposeCores(self):
        for core in self.cortexA12cores:
            self.addDeviceInterface(core)

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


