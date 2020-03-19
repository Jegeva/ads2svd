from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CTISyncSMPDevice

ctiDevs_v8Generic = [["CSCTI_0", "CSCTI_1", "CSCTI_2", "CSCTI_3"],["CSCTI_4", "CSCTI_5", "CSCTI_6", "CSCTI_7"]]
clusterDeviceNames_v8Generic = ["V8-Generic_SMP_1", "V8-Generic_SMP_2"]
coreDevs_v8Generic = [["X-Gene_0", "X-Gene_1", "X-Gene_2", "X-Gene_3"],["X-Gene_4", "X-Gene_5", "X-Gene_6", "X-Gene_7"]]
NUM_CLUSTERS_V8_GENERIC = 2
NUM_CORES_V8_GENERIC_CLUSTERS = [4,4]
coresDap0 = ["X-Gene_0", "X-Gene_1", "X-Gene_2", "X-Gene_3", "X-Gene_4", "X-Gene_5", "X-Gene_6", "X-Gene_7"]
CTM_CHANNEL_SYNC_STOP = 2  # Use channel 2 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 3  # Use channel 3 for trace triggers


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

        apDevs_AHBs = ["CSMEMAP_0"]
        self.AHBs = []

        apDevs_APBs = ["CSMEMAP_1"]
        self.APBs = []

        for i in range(len(apDevs_AHBs)):
            apDevice = AHBAP(self, self.findDevice(apDevs_AHBs[i]), "AHB_%d" % i)
            self.AHBs.append(apDevice)

        for i in range(len(apDevs_APBs)):
            apDevice = APBAP(self, self.findDevice(apDevs_APBs[i]), "APB_%d" % i)
            self.APBs.append(apDevice)

        self.v8Genericcores = []
        self.clusterCores_v8Generic = {}

        self.CoreCTIs = []

        for cluster in range(NUM_CLUSTERS_V8_GENERIC):
            self.clusterCores_v8Generic[cluster] = []
            for core in range(NUM_CORES_V8_GENERIC_CLUSTERS[cluster]):
                # Create core
                coreDevice = Device(self, self.findDevice(coreDevs_v8Generic[cluster][core]), coreDevs_v8Generic[cluster][core])
                self.v8Genericcores.append(coreDevice)
                self.clusterCores_v8Generic[cluster].append(coreDevice)

                # Create CTI (if a CTI exists for this core)
                if not ctiDevs_v8Generic[cluster][core] == None:
                    coreCTI = CSCTI(self, self.findDevice(ctiDevs_v8Generic[cluster][core]), ctiDevs_v8Generic[cluster][core])
                    coreCTI.disableAllInputs()
                    coreCTI.disableAllOutputs()
                    coreCTI.setChannelGate((1<<CTM_CHANNEL_SYNC_START) | (1<<CTM_CHANNEL_SYNC_STOP) | (1<<CTM_CHANNEL_TRACE_TRIGGER))
                    self.CoreCTIs.append(coreCTI)

    def registerFilters(self, core, dap):
        '''Register MemAP filters to allow access to the APs for the device'''
        if dap == 0:
            core.registerAddressFilters([
                AHBMemAPAccessor("AHB_0", self.AHBs[0], "AHB bus accessed via AP 0 (CSMEMAP_0)"),
                AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 1 (CSMEMAP_1)"),
            ])

    def exposeCores(self):
        for coreName in coresDap0:
            core = self.getDeviceInterface(coreName)
            self.registerFilters(core, 0)
            self.addDeviceInterface(core)

    def getCTIInfoForCore(self, core):
        '''Get the funnel port number for a trace source'''

        coreNames = ["X-Gene_0", "X-Gene_1", "X-Gene_2", "X-Gene_3", "X-Gene_4", "X-Gene_5", "X-Gene_6", "X-Gene_7"]
        ctiNames = ["CSCTI_0", "CSCTI_1", "CSCTI_2", "CSCTI_3", "CSCTI_4", "CSCTI_5", "CSCTI_6", "CSCTI_7"]
        ctiTriggers = [1, 1, 1, 1, 1, 1, 1, 1]

        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return CTISyncSMPDevice.DeviceCTIInfo(self.getDeviceInterface(ctiNames[i]), CTISyncSMPDevice.DeviceCTIInfo.NONE, ctiTriggers[i], 0, 0)

        return None

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for sync start/stop
        for cluster in range(NUM_CLUSTERS_V8_GENERIC):
            # SMP Device for this cluster
            ctiInfo = {}
            for c in self.clusterCores_v8Generic[cluster]:
                ctiInfo[c] = self.getCTIInfoForCore(c)

            smp = CTISyncSMPDevice(self, clusterDeviceNames_v8Generic[cluster], self.clusterCores_v8Generic[cluster], ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
            self.registerFilters(smp, 0)
            self.addDeviceInterface(smp)

        # V8-Genericx8 CTI SMP
        ctiInfo = {}
        for c in self.v8Genericcores:
            ctiInfo[c] = self.getCTIInfoForCore(c)

        smp = CTISyncSMPDevice(self, "V8-Genericx8 SMP", self.v8Genericcores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp, 0)
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

