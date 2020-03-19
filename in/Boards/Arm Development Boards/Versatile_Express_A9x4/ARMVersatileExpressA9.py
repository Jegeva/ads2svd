# Copyright (C) 2018-2019 Arm Limited (or its affiliates). All rights reserved.

from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTLiveStoredStreamingTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import RDDISyncSMPDevice
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.configurations import ConfigurationBase
from com.arm.debug.dtsl.components import ETMv3_3TraceSource

NUM_CORES = 4

ITM_ATB_ID = 1
ITM_FUNNEL_PORT = 3

PTM_ATB_ID_BASE = 2

CTM_CHANNEL_SYNC_STOP     = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START    = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers

DSTREAM_PORTWIDTH = 16

def getFunnelPortForCore(core):

    # select port for desired core
    port = -1
    if core == 3:
        # core 3 isn't on port 3, but on port 4!
        port = 4
    else:
        # otherwise core n is on port n
        port = core

    return port


class BaseDtslScript(DTSLv1):
    '''Platform configurations for the Versatile Express A9'''

    @staticmethod
    def getETBOptions():
        return ("ETB", "On Chip Trace Buffer (ETB)")

    @staticmethod
    def getTraceCaptureDeviceOptions():
        return DTSLv1.radioEnumOption(
            name='traceCaptureDevice',
            displayName = 'Trace capture method',
            description="Specify how trace data is to be collected",
            defaultValue="none",
            values = [
                ("none", "None"),
                BaseDtslScript.getETBOptions()
            ]
        )

    @staticmethod
    def getCoreTraceOptions():
        TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range.
