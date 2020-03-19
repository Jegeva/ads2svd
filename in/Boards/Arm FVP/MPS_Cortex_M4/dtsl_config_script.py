from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device



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

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        self.cores = dict()

        self.cores["coretile.core"] = Device(self, self.findDevice("coretile.core"), "ARM_Cortex-M4" )

    def exposeCores(self):
        '''Expose cores'''
        self.addDeviceInterface(self.cores["coretile.core"])


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


