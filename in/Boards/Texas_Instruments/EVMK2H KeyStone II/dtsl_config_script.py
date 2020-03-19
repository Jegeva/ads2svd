# Copyright (C) 2015-2019 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import AxBMemAPAccessor
import time
import datetime

from jarray import array, zeros
from java.lang import Long

# import core specific functions from Cores folder
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a15_rams

NUM_CORES_CORTEX_A15 = 4
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 16
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers

RSZ = 0x001
STS = 0x003
RAMRDAT = 0x004
RAMRPTR = 0x005
RAMWPTR = 0x006
CTL = 0x008
MODE = 0x00A
AXICTL = 0x044
FFSR = 0xC0
FFCR = 0xC1
DEVID = 0x3F2

class CT_TBR(CSTMC):
    def postConnect(self):
        CSTMC.postConnect(self)

        self.writeRegister(0x42, 0x0000000F)
        self.writeRegister(0x43, 0x006F00FF)

    def memRead(self, page, address, size, rule, count, data):
        CSTMC.memRead(self, page, address / 4, size, rule, count, data)

    def decodeRAMSize(self, value):
        result = 0
        if value == 1:
            result = 0x400
        if value == 2:
            result = 0x800
        if value == 3:
            result = 0x1000
        if value == 4:
            result = 0x2000
        if value == 5:
            result = 0x4000
        if value == 6:
            result = 0x8000

        return result

    def regWriteBlock(self, start, count, data):
        for i in range(count):
            self.writeRegister(start + i, data[i])

    def regReadBlock(self, start, count, data):
        for i in range(count):
            data[i] = self.readRegister(start + i)

    def regWriteList(self, regList, data):
        for i in range(len(regList)):
            self.writeRegister(regList[i], data[i])

    def regReadList(self, regList, data):
        for i in range(len(regList)):
            data[i] = self.readRegister(regList[i])

    def readRegister(self, reg):
        data = zeros(1, 'i')
        CSTMC.regReadBlock(self, reg, 1, data)
        value = data[0]

        orig = value
        if reg == RSZ:
            value = self.decodeRAMSize(value & 0x00000007)
        if reg == FFCR:
            value &= 0xFFFFFFBF
        if reg == DEVID:
            value = 0x400 # 128-bit memory width
        if reg == FFSR:
            value |= 0x2

        if reg == RAMRPTR or reg == RAMWPTR:
            value = value * 4
        return value

    def writeRegister(self, reg, value):
        orig_value = value
        if reg != MODE and reg != AXICTL:
            if reg == RAMRPTR or reg == RAMWPTR:
                value = value / 4
            if reg == CTL:
                orig = self.readRegister(CTL)
                value = (orig & 0xFFFFFFFE) | (value & 0x00000001)

            value = Long(value & 0xFFFFFFFFl).intValue()
            CSTMC.regWriteBlock(self, reg, 1, [ value ])



