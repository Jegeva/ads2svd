from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource

tmDevs_cortexA57 = [["CSETM_0", "CSETM_1"],["CSETM_2", "CSETM_3"],["CSETM_4", "CSETM_5"],["CSETM_6", "CSETM_7"]]
ctiDevs_cortexA57 = [["CSCTI_2", "CSCTI_3"],["CSCTI_4", "CSCTI_5"],["CSCTI_6", "CSCTI_7"],["CSCTI_8", "CSCTI_9"]]
clusterDeviceNames_cortexA57 = ["Cortex-A57_SMP_0", "Cortex-A57_SMP_1", "Cortex-A57_SMP_2", "Cortex-A57_SMP_3"]
coreDevs_cortexA57 = [["Cortex-A57_0", "Cortex-A57_1"],["Cortex-A57_2", "Cortex-A57_3"],["Cortex-A57_4", "Cortex-A57_5"],["Cortex-A57_6", "Cortex-A57_7"]]
NUM_CLUSTERS_CORTEX_A57 = 4
NUM_CORES_CORTEX_A57_CLUSTERS = [2,2,2,2]
coresDap0 = ["Cortex-A57_0", "Cortex-A57_1", "Cortex-A57_2", "Cortex-A57_3", "Cortex-A57_4", "Cortex-A57_5", "Cortex-A57_6", "Cortex-A57_7"]
CTM_CHANNEL_SYNC_STOP = 2  # Use channel 2 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 3  # Use channel 3 for trace triggers

# Import core specific functions
import a57_rams


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ])]
            )
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # Only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
        for i in range(len(self.APBs)):
            if self.APBs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.APBs[i])

        for i in range(len(self.AXIs)):
            if self.AXIs[i] not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.AXIs[i])

        self.exposeCores()

        self.setupCTISyncSMP()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        apDevs_APBs = ["CSMEMAP_0"]
        self.APBs = []

        apDevs_AXIs = ["CSMEMAP_1"]
        self.AXIs = []

        for i in range(len(apDevs_APBs)):
            apDevice = APBAP(self, self.findDevice(apDevs_APBs[i]), "APB_%d" % i)
            self.APBs.append(apDevice)

        for i in range(len(apDevs_AXIs)):
            apDevice = AXIAP(self, self.findDevice(apDevs_AXIs[i]), "AXI_%d" % i)
            self.AXIs.append(apDevice)

        self.cortexA57cores = []
        self.clusterCores_cortexA57 = {}

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, self.findDevice("CSCTI_1"), "CSCTI_1")

        self.CoreCTIs = []

        self.macrocells = {}
        self.macrocells["cortexA57"] = [ [] for i in range(NUM_CLUSTERS_CORTEX_A57) ]


        for cluster in range(NUM_CLUSTERS_CORTEX_A57):
            #Ensure that any macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
            self.clusterCores_cortexA57[cluster] = []
            for core in range(NUM_CORES_CORTEX_A57_CLUSTERS[cluster]):
                # Create core
                coreDevice = a57_rams.A57CoreDevice(self, self.findDevice(coreDevs_cortexA57[cluster][core]), coreDevs_cortexA57[cluster][core])
                self.cortexA57cores.append(coreDevice)
                self.clusterCores_cortexA57[cluster].append(coreDevice)

                # Create CTI (if a CTI exists for this core)
                if not ctiDevs_cortexA57[cluster][core] == None:
                    coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexA57[cluster][core]), ctiDevs_cortexA57[cluster][core])
                    self.CoreCTIs.append(coreCTI)


    def registerFilters(self, core, dap):
        '''Register MemAP filters to allow access to the APs for the device'''
        if dap == 0:
            core.registerAddressFilters([
                AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 0 (CSMEMAP_0)"),
                AXIMemAPAccessor("AXI_0", self.AXIs[0], "AXI bus accessed via AP 1 (CSMEMAP_1)", 64),
            ])

    def exposeCores(self):
        for coreName in coresDap0:
            core = self.getDeviceInterface(coreName)
            self.registerFilters(core, 0)
            self.addDeviceInterface(core)
        for core in self.cortexA57cores:
            a57_rams.registerInternalRAMs(core)

    def getCTIInfoForCore(self, core):
        '''Get the funnel port number for a trace source'''

        coreNames = ["Cortex-A57_0", "Cortex-A57_1", "Cortex-A57_2", "Cortex-A57_3", "Cortex-A57_4", "Cortex-A57_5", "Cortex-A57_6", "Cortex-A57_7"]
        ctiNames = ["CSCTI_2", "CSCTI_3", "CSCTI_4", "CSCTI_5", "CSCTI_6", "CSCTI_7", "CSCTI_8", "CSCTI_9"]
        ctiTriggers = [1, 1, 1, 1, 1, 1, 1, 1]

        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return CTISyncSMPDevice.DeviceCTIInfo(self.getDeviceInterface(ctiNames[i]), CTISyncSMPDevice.DeviceCTIInfo.NONE, ctiTriggers[i], 0, 0)

        return None

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for sync start/stop
        for cluster in range(NUM_CLUSTERS_CORTEX_A57):
            # SMP Device for this cluster
            ctiInfo = {}
            for c in self.clusterCores_cortexA57[cluster]:
                ctiInfo[c] = self.getCTIInfoForCore(c)

            smp = CTISyncSMPDevice(self, clusterDeviceNames_cortexA57[cluster], self.clusterCores_cortexA57[cluster], ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
            self.registerFilters(smp, 0)
            self.addDeviceInterface(smp)

        # Cortex-A57x8 CTI SMP
        ctiInfo = {}
        for c in self.cortexA57cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)

        smp = CTISyncSMPDevice(self, "Cortex-A57x8 SMP", self.cortexA57cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp, 0)
        self.addDeviceInterface(smp)

        # Automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CoreCTIs)

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        self.updateDynamicOptions()


    def updateDynamicOptions(self):
        '''Update the dynamic options'''

        for core in range(0, len(self.cortexA57cores)):
            a57_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA57cores[core])
            a57_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA57cores[core])

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList
    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+
    def addManagedPlatformDevices(self, devs):
        '''Add devices to the list of devices managed by the configuration, as long as they are not already present'''
        for d in devs:
            if d not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(d)

    def postConnect(self):
        DTSLv1.postConnect(self)

