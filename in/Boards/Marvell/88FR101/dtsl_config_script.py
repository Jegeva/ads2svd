from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device

coreDevs_aRM966ES = ["Debug 88FR101"]
NUM_CORES_ARM966E_S = 1


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.exposeCores()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        self.aRM966EScores = []

        for core in range(NUM_CORES_ARM966E_S):
            # Create core
            coreDevice = Device(self, self.findDevice(coreDevs_aRM966ES[core]), coreDevs_aRM966ES[core])
            self.aRM966EScores.append(coreDevice)

    def exposeCores(self):
        for core in self.aRM966EScores:
            self.addDeviceInterface(core)

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

class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return [
        ]

