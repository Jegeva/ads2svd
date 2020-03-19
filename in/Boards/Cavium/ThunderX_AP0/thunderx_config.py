from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import DSTREAMCacheAccessor
from com.arm.debug.dtsl.components import InternalRAMMapper
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CacheInfo
from com.arm.debug.dtsl import DTSLException
from com.arm.debug.dtsl.nativelayer import NativeException
from com.arm.rddi import RDDI

CFG_SET_EXT_AP_TAR = "SET_EXT_AP_TAR"
CFG_EXT_AP_TAR_VALUE = "EXT_AP_TAR_VALUE"
CFG_SET_MDSCR_MDE = "SET_MDSCR_MDE"
CFG_ENABLE_ISB_HAZARD = "ENABLE_ISB_HAZARD"


CFG_CACHE_DEBUG_MODE = "CACHE_DEBUG_MODE"
CFG_CACHE_PRESERVATION_MODE = "CACHE_PRESERVATION_MODE"

class ThunderXCoreDevice(Device):
    '''Extend device to set configuration item after connecting'''

    def __init__(self, configuration, deviceNumber, name):
        Device.__init__(self, configuration, deviceNumber, name)
        self.postConnectConfig = {}
        self.isConnected = False

    def openConn(self, pId, pVersion, pMessage):
        Device.openConn(self, pId, pVersion, pMessage)
        for k, v in self.postConnectConfig.items():
            try:
                self.setConfig(k, v)
            except NativeException, e:
                # ignore missing config item on older firmware
                if e.getRDDIErrorCode() != RDDI.RDDI_ITEMNOTSUP:
                    raise
        self.isConnected = True

    def closeConn(self):
        self.isConnected = False
        Device.closeConn(self)

    def addPostConnectConfigItem(self, name, value):
        self.postConnectConfig[name] = value

    def setConfigWhenConnected(self, name, value):
        self.addPostConnectConfigItem(name, value)
        if self.isConnected:
            self.setConfig(name, value)

# not needed in TX - keep for future reference
RAM_LIST = ["L1-I_TAG", "L1-I_DATA", "L1-D_TAG", "L1-D_DATA", "L1_TLB" ]

def registerInternalRAMs(core, underlyingMemoryDevice=None):
    addressFilters = []
    mapper = InternalRAMMapper(core)
    for ram in RAM_LIST:
        # Change the name to an address space friendly one
        addressFilters.append(DSTREAMCacheAccessor(core, mapper, ram.replace("-", "_")))
    # Register all the new accessors with the device
    core.registerAddressFilters(addressFilters)
    cacheInfo = CacheInfo()
    if not underlyingMemoryDevice is None:
        cacheInfo.setUnderlyingMemory(underlyingMemoryDevice)
    else:
        cacheInfo.setUnderlyingMemory(core)
    core.setCacheInfo(cacheInfo)


def applyBoolOptions(configuration, device, optionName, cfgItem):
    # Convert from a boolean to "1" or "0" for required by the config item
    stringValue = "1" if (configuration.getOptionValue(optionName)) else "0"
    try:
        device.setConfigWhenConnected(cfgItem, stringValue)
    except NativeException, e:
        # ignore missing config item on older firmware
        if e.getRDDIErrorCode() != RDDI.RDDI_ITEMNOTSUP:
            raise

def applyHexOptions(configuration, device, optionName, cfgItem):
    # Convert from a boolean to "1" or "0" for required by the config item
    stringValue = hex(configuration.getOptionValue(optionName))
    try:
        device.setConfigWhenConnected(cfgItem, stringValue)
    except NativeException, e:
        # ignore missing config item on older firmware
        if e.getRDDIErrorCode() != RDDI.RDDI_ITEMNOTSUP:
            raise

# not needed in TX - keep for future reference
def applyCacheDebug(configuration, optionName, device):
    applyOptions(configuration, device, optionName, CFG_CACHE_DEBUG_MODE)

# not needed in TX - keep for future reference
def applyCachePreservation(configuration, optionName, device):
    applyBoolOptions(configuration, device, optionName, CFG_CACHE_PRESERVATION_MODE)

def applyMDSCRMDE(configuration, optionName, device):
    applyBoolOptions(configuration, device, optionName, CFG_SET_MDSCR_MDE)

def applyEnableISBHazard(configuration, optionName, device):
    applyBoolOptions(configuration, device, optionName, CFG_ENABLE_ISB_HAZARD)

def applyExtAPTAR(configuration, optionName, device):
    applyBoolOptions(configuration, device, optionName, CFG_SET_EXT_AP_TAR)

def applyExtAPTARValue(configuration, optionName, device):
    applyHexOptions(configuration, device, optionName, CFG_EXT_AP_TAR_VALUE)