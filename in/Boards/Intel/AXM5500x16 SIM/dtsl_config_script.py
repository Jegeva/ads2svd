from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import PVCacheDevice
from com.arm.debug.dtsl.components import PVCacheMemoryAccessor
from com.arm.debug.dtsl.components import PVCacheMemoryCapabilities
from com.arm.debug.dtsl.components import ConnectableDevice
from com.arm.debug.dtsl.components import CadiSyncSMPDevice
from com.arm.debug.dtsl.components import DeviceCluster
from java.lang import StringBuilder

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

        self.cores["AxxiaV7Model.cluster0.cpu0"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu0$"), "ARM_Cortex-A15_0" )
        self.cores["AxxiaV7Model.cluster0.cpu1"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu1$"), "ARM_Cortex-A15_1" )
        self.cores["AxxiaV7Model.cluster0.cpu2"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu2$"), "ARM_Cortex-A15_2" )
        self.cores["AxxiaV7Model.cluster0.cpu3"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu3$"), "ARM_Cortex-A15_3" )
        self.cores["AxxiaV7Model.cluster1.cpu0"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu0$"), "ARM_Cortex-A15_4" )
        self.cores["AxxiaV7Model.cluster1.cpu1"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu1$"), "ARM_Cortex-A15_5" )
        self.cores["AxxiaV7Model.cluster1.cpu2"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu2$"), "ARM_Cortex-A15_6" )
        self.cores["AxxiaV7Model.cluster1.cpu3"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu3$"), "ARM_Cortex-A15_7" )
        self.cores["AxxiaV7Model.cluster2.cpu0"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu0$"), "ARM_Cortex-A15_8" )
        self.cores["AxxiaV7Model.cluster2.cpu1"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu1$"), "ARM_Cortex-A15_9" )
        self.cores["AxxiaV7Model.cluster2.cpu2"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu2$"), "ARM_Cortex-A15_10" )
        self.cores["AxxiaV7Model.cluster2.cpu3"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu3$"), "ARM_Cortex-A15_11" )
        self.cores["AxxiaV7Model.cluster3.cpu0"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu0$"), "ARM_Cortex-A15_12" )
        self.cores["AxxiaV7Model.cluster3.cpu1"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu1$"), "ARM_Cortex-A15_13" )
        self.cores["AxxiaV7Model.cluster3.cpu2"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu2$"), "ARM_Cortex-A15_14" )
        self.cores["AxxiaV7Model.cluster3.cpu3"] = ConnectableDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu3$"), "ARM_Cortex-A15_15" )

        self.cluster0cores = []

        self.cluster0cores.append(self.cores["AxxiaV7Model.cluster0.cpu0"])
        self.cluster0cores.append(self.cores["AxxiaV7Model.cluster0.cpu1"])
        self.cluster0cores.append(self.cores["AxxiaV7Model.cluster0.cpu2"])
        self.cluster0cores.append(self.cores["AxxiaV7Model.cluster0.cpu3"])


        self.cluster1cores = []

        self.cluster1cores.append(self.cores["AxxiaV7Model.cluster1.cpu0"])
        self.cluster1cores.append(self.cores["AxxiaV7Model.cluster1.cpu1"])
        self.cluster1cores.append(self.cores["AxxiaV7Model.cluster1.cpu2"])
        self.cluster1cores.append(self.cores["AxxiaV7Model.cluster1.cpu3"])


        self.cluster2cores = []

        self.cluster2cores.append(self.cores["AxxiaV7Model.cluster2.cpu0"])
        self.cluster2cores.append(self.cores["AxxiaV7Model.cluster2.cpu1"])
        self.cluster2cores.append(self.cores["AxxiaV7Model.cluster2.cpu2"])
        self.cluster2cores.append(self.cores["AxxiaV7Model.cluster2.cpu3"])


        self.cluster3cores = []

        self.cluster3cores.append(self.cores["AxxiaV7Model.cluster3.cpu0"])
        self.cluster3cores.append(self.cores["AxxiaV7Model.cluster3.cpu1"])
        self.cluster3cores.append(self.cores["AxxiaV7Model.cluster3.cpu2"])
        self.cluster3cores.append(self.cores["AxxiaV7Model.cluster3.cpu3"])


        self.caches = dict()

        self.caches["AxxiaV7Model.cluster0.cpu0.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu0\\.l1icache$"), "l1icache_0")
        self.caches["AxxiaV7Model.cluster0.cpu0.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu0\\.l1dcache$"), "l1dcache_0")
        self.caches["AxxiaV7Model.cluster0.cpu1.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu1\\.l1icache$"), "l1icache_1")
        self.caches["AxxiaV7Model.cluster0.cpu1.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu1\\.l1dcache$"), "l1dcache_1")
        self.caches["AxxiaV7Model.cluster0.cpu2.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu2\\.l1icache$"), "l1icache_2")
        self.caches["AxxiaV7Model.cluster0.cpu2.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu2\\.l1dcache$"), "l1dcache_2")
        self.caches["AxxiaV7Model.cluster0.cpu3.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu3\\.l1icache$"), "l1icache_3")
        self.caches["AxxiaV7Model.cluster0.cpu3.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.cpu3\\.l1dcache$"), "l1dcache_3")
        self.caches["AxxiaV7Model.cluster0.l2_cache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster0\\.l2_cache$"), "l2_cache$")
        self.caches["AxxiaV7Model.cluster1.cpu0.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu0\\.l1icache$"), "l1icache_0")
        self.caches["AxxiaV7Model.cluster1.cpu0.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu0\\.l1dcache$"), "l1dcache_0")
        self.caches["AxxiaV7Model.cluster1.cpu1.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu1\\.l1icache$"), "l1icache_1")
        self.caches["AxxiaV7Model.cluster1.cpu1.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu1\\.l1dcache$"), "l1dcache_1")
        self.caches["AxxiaV7Model.cluster1.cpu2.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu2\\.l1icache$"), "l1icache_2")
        self.caches["AxxiaV7Model.cluster1.cpu2.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu2\\.l1dcache$"), "l1dcache_2")
        self.caches["AxxiaV7Model.cluster1.cpu3.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu3\\.l1icache$"), "l1icache_3")
        self.caches["AxxiaV7Model.cluster1.cpu3.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.cpu3\\.l1dcache$"), "l1dcache_3")
        self.caches["AxxiaV7Model.cluster1.l2_cache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster1\\.l2_cache$"), "l2_cache$")
        self.caches["AxxiaV7Model.cluster2.cpu0.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu0\\.l1icache$"), "l1icache_0")
        self.caches["AxxiaV7Model.cluster2.cpu0.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu0\\.l1dcache$"), "l1dcache_0")
        self.caches["AxxiaV7Model.cluster2.cpu1.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu1\\.l1icache$"), "l1icache_1")
        self.caches["AxxiaV7Model.cluster2.cpu1.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu1\\.l1dcache$"), "l1dcache_1")
        self.caches["AxxiaV7Model.cluster2.cpu2.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu2\\.l1icache$"), "l1icache_2")
        self.caches["AxxiaV7Model.cluster2.cpu2.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu2\\.l1dcache$"), "l1dcache_2")
        self.caches["AxxiaV7Model.cluster2.cpu3.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu3\\.l1icache$"), "l1icache_3")
        self.caches["AxxiaV7Model.cluster2.cpu3.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.cpu3\\.l1dcache$"), "l1dcache_3")
        self.caches["AxxiaV7Model.cluster2.l2_cache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster2\\.l2_cache$"), "l2_cache$")
        self.caches["AxxiaV7Model.cluster3.cpu0.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu0\\.l1icache$"), "l1icache_0")
        self.caches["AxxiaV7Model.cluster3.cpu0.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu0\\.l1dcache$"), "l1dcache_0")
        self.caches["AxxiaV7Model.cluster3.cpu1.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu1\\.l1icache$"), "l1icache_1")
        self.caches["AxxiaV7Model.cluster3.cpu1.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu1\\.l1dcache$"), "l1dcache_1")
        self.caches["AxxiaV7Model.cluster3.cpu2.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu2\\.l1icache$"), "l1icache_2")
        self.caches["AxxiaV7Model.cluster3.cpu2.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu2\\.l1dcache$"), "l1dcache_2")
        self.caches["AxxiaV7Model.cluster3.cpu3.l1icache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu3\\.l1icache$"), "l1icache_3")
        self.caches["AxxiaV7Model.cluster3.cpu3.l1dcache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.cpu3\\.l1dcache$"), "l1dcache_3")
        self.caches["AxxiaV7Model.cluster3.l2_cache"] = PVCacheDevice(self, self.findDeviceRegex(".*AxxiaV7Model\\.cluster3\\.l2_cache$"), "l2_cache$")

        self.addManagedPlatformDevices(self.caches.values())

        self.addPVCache(self.cores["AxxiaV7Model.cluster0.cpu0"], self.caches["AxxiaV7Model.cluster0.cpu0.l1icache"], self.caches["AxxiaV7Model.cluster0.cpu0.l1dcache"], self.caches["AxxiaV7Model.cluster0.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster0.cpu1"], self.caches["AxxiaV7Model.cluster0.cpu1.l1icache"], self.caches["AxxiaV7Model.cluster0.cpu1.l1dcache"], self.caches["AxxiaV7Model.cluster0.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster0.cpu2"], self.caches["AxxiaV7Model.cluster0.cpu2.l1icache"], self.caches["AxxiaV7Model.cluster0.cpu2.l1dcache"], self.caches["AxxiaV7Model.cluster0.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster0.cpu3"], self.caches["AxxiaV7Model.cluster0.cpu3.l1icache"], self.caches["AxxiaV7Model.cluster0.cpu3.l1dcache"], self.caches["AxxiaV7Model.cluster0.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster1.cpu0"], self.caches["AxxiaV7Model.cluster1.cpu0.l1icache"], self.caches["AxxiaV7Model.cluster1.cpu0.l1dcache"], self.caches["AxxiaV7Model.cluster1.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster1.cpu1"], self.caches["AxxiaV7Model.cluster1.cpu1.l1icache"], self.caches["AxxiaV7Model.cluster1.cpu1.l1dcache"], self.caches["AxxiaV7Model.cluster1.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster1.cpu2"], self.caches["AxxiaV7Model.cluster1.cpu2.l1icache"], self.caches["AxxiaV7Model.cluster1.cpu2.l1dcache"], self.caches["AxxiaV7Model.cluster1.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster1.cpu3"], self.caches["AxxiaV7Model.cluster1.cpu3.l1icache"], self.caches["AxxiaV7Model.cluster1.cpu3.l1dcache"], self.caches["AxxiaV7Model.cluster1.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster2.cpu0"], self.caches["AxxiaV7Model.cluster2.cpu0.l1icache"], self.caches["AxxiaV7Model.cluster2.cpu0.l1dcache"], self.caches["AxxiaV7Model.cluster2.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster2.cpu1"], self.caches["AxxiaV7Model.cluster2.cpu1.l1icache"], self.caches["AxxiaV7Model.cluster2.cpu1.l1dcache"], self.caches["AxxiaV7Model.cluster2.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster2.cpu2"], self.caches["AxxiaV7Model.cluster2.cpu2.l1icache"], self.caches["AxxiaV7Model.cluster2.cpu2.l1dcache"], self.caches["AxxiaV7Model.cluster2.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster2.cpu3"], self.caches["AxxiaV7Model.cluster2.cpu3.l1icache"], self.caches["AxxiaV7Model.cluster2.cpu3.l1dcache"], self.caches["AxxiaV7Model.cluster2.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster3.cpu0"], self.caches["AxxiaV7Model.cluster3.cpu0.l1icache"], self.caches["AxxiaV7Model.cluster3.cpu0.l1dcache"], self.caches["AxxiaV7Model.cluster3.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster3.cpu1"], self.caches["AxxiaV7Model.cluster3.cpu1.l1icache"], self.caches["AxxiaV7Model.cluster3.cpu1.l1dcache"], self.caches["AxxiaV7Model.cluster3.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster3.cpu2"], self.caches["AxxiaV7Model.cluster3.cpu2.l1icache"], self.caches["AxxiaV7Model.cluster3.cpu2.l1dcache"], self.caches["AxxiaV7Model.cluster3.l2_cache"])
        self.addPVCache(self.cores["AxxiaV7Model.cluster3.cpu3"], self.caches["AxxiaV7Model.cluster3.cpu3.l1icache"], self.caches["AxxiaV7Model.cluster3.cpu3.l1dcache"], self.caches["AxxiaV7Model.cluster3.l2_cache"])


    def exposeCores(self):
        '''Expose cores'''
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster0.cpu0"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster0.cpu1"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster2.cpu2"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster2.cpu3"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster3.cpu0"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster3.cpu1"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster3.cpu2"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster3.cpu3"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster0.cpu2"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster0.cpu3"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster1.cpu0"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster1.cpu1"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster1.cpu2"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster1.cpu3"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster2.cpu0"])
        self.addDeviceInterface(self.cores["AxxiaV7Model.cluster2.cpu1"])


    def setupCadiSyncSMP(self):
        '''Create SMP device using RDDI synchronization'''

        # Create SMP device and expose from configuration
        # cluster0 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A15x4_0 SMP", self.cluster0cores)
        self.addDeviceInterface(smp)

        # cluster1 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A15x4_1 SMP", self.cluster1cores)
        self.addDeviceInterface(smp)

        # cluster2 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A15x4_2 SMP", self.cluster2cores)
        self.addDeviceInterface(smp)

        # cluster3 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A15x4_3 SMP", self.cluster3cores)
        self.addDeviceInterface(smp)

        # MULTI CLUSTER SMP
        clusters = [ DeviceCluster("cluster0", self.cluster0cores), DeviceCluster("cluster1", self.cluster1cores), DeviceCluster("cluster2", self.cluster2cores), DeviceCluster("cluster3", self.cluster3cores) ]
        smp = CadiSyncSMPDevice(self, "Cortex-A15 SMP", clusters)
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

    def confirmDeviceType(self, num, unique):
        '''Attempts to match the unique string inside the details from GetDeviceDetails '''
        devDetails = StringBuilder(256)
        self.getDebug().getDeviceDetails(num, None, devDetails)
        if unique in devDetails.toString():
            return True
        return False

    def countCores(self, coreName):
        devDetails = StringBuilder(256)
        cores = 0
        count = self.getDebug().getDeviceCount()
        for d in range(count):
            if self.confirmDeviceType(d+1, coreName):
                cores += 1
        return cores

    def verify(self):
        if self.confirmDeviceType(1,"device=AXM5500,") == False:
            return False
        return self.countCores("type=Core, device=ARM_Cortex-A15") == 16
