# Copyright (C) 2015-2017 ARM Limited. All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1, TimestampInfo
from com.arm.debug.dtsl.components import Device, DeviceInfo
from com.arm.debug.dtsl.components import ConnectableTraceSource
from com.arm.debug.dtsl.components import DeviceCluster
from com.arm.debug.dtsl.components import RDDISyncSMPDevice
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETMv3_3TraceSource, ETMv3_4TraceSource, ETMv3_5TraceSource
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl.components import FileTraceCapture
from com.arm.debug.dtsl.components import MEMAP
from com.arm.debug.dtsl.components import DeviceMemoryAccessor
from com.arm.debug.dtsl.impl import INIFile
from com.arm.debug.dtsl import DTSLException
import os.path
from java.lang import StringBuilder
import re

class Metadata():
    def __init__(self, snapshotFile):
        self.snapshotFile = snapshotFile
        self.snapshotPath = os.path.split(snapshotFile)[0]

        self.contents = INIFile.read(snapshotFile)

        # check the version is present and correct
        snapshotInfo = self.contents.getSection("snapshot")
        if snapshotInfo is None:
            raise DTSLException, "Snapshot file %s is missing required section [snapshot]" % self.snapshotFile
        version = snapshotInfo.get("version")
        if version is None:
            raise DTSLException, "Snapshot file %s is missing required version entry in [snapshot] section" % self.snapshotFile
        if version != "1.0":
            # only v1.0
            raise DTSLException, "Snapshot file %s version %s is not supported" % (self.snapshotFile, version)

        # load device data
        self.__buildDeviceInfo()

        # load trace metadata if present
        trace = self.contents.getSection("trace")
        self.traceMetadata = None
        if trace is not None:
            traceMetadataFile = trace.get("metadata")
            if traceMetadataFile is not None:
                traceMetadataPath = os.path.join(self.snapshotPath, traceMetadataFile)
                self.traceMetadata = INIFile.read(traceMetadataPath)


    def getClusters(self):
        # get list of cluster information.  Each entry is tuple (name, [devices])
        clusterInfo = []
        clusterDefs = self.contents.getSection("clusters")
        if clusterDefs is not None:
            for e in clusterDefs.entrySet():
                clusterName = e.getKey()
                clusterDevs = e.getValue()
                clusterInfo.append( (clusterName, [ d.strip() for d in clusterDevs.split(',') ]) )
        return clusterInfo


    def getTraceSourceCores(self):
        # get map of trace sources to cores
        if self.traceMetadata is None:
            # no trace
            return {}
        else:
            traceSourceCores = {}
            # get map of core name -> trace source name and build reverse map
            sourceSection = self.traceMetadata.getSection("core_trace_sources")
            if sourceSection is not None:
                for e in sourceSection.entrySet():
                    coreName = e.getKey()
                    traceSource = e.getValue()
                    # handle association by location tag
                    if traceSource.startswith('@'):
                        location = traceSource[1:]
                        traceSource = self.findDeviceByLocation(location)
                    traceSourceCores[traceSource] = coreName
            return traceSourceCores


    def getTraceSourcesForBuffer(self, buffer):
        # return list of source names in this buffer
        sources = []
        if self.traceMetadata is not None:
            sourceBuffers = self.traceMetadata.getSection("source_buffers")
            if sourceBuffers is not None:
                for e in sourceBuffers.entrySet():
                    traceSource = e.getKey()
                    # only use first buffer if source can be in multiple
                    sourceBuffer = [ b.strip() for b in e.getValue().split(",") ][0]
                    if buffer == sourceBuffer:
                        sources.append(traceSource)
        return sources


    def getTraceBuffers(self):
        # return list of (buffer IDs)
        traceBuffers=[]
        if self.traceMetadata is not None:
            traceBuffersSection = self.traceMetadata.getSection("trace_buffers")
            if traceBuffersSection is not None:
                traceBuffersIDs = traceBuffersSection.get("buffers")
                if traceBuffersIDs is not None:
                    traceBuffers = [ b.strip() for b in traceBuffersIDs.split(",") ]
        return traceBuffers


    def getTraceBufferInfo(self, buffer):
        if self.traceMetadata is None:
            raise DTSLException, "Snapshot %s does not contain trace metadata" % self.snapshotFile
        bufferMetadata = self.traceMetadata.getSection(buffer)
        if bufferMetadata is None:
            raise DTSLException, "Snapshot %s does not contain metadata for trace buffer %s" % (self.snapshotFile, buffer)
        return bufferMetadata


    def getTraceTimestampInfo(self):
        if self.traceMetadata is None:
            return None
        else:
            return self.traceMetadata.getSection("timestamp")


    def findDeviceByLocation(self, location):
        found = None
        for name, info in self.__deviceInfo.iteritems():
            if info.get('location', None) == location:
                if found is None:
                    found = name
                else:
                    raise DTSLException, "Snapshot %s contains multiple devices with location \"%s\"" % (self.snapshotFile, location)
        if found is None:
            raise DTSLException, "Snapshot %s does not contain device with location \"%s\"" % (self.snapshotFile, location)
        return found


    def getDevices(self):
        return self.__deviceNames


    def getDeviceInfo(self, dev):
        return self.__deviceInfo.get(dev)


    def __buildDeviceInfo(self):
        self.__deviceNames = []
        self.__deviceInfo = {}
        devices = self.contents.getSection("device_list")
        if devices is not None:
            devID = 1
            for r in devices.entrySet():
                devName = "UNKNOWN"
                devIni = r.getValue()
                devInfo = INIFile.read(os.path.join(self.snapshotPath, devIni))
                devGlobals = devInfo.getSection("device")
                devInfo = {}
                if devGlobals is not None:
                    for e in devGlobals.entrySet():
                        devInfo[e.getKey().strip()] = e.getValue().strip()
                if "name" in devInfo:
                    devName = devInfo["name"]

                # add device ID
                devInfo['id'] = devID
                devID += 1

                self.__deviceNames.append(devName)
                self.__deviceInfo[devName] = devInfo