This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
        return DTSLv1.booleanOption(
            'traceenable', 'Enable core trace',
            description="Enable or disable core trace",
            defaultValue=False,
            isDynamic = True,
            childOptions =
                # Allow each source to be enabled/disabled individually
                [ DTSLv1.booleanOption('core_%d' % c, "Enable core %d trace" % c, description="Enable collection of trace for core %d" % c, defaultValue=True, isDynamic=True) for c in range(0, NUM_CORES) ] + [
                DTSLv1.booleanOption(
                    name='cycleaccurate',
                    displayName = 'Cycle accurate trace',
                    defaultValue=False,
                    isDynamic=True
                ),
                # Trace range selection (e.g. for linux kernel)
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
                    ]
                )
            ]
        )


    @staticmethod
    def getTargetITMOptions():
        return DTSLv1.infoElement(
            name='target',
            displayName='Target ITM Settings',
            description='These are the target programmed ITM settings the debugger needs to know about',
            childOptions=[
                DTSLv1.integerOption(
                    name='targetITMATBID',
                    displayName='ITM ATBID',
                    description='The ITM ATB ID as setup by the target (1..112)',
                    minimum=1,
                    maximum=112,
                    defaultValue=ITM_ATB_ID
                )
            ]
        )

    @staticmethod
    def getDebuggerITMOptions():
        return DTSLv1.infoElement(
            name='debugger',
            displayName='Debugger ITM Settings',
            description='These are the settings the debugger will write to the ITM',
            childOptions=[
                DTSLv1.booleanOption(
                    name='TSENA',
                    displayName = 'Enable differential timestamps',
                    defaultValue=True,
                    isDynamic=True
                ),
                DTSLv1.enumOption(
                    name='TSPrescale',
                    displayName='Timestamp prescale',
                    defaultValue='none',
                    isDynamic=True,
                    values = [
                        ('none', 'no prescaling'),
                        ('d4',   'divide by 4'),
                        ('d16',  'divide by 16'),
                        ('d64',  'divide by 64')
                    ]
                ),
                DTSLv1.integerOption(
                    name='SyncCount',
                    displayName='Sync count',
                    description='The clock delay between output of SYNC packets 0..4095',
                    minimum=0,
                    maximum=4095,
                    defaultValue=1024
                ),
                DTSLv1.integerOption(
                    name='STIMENA',
                    displayName = 'Stimulus port enables',
                    description='Port[31]..Port[0], 1 bit per port, value of 1=enabled',
                    minimum=0x00000000,
                    maximum=0xFFFFFFFF,
                    defaultValue=0xFFFFFFFF,
                    display=IIntegerOption.DisplayFormat.HEX,
                    isDynamic=True
                )
            ]
        )

    @staticmethod
    def getCaptureDeviceTabPage():
        return DTSLv1.tabPage(
            "traceBuffer", "Trace Capture",
            childOptions=[
                BaseDtslScript.getTraceCaptureDeviceOptions()
            ]
        )

    @staticmethod
    def getCoreTraceTabPage():
        return DTSLv1.tabPage(
            "coretrace", "Core Trace",
            childOptions=[
                BaseDtslScript.getCoreTraceOptions()
            ]
        )

    @staticmethod
    def getITMTraceTabPage():
        return DTSLv1.tabPage(
            name='ITM',
            displayName='ITM',
            childOptions=[
                DTSLv1.booleanOption(
                    name='itmTraceEnabled',
                    displayName = 'Enable ITM Trace',
                    defaultValue=False,
                    isDynamic=True,
                    childOptions = [
                        DTSLv1.radioEnumOption(
                            name='itmowner',
                            displayName = 'ITM Owner',
                            description='Specify whether the target or the debugger will own/setup the ITM',
                            defaultValue='Target',
                            values=[
                                ('Target', 'The target will setup the ITM', BaseDtslScript.getTargetITMOptions()),
                                ('Debugger', 'Arm Debugger will setup the ITM', BaseDtslScript.getDebuggerITMOptions())
                            ]
                        )
                    ]
                )
            ]
        )

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet(
                "options", "Options",
                childOptions=[
                    BaseDtslScript.getCaptureDeviceTabPage(),
                    BaseDtslScript.getCoreTraceTabPage(),
                    BaseDtslScript.getITMTraceTabPage()
                ]
            )
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)
        self.traceSources = []
        self.reservedATBIDs = {}
        # locate devices on the platform and create corresponding objects
        self.discoverDevices()
        self.mgdPlatformDevs = set()
        # only AHB/APB is managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB)
        self.mgdPlatformDevs.add(self.APB)

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}
        # setup debug devices
        self.exposeCores()
        self.setupCTISyncSMP()
        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeEnable = False
        self.traceRangeStart = None
        self.traceRangeEnd = None
        self.traceRangeIDs = None

        self.setManagedDevices(self.mgdPlatformDevs)

    def discoverDevices(self):
        '''find and create devices'''
        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = AHBAP(self, ahbDev, "CSMEMAP")
        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB = APBAP(self, apbDev, "CSMEMAP")

        # Cross trigger for ETB/TPIU
        outCTIDev = self.findDevice("CSCTI")
        self.outCTI = CSCTI(self, outCTIDev, "CTI_out")
        # find each core and associated PTM & CTI
        coreDev = 1
        ptmDev = 1
        coreCTIDev = outCTIDev
        self.cores = []
        self.PTMs  = []
        self.CTIs  = []
        self.ctiMap = {} # map cores to associated CTIs
        for i in range(0, NUM_CORES):
            # find the next core / PTM / CTI
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            # create Device representation for the core and expose to debugger
            dev = Device(self, coreDev, "Cortex-A9_%d" % i)
            self.cores.append(dev)
            # create the PTM for this core
            streamID = PTM_ATB_ID_BASE+i
            ptm = self.createPTM(ptmDev, streamID, "PTM_%d" % i)
            self.PTMs.append(ptm)
            self.traceSources.append(ptm)
            # create CTI for this core
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            self.CTIs.append(coreCTI)
            self.ctiMap[dev] = coreCTI
        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")
        # Funnel
        funnelDev = self.findDevice("CSTFunnel")
        self.funnel = self.createFunnel(funnelDev, "Funnel")
        # ITM
        itmDev = self.findDevice("CSITM")
        self.ITM = self.createITM(itmDev, ITM_ATB_ID, "ITM")
        self.traceSources.append(self.ITM)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES):
            self.registerCoreTraceSource(traceCapture, self.cores[c], self.PTMs[c])
        self.registerTraceSource(traceCapture, self.ITM)

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''
        # Build map of sources to funnel ports
        portMap = {
            self.ITM: ITM_FUNNEL_PORT,
        }
        for i in range(0, NUM_CORES):
            portMap[self.PTMs[i]] = getFunnelPortForCore(i)
        return portMap.get(source, None)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''
        if source in self.PTMs:
            coreNum = self.PTMs.index(source)
            # PTM trigger is on input 6
            return (self.CTIs[coreNum], 6, CTM_CHANNEL_TRACE_TRIGGER)
        # no associated CTI
        return (None, None, None)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == "ETB":
            # ETB trigger input is CTI out 1
            return (self.outCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)
        else:
            # no associated CTI
            return (None, None, None)

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # disable the TPIU by default to allow ETB to work at full rate
        tpiu.setEnabled(False)
        return tpiu

    def createETBTraceCapture(self):
        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")

    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, funnelDev, name)
        funnel.setAllPortsDisabled() # Will enable for each source later
        return funnel

    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, itmDev, streamID, name)
        # disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

    def createPTM(self, ptmDev, streamID, name):
        ptm = PTMTraceSource(self, ptmDev, streamID, name)
        # disabled by default - will enable with option
        ptm.setEnabled(False)
        return ptm

    def exposeCores(self):
        for core in self.cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP_1")])

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

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def enableCTIInput(self, cti, input, channel, enabled):
        '''Enable/disable cross triggering between an input and a channel'''
        if enabled:
            cti.enableInputEvent(input, channel)
        else:
            cti.disableInputEvent(input, channel)

    def enableCTIOutput(self, cti, output, channel, enabled):
        '''Enable/disable cross triggering between a channel and an output'''
        if enabled:
            cti.enableOutputEvent(output, channel)
        else:
            cti.disableOutputEvent(output, channel)

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
        '''Register trace source with trace capture device'''
        traceCapture.addTraceSource(source)
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        port = self.getFunnelPortForSource(source)
        if enabled:
            self.funnel.setPortEnabled(port)
        else:
            self.funnel.setPortDisabled(port)

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.enableCTIInput(cti, input, channel, enabled)

    def enableCTIsForSink(self, sink, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, output, channel = self.getCTIForSink(sink)
        if cti:
            self.enableCTIOutput(cti, output, channel, enabled)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def setupETBTrace(self):
        '''Setup ETB trace capture'''
        # use continuous mode
        self.ETB.setFormatterMode(FormatterMode.CONTINUOUS)
        # register other trace components with ETB and register ETB with configuration
        self.ETB.setTraceComponentOrder([ self.funnel ])
        self.addTraceCaptureInterface(self.ETB)
        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETB", [self.funnel, self.tpiu, self.outCTI, self.ETB])
        # register trace sources
        self.registerTraceSources(self.ETB)

    def setETBTraceEnabled(self, enabled):
        '''Enable/disable ETB trace capture'''
        self.enableCTIsForSink("ETB", enabled)

    def setupSimpleSyncSMP(self):
        '''Create SMP device using RDDI synchronization'''
        # create SMP device and expose from configuration
        self.smp = RDDISyncSMPDevice(self, "SMP", 1, self.cores)
        self.registerFilters(self.smp)
        self.addDeviceInterface(self.smp)

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''
        # Setup CTIs for synch start/stop
        ctiInfo = {}
        for c in self.cores:
            # use standard Cortex event mapping : in/out on trigger 0 for stop, out on trigger 7 for start
            ctiInfo[c] = CTISyncSMPDevice.DeviceCTIInfo(self.ctiMap[c], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        self.smp = CTISyncSMPDevice(self, "SMP", self.cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(self.smp)
        self.addDeviceInterface(self.smp)
        # automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CTIs)

    def getPTMs(self):
        '''Get the PTMs'''
        return self.PTMs

    def setITMEnabled(self, enabled):
        '''Enable/disable the ITM trace source'''
        self.setTraceSourceEnabled(self.ITM, enabled)

    def setITMEnableTimestamps(self, enabled):
        '''Enable/disable the ITM timestamp'''
        self.ITM.setEnableTimestamps(enabled)

    def setITMTSPrescale(self, TSPrescale):
        '''Set the ITM timestamp prescale value'''
        psValue = {"none":0, "d4":1, "d16":2, "d64":3}
        self.ITM.setTSPrescale(psValue[TSPrescale])

    def setITMPortEnables(self, portBitSet):
        '''Set the ITM port enable bitset'''
        self.ITM.setPortEnables(portBitSet)

    def setITMOwnedByDebugger(self, state):
        self.ITM.setIsSetupByTarget(not state)

    def setITMSyncCount(self, syncCount):
        self.ITM.setSyncCount(syncCount)

    def updateATBIDAssignments(self):
        '''Modifies all trace source ATB IDs to take in to account
           any reserved IDs (e.g. ones that are hard coded in the target).
           When we are done, all trace sources will have a unique ID and
           those that are preset will have the correct values.
        '''
        atbID = 1 # First valid ATB ID is 1
        for source in self.traceSources:
            if source.getName() in self.reservedATBIDs:
                # This source has a reserved ATB ID so set it
                # from the reserved list
                id = self.reservedATBIDs[source.getName()]
                source.setStreamID(id)
            else:
                # Make sure the current ID is not on the reserved list
                while atbID in self.reservedATBIDs.values():
                    atbID = atbID + 1
                    if atbID > 112:
                        raise RuntimeError, "Could not locate an unused ATBID for %s" % source.getName()
                source.setStreamID(atbID)
                atbID = atbID + 1

    def setInternalTraceRange(self, traceRangeEnable, traceRangeStart, traceRangeEnd):
        # values are different to current config
        if (traceRangeEnable != self.traceRangeEnable) or \
            (traceRangeStart != self.traceRangeStart) or \
            (traceRangeEnd != self.traceRangeEnd):
            # clear existing ranges
            if self.traceRangeIDs:
                for i in range(0, NUM_CORES):
                    self.PTMs[i].clearTraceRange(self.traceRangeIDs[i])
                self.traceRangeIDs = None
            # set new ranges
            if traceRangeEnable:
                self.traceRangeIDs = [
                    self.PTMs[i].addTraceRange(traceRangeStart, traceRangeEnd)
                    for i in range(0, NUM_CORES)
                ]
            self.traceRangeEnable = traceRangeEnable
            self.traceRangeStart = traceRangeStart
            self.traceRangeEnd = traceRangeEnd

    def debuggerOwnsITM(self, obase):
        ''' Indicates if the debugger owns the ITM (vs the target owning it)
            Param: obase the option path string to the ITM owner option
        '''
        return self.getOptionValue(obase) == "Debugger"

    def setITMOptions(self, obase):
        '''Configures the ITM options for the use case when the debugger
           has control/ownership of the ITM
           Param: obase the option path string to the debugger's ITM options
        '''
        self.setITMEnableTimestamps(self.getOptionValue(obase+".TSENA"))
        self.setITMTSPrescale(self.getOptionValue(obase+".TSPrescale"))
        self.setITMPortEnables(self.getOptionValue(obase+".STIMENA"))
        self.setITMSyncCount(self.getOptionValue(obase+".SyncCount"))

    def getTraceDeviceName(self, obase):
        ''' Gets the configured trace device name
            Param: obase the option path string to the trace buffer options
        '''
        return self.getOptionValue(obase+".traceBuffer.traceCaptureDevice")

    def traceDeviceIsNone(self, obase):
        ''' Indicates if no trace capture device has been selected
            Param: obase the option path string to the trace buffer options
        '''
        return self.getTraceDeviceName(obase) == "None"

    def setInitialOptions(self, obase):
        '''Takes the configuration options and configures the
           DTSL objects prior to target connection
           Param: obase the option path string to top level options
        '''
        if self.getTraceDeviceName(obase) == "ETB":
            self.createETBTraceCapture()
            self.setupETBTrace()
            self.setETBTraceEnabled(True)
        else:
            self.setETBTraceEnabled(False)

        if self.traceDeviceIsNone(obase):
            # Disable all trace sources
            for source in self.traceSources:
                self.setTraceSourceEnabled(source, False)
        else:
            # Setup PTM trace
            obasePTM = obase+".coretrace.traceenable"
            masterCoreTraceEnabled = self.getOptionValue(obasePTM)
            cycleAccurate = self.getOptionValue(obasePTM+".cycleaccurate")
            for i in range(0, NUM_CORES):
                ptmEnabled = masterCoreTraceEnabled and self.getOptionValue(obasePTM+".core_%d" % (i))
                self.setTraceSourceEnabled(self.PTMs[i], ptmEnabled)
                self.PTMs[i].setCycleAccurate(cycleAccurate)
            traceRange = self.getOptionValue(obasePTM+".traceRange")
            traceRangeStart = self.getOptionValue(obasePTM+".traceRange.start")
            traceRangeEnd = self.getOptionValue(obasePTM+".traceRange.end")
            self.setInternalTraceRange(traceRange, traceRangeStart, traceRangeEnd)
            # Setup ITM trace
            obaseITM = obase+".ITM"
            self.reservedATBIDs = {}
            self.setITMEnabled(self.getOptionValue(obaseITM+".itmTraceEnabled"))
            obaseITMOwner = obaseITM+".itmTraceEnabled.itmowner"
            if self.debuggerOwnsITM(obaseITMOwner):
                self.setITMOwnedByDebugger(True);
                self.setITMOptions(obaseITMOwner+".debugger")
            else:
                self.setITMOwnedByDebugger(False);
                self.reservedATBIDs["ITM"] = self.getOptionValue(obaseITMOwner+".target.targetITMATBID")
            self.updateATBIDAssignments()
            self.setManagedDevices(self.getManagedDevices(self.getTraceDeviceName(obase)))

    def updateDynamicOptions(self, obase):
        '''Takes any changes to the dynamic options and
           applies them. Note that some trace options may
           not take effect until trace is (re)started
           Param: obase the option path string to top level options
        '''
        if not self.traceDeviceIsNone(obase):
            # Setup PTM trace
            obasePTM = obase+".coretrace.traceenable"
            masterCoreTraceEnabled = self.getOptionValue(obasePTM)
            cycleAccurate = self.getOptionValue(obasePTM+".cycleaccurate")
            for i in range(0, NUM_CORES):
                ptmEnabled = masterCoreTraceEnabled and self.getOptionValue(obasePTM+".core_%d" % (i))
                self.setTraceSourceEnabled(self.PTMs[i], ptmEnabled)
                self.PTMs[i].setCycleAccurate(cycleAccurate)
            traceRange = self.getOptionValue(obasePTM+".traceRange")
            traceRangeStart = self.getOptionValue(obasePTM+".traceRange.start")
            traceRangeEnd = self.getOptionValue(obasePTM+".traceRange.end")
            self.setInternalTraceRange(traceRange, traceRangeStart, traceRangeEnd)
            # Setup ITM trace
            obaseITM = obase+".ITM"
            if self.getOptionValue(obaseITM+".itmTraceEnabled"):
                self.setITMEnabled(True)
                obaseITMOwner = obaseITM+".itmTraceEnabled.itmowner"
                if self.debuggerOwnsITM(obaseITMOwner):
                    self.setITMOptions(obaseITMOwner+".debugger")
            else:
                self.setITMEnabled(False)

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed.
           This will be called:
              * after construction but before device connection
              * during a debug session should the user change the DTSL options
        '''
        obase = "options"
        if self.isConnected():
            self.updateDynamicOptions(obase)
        else:
            self.setInitialOptions(obase)



class DSTREAMDtslScript(BaseDtslScript):
    '''Platform configurations for the Versatile Express A9
       Using the DSTREAM Debug and Trace unit
    '''

    @staticmethod
    def getDSTREAMOptions():
        return (
            "DSTREAM", "DSTREAM 4GB Trace Buffer",
            DTSLv1.infoElement(
                "dstream", "", "dummy",
                childOptions=[
                    DTSLv1.booleanOption(
                        name='clearTraceOnConnect',
                        displayName='Clear Trace Buffer on connect',
                        defaultValue=True
                    ),
                    DTSLv1.booleanOption(
                        name='startTraceOnConnect',
                        displayName='Start Trace Buffer on connect',
                        defaultValue=True
                    ),
                    DTSLv1.enumOption(
                        name='traceWrapMode',
                        displayName='Trace full action',
                        defaultValue='wrap',
                        values=[
                            ('wrap', 'Trace wraps on full and continues to store data'),
                            ('stop', 'Trace halts on full')
                        ]
                    )
                ]
            )
        )


    @staticmethod
    def getTraceCaptureDeviceOptions():
        return DTSLv1.radioEnumOption(
            name='traceCaptureDevice',
            displayName = 'Trace capture method',
            description="Specify how trace data is to be collected",
            defaultValue="none",
            values = [
                ("none", "None"),
                BaseDtslScript.getETBOptions(),
                DSTREAMDtslScript.getDSTREAMOptions()
            ]
        )

    @staticmethod
    def getCaptureDeviceTabPage():
        return DTSLv1.tabPage(
            "traceBuffer", "Trace Capture",
            childOptions=[
                DSTREAMDtslScript.getTraceCaptureDeviceOptions()
            ]
        )

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet(
                "options", "Options",
                childOptions=[
                    DSTREAMDtslScript.getCaptureDeviceTabPage(),
                    BaseDtslScript.getCoreTraceTabPage(),
                    BaseDtslScript.getITMTraceTabPage()
                ]
            )
        ]


    def __init__(self, root):
        BaseDtslScript.__init__(self, root)

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def setPortWidth(self, portWidth):
        self.tpiu.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def setupDSTREAMTrace(self, portwidth):
        '''Setup DSTREAM trace capture'''
        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        # configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        # set the DSTREAM and TPIU port width
        self.setPortWidth(portwidth)
        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.funnel, self.tpiu ])
        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [self.funnel, self.tpiu, self.outCTI, self.DSTREAM])
        # register trace sources
        self.registerTraceSources(self.DSTREAM)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.tpiu.setEnabled(enabled)
        self.enableCTIsForSink("TPIU", enabled)

    def setDSTREAMClearTraceOnConnect(self, enabled):
        '''Configuration option setter method to enable/disable clear trace buffer on connect'''
        self.DSTREAM.setClearOnConnect(enabled)

    def setDSTREAMStartTraceOnConnect(self, enabled):
        '''Configuration option setter method to enable/disable auto start trace buffer on connect only'''
        self.DSTREAM.setAutoStartTraceOnConnect(enabled)

    def setDSTREAMTraceWrapMode(self, mode):
        '''Configuration option setter method for the buffer wrap mode'''
        if mode == "wrap":
            self.DSTREAM.setWrapOnFull(True)
        else:
            self.DSTREAM.setWrapOnFull(False)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        if sink == "ETB":
            # ETB trigger input is CTI out 1
            return (self.outCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)
        elif sink == "TPIU":
            # TPIU trigger input is CTI out 3
            return (self.outCTI, 3, CTM_CHANNEL_TRACE_TRIGGER)
        else:
            # no associated CTI
            return (None, None, None)

    def traceDeviceIsDSTREAM(self, obase):
        ''' Indicates if the trace capture device is configured to be DSTREAM
            Param: obase the option path string to the trace buffer options
        '''
        return self.getOptionValue(obase+".traceBuffer.traceCaptureDevice") in ["DSTREAM", "DSTREAM_PT_Store_and_Forward", "DSTREAM_PT_StreamingTrace"]

    def setDSTREAMOptions(self, obase):
        '''Configures the DSTREAM options
           Param: obase the option path string to the DSTREAM options
        '''
        self.setDSTREAMTraceWrapMode(self.getOptionValue(obase+".traceWrapMode"))
        self.setDSTREAMClearTraceOnConnect(self.getOptionValue(obase+".clearTraceOnConnect"))
        self.setDSTREAMStartTraceOnConnect(self.getOptionValue(obase+".startTraceOnConnect"))

    def setInitialOptions(self, obase):
        '''Takes the configuration options and configures the
           DTSL objects prior to target connection
           Param: obase the option path string to top level options
        '''
        if self.traceDeviceIsDSTREAM(obase):
            self.createDSTREAM()
            self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)
            self.setDSTREAMTraceEnabled(True)
            self.setDSTREAMOptions(obase+".traceBuffer.traceCaptureDevice.DSTREAM")
        else:
            self.setDSTREAMTraceEnabled(False)
        BaseDtslScript.setInitialOptions(self, obase)

    def updateDynamicOptions(self, obase):
        '''Takes any changes to the dynamic options and
           applies them. Note that some trace options may
           not take effect until trace is (re)started
           Param: obase the option path string to top level options
        '''
        BaseDtslScript.updateDynamicOptions(self, obase)

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed.
           This will be called:
              * after construction but before device connection
              * during a debug session should the user change the DTSL options
        '''
        obase = "options"
        if self.isConnected():
            self.updateDynamicOptions(obase)
        else:
            self.setInitialOptions(obase)

class DtslScript_DSTREAM_ST_Family(DSTREAMDtslScript):

    def setDSTREAMOptions(self, obase):
        '''Configures the DSTREAM options
           Param: obase the option path string to the DSTREAM options
        '''
        dstream_opts = "options.traceBuffer.traceCaptureDevice." + self.getDstreamOptionString() + "."

        portWidthOpt = self.getOptions().getOption(dstream_opts + "tpiuPortWidth")
        if portWidthOpt:
           portWidth = self.getOptionValue(dstream_opts + "tpiuPortWidth")
           self.setPortWidth(int(portWidth))

        traceBufferSizeOpt = self.getOptions().getOption(dstream_opts + "traceBufferSize")
        if traceBufferSizeOpt:
            traceBufferSize = self.getOptionValue(dstream_opts + "traceBufferSize")
            self.setTraceBufferSize(traceBufferSize)

    def getDstreamOptionString(self):
        return "dstream"

    def setupDSTREAMTrace(self, portwidth):
        '''Setup DSTREAM trace capture'''
        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        # set the DSTREAM and TPIU port width
        self.setPortWidth(portwidth)
        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.funnel, self.tpiu ])
        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(self.getOptionValue("options.traceBuffer.traceCaptureDevice"), [self.funnel, self.tpiu, self.outCTI, self.DSTREAM])
        # register trace sources
        self.registerTraceSources(self.DSTREAM)

    def setTraceBufferSize(self, mode):
        '''Configuration option setter method for the trace cache buffer size'''
        cacheSize = 64*1024*1024
        if (mode == "64MB"):
            cacheSize = 64*1024*1024
        if (mode == "128MB"):
            cacheSize = 128*1024*1024
        if (mode == "256MB"):
            cacheSize = 256*1024*1024
        if (mode == "512MB"):
            cacheSize = 512*1024*1024
        if (mode == "1GB"):
            cacheSize = 1*1024*1024*1024
        if (mode == "2GB"):
            cacheSize = 2*1024*1024*1024
        if (mode == "4GB"):
            cacheSize = 4*1024*1024*1024
        if (mode == "8GB"):
            cacheSize = 8*1024*1024*1024
        if (mode == "16GB"):
            cacheSize = 16*1024*1024*1024
        if (mode == "32GB"):
            cacheSize = 32*1024*1024*1024
        if (mode == "64GB"):
            cacheSize = 64*1024*1024*1024
        if (mode == "128GB"):
            cacheSize = 128*1024*1024*1024

        self.DSTREAM.setMaxCaptureSize(cacheSize)

class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):
    '''Platform configurations for the Versatile Express A9
       Using the DSTREAM-ST Debug and Trace unit
    '''

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet(
                "options", "Options",
                childOptions=[
                    DtslScript_DSTREAM_ST.getCaptureDeviceTabPage(),
                    BaseDtslScript.getCoreTraceTabPage(),
                    BaseDtslScript.getITMTraceTabPage()
                ]
            )
        ]

    @staticmethod
    def getCaptureDeviceTabPage():
        return DTSLv1.tabPage(
            "traceBuffer", "Trace Capture",
            childOptions=[
                DtslScript_DSTREAM_ST.getTraceCaptureDeviceOptions()
            ]
        )

    @staticmethod
    def getTraceCaptureDeviceOptions():
        return DTSLv1.radioEnumOption(
            name='traceCaptureDevice',
            displayName = 'Trace capture method',
            description="Specify how trace data is to be collected",
            defaultValue="none",
            values = [
                ("none", "None"),
                BaseDtslScript.getETBOptions(),
                DtslScript_DSTREAM_ST.getDSTREAMOptions()
            ]
        )

    @staticmethod
    def getDSTREAMOptions():
        return (
            "DSTREAM", "Streaming Trace",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")],isDynamic=False),
                    DTSLv1.enumOption('traceBufferSize', 'Trace buffer size', defaultValue="4GB",
                        values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"),
                                  ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"),
                                  ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                ]
            )
        )

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMSTStoredTraceCapture(self, "DSTREAM")

