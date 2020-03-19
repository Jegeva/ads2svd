from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CTISyncSMPDevice

NUM_CORES_CORTEX_A9 = 4
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers


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

        # Only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
        for i in range(len(self.AHBs)):
            if self.AHBs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.AHBs[i])

        for i in range(len(self.APBs)):
            if self.APBs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.APBs[i])

        self.exposeCores()

        self.setupCTISyncSMP()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        apDevs_AHBs = ["CSMEMAP_1"]
        self.AHBs = []

        apDevs_APBs = ["CSMEMAP_0"]
        self.APBs = []

        for i in range(len(apDevs_AHBs)):
            apDevice = AHBAP(self, self.findDevice(apDevs_AHBs[i]), "AHB_%d" % i)
            self.AHBs.append(apDevice)

        for i in range(len(apDevs_APBs)):
            apDevice = APBAP(self, self.findDevice(apDevs_APBs[i]), "APB_%d" % i)
            self.APBs.append(apDevice)

        coreDevs_cortexA9 = ["Cortex-A9_0", "Cortex-A9_1", "Cortex-A9_2", "Cortex-A9_3"]
        self.cortexA9cores = []

        self.CoreCTIs = []
        ctiDevs_cortexA9 = ["CSCTI_0", "CSCTI_1", "CSCTI_2", "CSCTI_3"]

        for core in range(NUM_CORES_CORTEX_A9):
            # Create core
            coreDevice = Device(self, self.findDevice(coreDevs_cortexA9[core]), "Cortex-A9_%d" % core)
            self.cortexA9cores.append(coreDevice)

            # Create CTI (if a CTI exists for this core)
            if not ctiDevs_cortexA9[core] == None:
                coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexA9[core]), "Cortex-A9_CTI_%d" % core)
                self.CoreCTIs.append(coreCTI)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the APs for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB_0", self.AHBs[0], "AHB bus accessed via AP 1 (CSMEMAP_1)"),
            AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 0 (CSMEMAP_0)"),
        ])

    def exposeCores(self):
        for core in self.cortexA9cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def getCTIInfoForCore(self, core):
        '''Get the CTI info associated with a core
        return None if no associated CTI info
        '''

        # Build map of cores to DeviceCTIInfo objects
        ctiInfoMap = {}
        ctiInfoMap[self.cortexA9cores[0]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[0], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        ctiInfoMap[self.cortexA9cores[1]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[1], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        ctiInfoMap[self.cortexA9cores[2]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[2], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        ctiInfoMap[self.cortexA9cores[3]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[3], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)

        return ctiInfoMap.get(core, None)

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for sync start/stop
        # Cortex-A9 CTI SMP setup
        ctiInfo = {}
        for c in self.cortexA9cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)
        smp = CTISyncSMPDevice(self, "Cortex-A9 SMP", self.cortexA9cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp)
        self.addDeviceInterface(smp)

        # Automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CoreCTIs)

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

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the list of devices managed by the configuration, as long as they are not already present'''
        for d in devs:
            if d not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(d)

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.enableCTIInput(cti, input, channel, enabled)

    def enableCTIInput(self, cti, input, channel, enabled):
        '''Enable/disable cross triggering between an input and a channel'''
        if enabled:
            cti.enableInputEvent(input, channel)
        else:
            cti.disableInputEvent(input, channel)

class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return [
        ]


