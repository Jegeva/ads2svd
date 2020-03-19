from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CadiSyncSMPDevice
from com.arm.debug.dtsl.components import DeviceCluster



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

        self.cores["cluster.cpu0"] = Device(self, self.findDevice("cluster.cpu0"), "ARM_Cortex-A12_0" )
        self.cores["cluster.cpu1"] = Device(self, self.findDevice("cluster.cpu1"), "ARM_Cortex-A12_1" )
        self.cores["cluster.cpu2"] = Device(self, self.findDevice("cluster.cpu2"), "ARM_Cortex-A12_2" )

        self.cluster0cores = []

        self.cluster0cores.append(self.cores["cluster.cpu0"])
        self.cluster0cores.append(self.cores["cluster.cpu1"])
        self.cluster0cores.append(self.cores["cluster.cpu2"])


    def exposeCores(self):
        '''Expose cores'''
        self.addDeviceInterface(self.cores["cluster.cpu0"])
        self.addDeviceInterface(self.cores["cluster.cpu1"])
        self.addDeviceInterface(self.cores["cluster.cpu2"])


    def setupCadiSyncSMP(self):
        '''Create SMP device using RDDI synchronization'''

        # Create SMP device and expose from configuration
        # cluster0 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A12x3 SMP0", self.cluster0cores)
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


