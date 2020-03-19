# Copyright (C) 2017-2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import Device

coreNames = ["V8M-Generic"]
dapIndices = [0]
ctiNames = [None]
ctiCoreTriggers = [None]
ctiMacrocellTriggers = [None]
macrocellNames = [None]
funnelNames = [None]
funnelPorts = [None]
coreNames_v8MGeneric = ["V8M-Generic"]


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

        self.AHB_Ms = []

        ap = CortexM_AHBAP(self, self.findDevice("CSMEMAP"), "AHB_M_0")
        self.mgdPlatformDevs.append(ap)
        self.AHB_Ms.append(ap)

        self.v8MGenericcores = []
        for core in range(len(coreNames_v8MGeneric)):
            # Create core
            coreDevice = Device(self, self.findDevice(coreNames_v8MGeneric[core]), coreNames_v8MGeneric[core])
            self.v8MGenericcores.append(coreDevice)

    def registerFilters(self, core, dap):
        '''Register MemAP filters to allow access to the APs for the device'''
        if dap == 0:
            core.registerAddressFilters([
                AHBCortexMMemAPAccessor("AHB_M_0", self.AHB_Ms[0], "AHB-M bus accessed via AP 0 (CSMEMAP)"),
            ])

    def exposeCores(self):
        '''Ensure that cores have access to memory'''
        for i in range(len(coreNames)):
            core = self.getDeviceInterface(coreNames[i])
            self.registerFilters(core, dapIndices[i])
            self.addDeviceInterface(core)

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        if not self.isConnected():
            try:
                self.setInitialOptions()
            except:
                pass
        self.updateDynamicOptions()

    def setInitialOptions(self):
        '''Set the initial options'''

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

class DtslScript_DSTREAM_ST(DtslScript):
    @staticmethod
    def getOptionList():
        return DtslScript.getOptionList()

class DtslScript_DSTREAM_PT(DtslScript):
    @staticmethod
    def getOptionList():
        return DtslScript.getOptionList()
