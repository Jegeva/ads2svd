from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceCluster
from com.arm.debug.dtsl.components import RDDISyncSMPDevice
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import FileTraceCapture
from com.arm.debug.dtsl.trace import CSLIBTraceDumpMetadata
from com.arm.debug.dtsl import DTSLException
import os.path

class Coredump(DTSLv1):
    @staticmethod
    def getOptionList():
        return [ ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)
        # tracks which devices are always managed
        self.mgdPlatformDevs = set()
        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}
        self.discoverDevices()
        self.setupFileTrace()
        self.openFileTrace()

    def discoverDevices(self):
        # cores
        self.cores = []
        cortexA15s = []
        cortexA7s = []
        for name in ["Cortex-A15_0", "Cortex-A15_1"]:
            devID = self.findDevice(name)
            core = Device(self, devID, name)
            self.cores.append(core)
            cortexA15s.append(core)
            self.addDeviceInterface(core)
        for name in ["Cortex-A7_0", "Cortex-A7_1", "Cortex-A7_2"]:
            devID = self.findDevice(name)
            core = Device(self, devID, name)
            self.cores.append(core)
            cortexA7s.append(core)
            self.addDeviceInterface(core)
        # SMP sync groups
        smpA7 = RDDISyncSMPDevice(self, "smp_a7", cortexA7s)
        self.addDeviceInterface(smpA7)
        smpA15 = RDDISyncSMPDevice(self, "smp_a15", cortexA15s)
        self.addDeviceInterface(smpA15)
        # big.LITTLE
        clusters = [ DeviceCluster("big", cortexA15s), DeviceCluster("LITTLE", cortexA7s) ]
        bl = RDDISyncSMPDevice(self, "smp_bl", clusters)
        self.addDeviceInterface(bl)
        # Find all the trace sources
        streamID = 1
        self.traceSources = []
        for name in ["PTM_0", "PTM_1"]:
            devID = self.findDevice(name)
            ptm = PTMTraceSource(self, devID, streamID, name)
            self.traceSources.append(ptm)
            streamID += 1
        for name in ["ETM_0", "ETM_1", "ETM_2"]:
            devID = self.findDevice(name)
            etm = ETMv3_5TraceSource(self, devID, streamID, name)
            self.traceSources.append(etm)
            streamID += 1
        for name in ["ITM_0"]:
            devID = self.findDevice(name)
            itm = ITMTraceSource(self, devID, streamID, name)
            self.traceSources.append(itm)
            streamID += 1
        # Define associations between cores and trace sources
        self.__traceSourceCores = {
            'PTM_0': 'Cortex-A15_0',
            'PTM_1': 'Cortex-A15_1',
            'ETM_0': 'Cortex-A7_0',
            'ETM_1': 'Cortex-A7_1',
            'ETM_2': 'Cortex-A7_2'
        }


    def setupFileTrace(self):
        '''Setup file trace capture'''
        self.fileTrace = FileTraceCapture(self, "File")
        self.addTraceCaptureInterface(self.fileTrace)
        self.registerTraceSources(self.fileTrace)
        for s in self.fileTrace.getTraceSources():
            s.setSnapshotMode(True)
            s.setEnabled(True)
        self.addManagedTraceDevices(self.fileTrace.getName(), [ self.fileTrace ])


    def openFileTrace(self):
        # core dump location is connection address
        snapshotFile = self.getConnectionAddress()
        snapshotPath = os.path.split(snapshotFile)[0]
        # reset file trace
        traceMode = "None"
        self.fileTrace.setTraceFile(None)
        # load metadata
        if snapshotPath:
            metadata = CSLIBTraceDumpMetadata.read(snapshotFile)
            for dump in metadata.getTraceDumpMetadata().keySet():
                dumpFile = os.path.join(snapshotPath, dump)
                dumpMetadata = metadata.getTraceDumpMetadata().get(dump)
                dumpFormat = dumpMetadata.get("format")
                self.fileTrace.setTraceFile(dumpFile)
                self.fileTrace.setTraceFormat(dumpFormat)
                traceMode = "File"
                break
        self.setManagedDevices(self.getManagedDevices(traceMode))


    def registerTraceSources(self, traceCapture):
        for source in self.traceSources:
            coreName = self.__traceSourceCores.get(source.getName(), None)
            if coreName is not None:
                self.registerCoreTraceSource(traceCapture, coreName, source)
            else:
                self.registerTraceSource(traceCapture, source)


    def registerCoreTraceSource(self, traceCapture, coreName, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, coreName)

        # source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])


    def registerTraceSource(self, traceCapture, source):
        '''Register trace source with trace capture device'''
        traceCapture.addTraceSource(source)
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])


    def addManagedTraceDevices(self, traceKey, devs):
        '''Add devices to the set of devices managed by the configuration for this trace mode'''
        traceDevs = self.mgdTraceDevs.get(traceKey)
        if not traceDevs:
            traceDevs = set()
            self.mgdTraceDevs[traceKey] = traceDevs
        for d in devs:
            traceDevs.add(d)


    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())


    def getTraceCaptureForSource(self, source):
        # get the capture device for the trace source
        return self.fileTrace

