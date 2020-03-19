from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import APBAP, AXIAP, AXIMemAPAccessor, AxBMemAPAccessor, CSCTI, CSDAP, CSFunnel, CTISyncSMPDevice, Device, DeviceCluster, FormatterMode, MemoryRouter, PTMTraceSource, RDDISyncSMPDevice, STMRegisters, STMTraceSource, TMCETBTraceCapture
from jarray import zeros
from struct import unpack, pack

# import core specific functions from Cores folder
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a15_rams

from com.arm.rddi import RDDI, RDDI_ACC_SIZE

CLUSTER_SIZES = [ 4, 4, 4, 4 ]
NUM_CLUSTERS = len(CLUSTER_SIZES)

ATB_ID_BASE = 2
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
useCTIsForSMP = True
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
CORTEX_A15_TRACE_OPTIONS = 0


class STMImpl(STMTraceSource):
    def postConnect(self):
        STMTraceSource.postConnect(self)
        self.setControlReg(False)

    def traceStart(self, traceCapture):
        self.setControlReg(True)

    def traceStop(self, traceCapture):
        self.setControlReg(False)

    def setControlReg(self, traceEnabled):
        # Disable trace
        crVal = self.readRegister(STMRegisters.STMTCSR)
        crVal &= ~STMRegisters.STMTCSR_EN
        self.writeRegister(STMRegisters.STMTCSR, crVal)
        if traceEnabled:
            # Enable all h/w event trace inputs
            self.writeRegister(STMRegisters.STMIDBLK0+STMRegisters.STMHW_EventEnable, 0xFFFFFFFF)
            # Disable all h/w events from generating a trigger
            self.writeRegister(STMRegisters.STMIDBLK0+STMRegisters.STMHW_TriggerEnable, 0x00000000)
            # enable h/w event trace
            self.writeRegister(STMRegisters.STMIDBLK0+STMRegisters.STMHW_MainControl, 0x00000001)
            # set SYNC frequency
            self.writeRegister(STMRegisters.STMSYNCR, 0x00000200)
            # set Timetamp frequency
            self.writeRegister(STMRegisters.STMTSFREQR, 25000000)
            # Set STM ATBID
            crVal &= ~STMRegisters.STMTCSR_TRACEID_MASK
            crVal |= (((self.streamID() << STMRegisters.STMTCSR_TRACEID_SHIFT) & STMRegisters.STMTCSR_TRACEID_MASK))
            # Enable h/w event trace
            crVal |= STMRegisters.STMTCSR_HWTEN
            # Enable timestanps
            crVal |= STMRegisters.STMTCSR_TSEN
            # Enable periodinc SYNC
            crVal |= STMRegisters.STMTCSR_SYNCEN
            # Enable STM
            crVal |= STMRegisters.STMTCSR_EN
            self.writeRegister(STMRegisters.STMTCSR, crVal)


class TraceRangeOptions:
    def __init__(self, cluster = None, coreTraceName = None, dtsl = None):
        if coreTraceName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("options.trace_%d.%s.traceRange" % (cluster, coreTraceName))
            self.traceRangeStart = dtsl.getOptionValue("options.trace_%d.%s.traceRange.start" % (cluster, coreTraceName))
            self.traceRangeEnd = dtsl.getOptionValue("options.trace_%d.%s.traceRange.end" % (cluster, coreTraceName))
            self.traceRangeIDs = None

    def defaultSetup(self):
        self.traceRangeEnable = False
        self.traceRangeStart = None
        self.traceRangeEnd = None
        self.traceRangeIDs = None


