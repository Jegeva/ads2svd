# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import AHBMemAPAccessor
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl.components import MemoryRouter
from com.arm.debug.dtsl.components import DapMemoryAccessor

CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers

# Change these parameters to get specific AP / Core number variants
NUM_CORES_THUNDERX = 48 # number of cores in the .rvc
BASE_IDX_CORE_0 = 3 # base core index in .rvc + 1
SCANCHAIN_TEMPL_PER_CORE = 2  # 3 if core+cti+pmu, 2 if core+cti only declared in scanchain .rvc
# need to set option 'writeTARExt' default value to true for AP1 support - below...

# thunderX script for TXx2 on t88
import thunderx_config  # ctx object for setting config items from DTSL
import cavium_dap        # AP1 customisation on connect

class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("hwcfg", "Hardware Config", childOptions=[
                    # HW workarounds for Cav systems
                    DTSLv1.booleanOption('mdscrMDE', 'Set MDSCR.MDE for HW breaks',
                                         description='Automatically set MDSCR.MDE when using hardware breakpoints',
                                         defaultValue=True, isDynamic=True),
                    DTSLv1.booleanOption('isbHazard', 'Enable ISB Hazard',
                                         description='Automatically override the ISB optimisation by setting bit in CVMCTL_EL1',
                                         defaultValue=True, isDynamic=True),
                ]),
                DTSLv1.tabPage("sysAP", "System AP Options", childOptions=[
                    # system AP control
                    DTSLv1.booleanOption('writeTARExt', 'Write Extended AP.TAR on connect',
                                         description='When configured to use the System AP for debug, write a value to the AP.TAR[63:32] bits',
                                         defaultValue=True, isDynamic=True,
                                         childOptions = [
                                            DTSLv1.integerOption('valueTARExt', 'Value for Extended AP.TAR',
                                            description='Value to write to the AP.TAR[63:32] bits.',
                                            defaultValue=0x000087A0, isDynamic=True,
                                            display=IIntegerOption.DisplayFormat.HEX),
                                    ]),
                ]),
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()


        # Only DAP device is managed by default - others will be added when enabling trace, SMP etc
        # use DAP as this has Cavium custom handling
        if self.dap not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.dap)

        self.exposeCores()

        # last called - allow derived class to do more init before completion
        self.init_completion();


        ''' base version just does managed device list '''
    def init_completion(self):
        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        # use DAP rather than APs - cavium custom handling
        # use Cavium dap rather than CSDAP for AP1 handling on connect
        self.dap = cavium_dap.CaviumDAP(self, 1, "DAP")

        self.thunderXcores = []

        streamID = 1

        for i in range(0, NUM_CORES_THUNDERX):
            # Create core
            coreIdx = BASE_IDX_CORE_0 + (i*SCANCHAIN_TEMPL_PER_CORE)

            core = thunderx_config.ThunderXCoreDevice(self, coreIdx, "ThunderX_%02d" % i)
            self.thunderXcores.append(core)


    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        #core.registerAddressFilters([
        #    AxBMemAPAccessor("APB0", self.APB0, "APB bus accessed via AP"),
        #    AxBMemAPAccessor("APB1", self.APB1, "APB bus accessed via AP"),
        #])

    def exposeCores(self):
        for core in self.thunderXcores:
            self.addDeviceInterface(self.createDAPWrapper(core))


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
        # apply the TAR value to the cavium dap only
        cavium_dap.applyExtAPTAR(configuration = self,
                                optionName = "options.sysAP.writeTARExt",
                                device = self.dap)
        cavium_dap.applyExtAPTARValue(configuration = self,
                                optionName = "options.sysAP.writeTARExt.valueTARExt",
                                device = self.dap)

        # core updates on each core in use.
        for i in range(0, NUM_CORES_THUNDERX):
            thunderx_config.applyMDSCRMDE(configuration = self,
                                     optionName = "options.hwcfg.mdscrMDE",
                                     device = self.thunderXcores[i])
            thunderx_config.applyEnableISBHazard(configuration = self,
                                            optionName = "options.hwcfg.isbHazard",
                                            device = self.thunderXcores[i])


    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+


    def createDAPWrapper(self, core):
        '''Add a wrapper around a core to allow access to AP buses via the DAP
            Treat both Cav APs as APB AP.
        '''
        return MemoryRouter(
            [DapMemoryAccessor("APB0", self.dap, 0, "APB bus accessed via AP_0 on DAP_0"),
             DapMemoryAccessor("APB1", self.dap, 1, "APB bus accessed via AP_1 on DAP_0")],
            core)

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

'''
Only want CTI management in the SMP connection.
Otherwise bug in Arm DS / DTSL means connecting to single core
will connect to all CTIs in SMP anyway - up to 48 for cavium!
'''
class DtslScript_SMP(DtslScript):

    def __init__(self, root):
        DtslScript.__init__(self,root)


    def init_completion(self):
        self.setupCTISyncSMP()
        DtslScript.init_completion(self)


    def discoverDevices(self):
        DtslScript.discoverDevices(self)

        self.CoreCTIs = []
        for i in range(0, NUM_CORES_THUNDERX):
            # Create core - T88 has cores / CTIs on a SCANCHAIN_TEMPL_PER_CORE device separation
            ctiIdx = BASE_IDX_CORE_0 + (i*SCANCHAIN_TEMPL_PER_CORE)

            coreCTI = CSCTI(self, ctiIdx+1, "CoreCTIs[%d]" % i)
            self.CoreCTIs.append(coreCTI)

    def getCTIInfoForCore(self, core):
        '''Get the CTI info associated with a core
        return None if no associated CTI info
        '''
        # Build map of cores to DeviceCTIInfo objects
        ctiInfoMap = {}
        for i in range(0, NUM_CORES_THUNDERX):
            ctiInfoMap[self.thunderXcores[i]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[i], CTISyncSMPDevice.DeviceCTIInfo.NONE, 1, 0, 0)

        return ctiInfoMap.get(core, None)


    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for sync start/stop
        # ThunderX CTI SMP setup
        ctiInfo = {}
        for c in self.thunderXcores:
            ctiInfo[c] = self.getCTIInfoForCore(c)
        smp = CTISyncSMPDevice(self, "ThunderX SMP", self.thunderXcores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        #self.registerFilters(smp)
        self.addDeviceInterface(smp)

        # Automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CoreCTIs)

