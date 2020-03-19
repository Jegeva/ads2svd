from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel

NUM_CORES_CORTEX_A9 = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
ATB_ID_BASE = 2
DSTREAM_PORTWIDTH = 16
CORTEX_A9_TRACE_OPTIONS = 0
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers

class TraceRangeOptions:
    def __init__(self, coreTraceName = None, dtsl = None):
        if coreTraceName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("%s.traceRange" % coreTraceName)
            self.traceRangeStart = dtsl.getOptionValue("%s.traceRange.start" % coreTraceName)
            self.traceRangeEnd = dtsl.getOptionValue("%s.traceRange.end" % coreTraceName)
            self.traceRangeIDs = None

    def defaultSetup(self):
        self.traceRangeEnable = False
        self.traceRangeStart = None
        self.traceRangeEnd = None
        self.traceRangeIDs = None


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return []

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # only AHB/APB are managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB)
        self.mgdPlatformDevs.add(self.APB)

        self.exposeCores()

        self.setupCTISyncSMP()

        self.setManagedDevices(self.mgdPlatformDevs)

    def discoverDevices(self):
        '''find and create devices'''

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        cortexA9coreDev = 0
        self.cortexA9cores = []

        # Trace start/stop CTI
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")
        coreCTIDev = outCTIDev
        self.CTIs  = []
        self.cortexA9ctiMap = {} # map cores to associated CTIs

        for i in range(0, NUM_CORES_CORTEX_A9):
            # create core
            cortexA9coreDev = self.findDevice("Cortex-A9", cortexA9coreDev+1)
            dev = Device(self, cortexA9coreDev, "Cortex-A9_%d" % i)
            self.cortexA9cores.append(dev)

            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            self.CTIs.append(coreCTI)
            self.cortexA9ctiMap[dev] = coreCTI

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the set of devices managed by the configuration'''
        for d in devs:
            self.mgdPlatformDevs.add(d)

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP_1")])

    def exposeCores(self):
        for core in self.cortexA9cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for synch start/stop
        # Cortex-A9 CTI SMP setup
        ctiInfo = {}
        for c in self.cortexA9cores:
            # use standard Cortex event mapping : in/out on trigger 0 for stop, out on trigger 7 for start
            ctiInfo[c] = CTISyncSMPDevice.DeviceCTIInfo(self.cortexA9ctiMap[c], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        smp = CTISyncSMPDevice(self, "Cortex-A9 SMP", self.cortexA9cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp)
        self.addDeviceInterface(smp)

        # automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CTIs)

