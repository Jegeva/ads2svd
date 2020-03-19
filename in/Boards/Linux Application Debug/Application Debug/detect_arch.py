''' Copyright (C) 2016,2019 Arm Limited (or its affiliates). All rights reserved.
'''
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.rddi import RDDI_CAP_ID

from com.arm.debug.dtsl.interfaces import IDevice

from com.arm.debug.dtsl.rddi import DeviceRegisterInfo
from com.arm.debug.core.interfaces.engine import DebugException

from com.arm.debug.dtsl.configurations import ConfigurationBase

from inspect import getmembers


from com.arm.debug.dtsl import DTSLException
import os.path
from java.lang import StringBuilder
from java.lang import String
import re

from com.arm.debug.dtsl.interfaces import IDeviceInfo

# Need to dynamically determine whether or not the remote has SVE or no
class DeviceInfo(IDeviceInfo):

    def __init__(self, device):
        self.device = device

    def getDeviceClass(self):
        return "core"

    def getType(self):
        pcSize = self.device.getRegisterSize("PC")
        # Check connected to an AArch64 target
        if pcSize != 64:
            raise DTSLException("Unsupported PC size of %d bits " % pcSize)
        else:
            return "GDBServerPseudoCoreAArch64"

class LinuxApp(DTSLv1):

    def __init__(self, root):
        DTSLv1.__init__(self, root)

    def addDevice(self, device):
        DTSLv1.addDevice(self, device)
        device.setDeviceInfo(DeviceInfo(device))



