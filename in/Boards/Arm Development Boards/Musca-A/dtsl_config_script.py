# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.components import CSCTI

from struct import pack, unpack
from jarray import array, zeros
from java.lang import Byte
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE

coreNames_cortexM33 = ["Cortex-M33_0", "Cortex-M33_1"]

class CacheMaintCore(Device):
    def __init__(self, config, id, name, clearCPUWAITRegOnConnect=False):
        Device.__init__(self, config, id, name)
        self.clearCPUWAITRegOnConnect = clearCPUWAITRegOnConnect

    def to_s8(self, val):
        return val > 127 and val - 256 or val

    def openConn(self, pId, pVersion, pMessage):
        Device.openConn(self, pId, pVersion, pMessage)
        if self.clearCPUWAITRegOnConnect:
            buf = zeros(4,'b')
            self.memWrite(0x0, 0x50021118, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)

    def memRead(self, page, address, size, rule, count, pDataOut):
        Device.memRead(self, page, address, size, rule, count, pDataOut)

    def __invalidate_Icache(self):
        buf = zeros(4,'b')
        # Read I cache control register
        Device.memRead(self, 0x0, 0x50010004, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)

        # If I cache is enabled, invalidate all
        if buf[0] & 0x1:
            buf[0] = buf[0] | 0x4
            self.memWrite(0x0,  0x50010004, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)

    def setSWBreak(self, page, addr, flags):
        brkID = Device.setSWBreak(self, page, addr, flags)
        self.__invalidate_Icache()
        return brkID

    def memWrite(self, page, addr, size, rule, check, count, data):
        Device.memWrite(self, page, addr, size, rule, check, count, data)

class DtslScript(ConfigurationBaseSDF):

    @staticmethod
    def getOptionCTISyncPage():
        return DTSLv1.tabPage("sync", "CTI Synchronization", childOptions=[
                    DTSLv1.booleanOption(coreNames_cortexM33[0], coreNames_cortexM33[0], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption(coreNames_cortexM33[1], coreNames_cortexM33[1], description="Add core to synchronization group", defaultValue=False, isDynamic=True),
                ])

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionCTISyncPage()
            ])
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
        APBAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        CortexM_AHBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        CortexM_AHBAP(self, self.findDevice("CSMEMAP_2"), "CSMEMAP_2")

        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSCTI_1"), "CSCTI_1")

        self.cortexM33cores = []
        for coreName in (coreNames_cortexM33):
            # Create core
            if coreName == "Cortex-M33_1":
                coreDevice = CacheMaintCore(self, self.findDevice(coreName), coreName, True)
            else:
                coreDevice = CacheMaintCore(self, self.findDevice(coreName), coreName)
            self.cortexM33cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)

            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
                self.registerCoreForCrossSync(coreDevice)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_0"), "APB bus accessed via AP 0 (CSMEMAP_0)"),
            AHBCortexMMemAPAccessor("AHB_M_0", self.getDeviceInterface("CSMEMAP_1"), "AHB-M bus accessed via AP 1 (CSMEMAP_1)"),
            AHBCortexMMemAPAccessor("AHB_M_1", self.getDeviceInterface("CSMEMAP_2"), "AHB-M bus accessed via AP 2 (CSMEMAP_2)"),
        ])

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        for core in range(len(self.cortexM33cores)):
            enable = self.getOptionValue('options.sync.%s' % coreNames_cortexM33[core])
            self.setCrossSyncEnabled(self.cortexM33cores[core], enable)

    def addDeviceInterface(self, device):
        '''Add the device to the configuration and register its address filters'''
        ConfigurationBase.addDeviceInterface(self, device)
        self.registerFilters(device)