class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace_%d" % c, "Cluster %d Trace" %c, childOptions=
                    [ DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                          values = [("none", "None"), ("ETB_%d" % c, "On Chip Trace Buffer (ETB)")]),
                     DTSLv1.booleanOption('cortexA15coreTrace', 'Enable Cortex-A15 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A15_%d' % core,
                                                   "Enable Cortex-A15 %d trace" % core, defaultValue=True)
                              for core in range(CLUSTER_SIZES[c]) ] +
                            # Pull in common options for PTMs (cycle accurate etc)
                            PTMTraceSource.defaultOptions(DtslScript.getPTMsForCluster(c)) +
                            [ # Trace range selection (e.g. for linux kernel)
                            DTSLv1.booleanOption('traceRange', 'Trace capture range',
                                description=TRACE_RANGE_DESCRIPTION,
                                defaultValue = False,
                                childOptions = [
                                    DTSLv1.integerOption('start', 'Start address',
                                        description='Start address for trace capture',
                                        defaultValue=0,
                                        display=IIntegerOption.DisplayFormat.HEX),
                                    DTSLv1.integerOption('end', 'End address',
                                        description='End address for trace capture',
                                        defaultValue=0xFFFFFFFF,
                                        display=IIntegerOption.DisplayFormat.HEX)
                                ])
                            ]
                        ),
                ])
                for c in range(NUM_CLUSTERS)
            ]+  [ DtslScript.generateClusterRAMsTab() ] + [
                DTSLv1.tabPage("trace_sys", "System Trace", childOptions=[
                     DTSLv1.booleanOption('sys', 'System STM trace', defaultValue=False),
                     DTSLv1.booleanOption('ccn', 'CCN-504 STM trace', defaultValue=False),
                     ])
            ])
        ]

    @staticmethod
    def generateClusterRAMsTab():
        return  DTSLv1.tabPage("cacheRams", "Cache RAMs", childOptions =[
                    DTSLv1.optionGroup("cluster_%d" % x, "Cluster %d" % x, childOptions = [
                        # Turn cache debug mode on/off for a single core
                        DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                             description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                             defaultValue=False, isDynamic=True),
                        DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                             description='Preserve the contents of caches while the core is stopped.',
                                             defaultValue=False, isDynamic=True),
                    ])
                    for x in range(NUM_CLUSTERS)
                 ])

    def getTraceCaptureForSource(self, source):
        for i in range(NUM_CLUSTERS):
            if source in self.PTMs[i]:
                return self.getTraceCaptureFromOption("options.trace_%d.traceCapture" % i)

        if source is self.systemSTM and self.getOptionValue("options.trace_sys.sys"):
            return self.systemETB

        if source is self.ccnSTM and self.getOptionValue("options.trace_sys.ccn"):
            return self.ccnETB

        return None

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # only APB/AXI devices managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.axi)
        self.mgdPlatformDevs.add(self.apb)

        self.exposeCores()

        self.setupSMP()

        self.setupSystemETBTrace()
        self.setupCCNETBTrace()
        for c in range(NUM_CLUSTERS):
            self.setupClusterETBTrace(c)

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-A15 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''find and create devices'''

        axiDev = self.findDevice("CSMEMAP")
        self.axi = AXIAP(self, axiDev, "AXI-AP")

        apbDev = self.findDevice("CSMEMAP", axiDev+1)
        self.apb = APBAP(self, apbDev, "APB-AP")

        cortexA15coreDev = 0
        self.cortexA15cores = [ [] for i in range(NUM_CLUSTERS) ]

        streamID = ATB_ID_BASE

        # System STM
        stmDev = self.findDevice("CSSTM")
        self.systemSTM = STMImpl(self, stmDev, streamID, "STM_sys")
        streamID += 1

        # CCN-504 STM
        stmDev = self.findDevice("CSSTM", stmDev+1)
        self.ccnSTM = STMImpl(self, stmDev, streamID, "STM_ccn")
        streamID += 1

        # CTI for ETB0 & ETB1
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI_0 = CSCTI(self, outCTIDev, "CTI_out_0")

        if NUM_CLUSTERS > 2:
            # CTI for ETB2 & ETB3
            outCTIDev = self.findDevice("CSCTI", outCTIDev+1)
            self.outCTI_1 = CSCTI(self, outCTIDev, "CTI_out_1")

        # CTI for System STM
        sysCTIDev = self.findDevice("CSCTI", outCTIDev+1)
        self.systemCTI = CSCTI(self, sysCTIDev, "CTI_sys")

        # CTI for CCN-504 STM
        ccnCTIDev = self.findDevice("CSCTI", sysCTIDev+1)
        self.ccnCTI = CSCTI(self, ccnCTIDev, "CTI_ccn")

        # ETBs (TMCs)
        etbDev = 0
        self.ETBs = []
        for c in range(NUM_CLUSTERS):
            etbDev = self.findDevice("CSTMC", etbDev+1)
            self.ETBs.append(TMCETBTraceCapture(self, etbDev, "ETB_%d" % c))

        # ETB for System STM
        etbDev = self.findDevice("CSTMC", etbDev+1)
        self.systemETB = TMCETBTraceCapture(self, etbDev, "ETB_sys")

        # ETB for System CCN-504
        etbDev = self.findDevice("CSTMC", etbDev+1)
        self.ccnETB = TMCETBTraceCapture(self, etbDev, "ETB_ccn")

        funnelDev = 0
        self.funnels = []

        coreCTIDev = ccnCTIDev
        self.coreCTIs = [ [] for i in range(NUM_CLUSTERS) ]
        self.cortexA15ctiMap = {} # map cores to associated CTIs
        ptmDev = 1
        self.PTMs = [ [] for i in range(NUM_CLUSTERS) ]
        funnelDev = 1
        for c in range(NUM_CLUSTERS):
            for i in range(CLUSTER_SIZES[c]):
                # create core
                cortexA15coreDev = self.findDevice("Cortex-A15", cortexA15coreDev+1)
                dev = a15_rams.A15CoreDevice(self, cortexA15coreDev, "Cortex-A15_%d_%d" % (c, i))
                self.cortexA15cores[c].append(dev)

                # create CTI for this core
                coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
                coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (c, i))
                self.coreCTIs.append(coreCTI)
                self.cortexA15ctiMap[dev] = coreCTI

                # create the PTM for this core
                ptmDev = self.findDevice("CSPTM", ptmDev+1)
                ptm = PTMTraceSource(self, ptmDev, streamID, "PTM_%d_%d" % (c, i))
                streamID += 1
                # disabled by default - will enable with option
                ptm.setEnabled(False)
                self.PTMs[c].append(ptm)

            # Funnel
            funnelDev = self.findDevice("CSTFunnel", funnelDev+1)
            self.funnels.append(self.createFunnel(funnelDev, "Funnel_%d" % c))


    def exposeCores(self):
        for cluster in self.cortexA15cores:
            for core in cluster:
                a15_rams.registerInternalRAMs(core, self.axi)
                self.registerFilters(core)
                self.addDeviceInterface(core)


    def createSMPDevice(self, cores, clusters, name):
        # create SMP device and expose from configuration
        if useCTIsForSMP:
            ctiInfo = {}
            ctis = []
            for c in cores:
                cti = self.cortexA15ctiMap[c]
                # use standard Cortex event mapping : in/out on trigger 0 for stop, out on trigger 7 for start
                ctiInfo[c] = CTISyncSMPDevice.DeviceCTIInfo(cti, CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
                ctis.append(cti)
            smp = CTISyncSMPDevice(self, name, clusters, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
            # automatically handle connection to CTIs
            self.addManagedPlatformDevices(ctis)
        else:
            smp = RDDISyncSMPDevice(self, name, clusters)

        self.registerFilters(smp)
        self.addDeviceInterface(smp)


    def setupSMP(self):
        '''Create SMP device using RDDI synchronization'''

        for c in range(NUM_CLUSTERS):
            cores = self.cortexA15cores[c]
            self.createSMPDevice(cores, cores, "Cortex-A15_%d" % c)

        clusterMap = [ DeviceCluster("Cluster %d" % c, self.cortexA15cores[c]) for c in range(NUM_CLUSTERS) ]
        allCores = [ core for cluster in self.cortexA15cores for core in cluster ]
        self.createSMPDevice(allCores, clusterMap, "Cortex-A15_all")


    def setupSystemETBTrace(self):
        # use continuous mode
        self.systemETB.setFormatterMode(FormatterMode.CONTINUOUS)

        # register ETB with configuration
        self.addTraceCaptureInterface(self.systemETB)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETB_sys", [ self.systemCTI, self.systemETB ])

        # register trace sources
        self.registerTraceSource(self.systemETB, self.systemSTM)


    def setupCCNETBTrace(self):
        # use continuous mode
        self.ccnETB.setFormatterMode(FormatterMode.CONTINUOUS)

        # register ETB with configuration
        self.addTraceCaptureInterface(self.ccnETB)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETB_ccn", [ self.ccnCTI, self.ccnETB ])

        # register trace sources
        self.registerTraceSource(self.ccnETB, self.ccnSTM)

    def getOutCTI(self, cluster):
        # return outCTI_0 for cluster 0 and 1, outCTI_1 for cluster 2 and 3

        ctiMap = {}
        ctiMap[0] = self.outCTI_0
        ctiMap[1] = self.outCTI_0

        if NUM_CLUSTERS > 2:
            ctiMap[2] = self.outCTI_1
            ctiMap[3] = self.outCTI_1

        return ctiMap.get(cluster, None)



    def setupClusterETBTrace(self, c):
        '''Setup ETB trace capture'''

        # use continuous mode
        self.ETBs[c].setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETB and register ETB with configuration
        self.ETBs[c].setTraceComponentOrder([ self.funnels[c] ])
        self.addTraceCaptureInterface(self.ETBs[c])

        # automatically handle connection/disconnection to trace components
        outCTI = self.getOutCTI(c)
        self.addManagedTraceDevices("ETB_%d" % c, [ self.funnels[c], outCTI, self.ETBs[c] ])

        # register trace sources
        self.registerClusterTraceSources(c, self.ETBs[c])


    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == self.ETBs[0]:
            # ETB 0 trigger input is CTI_0 out 1
            return (self.outCTI_0, 1, CTM_CHANNEL_TRACE_TRIGGER)
        elif NUM_CLUSTERS > 1 and sink == self.ETBs[1]:
            # ETB 1 trigger input is CTI_0 out 3
            return (self.outCTI_0, 3, CTM_CHANNEL_TRACE_TRIGGER)
        if NUM_CLUSTERS > 2 and sink == self.ETBs[2]:
            # ETB 2 trigger input is CTI_1 out 1
            return (self.outCTI_1, 1, CTM_CHANNEL_TRACE_TRIGGER)
        elif NUM_CLUSTERS > 3 and sink == self.ETBs[3]:
            # ETB 3 trigger input is CTI_1 out 3
            return (self.outCTI_1, 3, CTM_CHANNEL_TRACE_TRIGGER)
        elif sink == self.systemETB:
            # system ETB trigger input is CTI out 1
            return (self.systemCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)
        elif sink == self.ccnETB:
            # ccn ETB trigger input is CTI out 1
            return (self.ccnCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)

        # no associated CTI
        return (None, None, None)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a source
        return (None, None, None) if no associated CTI
        '''
        for c in range(NUM_CLUSTERS):
            if source in self.PTMs[c]:
                coreNum = self.PTMs[c].index(source)
                # PTM trigger is on input 6
                if coreNum < len(self.coreCTIs[c]):
                    return (self.coreCTIs[c][coreNum], 6, CTM_CHANNEL_TRACE_TRIGGER)

        # Use TRIGOUTSPTE signal
        if source == self.systemSTM:
            return (self.systemCTI, 2, CTM_CHANNEL_TRACE_TRIGGER)
        elif source == self.ccnSTM:
            return (self.ccnCTI, 2, CTM_CHANNEL_TRACE_TRIGGER)

        # no associated CTI
        return (None, None, None)

    def setTraceSourceEnabled(self, funnel, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(funnel, source, enabled)
        self.enableCTIsForSource(source, enabled)

    def setETBTraceEnabled(self, etb, enabled):
        '''Enable/disable ETB trace capture'''
        self.enableCTIsForSink(etb, enabled)


    def registerClusterTraceSources(self, c, traceCapture):
        '''Register all trace sources with trace capture device'''
        for i in range(CLUSTER_SIZES[c]):
            self.registerCoreTraceSource(traceCapture, self.cortexA15cores[c][i], self.PTMs[c][i])


    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

        # CTI (if present) is also managed by the configuration
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.addManagedTraceDevices(traceCapture.getName(), [ cti ])


    def registerTraceSource(self, traceCapture, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture
        traceCapture.addTraceSource(source)

        # source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

        # CTI (if present) is also managed by the configuration
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.addManagedTraceDevices(traceCapture.getName(), [ cti ])


    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnel ports
        portMap = {}
        for c in range(NUM_CLUSTERS):
            for i in range(CLUSTER_SIZES[c]):
                # assume cores are assigned linearly to funnel ports within each cluster
                portMap[self.PTMs[c][i]] = i

        return portMap.get(source, None)


    def verify(self):
        addr = 0x80000FE0
        expected = [ 0x3A, 0x60, 0x0B, 0x0 ]
        mask = [ 0xFF, 0xFF, 0x0F, 0x0 ]
        return self.confirmValue(self.apb, addr, expected, mask)


    def confirmValue(self, ap, addr, expected, mask):
        buffer = zeros(len(expected), 'i')
        ap.readMem(addr, len(expected), buffer)
        actual = [ buffer[i] for i in range(len(buffer)) ]
        for e, m, a in zip(expected, mask, actual):
            if ((a & m) != (e & m)):
                print "Expected %08x but read %08x (with mask %08x)" % (e, a, m)
                return False
        return True


    def postConnect(self):
        DTSLv1.postConnect(self)

        # Take the ETF RAMs out of light sleep
        value = self.axi.readMem(0x20100300CC)
        #print ("Read dbg_sw_enable (pre): 0x%08X" % value)
        value |= 0x0000000C
        self.axi.writeMem(0x20100300CC, value)
        value = self.axi.readMem(0x20100300CC)
        #print("Read dbg_sw_enable (post): 0x%08X" % value)


    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        mDevs = set()
        for c in range(NUM_CLUSTERS):
            traceMode = self.getOptionValue("options.trace_%d.traceCapture" % c)
            self.setTraceCaptureMethod(self.ETBs[c], traceMode)
            mDevs = mDevs | self.getManagedDevices(traceMode)
        if self.getOptionValue("options.trace_sys.sys"):
            print "Sys STM enabled"
            mDevs = mDevs | self.getManagedDevices("ETB_sys")
        if self.getOptionValue("options.trace_sys.ccn"):
            print "CCN STM enabled"
            mDevs = mDevs | self.getManagedDevices("ETB_ccn")
        self.setManagedDevices(mDevs)

        ptmStartIndex = 0
        for c in range(NUM_CLUSTERS):
            coreTraceEnabled = self.getOptionValue("options.trace_%d.cortexA15coreTrace" % c)
            for i in range(CLUSTER_SIZES[c]):
                thisCoreTraceEnabled = self.getOptionValue("options.trace_%d.cortexA15coreTrace.Cortex_A15_%d" % (c, i))
                funnel = self.funnels[c]
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(funnel, self.PTMs[c][i], enableSource)

            self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A15_TRACE_OPTIONS],
                                       TraceRangeOptions(c, "cortexA15coreTrace", self),
                                       self.PTMs[c])

        self.enableSTMTrace(self.systemSTM, self.systemETB, self.getOptionValue("options.trace_sys.sys"))
        self.enableSTMTrace(self.ccnSTM, self.ccnETB, self.getOptionValue("options.trace_sys.ccn"))

        for i in range(len(CLUSTER_SIZES)):
            for j in range(0, CLUSTER_SIZES[i]):
                a15_rams.applyCacheDebug(configuration = self,
                                         optionName = "options.cacheRams.cluster_%d.cacheDebug" % i,
                                         device = self.cortexA15cores[i][j])
                a15_rams.applyCachePreservation(configuration = self,
                                                optionName = "options.cacheRams.cluster_%d.cachePreserve" % i,
                                                device = self.cortexA15cores[i][j])


    def enableSTMTrace(self, stm, etb, enabled):
        if enabled:
            self.setTraceCaptureMethod(etb, "ETB")
        else:
            self.setTraceCaptureMethod(etb, "none")
        stm.setEnabled(enabled)
        self.enableCTIsForSource(stm, enabled)


    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def setTraceCaptureMethod(self, etb, method):
        if method == "none":
            self.setETBTraceEnabled(etb, False)
        elif method.startswith("ETB"):
            self.setETBTraceEnabled(etb, True)

    @staticmethod
    def getPTMsForCluster(c):
        '''Get the PTMs for a cluster'''
        def getPTMs(self):
            return self.PTMs[c]
        # Return an unbound method listing cluster c's clusters
        return getPTMs

    def setCoreTraceEnabled(self, enabled):
        '''Enable/disable the core trace sources'''
        for cluster in self.PTMs:
            for source in cluster:
                self.setTraceSourceEnabled(source, enabled)

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the set of devices managed by the configuration'''
        for d in devs:
            self.mgdPlatformDevs.add(d)

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

    def registerFilters(self, core):
        '''Add a wrapper around a core to allow access to AHB and APB via the DAP'''
        core.registerAddressFilters(
            [AXIMemAPAccessor("AXI", self.axi, "AXI bus accessed via AP_0", 40),
             AxBMemAPAccessor("APB", self.apb, "APB bus accessed via AP_1")])

    def enableCTIInput(self, cti, input, channel, enabled):
        '''Enable/disable cross triggering between an input and a channel'''
        if enabled:
            cti.enableInputEvent(input, channel)
        else:
            cti.disableInputEvent(input, channel)

    def enableCTIsForSink(self, sink, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, output, channel = self.getCTIForSink(sink)
        if cti:
            self.enableCTIOutput(cti, output, channel, enabled)

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.enableCTIInput(cti, input, channel, enabled)

    def enableCTIOutput(self, cti, output, channel, enabled):
        '''Enable/disable cross triggering between a channel and an output'''
        if enabled:
            cti.enableOutputEvent(output, channel)
        else:
            cti.disableOutputEvent(output, channel)

    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, funnelDev, name)
        funnel.setAllPortsDisabled() # Will enable for each source later
        return funnel

    def enableFunnelPortForSource(self, funnel, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        port = self.getFunnelPortForSource(source)
        if enabled:
            funnel.setPortEnabled(port)
        else:
            funnel.setPortDisabled(port)

    def setInternalTraceRange(self, currentTraceOptions, newTraceOptions, traceMacrocells):
        # values are different to current config
        if (newTraceOptions.traceRangeEnable != currentTraceOptions.traceRangeEnable) or \
            (newTraceOptions.traceRangeStart != currentTraceOptions.traceRangeStart) or \
            (newTraceOptions.traceRangeEnd != currentTraceOptions.traceRangeEnd):

            # clear existing ranges
            if currentTraceOptions.traceRangeIDs:
                for i in range(0, len(traceMacrocells)):
                    traceMacrocells[i].clearTraceRange(currentTraceOptions.traceRangeIDs[i])
                currentTraceOptions.traceRangeIDs = None

            # set new ranges
            if newTraceOptions.traceRangeEnable:
                currentTraceOptions.traceRangeIDs = [
                    traceMacrocells[i].addTraceRange(newTraceOptions.traceRangeStart, newTraceOptions.traceRangeEnd)
                    for i in range(0, len(traceMacrocells))
                    ]

            currentTraceOptions.traceRangeEnable = newTraceOptions.traceRangeEnable
            currentTraceOptions.traceRangeStart = newTraceOptions.traceRangeStart
            currentTraceOptions.traceRangeEnd = newTraceOptions.traceRangeEnd

class DtslScript_AXM5516(DtslScript):
    pass

class DtslScript_AXM5512(DtslScript):
    @staticmethod
    def getOptionList():
        global CLUSTER_SIZES # we need to use the global keyword, or our changes won't be reflected in the variable used by the parent class
        CLUSTER_SIZES = [ 4, 4, 4 ]
        global NUM_CLUSTERS
        NUM_CLUSTERS = len(CLUSTER_SIZES)
        return DtslScript.getOptionList()

    def __init__(self, root):
        global CLUSTER_SIZES # in case a separate instance of the interpreter is created, where the above getOptionList code has not run
        CLUSTER_SIZES = [ 4, 4, 4 ]
        global NUM_CLUSTERS
        NUM_CLUSTERS = len(CLUSTER_SIZES)
        DtslScript.__init__(self, root)

class DtslScript_AXM5508(DtslScript):
    @staticmethod
    def getOptionList():
        global CLUSTER_SIZES
        CLUSTER_SIZES = [ 4, 4 ]
        global NUM_CLUSTERS
        NUM_CLUSTERS = len(CLUSTER_SIZES)
        return DtslScript.getOptionList()

    def __init__(self, root):
        global CLUSTER_SIZES
        CLUSTER_SIZES = [ 4, 4 ]
        global NUM_CLUSTERS
        NUM_CLUSTERS = len(CLUSTER_SIZES)
        DtslScript.__init__(self, root)

class DtslScript_AXM5504(DtslScript):
    @staticmethod
    def getOptionList():
        global CLUSTER_SIZES
        CLUSTER_SIZES = [ 4 ]
        global NUM_CLUSTERS
        NUM_CLUSTERS = len(CLUSTER_SIZES)
        return DtslScript.getOptionList()

    def __init__(self, root):
        global CLUSTER_SIZES
        CLUSTER_SIZES = [ 4 ]
        global NUM_CLUSTERS
        NUM_CLUSTERS = len(CLUSTER_SIZES)
        DtslScript.__init__(self, root)
