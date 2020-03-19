# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import MTBTraceCapture

NUM_CORES_CORTEX_M0_PLUS = 1
ATB_ID_BASE = 2


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("MTB", "On Chip Trace Buffer (MTB)")]
                        ),
                ]),
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # only AHB is managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB)

        self.exposeCores()

        self.setupMTBTrace()

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = CortexM_AHBAP(self, ahbDev, "CSMEMAP")

        cortexM0PLUScoreDev = 0
        self.cortexM0PLUScores = []

        streamID = ATB_ID_BASE

        mtbDev = 0
        self.MTBs = []

        for i in range(0, NUM_CORES_CORTEX_M0_PLUS):
            # create core
            cortexM0PLUScoreDev = self.findDevice("Cortex-M0+", cortexM0PLUScoreDev+1)
            dev = Device(self, cortexM0PLUScoreDev, "Cortex-M0+")
            self.cortexM0PLUScores.append(dev)

            # Create MTB for core
            mtbDev = self.findDevice("CSMTB", mtbDev + 1)
            self.MTBs.append(MTBTraceCapture(self, mtbDev, "MTB", self.cortexM0PLUScores[i]))

    def exposeCores(self):
        for core in self.cortexM0PLUScores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def setupMTBTrace(self):
        ''' Setup MTB trace capture'''
        for mtb in self.MTBs:
            mtb.setTraceBufferSize(4096)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("MTB", self.MTBs)

        for mtb in self.MTBs:
            self.addTraceCaptureInterface(mtb)

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        optionValues = self.getOptionValues()
        traceMode = optionValues.get("options.trace.traceCapture")
        self.setManagedDevices(self.getManagedDevices(traceMode))

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the set of devices managed by the configuration'''
        for d in devs:
            self.mgdPlatformDevs.add(d)

    def addManagedTraceDevices(self, traceKey, devs):
        '''Add devices to the set of devices managed by the configuration for this trace mode'''
        traceDevs = self.mgdTraceDevs.get(traceKey)
        if not traceDevs:
            traceDevs = set()
            self.mgdTraceDevs[traceKey] = traceDevs
        for d in devs:
            traceDevs.add(d)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB for the device'''
        core.registerAddressFilters([AHBCortexMMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0")])
