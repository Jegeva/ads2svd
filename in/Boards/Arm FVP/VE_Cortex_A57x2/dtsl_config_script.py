from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import PVCacheDevice
from com.arm.debug.dtsl.components import PVCacheMemoryAccessor
from com.arm.debug.dtsl.components import PVCacheMemoryCapabilities
from com.arm.debug.dtsl.components import ConnectableDevice
from com.arm.debug.dtsl.components import CadiSyncSMPDevice
from com.arm.debug.dtsl.components import DeviceCluster

CONTENTS, TAGS = 0, 1


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.exposeCores()

        self.setupCadiSyncSMP()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        self.cores = dict()

        self.cores["cluster.cpu0"] = ConnectableDevice(self, self.findDevice("cluster.cpu0"), "ARM_Cortex-A57_0" )
        self.cores["cluster.cpu1"] = ConnectableDevice(self, self.findDevice("cluster.cpu1"), "ARM_Cortex-A57_1" )

        self.cluster0cores = []

        self.cluster0cores.append(self.cores["cluster.cpu0"])
        self.cluster0cores.append(self.cores["cluster.cpu1"])


        self.caches = dict()

        self.caches["cluster.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("cluster.cpu0.l1dcache"), "l1dcache_0")
        self.caches["cluster.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("cluster.cpu0.l1icache"), "l1icache_0")
        self.caches["cluster.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("cluster.cpu1.l1dcache"), "l1dcache_1")
        self.caches["cluster.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("cluster.cpu1.l1icache"), "l1icache_1")
        self.caches["cluster.l2_cache"] = PVCacheDevice(self, self.findDevice("cluster.l2_cache"), "l2_cache")

        self.addManagedPlatformDevices(self.caches.values())

        self.addPVCache(self.cores["cluster.cpu0"], self.caches["cluster.cpu0.l1icache"], self.caches["cluster.cpu0.l1dcache"], self.caches["cluster.l2_cache"])
        self.addPVCache(self.cores["cluster.cpu1"], self.caches["cluster.cpu1.l1icache"], self.caches["cluster.cpu1.l1dcache"], self.caches["cluster.l2_cache"])


    def exposeCores(self):
        '''Expose cores'''
        self.addDeviceInterface(self.cores["cluster.cpu0"])
        self.addDeviceInterface(self.cores["cluster.cpu1"])


    def setupCadiSyncSMP(self):
        '''Create SMP device using RDDI synchronization'''

        # Create SMP device and expose from configuration
        # cluster0 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A57x2 SMP0", self.cluster0cores)
        self.addDeviceInterface(smp)


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

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the list of devices managed by the configuration, as long as they are not already present'''
        for d in devs:
            if d not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(d)

    def addPVCache(self, dev, l1i, l1d, l2):
        '''Add cache devices'''

        rams = [
            (l1i, 'L1I', CONTENTS), (l1d, 'L1D', CONTENTS),
            (l1i, 'L1ITAG', TAGS), (l1d, 'L1DTAG', TAGS),
            (l2, 'L2', CONTENTS), (l2, 'L2TAG', TAGS)
        ]
        ramCapabilities = PVCacheMemoryCapabilities()
        for cacheDev, name, id in rams:
            cacheAcc = PVCacheMemoryAccessor(cacheDev, name, id)
            dev.registerAddressFilter(cacheAcc)
            ramCapabilities.addRAM(cacheAcc)
        dev.addCapabilities(ramCapabilities)


