from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CTISyncSMPDevice

ctiDevs_cortexA53 = ["CSCTI_0", "CSCTI_1", "CSCTI_2", "CSCTI_3"]
coreDevs_cortexA53 = ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
NUM_CORES_CORTEX_A53 = 4
coresDap0 = ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
CTM_CHANNEL_SYNC_STOP = 2  # Use channel 2 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 3  # Use channel 3 for trace triggers

# Import core specific functions
import a53_rams


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

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # Only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
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

        apDevs_APBs = ["CSMEMAP"]
        self.APBs = []

        for i in range(len(apDevs_APBs)):
            apDevice = APBAP(self, self.findDevice(apDevs_APBs[i]), "APB_%d" % i)
            self.APBs.append(apDevice)

        self.cortexA53cores = []

        self.CoreCTIs = []

        for core in range(NUM_CORES_CORTEX_A53):
            # Create core
            coreDevice = a53_rams.A53CoreDevice(self, self.findDevice(coreDevs_cortexA53[core]), coreDevs_cortexA53[core])
            self.cortexA53cores.append(coreDevice)

            # Create CTI (if a CTI exists for this core)
            if not ctiDevs_cortexA53[core] == None:
                coreCTI = CSCTI(self, self.findDevice(ctiDevs_cortexA53[core]), ctiDevs_cortexA53[core])
                self.CoreCTIs.append(coreCTI)

    def registerFilters(self, core, dap):
        '''Register MemAP filters to allow access to the APs for the device'''
        if dap == 0:
            core.registerAddressFilters([
                AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 0 (CSMEMAP)"),
            ])

    def exposeCores(self):
        for coreName in coresDap0:
            core = self.getDeviceInterface(coreName)
            self.registerFilters(core, 0)
            self.addDeviceInterface(core)
        for core in self.cortexA53cores:
            a53_rams.registerInternalRAMs(core)

    def getCTIInfoForCore(self, core):
        '''Get the CTI info for the given core - return None if no CTI found'''

        coreNames = ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
        ctiNames = ["CSCTI_0", "CSCTI_1", "CSCTI_2", "CSCTI_3"]
        ctiTriggers = [1, 1, 1, 1]

        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return CTISyncSMPDevice.DeviceCTIInfo(self.getDeviceInterface(ctiNames[i]), CTISyncSMPDevice.DeviceCTIInfo.NONE, ctiTriggers[i], 0, 0)

        return None

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''
        macrocellNames = []
        ctiNames = []
        ctiTriggers = []

        sourceName = source.getName()
        for i in range(len(macrocellNames)):
            if sourceName == macrocellNames[i]:
                return (self.getDeviceInterface(ctiNames[i]), ctiTriggers[i], CTM_CHANNEL_TRACE_TRIGGER)

        return (None, None, None)

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for sync start/stop
        # Cortex-A53x4 CTI SMP
        ctiInfo = {}
        for c in self.cortexA53cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)

        smp = CTISyncSMPDevice(self, "Cortex-A53x4 SMP", self.cortexA53cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
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

        for core in range(0, len(self.cortexA53cores)):
            a53_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA53cores[core])
            a53_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA53cores[core])

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

