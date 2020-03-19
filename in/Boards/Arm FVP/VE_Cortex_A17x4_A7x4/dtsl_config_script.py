# Copyright (C) 2014-2017 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceInfo
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

        self.setupCadiBigLittle()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        self.cores = dict()
        self.createModelCore("coretile.cluster0.cpu0", "ARM_Cortex-A17_0", "Cortex-A17")
        self.createModelCore("coretile.cluster0.cpu1", "ARM_Cortex-A17_1", "Cortex-A17")
        self.createModelCore("coretile.cluster0.cpu2", "ARM_Cortex-A17_2", "Cortex-A17")
        self.createModelCore("coretile.cluster0.cpu3", "ARM_Cortex-A17_3", "Cortex-A17")
        self.createModelCore("coretile.cluster1.cpu0", "ARM_Cortex-A7_0", "Cortex-A7")
        self.createModelCore("coretile.cluster1.cpu1", "ARM_Cortex-A7_1", "Cortex-A7")
        self.createModelCore("coretile.cluster1.cpu2", "ARM_Cortex-A7_2", "Cortex-A7")
        self.createModelCore("coretile.cluster1.cpu3", "ARM_Cortex-A7_3", "Cortex-A7")

        self.cluster0cores = []
        self.cluster0cores.append(self.cores["coretile.cluster0.cpu0"])
        self.cluster0cores.append(self.cores["coretile.cluster0.cpu1"])
        self.cluster0cores.append(self.cores["coretile.cluster0.cpu2"])
        self.cluster0cores.append(self.cores["coretile.cluster0.cpu3"])
        self.cluster1cores = []
        self.cluster1cores.append(self.cores["coretile.cluster1.cpu0"])
        self.cluster1cores.append(self.cores["coretile.cluster1.cpu1"])
        self.cluster1cores.append(self.cores["coretile.cluster1.cpu2"])
        self.cluster1cores.append(self.cores["coretile.cluster1.cpu3"])

        self.caches = dict()
        self.caches["coretile.cluster1.cpu0.l1dcache"] = PVCacheDevice(self, self.findDevice("coretile.cluster1.cpu0.l1dcache"), "l1dcache_0")
        self.caches["coretile.cluster1.cpu0.l1icache"] = PVCacheDevice(self, self.findDevice("coretile.cluster1.cpu0.l1icache"), "l1icache_0")
        self.caches["coretile.cluster1.cpu1.l1dcache"] = PVCacheDevice(self, self.findDevice("coretile.cluster1.cpu1.l1dcache"), "l1dcache_1")
        self.caches["coretile.cluster1.cpu1.l1icache"] = PVCacheDevice(self, self.findDevice("coretile.cluster1.cpu1.l1icache"), "l1icache_1")
        self.caches["coretile.cluster1.cpu2.l1dcache"] = PVCacheDevice(self, self.findDevice("coretile.cluster1.cpu2.l1dcache"), "l1dcache_2")
        self.caches["coretile.cluster1.cpu2.l1icache"] = PVCacheDevice(self, self.findDevice("coretile.cluster1.cpu2.l1icache"), "l1icache_2")
        self.caches["coretile.cluster1.cpu3.l1dcache"] = PVCacheDevice(self, self.findDevice("coretile.cluster1.cpu3.l1dcache"), "l1dcache_3")
        self.caches["coretile.cluster1.cpu3.l1icache"] = PVCacheDevice(self, self.findDevice("coretile.cluster1.cpu3.l1icache"), "l1icache_3")
        self.caches["coretile.cluster1.l2_cache"] = PVCacheDevice(self, self.findDevice("coretile.cluster1.l2_cache"), "l2_cache")

        self.addManagedPlatformDevices(self.caches.values())

        self.addPVCache(self.cores["coretile.cluster1.cpu0"], self.caches["coretile.cluster1.cpu0.l1icache"], self.caches["coretile.cluster1.cpu0.l1dcache"], self.caches["coretile.cluster1.l2_cache"])
        self.addPVCache(self.cores["coretile.cluster1.cpu1"], self.caches["coretile.cluster1.cpu1.l1icache"], self.caches["coretile.cluster1.cpu1.l1dcache"], self.caches["coretile.cluster1.l2_cache"])
        self.addPVCache(self.cores["coretile.cluster1.cpu2"], self.caches["coretile.cluster1.cpu2.l1icache"], self.caches["coretile.cluster1.cpu2.l1dcache"], self.caches["coretile.cluster1.l2_cache"])
        self.addPVCache(self.cores["coretile.cluster1.cpu3"], self.caches["coretile.cluster1.cpu3.l1icache"], self.caches["coretile.cluster1.cpu3.l1dcache"], self.caches["coretile.cluster1.l2_cache"])

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
        self.tracecapture.addTraceSource(fmtSource, self.cores["coretile.cluster0.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+1, StreamId+1, "FMT_1")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["coretile.cluster0.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+2, StreamId+2, "FMT_2")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["coretile.cluster0.cpu2"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+3, StreamId+3, "FMT_3")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["coretile.cluster0.cpu3"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+4, StreamId+4, "FMT_4")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["coretile.cluster1.cpu0"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+5, StreamId+5, "FMT_5")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["coretile.cluster1.cpu1"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+6, StreamId+6, "FMT_6")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["coretile.cluster1.cpu2"].getID())
        fmtSource.setEnabled(True)

        fmtSource =  FMTraceSource(self, DeviceId+7, StreamId+7, "FMT_7")
        self.traceSources.append(fmtSource)
        self.tracecapture.addTraceSource(fmtSource, self.cores["coretile.cluster1.cpu3"].getID())
        fmtSource.setEnabled(True)


    def createModelCore(self, deviceName, dtslName, coreDefinition):
        dev = self.findDevice(deviceName)
        connectable = ConnectableDevice(self, dev, dtslName)
        self.cores[deviceName] = connectable
        deviceInfo = DeviceInfo("core", coreDefinition)
        self.cores[deviceName].setDeviceInfo(deviceInfo)

    def exposeCores(self):
        '''Expose cores'''
        self.addDeviceInterface(self.cores["coretile.cluster0.cpu0"])
        self.addDeviceInterface(self.cores["coretile.cluster0.cpu1"])
        self.addDeviceInterface(self.cores["coretile.cluster0.cpu2"])
        self.addDeviceInterface(self.cores["coretile.cluster0.cpu3"])
        self.addDeviceInterface(self.cores["coretile.cluster1.cpu0"])
        self.addDeviceInterface(self.cores["coretile.cluster1.cpu1"])
        self.addDeviceInterface(self.cores["coretile.cluster1.cpu2"])
        self.addDeviceInterface(self.cores["coretile.cluster1.cpu3"])


    def setupCadiSyncSMP(self):
        '''Create SMP device using CADI synchronization'''

        # cluster0 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A17x4 SMP0", self.cluster0cores)
        self.addDeviceInterface(smp)

        # cluster1 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A7x4 SMP1", self.cluster1cores)
        self.addDeviceInterface(smp)


    def setupCadiBigLittle(self):
        # big.LITTLE
        cores = [ DeviceCluster("big", self.cluster0cores), DeviceCluster("LITTLE", self.cluster1cores) ]
        bigLITTLE = CadiSyncSMPDevice(self, "Cortex-A17/A7 big.LITTLE", cores)
        self.addDeviceInterface(bigLITTLE)

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

    def addPVCache(self, dev, l1i, l1d, l2):
        '''Add cache devices'''

        rams = [
            (l1i, 'L1I', CONTENTS), (l1d, 'L1D', CONTENTS),
            (l1i, 'L1ITAG', TAGS), (l1d, 'L1DTAG', TAGS),
            (l2, 'L2', CONTENTS), (l2, 'L2TAG', TAGS)
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

