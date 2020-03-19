from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DeviceCluster
from com.arm.debug.dtsl.components import RDDISyncSMPDevice
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl.components import FileTraceCapture
from com.arm.debug.dtsl.trace import CSLIBTraceDumpMetadata
from com.arm.debug.dtsl import DTSLException
import re
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
        # Associations between cores and trace sources
        self.__traceSourceCores = {}

        deviceList = self.getDeviceList()

        # Find all the cores: named cpu_0, cpu_1, ..., cpu_N
        coreInfo = self.getDevicesOfName("cpu", deviceList)

        if len(coreInfo) > 1:
            # create individual and SMP devices if more than one core is present

            # Put CPUs into 4 core clusters to match real hardware
            # cpu_0..3 are in cluster 0, cpu_4..7 in cluster 1, ...
            clusters = [ [], [], [], [] ]
            for devNum, name in coreInfo:
                coreNum = int(name[4:])
                clusterNum = coreNum / 4
                dev = Device(self, devNum, name)
                clusters[clusterNum].append(dev)
                self.addDeviceInterface(dev)
                self.__traceSourceCores['PTM_%d' % coreNum] = name

            clusterInfos = [ ]
            for c in range(len(clusters)):
                if len(clusters[c]) > 0:
                    clusterInfos.append(DeviceCluster("Cluster %d" % c, clusters[c]))

            smp = RDDISyncSMPDevice(self, "cpu", clusterInfos)
            self.addDeviceInterface(smp)

        elif len(coreInfo) == 1:
            # only one core: present as "cpu"
            devNum, name = coreInfo[0]
            dev = Device(self, devNum, "cpu")
            self.addDeviceInterface(dev)
            self.__traceSourceCores['PTM_0'] = "cpu"
        else:
            raise DTSLException, "No cores found"

        # Find all the trace sources
        streamID = 1
        self.clusterTraceSources = [ [], [], [], [] ]
        for devNum, name in self.getDevicesOfName("PTM", deviceList):
            m = re.match('(\d+)_\d+', name[4:])
            if m:
                clusterNum = int(m.group(1))
            else:
                ptmNum = int(name[4:])
                clusterNum = ptmNum / 4
            ptm = PTMTraceSource(self, devNum, streamID, name)
            self.clusterTraceSources[clusterNum].append(ptm)
            streamID += 1

        # STMs
        self.ccnSTM = []
        if 'STM_ccn' in deviceList:
            devNum = deviceList.index('STM_ccn')+1
            self.ccnSTM.append(STMTraceSource(self, devNum, streamID, 'STM_ccn'))
            streamID += 1
        self.sysSTM = []
        if 'STM_sys' in deviceList:
            devNum = deviceList.index('STM_sys')+1
            self.sysSTM.append(STMTraceSource(self, devNum, streamID, 'STM_sys'))
            streamID += 1


    def setupFileTrace(self):
        '''Setup file trace capture'''

        self.fileTraces = {}
        for i in range(4):
            name = "File_%d" % i
            self.fileTraces[name] = self.makeFileTrace(name, self.clusterTraceSources[i])
        self.fileTraces["File_ccn"] = self.makeFileTrace("File_ccn", self.ccnSTM)
        self.fileTraces["File_sys"] = self.makeFileTrace("File_sys", self.sysSTM)


    def makeFileTrace(self, name, traceSources):

        fileTrace = FileTraceCapture(self, name)

        self.addTraceCaptureInterface(fileTrace)

        self.registerTraceSources(fileTrace, traceSources)

        for s in traceSources:
            s.setSnapshotMode(True)
            s.setEnabled(True)

        return fileTrace


    def openFileTrace(self):

        # core dump location is connection address
        snapshotFile = self.getConnectionAddress()
        snapshotPath = os.path.split(snapshotFile)[0]

        # reset file trace
        for fileTrace in self.fileTraces.values():
            fileTrace.setTraceFile(None)

        # load metadata
        activeFileTraces = []
        if snapshotPath:
            metadata = CSLIBTraceDumpMetadata.read(snapshotFile)

            for dump in metadata.getTraceDumpMetadata().keySet():
                dumpFile = os.path.join(snapshotPath, dump)
                dumpMetadata = metadata.getTraceDumpMetadata().get(dump)
                dumpFormat = dumpMetadata.get("format")
                dumpComponent = dumpMetadata.get("component")

                fileTrace = self.mapComponentToFileTrace(dumpComponent)
                if fileTrace:
                    fileTrace.setTraceFile(dumpFile)
                    fileTrace.setTraceFormat(dumpFormat)
                    activeFileTraces.append(fileTrace.getName())
                    self.addManagedTraceDevices(fileTrace.getName(), [ fileTrace ])
        self.setManagedDevices(self.getManagedDevices(activeFileTraces))


    def mapComponentToFileTrace(self, component):
        if component.startswith("ETB_"):
            fileName = "File_" + component[4:]
            return self.fileTraces.get(fileName)
        else:
            return None


    def registerTraceSources(self, traceCapture, traceSources):
        for source in traceSources:
            coreName = self.__traceSourceCores.get(source.getName(), None)
            if coreName:
                self.registerCoreTraceSource(traceCapture, coreName, source)
            else:
                self.registerTraceSource(traceCapture, source)


    def getTraceCaptureForSource(self, source):
        # get the capture device for the trace source
        for c in self.fileTraces.values():
            if c.getTraceSources().contains(source):
                return c
        return None


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


    def getManagedDevices(self, traceKeys):
        '''Get the required set of managed devices for this configuration'''
        managedDevices = set()
        managedDevices |= self.mgdPlatformDevs
        for traceKey in traceKeys:
            managedDevices |= self.mgdTraceDevs.get(traceKey, set())
        return managedDevices

