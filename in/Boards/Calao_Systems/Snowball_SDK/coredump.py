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
from java.lang import StringBuilder

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
        deviceList = self.getDeviceList()

        # Find all the cores: named cpu_0, cpu_1, ..., cpu_N
        coreInfo = self.getDevicesOfName("cpu", deviceList)

        if len(coreInfo) > 1:
            # create individual and SMP devices if more than one core is present
            cores = []
            for devNum, name in coreInfo:
                dev = Device(self, devNum, name)
                cores.append(dev)
                self.addDeviceInterface(dev)

            smp = RDDISyncSMPDevice(self, "cpu", cores)
            self.addDeviceInterface(smp)

        else:
            # only one core: present as "cpu"
            devNum, name = coreInfo[0]
            dev = Device(self, devNum, "cpu")
            self.addDeviceInterface(dev)

        # Find all the trace sources
        streamID = 1
        self.traceSources = []
        for devNum, name in self.getDevicesOfName("PTM", deviceList):
            ptm = PTMTraceSource(self, devNum, streamID, name)
            self.traceSources.append(ptm)
            streamID += 1

        # Define associations between cores and trace sources
        if len(coreInfo) > 1:
            self.__traceSourceCores = {
                'PTM_0': 'cpu_0',
                'PTM_1': 'cpu_1',
            }
        else:
            self.__traceSourceCores = {
                'PTM_0': 'cpu',
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
            if coreName:
                self.registerCoreTraceSource(traceCapture, coreName, source)
            else:
                self.registerTraceSource(traceCapture, source)


    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+


    def getDeviceList(self):
        '''Get the list of devices reported by the connection'''
        devices = []
        numDevices = self.getDebug().getDeviceCount()
        for i in range(1, numDevices+1):
            name = StringBuilder(256)
            self.getDebug().getDeviceDetails(i, name, None)
            devices.append(name.toString())
        return devices


    def getDevicesOfName(self, prefix, deviceList):
        '''Get all devices of with a name starting with prefix from deviceList
        yields (device number, name) tuples
        '''
        return [ (devIndex+1, name)
                 for devIndex, name in enumerate(deviceList)
                 if name.startswith(prefix) ]


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