class DtslScript(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA15TabPage(),
                DtslScript.getOptionCortexA15PowerupTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionCacheRAMsTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("traceBuffer", "Trace Buffer", childOptions=[
                    DTSLv1.radioEnumOption(
                        'traceCapture',
                        'Trace capture method',
                        defaultValue="none",
                        values=[("none", "None"),
                                ("ETF0", "On Chip Trace Buffer (ETF0/TMC)"),
                                (DtslScript.getDSTREAMOptions())],
                        setter=DtslScript.setTraceCaptureMethod)
        ])

    @staticmethod
    def getDSTREAMOptions():
        return (
            "DSTREAM", "DSTREAM 4GB Trace Buffer",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="16",
                        values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False)
                ]
            )
        )

    @staticmethod
    def getOptionCortexA15TabPage():
        return DTSLv1.tabPage("cortexA15", "Cortex-A15 Trace", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A15 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_A15_%d' % c, "Enable Cortex-A15 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_A15) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "PTM Triggers halt execution", description="Enable the PTM triggers to halt execution", defaultValue=False) ] +
                            [ PTMTraceSource.cycleAccurateOption(DtslScript.getPTMs) ] +
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

    @staticmethod
    def getOptionCortexA15PowerupTabPage():
        return DTSLv1.tabPage("cortexA15_powerup", "Cortex-A15 Power Up", childOptions=[
                    DTSLv1.booleanOption('A15_1', "Power up Cortex-A15_1", defaultValue=False),
                    DTSLv1.booleanOption('A15_2', "Power up Cortex-A15_2", defaultValue=False),
                    DTSLv1.booleanOption('A15_3', "Power up Cortex-A15_3", defaultValue=False),
                ])

    @staticmethod
    def getOptionSTMTabPage():
        return DTSLv1.tabPage("stm", "STM", childOptions=[
                    DTSLv1.booleanOption('STM0', 'Enable STM 0 trace', defaultValue=False),
                ])

    @staticmethod
    def getOptionCacheRAMsTabPage():
        return DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ])

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # Only AHB/ABP devices are managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.append(self.AHB)
        self.mgdPlatformDevs.append(self.APB)

        self.exposeCores()

        self.traceRangeIDs = {}

        traceComponentOrder = [ self.Funnel0, self.Funnel1 ]
        managedDevices = [ self.Funnel0, self.Funnel1, self.OutCTI0, self.TPIU, self.ETF0Trace ]
        self.setupETFTrace(self.ETF0Trace, "ETF0", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel0, self.Funnel1, self.ETF0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.Funnel1, self.ETF0, self.OutCTI0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH, traceComponentOrder, managedDevices)

        self.setupCTISyncSMP()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        cortexA15coreDevs = [11, 13, 15, 17]
        self.cortexA15cores = []

        streamID = 1
        memApDev = 0

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.AHB = AHBAP(self, memApDev, "AHB")

        memApDev = self.findDevice("CSMEMAP", memApDev + 1)
        self.APB = APBAP(self, memApDev, "APB")

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, 5, "OutCTI0")

        coreCTIDevs = [19, 20, 21, 22]
        self.CoreCTIs = []

        ptmDevs = [23, 24, 25, 26]
        self.PTMs = []

        # STM 0
        self.STM0 = self.createSTM(9, streamID, "STM0")
        streamID += 1

        for i in range(0, NUM_CORES_CORTEX_A15):
            # Create core
            core = a15_rams.A15CoreDevice(self, cortexA15coreDevs[i], "Cortex-A15_%d" % i)
            self.cortexA15cores.append(core)

        for i in range(0, len(coreCTIDevs)):
            # Create CTI
            coreCTI = CSCTI(self, coreCTIDevs[i], "CoreCTIs[%d]" % i)
            self.CoreCTIs.append(coreCTI)

        for i in range(0, len(ptmDevs)):
            # Create PTM
            ptm = PTMTraceSource(self, ptmDevs[i], streamID, "PTMs[%d]" % i)
            streamID += 1
            # Disabled by default - will enable with option
            ptm.setEnabled(False)
            self.PTMs.append(ptm)

        tmcDev = 1

        # ETF 0 aka CT_TBR, the TI equivalent
        self.ETF0 = CT_TBR(self, 10, "ETF0")

        # ETF 0 trace capture
        self.ETF0Trace = TMCETBTraceCapture(self, self.ETF0, "ETF0")

        # DSTREAM
        self.createDSTREAM()

        # TPIU
        self.TPIU = self.createTPIU(3, "TPIU")

        # Funnel 0
        # Note: Funnel0 is device 6
        self.Funnel0 = self.createFunnel(6, "Funnel0")

        # Funnel 1
        # Note: Funnel1 is device 4
        self.Funnel1 = self.createFunnel(4, "Funnel1")
        # self.Funnel0 is connected to self.Funnel1 port 0
        self.Funnel1.setPortEnabled(0)

    def exposeCores(self):
        for core in self.cortexA15cores:
            a15_rams.registerInternalRAMs(core, self.AHB)
            self.addDeviceInterface(core)
            self.registerFilters(core)

    def registerFilters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB, "APB bus accessed via AP_1")])

    def postConnect(self):
        if self.getOptionValue("options.traceBuffer.traceCapture") == "DSTREAM":
            self.setupPinMUXForTrace(self.AHB)
        self.powerUpCores(self.AHB)
        DTSLv1.postConnect(self)

    def powerUpCores(self, memap):
        if (self.getOptionValue("options.cortexA15_powerup.A15_1") == True):
            memap.writeMem(0x01E80414, 0)
            memap.writeMem(0x01E8040C, 1)
        if (self.getOptionValue("options.cortexA15_powerup.A15_2") == True):
            memap.writeMem(0x01E80420, 0)
            memap.writeMem(0x01E80418, 1)
        if (self.getOptionValue("options.cortexA15_powerup.A15_3") == True):
            memap.writeMem(0x01E8042C, 0)
            memap.writeMem(0x01E80424, 1)

    def setupPinMUXForTrace (self, memap):

        # reduce TRC CLK speed a bit
        addrPLLBase = 0x02310000
        addrPLLSTAT = addrPLLBase + 0x13C
        addrPLLCMD = addrPLLBase + 0x138
        addrPLLDIV3 = addrPLLBase + 0x120

        myvalue = 0x0
        memap.writeMem(addrPLLCMD, myvalue);
        myvalue = 0x8003
        memap.writeMem(addrPLLDIV3, myvalue);
        myvalue = 0x1
        memap.writeMem(addrPLLCMD, myvalue);

        # setup the DRM for external trace
        addrDRMBase = 0x03017000
        addrDPMClaim = addrDRMBase + 0x50
        addrDPMCtrlReg0 = addrDRMBase + 0x80

        # claim & enable the DRM
        myvalue = 0x40000000
        memap.writeMem(addrDPMClaim, myvalue)

        value = 0x80000000
        memap.writeMem(addrDPMClaim, value)

        data = [ 0x00000008, 0x00000008, 0x0000000A, 0x00000009, 0x00000008,
                   0x00000008, 0x00000008, 0x00000008, 0x00000008, 0x00000008,
                   0x00000008, 0x00000008, 0x00000008, 0x00000008, 0x00000008,
                   0x00000008, 0x00000008, 0x00000008]
        memap.writeMem(addrDPMCtrlReg0, data)


    def setupETFTrace(self, etfTrace, name, traceComponentOrder, managedDevices):
        '''Setup ETF trace capture'''
        # Use continuous mode
        etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)

        # Register other trace components with ETF and register ETF with configuration
        etfTrace.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etfTrace)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        self.setPortWidth(portWidth)

        # Configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def setPortWidth(self, portWidth):
        self.TPIU.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def getCTIInfoForCore(self, core):
        '''Get the CTI info associated with a core
        return None if no associated CTI info
        '''

        # Build map of cores to DeviceCTIInfo objects
        ctiInfoMap = {}
        ctiInfoMap[self.cortexA15cores[0]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[0], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        ctiInfoMap[self.cortexA15cores[1]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[1], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        ctiInfoMap[self.cortexA15cores[2]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[2], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)
        ctiInfoMap[self.cortexA15cores[3]] = CTISyncSMPDevice.DeviceCTIInfo(self.CoreCTIs[3], CTISyncSMPDevice.DeviceCTIInfo.NONE, 7, 0, 0)

        return ctiInfoMap.get(core, None)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sources to CTIs
        sourceCTIMap = {}
        sourceCTIMap[self.PTMs[0]] = (self.CoreCTIs[0], 6, CTM_CHANNEL_TRACE_TRIGGER)
        sourceCTIMap[self.PTMs[1]] = (self.CoreCTIs[1], 6, CTM_CHANNEL_TRACE_TRIGGER)
        sourceCTIMap[self.PTMs[2]] = (self.CoreCTIs[2], 6, CTM_CHANNEL_TRACE_TRIGGER)
        sourceCTIMap[self.PTMs[3]] = (self.CoreCTIs[3], 6, CTM_CHANNEL_TRACE_TRIGGER)

        return sourceCTIMap.get(source, (None, None, None))

    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sinks to CTIs
        sinkCTIMap = {}
        sinkCTIMap[self.DSTREAM] = (self.OutCTI0, 3, CTM_CHANNEL_TRACE_TRIGGER)

        return sinkCTIMap.get(sink, (None, None, None))

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''

        # Build map of cores to trace macrocells
        coreTMMap = {}
        coreTMMap[self.cortexA15cores[0]] = self.PTMs[0]
        coreTMMap[self.cortexA15cores[1]] = self.PTMs[1]
        coreTMMap[self.cortexA15cores[2]] = self.PTMs[2]
        coreTMMap[self.cortexA15cores[3]] = self.PTMs[3]

        return coreTMMap.get(core, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''

        # Setup CTIs for sync start/stop
        # Cortex-A15 CTI SMP setup
        ctiInfo = {}
        for c in self.cortexA15cores:
            ctiInfo[c] = self.getCTIInfoForCore(c)
        smp = CTISyncSMPDevice(self, "Cortex-A15 SMP", self.cortexA15cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(smp)
        self.addDeviceInterface(smp)

        # Automatically handle connection to CTIs
        self.addManagedPlatformDevices(self.CoreCTIs)

    def setETFTraceEnabled(self, etfTrace, enabled):
        '''Enable/disable ETF trace capture'''
        if enabled:
            # Ensure TPIU is disabled
            self.TPIU.setEnabled(False)
            # Put the ETF in ETB mode
            etfTrace.getTMC().setMode(CSTMC.Mode.ETB)
        else:
            pass
            # Put the ETF in FIFO mode
            #etfTrace.getTMC().setMode(CSTMC.Mode.ETF)

        self.enableCTIsForSink(etfTrace, enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A15):
            coreTM = self.getTMForCore(self.cortexA15cores[c])
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexA15cores[c], coreTM)

        self.registerTraceSource(traceCapture, self.STM0)

    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # Source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

        # CTI (if present) is also managed by the configuration
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.addManagedTraceDevices(traceCapture.getName(), [ cti ])

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''

        # Build map of sources to funnels and funnel ports
        funnelMap = {}
        funnelMap[self.STM0] = (self.Funnel0, 4)
        funnelMap[self.PTMs[0]] = (self.Funnel0, 0)
        funnelMap[self.PTMs[1]] = (self.Funnel0, 1)
        funnelMap[self.PTMs[2]] = (self.Funnel0, 2)
        funnelMap[self.PTMs[3]] = (self.Funnel0, 3)

        return funnelMap.get(source, (None, None))

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

        coreTraceEnabled = self.getOptionValue("options.cortexA15.coreTrace")
        for i in range(0, NUM_CORES_CORTEX_A15):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexA15.coreTrace.Cortex_A15_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexA15cores[i])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "cortexA15")
            self.setTriggerGeneratesDBGRQ(coreTM, self.getOptionValue("options.cortexA15.coreTrace.triggerhalt"))

        stmEnabled = self.getOptionValue("options.stm.STM0")
        self.setTraceSourceEnabled(self.STM0, stmEnabled)

        dstream_opts = "options.traceBuffer.traceCapture.dstream."

        portWidthOpt = self.getOptions().getOption(dstream_opts + "tpiuPortWidth")
        if portWidthOpt:
           portWidth = self.getOptionValue(dstream_opts + "tpiuPortWidth")
           self.setPortWidth(int(portWidth))

        traceBufferSizeOpt = self.getOptions().getOption(dstream_opts + "traceBufferSize")
        if traceBufferSizeOpt:
            traceBufferSize = self.getOptionValue(dstream_opts + "traceBufferSize")
            self.setTraceBufferSize(traceBufferSize)

        # Register trace sources for each trace sink
        self.registerTraceSources(self.ETF0Trace)
        self.registerTraceSources(self.DSTREAM)

        traceMode = self.getOptionValue("options.traceBuffer.traceCapture")
        self.setManagedDeviceList(self.getManagedDevices(traceMode))

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

        for i in range(0, NUM_CORES_CORTEX_A15):
            a15_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA15cores[i])
            a15_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA15cores[i])

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setETFTraceEnabled(self.ETF0Trace, False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "ETF0":
            self.setETFTraceEnabled(self.ETF0Trace, True)
            self.setDSTREAMTraceEnabled(False)
        elif method == "DSTREAM":
            self.setETFTraceEnabled(self.ETF0Trace, False)
            self.setDSTREAMTraceEnabled(True)

    def getPTMs(self):
        '''Get the PTMs'''
        return self.PTMs

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

    def addManagedPlatformDevices(self, devs):
        '''Add devices to the list of devices managed by the configuration, as long as they are not already present'''
        for d in devs:
            if d not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(d)

    def registerTraceSource(self, traceCapture, source):
        '''Register trace source with trace capture device'''
        traceCapture.addTraceSource(source)
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

    def addManagedTraceDevices(self, traceKey, devs):
        '''Add devices to the set of devices managed by the configuration for this trace mode'''
        traceDevs = self.mgdTraceDevs.get(traceKey)
        if not traceDevs:
            traceDevs = []
            self.mgdTraceDevs[traceKey] = traceDevs
        for d in devs:
            if d not in traceDevs:
                traceDevs.append(d)

    def setInternalTraceRange(self, coreTM, coreName):

        traceRangeEnable = self.getOptionValue("options.%s.coreTrace.traceRange" % coreName)
        traceRangeStart = self.getOptionValue("options.%s.coreTrace.traceRange.start" % coreName)
        traceRangeEnd = self.getOptionValue("options.%s.coreTrace.traceRange.end" % coreName)

        if coreTM in self.traceRangeIDs:
            coreTM.clearTraceRange(self.traceRangeIDs[coreTM])
            del self.traceRangeIDs[coreTM]

        if traceRangeEnable:
            self.traceRangeIDs[coreTM] = coreTM.addTraceRange(traceRangeStart, traceRangeEnd)

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.enableCTIInput(cti, input, channel, enabled)

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

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        funnel, port = self.getFunnelPortForSource(source)
        if funnel:
            if enabled:
                funnel.setPortEnabled(port)
            else:
                funnel.setPortDisabled(port)

    def createSTM(self, stmDev, streamID, name):
        stm = STMTraceSource(self, stmDev, streamID, name)
        # Disabled by default - will enable with option
        stm.setEnabled(False)
        return stm

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

    def enableResetHandling(self):
        script="""from LDDI import *
from icepick import *
from rvi import *
icePickDaps = [14]
setupDone = 0

def HandleOpenConn(dev, type, state):
    global setupDone
    global icePickDaps
    if type == 1:
        if not setupDone == 1:
            print "Enabling ICEPICK"
            icepick.enable_ICEPICK_D_Multi(icePickDaps)
            setupDone = 1
    return handleOpenConn(dev,type,state)

def UnknownStateRecovery():
    global icePickDaps
    print "UnknownStateRecovery"
    icepick.enable_ICEPICK_D_Multi(icePickDaps)

def HandleExeReset(flags):
    global icePickDaps
    print "ICEPICK reset"
    icepick.reset_ICEPICK_D()
    sleep(500)
    return False"""

        self.getDebug().setConfig(0, "PythonScript", script)

    def connectManagedDevices(self):
        self.enableResetHandling()
        DTSLv1.connectManagedDevices(self)

class DtslScript_RVI(DtslScript):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_RVI.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA15TabPage(),
                DtslScript.getOptionCortexA15PowerupTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionCacheRAMsTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("traceBuffer", "Trace Buffer", childOptions=[
                    DTSLv1.radioEnumOption(
                        'traceCapture',
                        'Trace capture method',
                        defaultValue="none",
                        values=[("none", "None"),
                                ("ETF0", "On Chip Trace Buffer (ETF0/TMC)")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency.")
        ])

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, portWidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        self.setPortWidth(portWidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_ST.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA15TabPage(),
                DtslScript.getOptionCortexA15PowerupTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionCacheRAMsTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("traceBuffer", "Trace Buffer", childOptions=[
                    DTSLv1.radioEnumOption(
                        'traceCapture',
                        'Trace capture method',
                        defaultValue="none",
                        values=[("none", "None"),
                                ("ETF0", "On Chip Trace Buffer (ETF0/TMC)"),
                                (DtslScript_DSTREAM_ST.getDSTREAMOptions())],
                        setter=DtslScript.setTraceCaptureMethod)
        ])

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

class DtslScript_DSTREAM_PT(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_PT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA15TabPage(),
                DtslScript.getOptionCortexA15PowerupTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionCacheRAMsTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("traceBuffer", "Trace Buffer", childOptions=[
                    DTSLv1.radioEnumOption(
                        'traceCapture',
                        'Trace capture method',
                        defaultValue="none",
                        values=[("none", "None"),
                                ("ETF0", "On Chip Trace Buffer (ETF0/TMC)"),
                                (DtslScript_DSTREAM_PT.getStoreAndForwardOptions())],
                        setter=DtslScript.setTraceCaptureMethod)
        ])

    @staticmethod
    def getStoreAndForwardOptions():
        return (
            "DSTREAM", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement(
                "dstream", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="16",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit"),
                                  ("5", "5 bit"), ("6", "6 bit"), ("7", "7 bit"), ("8", "8 bit"),
                                  ("9", "9 bit"), ("10", "10 bit"), ("11", "11 bit"), ("12", "12 bit"),
                                  ("13", "13 bit"), ("14", "14 bit"), ("15", "15 bit"), ("16", "16 bit")], isDynamic=False)
                ]
            )
        )

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")

