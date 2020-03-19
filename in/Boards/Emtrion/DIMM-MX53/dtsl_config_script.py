from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import GenericDevice
from com.arm.debug.dtsl.components import Device

NUM_CORES_CORTEX_A8 = 1


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # only AHB/APB are managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB)
        self.mgdPlatformDevs.add(self.APB)

        self.exposeCores()

        self.setManagedDevices(self.mgdPlatformDevs)

    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        cortexA8coreDev = 0
        self.cortexA8cores = []

        for i in range(0, NUM_CORES_CORTEX_A8):
            # create core
            cortexA8coreDev = self.findDevice("Cortex-A8", cortexA8coreDev+1)
            dev = Device(self, cortexA8coreDev, "Cortex-A8_%d" % i)
            self.cortexA8cores.append(dev)

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the set of devices managed by the configuration'''
        for d in devs:
            self.mgdPlatformDevs.add(d)

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP_1")])

    def exposeCores(self):
        for core in self.cortexA8cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()

