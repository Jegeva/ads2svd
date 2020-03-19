# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceInfo
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.components import CSCTI

clusterNames = ["Cortex-A5_SMP_0", "Cortex-A5_SMP_1"]
clusterCores = [["Cortex-A5_0", "Cortex-A5_1", "Cortex-A5_2", "Cortex-A5_3"], ["Cortex-A5_4"]]
coreNames_cortexA5 = ["Cortex-A5_0", "Cortex-A5_1", "Cortex-A5_2", "Cortex-A5_3", "Cortex-A5_4"]


# Import core specific functions
import a5_rams


class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                ])]
            )
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
        AXIAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        
        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSCTI_0"), "CSCTI_0")
        
        
        self.cortexA5cores = []
        for coreName in (coreNames_cortexA5):
            # Create core
            coreDevice = a5_rams.A5CoreDevice(self, self.findDevice(coreName), coreName)
            deviceInfo = DeviceInfo("core", "Cortex-A5")
            coreDevice.setDeviceInfo(deviceInfo)
            self.cortexA5cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            a5_rams.registerInternalRAMs(coreDevice)
            
            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
            
        self.setupCTISyncSMP()
        
    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AxBMemAPAccessor("APB", self.getDeviceInterface("CSMEMAP_0"), "APB bus accessed via AP 0 (CSMEMAP_0)"),
            AXIMemAPAccessor("AXI", self.getDeviceInterface("CSMEMAP_1"), "AXI bus accessed via AP 1 (CSMEMAP_1)", 64),
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
        
        for core in range(len(self.cortexA5cores)):
            a5_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA5cores[core])
        
    def addDeviceInterface(self, device):
        '''Add the device to the configuration and register its address filters'''
        ConfigurationBase.addDeviceInterface(self, device)
        self.registerFilters(device)
    
class DtslScript_DSTREAM_ST(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                ])]
            )
        ]

class DtslScript_DebugAndOnChipTrace(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                ])]
            )
        ]