class Snapshot(DTSLv1):
    @staticmethod
    def getOptionList():
        return [ ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # core dump location is connection address
        self.__snapshotFile = self.getConnectionAddress()
        self.__snapshotPath = os.path.split(self.__snapshotFile)[0]

        # Read metadata from snapshot .ini files
        self.__metadata = Metadata(self.__snapshotFile)

        # Create cores, trace sources and trace captures and MEMAP accessors
        self.createMemAccessors()
        self.createCores()
        self.createTraceSources()
        self.createTraceBuffers()

        # Report timestamp information if provided
        timestampInfo = self.__metadata.getTraceTimestampInfo()
        if timestampInfo is not None and 'frequency' in timestampInfo:
            freq = int(timestampInfo['frequency'])
            self.setTimestampInfo(TimestampInfo(freq))

        # automatically connect to trace sources and trace captures
        mgdDevs = []
        for source in self.traceSources.values():
            mgdDevs.append(source)
        for traceCapture in self.fileTraces:
            mgdDevs.append(traceCapture)
        self.setManagedDevices(mgdDevs)

    def createMemAccessors(self):
        self.memAccessors = []
        MEMAPInfo = self.getDevicesOfClass("memory")
        for MEMAPAccessor in MEMAPInfo:
            memap = self.makeMemAccessDevice(MEMAPAccessor)
            accessor = DeviceMemoryAccessor(memap.getName(), memap, "Memory access via " + memap.getName())
            self.memAccessors.append(accessor)

    def createCores(self):
        # Find all the cores
        coreInfo = self.getDevicesOfClass("core")

        if len(coreInfo) > 1:
            # create SMP device if more than one core is present
            clusterDefs = self.__metadata.getClusters()
            if clusterDefs:
                # snapshot defines cluster topology
                clusterInfos = []
                for clusterName, clusterDevNames in clusterDefs:
                    clusterDevs = []
                    for devName in clusterDevNames:
                        dev = self.makeCore(devName)
                        clusterDevs.append(dev)
                    clusterInfos.append(DeviceCluster(clusterName, clusterDevs))
                if len(clusterInfos) == 1:
                    # flatten single cluster
                    smp = RDDISyncSMPDevice(self, "SMP", clusterInfos[0].getDevices())
                else:
                    smp = RDDISyncSMPDevice(self, "SMP", clusterInfos)

            else:
                # no explicit cluster definition: create cluster of all cores
                cores = []
                for c in coreInfo:
                    dev = self.makeCore(c)
                    cores.append(dev)
                smp = RDDISyncSMPDevice(self, "SMP", cores)

            self.addDeviceInterface(smp)
            smp.registerAddressFilters(self.memAccessors)

        elif len(coreInfo) == 1:
            # only one core: present as single device
            dev = self.makeCore(coreInfo[0])
            self.addDeviceInterface(dev)
            dev.registerAddressFilters(self.memAccessors)

        else:
            raise DTSLException, "No cores found in snapshot %s" % self.__snapshotFile


    def createTraceSources(self):
        # Find and create all the trace sources
        self.traceSources = {}
        traceSourceInfo = self.getDevicesOfClass("trace_source")
        for traceSource in traceSourceInfo:
            source = self.makeTraceSource(traceSource)
            source.setSnapshotMode(True)
            source.setEnabled(True)
            self.traceSources[traceSource] = source


    def createTraceBuffers(self):
        '''Setup file trace capture'''

        # build map of cores associated with each source
        self.__traceSourceCores = self.__metadata.getTraceSourceCores()

        # create trace capture instances for each buffer in snapshot
        self.fileTraces = []
        traceBuffers = self.__metadata.getTraceBuffers()
        for bufferID in traceBuffers:
            # get buffer info from snapshot
            bufferMetadata = self.__metadata.getTraceBufferInfo(bufferID)
            bufferName = bufferMetadata.get("name")
            bufferFormat = bufferMetadata.get("format")

            # check the buffer exists
            bufferFile = bufferMetadata.get("file")
            if bufferName is None or bufferFile is None:
                raise DTSLException, "Snapshot %s does not contain valid metadata for trace buffer %s" % (self.__snapshotFile, bufferID)
            bufferPath = os.path.join(self.__snapshotPath, bufferFile)
            if not os.path.exists(bufferPath):
                raise DTSLException, "Snapshot %s does not contain trace buffer file %s" % (self.__snapshotFile, bufferFile)

            # create the trace capture instance
            fileTrace = FileTraceCapture(self, bufferName)
            fileTrace.setRequireUniqueStreamIDs(False)
            fileTrace.setTraceFile(bufferPath)
            fileTrace.setTraceFormat(bufferFormat)

            # add associated trace sources
            traceSourceNames = self.__metadata.getTraceSourcesForBuffer(bufferName)
            if not traceSourceNames and len(traceBuffers) == 1:
                traceSourceNames = self.getDevicesOfClass("trace_source")
            traceSources = []
            for sourceName in traceSourceNames:
                source = self.traceSources.get(sourceName)
                if source is None:
                    # Metadata associates an unknown source with this buffer - ignore and continue
                    continue
                traceSources.append(source)
            self.registerTraceSources(fileTrace, traceSources)

            self.addTraceCaptureInterface(fileTrace)
            self.fileTraces.append(fileTrace)


    def registerTraceSources(self, traceCapture, traceSources):
        # register trace sources with trace capture
        for source in traceSources:
            coreName = self.__traceSourceCores.get(source.getName(), None)
            if coreName:
                traceCapture.addTraceSource(source, coreName)
            else:
                traceCapture.addTraceSource(source)


    def getTraceCaptureForSource(self, source):
        # get the capture device for the trace source
        for c in self.fileTraces:
            if c.getTraceSources().contains(source):
                return c
        return None


    def getDevicesOfClass(self, devClass):
        # get list of names of device of a given class
        return [ name
                for name in self.__metadata.getDevices()
                if self.__metadata.getDeviceInfo(name).get('class', '').lower() == devClass.lower() ]


    def makeMemAccessDevice(self, devName):
        devInfo = self.__metadata.getDeviceInfo(devName)
        if devInfo is None:
            raise DTSLException, "Snapshot %s does not contain device %s" % (self.__snapshotFile, devName)
        accessor = MEMAP(self, devInfo['id'], devName)
        return accessor

    def makeCore(self, devName):
        # create a core
        devInfo = self.__metadata.getDeviceInfo(devName)
        if devInfo is None:
            raise DTSLException, "Snapshot %s does not contain device %s" % (self.__snapshotFile, devName)

        dev = Device(self, devInfo['id'], devName)

        # add information about class and type
        devClass = devInfo.get('class', '')
        devType = devInfo.get('type', '')
        info = DeviceInfo(devClass, devType)
        dev.setDeviceInfo(info)

        return dev


    def makeTraceSource(self, devName):
        # create a trace source
        devInfo = self.__metadata.getDeviceInfo(devName)
        if devInfo is None:
            raise DTSLException, "Unknown device %s" % devName

        # use the type information in the metadata to create the appropriate
        # DTSL object for this trace source. Use ConnectableTraceSource if no
        # specific source found
        klass = ConnectableTraceSource
        srcType = devInfo.get('type').lower()
        if srcType.startswith('pft') or srcType.startswith('ptm'):
            klass = PTMTraceSource
        elif srcType.startswith('etm3.5'):
            klass = ETMv3_5TraceSource
        elif srcType.startswith('etm3.4'):
            klass = ETMv3_4TraceSource
        elif srcType.startswith('etm3.3'):
            klass = ETMv3_3TraceSource
        elif srcType.startswith('etm4'):
            klass = ETMv4TraceSource
        elif srcType.startswith('itm'):
            klass = ITMTraceSource
        elif srcType.startswith('stm'):
            klass = STMTraceSource
        # stream ID is read from register image
        return klass(self, devInfo['id'], 1, devName)
