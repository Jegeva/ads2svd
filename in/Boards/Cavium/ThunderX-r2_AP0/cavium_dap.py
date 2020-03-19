from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl import DTSLException
from com.arm.debug.dtsl.nativelayer import NativeException
from com.arm.rddi import RDDI

# ID value for AP.TAR_63_32
TAR_63_32_ID = 2

class CaviumDAP(CSDAP):
    '''Extend device to set configuration item after connecting'''

    def __init__(self, configuration, deviceNumber, name):
        CSDAP.__init__(self, configuration, deviceNumber, name)
        self.TAR_63_32_value = 0x000000
        self.WriteTARExt = False
        self.isConnected = False

    def openConn(self, pId, pVersion, pMessage):
        CSDAP.openConn(self, pId, pVersion, pMessage)
        # if write tar ext set then write value to AP1 TAR[63:32]
        #if (self.WriteTARExt):
            # for some reason the DAP is not powered up at this point....
            #self.setConfig("DAP_POWER_UP","1")
            # now we can manipulate the AP
            #self.writeAPRegister(1,TAR_63_32_ID,self.TAR_63_32_value )
        self.isConnected = True

    def setConfig(self, pConfigName, pConfigValueIn):
        CSDAP.setConfig(self, pConfigName, pConfigValueIn)
        # if we see power up, and we are connected and we want to, write AP.TAR[63:32]
        if(pConfigName == "DAP_POWER_UP" and pConfigValueIn == "1" and self.isConnected and self.WriteTARExt):
            self.writeAPRegister(1,TAR_63_32_ID,self.TAR_63_32_value )

    def closeConn(self):
        self.isConnected = False
        CSDAP.closeConn(self)

    def setWriteTARFlag(self, setVal):
        self.WriteTARExt = setVal

    def setWriteTARValue(self, value):
        self.TAR_63_32_value = value
        # if we are on a live connection then write it now.
        if ( self.isConnected and self.WriteTARExt):
            self.writeAPRegister(1,TAR_63_32_ID,self.TAR_63_32_value )



def applyExtAPTAR(configuration, optionName, device):
    device.setWriteTARFlag(configuration.getOptionValue(optionName))
    #applyBoolOptions(configuration, device, optionName, CFG_SET_EXT_AP_TAR)

def applyExtAPTARValue(configuration, optionName, device):
    device.setWriteTARValue(configuration.getOptionValue(optionName))

    #applyHexOptions(configuration, device, optionName, CFG_EXT_AP_TAR_VALUE)