class DtslScript_DSTREAM_PT(DtslScript_DSTREAM_ST_Family):
    '''Platform configurations for the Versatile Express A9
       Using the DSTREAM-ST Debug and Trace unit
    '''

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet(
                "options", "Options",
                childOptions=[
                    DtslScript_DSTREAM_PT.getCaptureDeviceTabPage(),
                    BaseDtslScript.getCoreTraceTabPage(),
                    BaseDtslScript.getITMTraceTabPage()
                ]
            )
        ]

    @staticmethod
    def getCaptureDeviceTabPage():
        return DTSLv1.tabPage(
            "traceBuffer", "Trace Capture",
            childOptions=[
                DtslScript_DSTREAM_PT.getTraceCaptureDeviceOptions()
            ]
        )

    @staticmethod
    def getTraceCaptureDeviceOptions():
        return DTSLv1.radioEnumOption(
            name='traceCaptureDevice',
            displayName = 'Trace capture method',
            description="Specify how trace data is to be collected",
            defaultValue="none",
            values = [
                ("none", "None"),
                BaseDtslScript.getETBOptions(),
                DtslScript_DSTREAM_PT.getStoreAndForwardOptions(),
                DtslScript_DSTREAM_PT.getStreamingTraceOptions()
            ]
        )

    @staticmethod
    def getStoreAndForwardOptions():
        return (
            "DSTREAM_PT_Store_and_Forward", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement(
                "dpt_storeandforward", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="16",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit"),
                                  ("5", "5 bit"), ("6", "6 bit"), ("7", "7 bit"), ("8", "8 bit"),
                                  ("9", "9 bit"), ("10", "10 bit"), ("11", "11 bit"), ("12", "12 bit"),
                                  ("13", "13 bit"), ("14", "14 bit"), ("15", "15 bit"), ("16", "16 bit"),
                                  ("18", "18 bit"), ("20", "20 bit"), ("22", "22 bit"), ("24", "24 bit"),
                                  ("26", "26 bit"), ("28", "28 bit"), ("30", "30 bit"), ("32", "32 bit")], isDynamic=False)
                ]
            )
        )

    @staticmethod
    def getStreamingTraceOptions():
        return (
            "DSTREAM_PT_StreamingTrace", "DSTREAM-PT Streaming Trace",
            DTSLv1.infoElement(
                "dpt_streamingtrace", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="16",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit"),
                                  ("5", "5 bit"), ("6", "6 bit"), ("7", "7 bit"), ("8", "8 bit"),
                                  ("9", "9 bit"), ("10", "10 bit"), ("11", "11 bit"), ("12", "12 bit"),
                                  ("13", "13 bit"), ("14", "14 bit"), ("15", "15 bit"), ("16", "16 bit"),
                                  ("18", "18 bit"), ("20", "20 bit"), ("22", "22 bit"), ("24", "24 bit"),
                                  ("26", "26 bit"), ("28", "28 bit"), ("30", "30 bit"), ("32", "32 bit")], isDynamic=False),
                    DTSLv1.enumOption('traceBufferSize', 'Host trace buffer size', defaultValue="4GB",
                        values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"),
                                  ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"),
                                  ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                ]
            )
        )

    def getDstreamOptionString(self):
        if self.getOptionValue("options.traceBuffer.traceCaptureDevice") == "DSTREAM_PT_Store_and_Forward":
            return "dpt_storeandforward"
        if self.getOptionValue("options.traceBuffer.traceCaptureDevice") == "DSTREAM_PT_StreamingTrace":
            return "dpt_streamingtrace"

    def createDSTREAM(self):
        if self.getOptionValue("options.traceBuffer.traceCaptureDevice") == "DSTREAM_PT_Store_and_Forward":
            self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM_PT_Store_and_Forward")
        elif self.getOptionValue("options.traceBuffer.traceCaptureDevice") == "DSTREAM_PT_StreamingTrace":
            self.DSTREAM = DSTREAMPTLiveStoredStreamingTraceCapture(self, "DSTREAM_PT_StreamingTrace")
