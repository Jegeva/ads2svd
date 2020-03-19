# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceInfo
from com.arm.debug.dtsl.configurations import ConfigurationBase

coreNames_cortexM3 = ["Cortex-M3"]
coreNames_cortexA9 = ["Cortex-A9"]



class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
        ]

    def __init__(self, root):
        ConfigurationBaseSDF.__init__(self, root)

        self.discoverDevices()

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        #MemAp devices
        CortexM_AHBAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        AHBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        APBAP(self, self.findDevice("CSMEMAP_2"), "CSMEMAP_2")

        self.cortexM3cores = []
        for coreName in (coreNames_cortexM3):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-M3")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexM3cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)

        self.cortexA9cores = []
        for coreName in (coreNames_cortexA9):
            # Create core
            coreDevice = Device(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-A9")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexA9cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB", self.getDeviceInterface("CSMEMAP_1"), "AHB bus accessed via AP 0 (CSMEMAP_1)"),
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_2"), "APB bus accessed via AP 1 (CSMEMAP_2)"),
            AHBCortexMMemAPAccessor("AHB_M", self.getDeviceInterface("CSMEMAP_0"), "AHB-M bus accessed via AP 0 (CSMEMAP_0)"),
        ])

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

    def addDeviceInterface(self, device):
        '''Add the device to the configuration and register its address filters'''
        ConfigurationBase.addDeviceInterface(self, device)
        self.registerFilters(device)

class DtslScript_DSTREAM_ST(DtslScript):
    @staticmethod
    def getOptionList():
        return [
        ]

class DtslScript_DSTREAM_PT(DtslScript):
    @staticmethod
    def getOptionList():
        return [
        ]

class DtslScript_DebugAndOnChipTrace(DtslScript):
    @staticmethod
    def getOptionList():
        return [
        ]

