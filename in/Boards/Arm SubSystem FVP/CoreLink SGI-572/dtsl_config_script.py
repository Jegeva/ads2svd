# Copyright (C) 2017-2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import PVCacheDevice
from com.arm.debug.dtsl.components import PVCacheMemoryAccessor
from com.arm.debug.dtsl.components import PVCacheMemoryCapabilities
from com.arm.debug.dtsl.components import ConnectableDevice
from com.arm.debug.dtsl.components import CadiSyncSMPDevice
from com.arm.debug.dtsl.components import DeviceCluster

CONTENTS, TAGS = 0, 1


class DtslScript(DTSLv1):

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Locate devices on the platform and create corresponding objects
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
        self.cores["css.scp.armcortexm7ct"] = ConnectableDevice(self, self.findDevice("css.scp.armcortexm7ct"), "ARM_Cortex-M7_1" )
        self.cores["css.mcp.armcortexm7ct"] = ConnectableDevice(self, self.findDevice("css.mcp.armcortexm7ct"), "ARM_Cortex-M7_0" )
        self.cores["css.cluster11.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster11.cpu0"), "ARM_Cortex-A72_44" )
        self.cores["css.cluster11.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster11.cpu1"), "ARM_Cortex-A72_45" )
        self.cores["css.cluster11.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster11.cpu2"), "ARM_Cortex-A72_46" )
        self.cores["css.cluster11.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster11.cpu3"), "ARM_Cortex-A72_47" )
        self.cores["css.cluster10.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster10.cpu0"), "ARM_Cortex-A72_40" )
        self.cores["css.cluster10.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster10.cpu1"), "ARM_Cortex-A72_41" )
        self.cores["css.cluster10.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster10.cpu2"), "ARM_Cortex-A72_42" )
        self.cores["css.cluster10.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster10.cpu3"), "ARM_Cortex-A72_43" )
        self.cores["css.cluster9.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster9.cpu0"), "ARM_Cortex-A72_36" )
        self.cores["css.cluster9.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster9.cpu1"), "ARM_Cortex-A72_37" )
        self.cores["css.cluster9.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster9.cpu2"), "ARM_Cortex-A72_38" )
        self.cores["css.cluster9.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster9.cpu3"), "ARM_Cortex-A72_39" )
        self.cores["css.cluster8.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster8.cpu0"), "ARM_Cortex-A72_32" )
        self.cores["css.cluster8.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster8.cpu1"), "ARM_Cortex-A72_33" )
        self.cores["css.cluster8.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster8.cpu2"), "ARM_Cortex-A72_34" )
        self.cores["css.cluster8.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster8.cpu3"), "ARM_Cortex-A72_35" )
        self.cores["css.cluster7.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster7.cpu0"), "ARM_Cortex-A72_28" )
        self.cores["css.cluster7.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster7.cpu1"), "ARM_Cortex-A72_29" )
        self.cores["css.cluster7.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster7.cpu2"), "ARM_Cortex-A72_30" )
        self.cores["css.cluster7.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster7.cpu3"), "ARM_Cortex-A72_31" )
        self.cores["css.cluster6.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster6.cpu0"), "ARM_Cortex-A72_24" )
        self.cores["css.cluster6.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster6.cpu1"), "ARM_Cortex-A72_25" )
        self.cores["css.cluster6.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster6.cpu2"), "ARM_Cortex-A72_26" )
        self.cores["css.cluster6.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster6.cpu3"), "ARM_Cortex-A72_27" )
        self.cores["css.cluster5.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster5.cpu0"), "ARM_Cortex-A72_20" )
        self.cores["css.cluster5.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster5.cpu1"), "ARM_Cortex-A72_21" )
        self.cores["css.cluster5.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster5.cpu2"), "ARM_Cortex-A72_22" )
        self.cores["css.cluster5.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster5.cpu3"), "ARM_Cortex-A72_23" )
        self.cores["css.cluster4.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster4.cpu0"), "ARM_Cortex-A72_16" )
        self.cores["css.cluster4.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster4.cpu1"), "ARM_Cortex-A72_17" )
        self.cores["css.cluster4.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster4.cpu2"), "ARM_Cortex-A72_18" )
        self.cores["css.cluster4.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster4.cpu3"), "ARM_Cortex-A72_19" )
        self.cores["css.cluster3.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster3.cpu0"), "ARM_Cortex-A72_12" )
        self.cores["css.cluster3.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster3.cpu1"), "ARM_Cortex-A72_13" )
        self.cores["css.cluster3.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster3.cpu2"), "ARM_Cortex-A72_14" )
        self.cores["css.cluster3.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster3.cpu3"), "ARM_Cortex-A72_15" )
        self.cores["css.cluster2.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster2.cpu0"), "ARM_Cortex-A72_8" )
        self.cores["css.cluster2.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster2.cpu1"), "ARM_Cortex-A72_9" )
        self.cores["css.cluster2.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster2.cpu2"), "ARM_Cortex-A72_10" )
        self.cores["css.cluster2.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster2.cpu3"), "ARM_Cortex-A72_11" )
        self.cores["css.cluster1.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster1.cpu0"), "ARM_Cortex-A72_4" )
        self.cores["css.cluster1.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster1.cpu1"), "ARM_Cortex-A72_5" )
        self.cores["css.cluster1.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster1.cpu2"), "ARM_Cortex-A72_6" )
        self.cores["css.cluster1.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster1.cpu3"), "ARM_Cortex-A72_7" )
        self.cores["css.cluster0.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster0.cpu0"), "ARM_Cortex-A72_0" )
        self.cores["css.cluster0.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster0.cpu1"), "ARM_Cortex-A72_1" )
        self.cores["css.cluster0.cpu2"] = ConnectableDevice(self, self.findDevice("css.cluster0.cpu2"), "ARM_Cortex-A72_2" )
        self.cores["css.cluster0.cpu3"] = ConnectableDevice(self, self.findDevice("css.cluster0.cpu3"), "ARM_Cortex-A72_3" )

        self.cluster11cores = []
        self.cluster11cores.append(self.cores["css.cluster11.cpu0"])
        self.cluster11cores.append(self.cores["css.cluster11.cpu1"])
        self.cluster11cores.append(self.cores["css.cluster11.cpu2"])
        self.cluster11cores.append(self.cores["css.cluster11.cpu3"])
        self.cluster10cores = []
        self.cluster10cores.append(self.cores["css.cluster10.cpu0"])
        self.cluster10cores.append(self.cores["css.cluster10.cpu1"])
        self.cluster10cores.append(self.cores["css.cluster10.cpu2"])
        self.cluster10cores.append(self.cores["css.cluster10.cpu3"])
        self.cluster9cores = []
        self.cluster9cores.append(self.cores["css.cluster9.cpu0"])
        self.cluster9cores.append(self.cores["css.cluster9.cpu1"])
        self.cluster9cores.append(self.cores["css.cluster9.cpu2"])
        self.cluster9cores.append(self.cores["css.cluster9.cpu3"])
        self.cluster8cores = []
        self.cluster8cores.append(self.cores["css.cluster8.cpu0"])
        self.cluster8cores.append(self.cores["css.cluster8.cpu1"])
        self.cluster8cores.append(self.cores["css.cluster8.cpu2"])
        self.cluster8cores.append(self.cores["css.cluster8.cpu3"])
        self.cluster7cores = []
        self.cluster7cores.append(self.cores["css.cluster7.cpu0"])
        self.cluster7cores.append(self.cores["css.cluster7.cpu1"])
        self.cluster7cores.append(self.cores["css.cluster7.cpu2"])
        self.cluster7cores.append(self.cores["css.cluster7.cpu3"])
        self.cluster6cores = []
        self.cluster6cores.append(self.cores["css.cluster6.cpu0"])
        self.cluster6cores.append(self.cores["css.cluster6.cpu1"])
        self.cluster6cores.append(self.cores["css.cluster6.cpu2"])
        self.cluster6cores.append(self.cores["css.cluster6.cpu3"])
        self.cluster5cores = []
        self.cluster5cores.append(self.cores["css.cluster5.cpu0"])
        self.cluster5cores.append(self.cores["css.cluster5.cpu1"])
        self.cluster5cores.append(self.cores["css.cluster5.cpu2"])
        self.cluster5cores.append(self.cores["css.cluster5.cpu3"])
        self.cluster4cores = []
        self.cluster4cores.append(self.cores["css.cluster4.cpu0"])
        self.cluster4cores.append(self.cores["css.cluster4.cpu1"])
        self.cluster4cores.append(self.cores["css.cluster4.cpu2"])
        self.cluster4cores.append(self.cores["css.cluster4.cpu3"])
        self.cluster3cores = []
        self.cluster3cores.append(self.cores["css.cluster3.cpu0"])
        self.cluster3cores.append(self.cores["css.cluster3.cpu1"])
        self.cluster3cores.append(self.cores["css.cluster3.cpu2"])
        self.cluster3cores.append(self.cores["css.cluster3.cpu3"])
        self.cluster2cores = []
        self.cluster2cores.append(self.cores["css.cluster2.cpu0"])
        self.cluster2cores.append(self.cores["css.cluster2.cpu1"])
        self.cluster2cores.append(self.cores["css.cluster2.cpu2"])
        self.cluster2cores.append(self.cores["css.cluster2.cpu3"])
        self.cluster1cores = []
        self.cluster1cores.append(self.cores["css.cluster1.cpu0"])
        self.cluster1cores.append(self.cores["css.cluster1.cpu1"])
        self.cluster1cores.append(self.cores["css.cluster1.cpu2"])
        self.cluster1cores.append(self.cores["css.cluster1.cpu3"])
        self.cluster0cores = []
        self.cluster0cores.append(self.cores["css.cluster0.cpu0"])
        self.cluster0cores.append(self.cores["css.cluster0.cpu1"])
        self.cluster0cores.append(self.cores["css.cluster0.cpu2"])
        self.cluster0cores.append(self.cores["css.cluster0.cpu3"])

        self.caches = dict()
        self.caches["css.cluster11.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster11.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster11.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster11.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster11.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster11.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster11.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster11.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster11.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster11.l2_cache"), "l2_cache")
        self.caches["css.cluster10.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster10.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster10.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster10.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster10.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster10.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster10.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster10.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster10.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster10.l2_cache"), "l2_cache")
        self.caches["css.cluster9.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster9.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster9.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster9.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster9.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster9.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster9.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster9.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster9.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster9.l2_cache"), "l2_cache")
        self.caches["css.cluster8.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster8.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster8.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster8.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster8.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster8.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster8.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster8.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster8.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster8.l2_cache"), "l2_cache")
        self.caches["css.cluster7.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster7.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster7.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster7.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster7.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster7.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster7.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster7.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster7.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster7.l2_cache"), "l2_cache")
        self.caches["css.cluster6.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster6.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster6.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster6.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster6.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster6.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster6.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster6.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster6.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster6.l2_cache"), "l2_cache")
        self.caches["css.cluster5.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster5.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster5.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster5.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster5.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster5.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster5.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster5.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster5.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster5.l2_cache"), "l2_cache")
        self.caches["css.cluster4.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster4.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster4.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster4.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster4.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster4.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster4.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster4.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster4.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster4.l2_cache"), "l2_cache")
        self.caches["css.cluster3.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster3.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster3.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster3.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster3.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster3.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster3.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster3.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster3.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster3.l2_cache"), "l2_cache")
        self.caches["css.cluster2.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster2.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster2.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster2.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster2.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster2.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster2.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster2.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster2.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster2.l2_cache"), "l2_cache")
        self.caches["css.cluster1.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster1.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster1.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster1.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster1.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster1.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster1.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster1.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster1.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster1.l2_cache"), "l2_cache")
        self.caches["css.cluster0.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster0.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster0.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster0.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster0.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu2.l1dcache"), "l1dcache_2")
        self.caches["css.cluster0.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu2.l1icache"), "l1icache_2")
        self.caches["css.cluster0.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu3.l1dcache"), "l1dcache_3")
        self.caches["css.cluster0.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu3.l1icache"), "l1icache_3")
        self.caches["css.cluster0.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster0.l2_cache"), "l2_cache")

        self.addManagedPlatformDevices(self.caches.values())

        self.addPVCache(self.cores["css.cluster11.cpu0"], self.caches["css.cluster11.cpu0.l1icache"], self.caches["css.cluster11.cpu0.l1dcache"], self.caches["css.cluster11.l2_cache"])
        self.addPVCache(self.cores["css.cluster11.cpu1"], self.caches["css.cluster11.cpu1.l1icache"], self.caches["css.cluster11.cpu1.l1dcache"], self.caches["css.cluster11.l2_cache"])
        self.addPVCache(self.cores["css.cluster11.cpu2"], self.caches["css.cluster11.cpu2.l1icache"], self.caches["css.cluster11.cpu2.l1dcache"], self.caches["css.cluster11.l2_cache"])
        self.addPVCache(self.cores["css.cluster11.cpu3"], self.caches["css.cluster11.cpu3.l1icache"], self.caches["css.cluster11.cpu3.l1dcache"], self.caches["css.cluster11.l2_cache"])
        self.addPVCache(self.cores["css.cluster10.cpu0"], self.caches["css.cluster10.cpu0.l1icache"], self.caches["css.cluster10.cpu0.l1dcache"], self.caches["css.cluster10.l2_cache"])
        self.addPVCache(self.cores["css.cluster10.cpu1"], self.caches["css.cluster10.cpu1.l1icache"], self.caches["css.cluster10.cpu1.l1dcache"], self.caches["css.cluster10.l2_cache"])
        self.addPVCache(self.cores["css.cluster10.cpu2"], self.caches["css.cluster10.cpu2.l1icache"], self.caches["css.cluster10.cpu2.l1dcache"], self.caches["css.cluster10.l2_cache"])
        self.addPVCache(self.cores["css.cluster10.cpu3"], self.caches["css.cluster10.cpu3.l1icache"], self.caches["css.cluster10.cpu3.l1dcache"], self.caches["css.cluster10.l2_cache"])
        self.addPVCache(self.cores["css.cluster9.cpu0"], self.caches["css.cluster9.cpu0.l1icache"], self.caches["css.cluster9.cpu0.l1dcache"], self.caches["css.cluster9.l2_cache"])
        self.addPVCache(self.cores["css.cluster9.cpu1"], self.caches["css.cluster9.cpu1.l1icache"], self.caches["css.cluster9.cpu1.l1dcache"], self.caches["css.cluster9.l2_cache"])
        self.addPVCache(self.cores["css.cluster9.cpu2"], self.caches["css.cluster9.cpu2.l1icache"], self.caches["css.cluster9.cpu2.l1dcache"], self.caches["css.cluster9.l2_cache"])
        self.addPVCache(self.cores["css.cluster9.cpu3"], self.caches["css.cluster9.cpu3.l1icache"], self.caches["css.cluster9.cpu3.l1dcache"], self.caches["css.cluster9.l2_cache"])
        self.addPVCache(self.cores["css.cluster8.cpu0"], self.caches["css.cluster8.cpu0.l1icache"], self.caches["css.cluster8.cpu0.l1dcache"], self.caches["css.cluster8.l2_cache"])
        self.addPVCache(self.cores["css.cluster8.cpu1"], self.caches["css.cluster8.cpu1.l1icache"], self.caches["css.cluster8.cpu1.l1dcache"], self.caches["css.cluster8.l2_cache"])
        self.addPVCache(self.cores["css.cluster8.cpu2"], self.caches["css.cluster8.cpu2.l1icache"], self.caches["css.cluster8.cpu2.l1dcache"], self.caches["css.cluster8.l2_cache"])
        self.addPVCache(self.cores["css.cluster8.cpu3"], self.caches["css.cluster8.cpu3.l1icache"], self.caches["css.cluster8.cpu3.l1dcache"], self.caches["css.cluster8.l2_cache"])
        self.addPVCache(self.cores["css.cluster7.cpu0"], self.caches["css.cluster7.cpu0.l1icache"], self.caches["css.cluster7.cpu0.l1dcache"], self.caches["css.cluster7.l2_cache"])
        self.addPVCache(self.cores["css.cluster7.cpu1"], self.caches["css.cluster7.cpu1.l1icache"], self.caches["css.cluster7.cpu1.l1dcache"], self.caches["css.cluster7.l2_cache"])
        self.addPVCache(self.cores["css.cluster7.cpu2"], self.caches["css.cluster7.cpu2.l1icache"], self.caches["css.cluster7.cpu2.l1dcache"], self.caches["css.cluster7.l2_cache"])
        self.addPVCache(self.cores["css.cluster7.cpu3"], self.caches["css.cluster7.cpu3.l1icache"], self.caches["css.cluster7.cpu3.l1dcache"], self.caches["css.cluster7.l2_cache"])
        self.addPVCache(self.cores["css.cluster6.cpu0"], self.caches["css.cluster6.cpu0.l1icache"], self.caches["css.cluster6.cpu0.l1dcache"], self.caches["css.cluster6.l2_cache"])
        self.addPVCache(self.cores["css.cluster6.cpu1"], self.caches["css.cluster6.cpu1.l1icache"], self.caches["css.cluster6.cpu1.l1dcache"], self.caches["css.cluster6.l2_cache"])
        self.addPVCache(self.cores["css.cluster6.cpu2"], self.caches["css.cluster6.cpu2.l1icache"], self.caches["css.cluster6.cpu2.l1dcache"], self.caches["css.cluster6.l2_cache"])
        self.addPVCache(self.cores["css.cluster6.cpu3"], self.caches["css.cluster6.cpu3.l1icache"], self.caches["css.cluster6.cpu3.l1dcache"], self.caches["css.cluster6.l2_cache"])
        self.addPVCache(self.cores["css.cluster5.cpu0"], self.caches["css.cluster5.cpu0.l1icache"], self.caches["css.cluster5.cpu0.l1dcache"], self.caches["css.cluster5.l2_cache"])
        self.addPVCache(self.cores["css.cluster5.cpu1"], self.caches["css.cluster5.cpu1.l1icache"], self.caches["css.cluster5.cpu1.l1dcache"], self.caches["css.cluster5.l2_cache"])
        self.addPVCache(self.cores["css.cluster5.cpu2"], self.caches["css.cluster5.cpu2.l1icache"], self.caches["css.cluster5.cpu2.l1dcache"], self.caches["css.cluster5.l2_cache"])
        self.addPVCache(self.cores["css.cluster5.cpu3"], self.caches["css.cluster5.cpu3.l1icache"], self.caches["css.cluster5.cpu3.l1dcache"], self.caches["css.cluster5.l2_cache"])
        self.addPVCache(self.cores["css.cluster4.cpu0"], self.caches["css.cluster4.cpu0.l1icache"], self.caches["css.cluster4.cpu0.l1dcache"], self.caches["css.cluster4.l2_cache"])
        self.addPVCache(self.cores["css.cluster4.cpu1"], self.caches["css.cluster4.cpu1.l1icache"], self.caches["css.cluster4.cpu1.l1dcache"], self.caches["css.cluster4.l2_cache"])
        self.addPVCache(self.cores["css.cluster4.cpu2"], self.caches["css.cluster4.cpu2.l1icache"], self.caches["css.cluster4.cpu2.l1dcache"], self.caches["css.cluster4.l2_cache"])
        self.addPVCache(self.cores["css.cluster4.cpu3"], self.caches["css.cluster4.cpu3.l1icache"], self.caches["css.cluster4.cpu3.l1dcache"], self.caches["css.cluster4.l2_cache"])
        self.addPVCache(self.cores["css.cluster3.cpu0"], self.caches["css.cluster3.cpu0.l1icache"], self.caches["css.cluster3.cpu0.l1dcache"], self.caches["css.cluster3.l2_cache"])
        self.addPVCache(self.cores["css.cluster3.cpu1"], self.caches["css.cluster3.cpu1.l1icache"], self.caches["css.cluster3.cpu1.l1dcache"], self.caches["css.cluster3.l2_cache"])
        self.addPVCache(self.cores["css.cluster3.cpu2"], self.caches["css.cluster3.cpu2.l1icache"], self.caches["css.cluster3.cpu2.l1dcache"], self.caches["css.cluster3.l2_cache"])
        self.addPVCache(self.cores["css.cluster3.cpu3"], self.caches["css.cluster3.cpu3.l1icache"], self.caches["css.cluster3.cpu3.l1dcache"], self.caches["css.cluster3.l2_cache"])
        self.addPVCache(self.cores["css.cluster2.cpu0"], self.caches["css.cluster2.cpu0.l1icache"], self.caches["css.cluster2.cpu0.l1dcache"], self.caches["css.cluster2.l2_cache"])
        self.addPVCache(self.cores["css.cluster2.cpu1"], self.caches["css.cluster2.cpu1.l1icache"], self.caches["css.cluster2.cpu1.l1dcache"], self.caches["css.cluster2.l2_cache"])
        self.addPVCache(self.cores["css.cluster2.cpu2"], self.caches["css.cluster2.cpu2.l1icache"], self.caches["css.cluster2.cpu2.l1dcache"], self.caches["css.cluster2.l2_cache"])
        self.addPVCache(self.cores["css.cluster2.cpu3"], self.caches["css.cluster2.cpu3.l1icache"], self.caches["css.cluster2.cpu3.l1dcache"], self.caches["css.cluster2.l2_cache"])
        self.addPVCache(self.cores["css.cluster1.cpu0"], self.caches["css.cluster1.cpu0.l1icache"], self.caches["css.cluster1.cpu0.l1dcache"], self.caches["css.cluster1.l2_cache"])
        self.addPVCache(self.cores["css.cluster1.cpu1"], self.caches["css.cluster1.cpu1.l1icache"], self.caches["css.cluster1.cpu1.l1dcache"], self.caches["css.cluster1.l2_cache"])
        self.addPVCache(self.cores["css.cluster1.cpu2"], self.caches["css.cluster1.cpu2.l1icache"], self.caches["css.cluster1.cpu2.l1dcache"], self.caches["css.cluster1.l2_cache"])
        self.addPVCache(self.cores["css.cluster1.cpu3"], self.caches["css.cluster1.cpu3.l1icache"], self.caches["css.cluster1.cpu3.l1dcache"], self.caches["css.cluster1.l2_cache"])
        self.addPVCache(self.cores["css.cluster0.cpu0"], self.caches["css.cluster0.cpu0.l1icache"], self.caches["css.cluster0.cpu0.l1dcache"], self.caches["css.cluster0.l2_cache"])
        self.addPVCache(self.cores["css.cluster0.cpu1"], self.caches["css.cluster0.cpu1.l1icache"], self.caches["css.cluster0.cpu1.l1dcache"], self.caches["css.cluster0.l2_cache"])
        self.addPVCache(self.cores["css.cluster0.cpu2"], self.caches["css.cluster0.cpu2.l1icache"], self.caches["css.cluster0.cpu2.l1dcache"], self.caches["css.cluster0.l2_cache"])
        self.addPVCache(self.cores["css.cluster0.cpu3"], self.caches["css.cluster0.cpu3.l1icache"], self.caches["css.cluster0.cpu3.l1dcache"], self.caches["css.cluster0.l2_cache"])


    def exposeCores(self):
        '''Expose cores'''
        self.addDeviceInterface(self.cores["css.scp.armcortexm7ct"])
        self.addDeviceInterface(self.cores["css.mcp.armcortexm7ct"])
        self.addDeviceInterface(self.cores["css.cluster11.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster11.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster11.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster11.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster10.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster10.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster10.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster10.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster9.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster9.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster9.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster9.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster8.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster8.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster8.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster8.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster7.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster7.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster7.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster7.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster6.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster6.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster6.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster6.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster5.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster5.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster5.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster5.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster4.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster4.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster4.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster4.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster3.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster3.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster3.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster3.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster2.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster2.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster2.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster2.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster1.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster1.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster1.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster1.cpu3"])
        self.addDeviceInterface(self.cores["css.cluster0.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster0.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster0.cpu2"])
        self.addDeviceInterface(self.cores["css.cluster0.cpu3"])


    def setupCadiSyncSMP(self):
        '''Create SMP device using CADI synchronization'''

        # cluster11 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 11", self.cluster11cores)
        self.addDeviceInterface(smp)

        # cluster10 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 10", self.cluster10cores)
        self.addDeviceInterface(smp)

        # cluster9 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 9", self.cluster9cores)
        self.addDeviceInterface(smp)

        # cluster8 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 8", self.cluster8cores)
        self.addDeviceInterface(smp)

        # cluster7 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 7", self.cluster7cores)
        self.addDeviceInterface(smp)

        # cluster6 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 6", self.cluster6cores)
        self.addDeviceInterface(smp)

        # cluster5 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 5", self.cluster5cores)
        self.addDeviceInterface(smp)

        # cluster4 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 4", self.cluster4cores)
        self.addDeviceInterface(smp)

        # cluster3 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 3", self.cluster3cores)
        self.addDeviceInterface(smp)

        # cluster2 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 2", self.cluster2cores)
        self.addDeviceInterface(smp)

        # cluster1 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 1", self.cluster1cores)
        self.addDeviceInterface(smp)

        # cluster0 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A72x4 SMP Cluster 0", self.cluster0cores)
        self.addDeviceInterface(smp)

        # MULTI CLUSTER SMP
        clusters = [ DeviceCluster("cluster0", self.cluster0cores), DeviceCluster("cluster1", self.cluster1cores), DeviceCluster("cluster2", self.cluster2cores), DeviceCluster("cluster3", self.cluster3cores), DeviceCluster("cluster4", self.cluster4cores), DeviceCluster("cluster5", self.cluster5cores), DeviceCluster("cluster6", self.cluster6cores), DeviceCluster("cluster7", self.cluster7cores), DeviceCluster("cluster8", self.cluster8cores), DeviceCluster("cluster9", self.cluster9cores), DeviceCluster("cluster10", self.cluster10cores), DeviceCluster("cluster11", self.cluster11cores) ]
        smp = CadiSyncSMPDevice(self, "MULTI CLUSTER SMP", clusters)
        self.addDeviceInterface(smp)


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
        # Currently no initial options
        pass

    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        # Currently no dynamic options
        pass

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the list of devices managed by the configuration, as long as they are not already present'''
        for d in devs:
            if d not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(d)

    def addPVCache(self, dev, l1i, l1d, l2=0):
        '''Add cache devices'''

        if l2 !=0:
            rams = [
                (l1i, 'L1I', CONTENTS), (l1d, 'L1D', CONTENTS),
                (l1i, 'L1ITAG', TAGS), (l1d, 'L1DTAG', TAGS),
                (l2, 'L2', CONTENTS), (l2, 'L2TAG', TAGS)
            ]
        else:
            rams = [
                (l1i, 'L1I', CONTENTS), (l1d, 'L1D', CONTENTS),
                (l1i, 'L1ITAG', TAGS), (l1d, 'L1DTAG', TAGS),
            ]
        ramCapabilities = PVCacheMemoryCapabilities()
        for cacheDev, name, id in rams:
            cacheAcc = PVCacheMemoryAccessor(cacheDev, name, id)
            dev.registerAddressFilter(cacheAcc)
            ramCapabilities.addRAM(cacheAcc)
        dev.addCapabilities(ramCapabilities)

