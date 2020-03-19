from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import PVCacheDevice
from com.arm.debug.dtsl.components import PVCacheMemoryAccessor
from com.arm.debug.dtsl.components import PVCacheMemoryCapabilities
from com.arm.debug.dtsl.components import ConnectableDevice
from com.arm.debug.dtsl.components import CadiSyncSMPDevice
from com.arm.debug.dtsl.components import DeviceCluster
from com.arm.debug.dtsl.components import FMTraceCapture
from com.arm.debug.dtsl.components import FMTraceSource
from com.arm.debug.dtsl.components import FMTraceDevice

CONTENTS, TAGS = 0, 1
FM_SOURCE_ID_BASE    = 32
MTS_SERVER_PORT      = 31628
FM_TRACE_SOURCE_BASE = 32768


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("traceBuffer", "Trace Configuration", childOptions=[
                    DtslScript.getModelTraceCaptureOptions(),
                    DtslScript.getModelTraceClearOptions(),
                    DtslScript.getModelTraceStartOptions(),
                    DtslScript.getModelTraceBufferOptions(),
                    DtslScript.getModelTraceWrapOptions(),
                ])]
            )
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.exposeCores()

        self.setupModelTrace()

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
        self.cores["css.cluster11.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster11.cpu0"), "ARM_Cortex-A53_22" )
        self.cores["css.cluster11.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster11.cpu1"), "ARM_Cortex-A53_23" )
        self.cores["css.cluster10.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster10.cpu0"), "ARM_Cortex-A53_20" )
        self.cores["css.cluster10.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster10.cpu1"), "ARM_Cortex-A53_21" )
        self.cores["css.cluster9.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster9.cpu0"), "ARM_Cortex-A53_18" )
        self.cores["css.cluster9.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster9.cpu1"), "ARM_Cortex-A53_19" )
        self.cores["css.cluster8.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster8.cpu0"), "ARM_Cortex-A53_16" )
        self.cores["css.cluster8.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster8.cpu1"), "ARM_Cortex-A53_17" )
        self.cores["css.cluster7.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster7.cpu0"), "ARM_Cortex-A53_14" )
        self.cores["css.cluster7.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster7.cpu1"), "ARM_Cortex-A53_15" )
        self.cores["css.cluster6.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster6.cpu0"), "ARM_Cortex-A53_12" )
        self.cores["css.cluster6.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster6.cpu1"), "ARM_Cortex-A53_13" )
        self.cores["css.cluster5.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster5.cpu0"), "ARM_Cortex-A53_10" )
        self.cores["css.cluster5.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster5.cpu1"), "ARM_Cortex-A53_11" )
        self.cores["css.cluster4.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster4.cpu0"), "ARM_Cortex-A53_8" )
        self.cores["css.cluster4.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster4.cpu1"), "ARM_Cortex-A53_9" )
        self.cores["css.cluster3.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster3.cpu0"), "ARM_Cortex-A53_6" )
        self.cores["css.cluster3.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster3.cpu1"), "ARM_Cortex-A53_7" )
        self.cores["css.cluster2.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster2.cpu0"), "ARM_Cortex-A53_4" )
        self.cores["css.cluster2.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster2.cpu1"), "ARM_Cortex-A53_5" )
        self.cores["css.cluster1.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster1.cpu0"), "ARM_Cortex-A53_2" )
        self.cores["css.cluster1.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster1.cpu1"), "ARM_Cortex-A53_3" )
        self.cores["css.cluster0.cpu0"] = ConnectableDevice(self, self.findDevice("css.cluster0.cpu0"), "ARM_Cortex-A53_0" )
        self.cores["css.cluster0.cpu1"] = ConnectableDevice(self, self.findDevice("css.cluster0.cpu1"), "ARM_Cortex-A53_1" )

        self.cluster11cores = []
        self.cluster11cores.append(self.cores["css.cluster11.cpu0"])
        self.cluster11cores.append(self.cores["css.cluster11.cpu1"])
        self.cluster10cores = []
        self.cluster10cores.append(self.cores["css.cluster10.cpu0"])
        self.cluster10cores.append(self.cores["css.cluster10.cpu1"])
        self.cluster9cores = []
        self.cluster9cores.append(self.cores["css.cluster9.cpu0"])
        self.cluster9cores.append(self.cores["css.cluster9.cpu1"])
        self.cluster8cores = []
        self.cluster8cores.append(self.cores["css.cluster8.cpu0"])
        self.cluster8cores.append(self.cores["css.cluster8.cpu1"])
        self.cluster7cores = []
        self.cluster7cores.append(self.cores["css.cluster7.cpu0"])
        self.cluster7cores.append(self.cores["css.cluster7.cpu1"])
        self.cluster6cores = []
        self.cluster6cores.append(self.cores["css.cluster6.cpu0"])
        self.cluster6cores.append(self.cores["css.cluster6.cpu1"])
        self.cluster5cores = []
        self.cluster5cores.append(self.cores["css.cluster5.cpu0"])
        self.cluster5cores.append(self.cores["css.cluster5.cpu1"])
        self.cluster4cores = []
        self.cluster4cores.append(self.cores["css.cluster4.cpu0"])
        self.cluster4cores.append(self.cores["css.cluster4.cpu1"])
        self.cluster3cores = []
        self.cluster3cores.append(self.cores["css.cluster3.cpu0"])
        self.cluster3cores.append(self.cores["css.cluster3.cpu1"])
        self.cluster2cores = []
        self.cluster2cores.append(self.cores["css.cluster2.cpu0"])
        self.cluster2cores.append(self.cores["css.cluster2.cpu1"])
        self.cluster1cores = []
        self.cluster1cores.append(self.cores["css.cluster1.cpu0"])
        self.cluster1cores.append(self.cores["css.cluster1.cpu1"])
        self.cluster0cores = []
        self.cluster0cores.append(self.cores["css.cluster0.cpu0"])
        self.cluster0cores.append(self.cores["css.cluster0.cpu1"])

        self.caches = dict()
        self.caches["css.cluster11.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster11.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster11.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster11.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster11.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster11.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster11.l2_cache"), "l2_cache")
        self.caches["css.cluster10.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster10.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster10.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster10.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster10.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster10.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster10.l2_cache"), "l2_cache")
        self.caches["css.cluster9.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster9.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster9.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster9.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster9.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster9.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster9.l2_cache"), "l2_cache")
        self.caches["css.cluster8.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster8.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster8.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster8.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster8.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster8.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster8.l2_cache"), "l2_cache")
        self.caches["css.cluster7.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster7.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster7.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster7.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster7.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster7.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster7.l2_cache"), "l2_cache")
        self.caches["css.cluster6.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster6.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster6.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster6.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster6.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster6.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster6.l2_cache"), "l2_cache")
        self.caches["css.cluster5.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster5.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster5.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster5.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster5.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster5.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster5.l2_cache"), "l2_cache")
        self.caches["css.cluster4.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster4.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster4.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster4.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster4.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster4.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster4.l2_cache"), "l2_cache")
        self.caches["css.cluster3.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster3.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster3.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster3.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster3.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster3.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster3.l2_cache"), "l2_cache")
        self.caches["css.cluster2.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster2.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster2.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster2.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster2.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster2.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster2.l2_cache"), "l2_cache")
        self.caches["css.cluster1.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster1.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster1.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster1.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster1.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster1.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster1.l2_cache"), "l2_cache")
        self.caches["css.cluster0.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu0.l1dcache"), "l1dcache_0")
        self.caches["css.cluster0.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu0.l1icache"), "l1icache_0")
        self.caches["css.cluster0.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu1.l1dcache"), "l1dcache_1")
        self.caches["css.cluster0.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("css.cluster0.cpu1.l1icache"), "l1icache_1")
        self.caches["css.cluster0.l2_cache"] = PVCacheDevice(self, self.findDevice("css.cluster0.l2_cache"), "l2_cache")

        self.addManagedPlatformDevices(self.caches.values())

        self.addPVCache(self.cores["css.cluster11.cpu0"], self.caches["css.cluster11.cpu0.l1icache"], self.caches["css.cluster11.cpu0.l1dcache"], self.caches["css.cluster11.l2_cache"])
        self.addPVCache(self.cores["css.cluster11.cpu1"], self.caches["css.cluster11.cpu1.l1icache"], self.caches["css.cluster11.cpu1.l1dcache"], self.caches["css.cluster11.l2_cache"])
        self.addPVCache(self.cores["css.cluster10.cpu0"], self.caches["css.cluster10.cpu0.l1icache"], self.caches["css.cluster10.cpu0.l1dcache"], self.caches["css.cluster10.l2_cache"])
        self.addPVCache(self.cores["css.cluster10.cpu1"], self.caches["css.cluster10.cpu1.l1icache"], self.caches["css.cluster10.cpu1.l1dcache"], self.caches["css.cluster10.l2_cache"])
        self.addPVCache(self.cores["css.cluster9.cpu0"], self.caches["css.cluster9.cpu0.l1icache"], self.caches["css.cluster9.cpu0.l1dcache"], self.caches["css.cluster9.l2_cache"])
        self.addPVCache(self.cores["css.cluster9.cpu1"], self.caches["css.cluster9.cpu1.l1icache"], self.caches["css.cluster9.cpu1.l1dcache"], self.caches["css.cluster9.l2_cache"])
        self.addPVCache(self.cores["css.cluster8.cpu0"], self.caches["css.cluster8.cpu0.l1icache"], self.caches["css.cluster8.cpu0.l1dcache"], self.caches["css.cluster8.l2_cache"])
        self.addPVCache(self.cores["css.cluster8.cpu1"], self.caches["css.cluster8.cpu1.l1icache"], self.caches["css.cluster8.cpu1.l1dcache"], self.caches["css.cluster8.l2_cache"])
        self.addPVCache(self.cores["css.cluster7.cpu0"], self.caches["css.cluster7.cpu0.l1icache"], self.caches["css.cluster7.cpu0.l1dcache"], self.caches["css.cluster7.l2_cache"])
        self.addPVCache(self.cores["css.cluster7.cpu1"], self.caches["css.cluster7.cpu1.l1icache"], self.caches["css.cluster7.cpu1.l1dcache"], self.caches["css.cluster7.l2_cache"])
        self.addPVCache(self.cores["css.cluster6.cpu0"], self.caches["css.cluster6.cpu0.l1icache"], self.caches["css.cluster6.cpu0.l1dcache"], self.caches["css.cluster6.l2_cache"])
        self.addPVCache(self.cores["css.cluster6.cpu1"], self.caches["css.cluster6.cpu1.l1icache"], self.caches["css.cluster6.cpu1.l1dcache"], self.caches["css.cluster6.l2_cache"])
        self.addPVCache(self.cores["css.cluster5.cpu0"], self.caches["css.cluster5.cpu0.l1icache"], self.caches["css.cluster5.cpu0.l1dcache"], self.caches["css.cluster5.l2_cache"])
        self.addPVCache(self.cores["css.cluster5.cpu1"], self.caches["css.cluster5.cpu1.l1icache"], self.caches["css.cluster5.cpu1.l1dcache"], self.caches["css.cluster5.l2_cache"])
        self.addPVCache(self.cores["css.cluster4.cpu0"], self.caches["css.cluster4.cpu0.l1icache"], self.caches["css.cluster4.cpu0.l1dcache"], self.caches["css.cluster4.l2_cache"])
        self.addPVCache(self.cores["css.cluster4.cpu1"], self.caches["css.cluster4.cpu1.l1icache"], self.caches["css.cluster4.cpu1.l1dcache"], self.caches["css.cluster4.l2_cache"])
        self.addPVCache(self.cores["css.cluster3.cpu0"], self.caches["css.cluster3.cpu0.l1icache"], self.caches["css.cluster3.cpu0.l1dcache"], self.caches["css.cluster3.l2_cache"])
        self.addPVCache(self.cores["css.cluster3.cpu1"], self.caches["css.cluster3.cpu1.l1icache"], self.caches["css.cluster3.cpu1.l1dcache"], self.caches["css.cluster3.l2_cache"])
        self.addPVCache(self.cores["css.cluster2.cpu0"], self.caches["css.cluster2.cpu0.l1icache"], self.caches["css.cluster2.cpu0.l1dcache"], self.caches["css.cluster2.l2_cache"])
        self.addPVCache(self.cores["css.cluster2.cpu1"], self.caches["css.cluster2.cpu1.l1icache"], self.caches["css.cluster2.cpu1.l1dcache"], self.caches["css.cluster2.l2_cache"])
        self.addPVCache(self.cores["css.cluster1.cpu0"], self.caches["css.cluster1.cpu0.l1icache"], self.caches["css.cluster1.cpu0.l1dcache"], self.caches["css.cluster1.l2_cache"])
        self.addPVCache(self.cores["css.cluster1.cpu1"], self.caches["css.cluster1.cpu1.l1icache"], self.caches["css.cluster1.cpu1.l1dcache"], self.caches["css.cluster1.l2_cache"])
        self.addPVCache(self.cores["css.cluster0.cpu0"], self.caches["css.cluster0.cpu0.l1icache"], self.caches["css.cluster0.cpu0.l1dcache"], self.caches["css.cluster0.l2_cache"])
        self.addPVCache(self.cores["css.cluster0.cpu1"], self.caches["css.cluster0.cpu1.l1icache"], self.caches["css.cluster0.cpu1.l1dcache"], self.caches["css.cluster0.l2_cache"])

    def setupModelTrace(self):
        # Create Fast Models Trace Capture Device on a fixed MTS server port
        self.tracecapture = FMTraceCapture(self, "FMTrace", MTS_SERVER_PORT )
        self.tracecapture.setTraceMode(FMTraceCapture.TraceMode.Continuous)

        self.addTraceCaptureInterface(self.tracecapture)

        # Expose Trace Sources
        # We are using a fixed StreamID base, this needs to match the Stream ID
        # embedded in the trace stream for that core
        StreamId  = FM_SOURCE_ID_BASE
        DeviceId  = FM_TRACE_SOURCE_BASE
        self.traceSources = []

        fmtSource =  FMTraceSource(self, DeviceId+0, StreamId+0, "FMT_0")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.scp.armcortexm7ct"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+1, StreamId+1, "FMT_1")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.mcp.armcortexm7ct"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+2, StreamId+2, "FMT_2")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster11.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+3, StreamId+3, "FMT_3")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster11.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+4, StreamId+4, "FMT_4")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster10.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+5, StreamId+5, "FMT_5")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster10.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+6, StreamId+6, "FMT_6")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster9.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+7, StreamId+7, "FMT_7")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster9.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+8, StreamId+8, "FMT_8")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster8.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+9, StreamId+9, "FMT_9")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster8.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+10, StreamId+10, "FMT_10")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster7.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+11, StreamId+11, "FMT_11")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster7.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+12, StreamId+12, "FMT_12")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster6.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+13, StreamId+13, "FMT_13")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster6.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+14, StreamId+14, "FMT_14")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster5.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+15, StreamId+15, "FMT_15")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster5.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+16, StreamId+16, "FMT_16")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster4.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+17, StreamId+17, "FMT_17")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster4.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+18, StreamId+18, "FMT_18")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster3.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+19, StreamId+19, "FMT_19")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster3.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+20, StreamId+20, "FMT_20")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster2.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+21, StreamId+21, "FMT_21")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster2.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+22, StreamId+22, "FMT_22")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster1.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+23, StreamId+23, "FMT_23")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster1.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+24, StreamId+24, "FMT_24")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster0.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+25, StreamId+25, "FMT_25")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["css.cluster0.cpu1"].getID())
        fmtSource.setEnabled(True)


    def exposeCores(self):
        '''Expose cores'''
        self.addDeviceInterface(self.cores["css.scp.armcortexm7ct"])
        self.addDeviceInterface(self.cores["css.mcp.armcortexm7ct"])
        self.addDeviceInterface(self.cores["css.cluster11.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster11.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster10.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster10.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster9.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster9.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster8.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster8.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster7.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster7.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster6.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster6.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster5.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster5.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster4.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster4.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster3.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster3.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster2.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster2.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster1.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster1.cpu1"])
        self.addDeviceInterface(self.cores["css.cluster0.cpu0"])
        self.addDeviceInterface(self.cores["css.cluster0.cpu1"])


    def setupCadiSyncSMP(self):
        '''Create SMP device using CADI synchronization'''

        # cluster11 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 11", self.cluster11cores)
        self.addDeviceInterface(smp)

        # cluster10 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 10", self.cluster10cores)
        self.addDeviceInterface(smp)

        # cluster9 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 9", self.cluster9cores)
        self.addDeviceInterface(smp)

        # cluster8 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 8", self.cluster8cores)
        self.addDeviceInterface(smp)

        # cluster7 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 7", self.cluster7cores)
        self.addDeviceInterface(smp)

        # cluster6 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 6", self.cluster6cores)
        self.addDeviceInterface(smp)

        # cluster5 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 5", self.cluster5cores)
        self.addDeviceInterface(smp)

        # cluster4 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 4", self.cluster4cores)
        self.addDeviceInterface(smp)

        # cluster3 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 3", self.cluster3cores)
        self.addDeviceInterface(smp)

        # cluster2 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 2", self.cluster2cores)
        self.addDeviceInterface(smp)

        # cluster1 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 1", self.cluster1cores)
        self.addDeviceInterface(smp)

        # cluster0 SMP
        smp = CadiSyncSMPDevice(self, "ARM_Cortex-A53x2 SMP Cluster 0", self.cluster0cores)
        self.addDeviceInterface(smp)

        # MULTI CLUSTER SMP
        clusters = [ DeviceCluster("cluster11", self.cluster11cores), DeviceCluster("cluster10", self.cluster10cores), DeviceCluster("cluster9", self.cluster9cores), DeviceCluster("cluster8", self.cluster8cores), DeviceCluster("cluster7", self.cluster7cores), DeviceCluster("cluster6", self.cluster6cores), DeviceCluster("cluster5", self.cluster5cores), DeviceCluster("cluster4", self.cluster4cores), DeviceCluster("cluster3", self.cluster3cores), DeviceCluster("cluster2", self.cluster2cores), DeviceCluster("cluster1", self.cluster1cores), DeviceCluster("cluster0", self.cluster0cores) ]
        smp = CadiSyncSMPDevice(self, "MULTI CLUSTER SMP", clusters)
        self.addDeviceInterface(smp)


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

        self.setModelTraceOptions()

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

    @staticmethod
    def getModelTraceCaptureOptions():
        return DTSLv1.enumOption(
                    name='traceCaptureDevice',
                    displayName='Trace capture method',
                    defaultValue='None',
                    values=[('None', 'No Trace'),('FMTrace', 'Fast Models Trace')])

    @staticmethod
    def getModelTraceStartOptions():
        return DTSLv1.booleanOption(
                    name='startTraceOnConnect',
                    displayName='Start Trace Buffer on connect',
                    defaultValue=True)

    @staticmethod
    def getModelTraceClearOptions():
        return DTSLv1.booleanOption(
                    name='clearTraceOnConnect',
                    displayName='Clear Trace Buffer on connect',
                    defaultValue=True)

    @staticmethod
    def getModelTraceBufferOptions():
        return DTSLv1.enumOption(
                    name='bufferSize',
                    displayName='Trace capture buffer',
                    defaultValue='Buffer16M',
                    values=[
                       ('Buffer16M', '16MB '),
                       ('Buffer32M', '32MB '),
                       ('Buffer64M', '64MB '),
                       ('Buffer128M', '128MB ')])

    @staticmethod
    def getModelTraceWrapOptions():
        return DTSLv1.enumOption(
                    name='traceWrapMode',
                    displayName='Trace full action',
                    defaultValue='wrap',
                    values=[
                      ('wrap', 'Trace wraps on full and continues to store data'),
                      ('stop', 'Trace halts on full')])

    def setModelTraceOptions(self):
        '''Takes the configuration options and configures the
        DTSL objects prior to target connection'''
        self.tracecapture.setClearOnConnect(self.getOptionValue("options.traceBuffer.clearTraceOnConnect"))
        self.tracecapture.setAutoStartTraceOnConnect(self.getOptionValue("options.traceBuffer.startTraceOnConnect"))
        ''' Apply buffer wrap mode'''
        self.tracecapture.setWrapOnFull(True if self.getOptionValue("options.traceBuffer.traceWrapMode") == "wrap" else False)

        ''' Apply buffer size'''
        self.setModelTraceBufferSize(self.getOptionValue("options.traceBuffer.bufferSize"))

        ''' currently disabled until event view added'''
        self.tracecapture.setTraceOption( "INST_START", "OFF")
        self.tracecapture.setTraceOption( "INST_STOP", "OFF")

        ''' Add/Remove the trace capture device as per the status of traceCaptureDevice'''
        if self.getOptionValue("options.traceBuffer.traceCaptureDevice") == "FMTrace":
            if self.tracecapture not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.tracecapture)
        else:
            if self.tracecapture in self.mgdPlatformDevs:
                self.mgdPlatformDevs.remove(self.tracecapture)

        self.setManagedDeviceList(self.mgdPlatformDevs)


    def setModelTraceBufferSize(self, mode):
        '''Configuration option setter method for the buffer size'''
        captureSize =  16*1024*1024
        if (mode == "Buffer16M"):
            captureSize = 16*1024*1024
        if (mode == "Buffer32M"):
            captureSize = 32*1024*1024
        if (mode == "Buffer64M"):
            captureSize = 64*1024*1024
        if (mode == "Buffer128M"):
            captureSize = 128*1024*1024

        self.tracecapture.setMaxCaptureSize(captureSize)

