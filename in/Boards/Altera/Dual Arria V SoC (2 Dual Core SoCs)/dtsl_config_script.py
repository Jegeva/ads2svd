from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CTISyncSMPDevice

from struct import pack, unpack
from jarray import array, zeros

NUM_CORES_CORTEX_A9 = 4
NUM_CORES_CORTEX_A9_PER_HPS = 2
NUM_HPS = 2
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

       # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # Only MEM_AP devices are managed by default - others will be added when enabling trace, SMP etc
        if self.AHB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.AHB)
        if self.APB not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.APB)
        if self.AHB1 not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.AHB1)
        if self.APB1 not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.APB1)

        self.exposeCores()

        self.setupCTISyncSMP()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        memApDev = 0

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.AHB = AHBAP(self, memApDev, "AHB")

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.APB = APBAP(self, memApDev, "APB")

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.AHB1 = AHBAP(self, memApDev, "AHB1")

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.APB1 = APBAP(self, memApDev, "APB1")

        cortexA9coreDevs = [9, 11, 27, 29]
        self.cortexA9cores = []

        streamID = 1

        coreCTIDevs = [13, 14, 31, 32]
        self.CoreCTIs = []

        for i in range(0, NUM_CORES_CORTEX_A9):
            # Create core
            core = Device(self, cortexA9coreDevs[i], "Cortex-A9_%d" % i)
            self.cortexA9cores.append(core)

        for i in range(0, len(coreCTIDevs)):
            # Create CTI
            coreCTI = CSCTI(self, coreCTIDevs[i], "CoreCTIs[%d]" % i)
            self.CoreCTIs.append(coreCTI)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters([
            AHBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP"),
            AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP"),
            AHBMemAPAccessor("AHB1", self.AHB1, "AHB bus accessed via AP"),
            AxBMemAPAccessor("APB1", self.APB1, "APB bus accessed via AP"),
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
        smp = []
        core = 0;

        for h in range(0, NUM_HPS):
            ctiInfo = {}
            hpsCores = []
            for c in range(0, NUM_CORES_CORTEX_A9_PER_HPS):
                ctiInfo[self.cortexA9cores[core]] = self.getCTIInfoForCore(self.cortexA9cores[core])
                hpsCores.append(self.cortexA9cores[core])
                core += 1

            smp.append(CTISyncSMPDevice(self, "HPS%d Cortex-A9 SMP" % h, hpsCores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP))
            self.registerFilters(smp[h])
            self.addDeviceInterface(smp[h])


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


    def verify(self):
        mask = [ 0xF, 0x0, 0x0, 0x0, 0xFF, 0xFF, 0xF, 0x0 ]
        expectedROMTable = [ 0L, 0L, 0L, 0L, 1L, 224L, 14L, 0L ]
        addrROMTable = 0x80000fd0
        return self.confirmValue(addrROMTable, expectedROMTable, mask)



    def confirmValue(self, addr, expected, mask):
        actual = zeros(len(expected), 'l')
        for i in range(0,len(expected)-1) :
            j = i*4
            buffer = zeros(4, 'b')
            try:
                self.APB.readMem(addr+j, 4, buffer)
            except DTSLException:
                return False
            value = unpack('<I', buffer)[0]
            actual[i] = value
            if ((actual[i] & mask[i]) != (expected[i] & mask[i])):
                return False
        return True

class RVI_DtslScript(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]

class USBBlaster_DtslScript(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
            ])
        ]


