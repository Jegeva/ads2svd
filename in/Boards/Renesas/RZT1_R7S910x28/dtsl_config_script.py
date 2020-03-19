# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl.components import MemoryRouter
from com.arm.debug.dtsl.components import DapMemoryAccessor
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import ETMv3_4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE
from struct import pack, unpack
from jarray import zeros
from java.lang import StringBuilder

NUM_CORES_CORTEX_R4 = 1
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
DSTREAM_PORTWIDTH = 8
CTM_CHANNEL_SYNC_STOP = 0  # Use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # Use channel 2 for trace triggers

# for TPIU trace pinmuxing
REGADR_BASE   = 0xA0000000
REGADR_PWPR   = REGADR_BASE + 0x02FF        # MPC.PWPR
REGADR_PP6PFS = REGADR_BASE + 0x02BE        # MPC.PP6PFS
REGADR_PP7PFS = REGADR_BASE + 0x02BF        # MPC.PP7PFS
REGADR_PR0PFS = REGADR_BASE + 0x02C0        # MPC.PR0PFS
REGADR_PR1PFS = REGADR_BASE + 0x02C1        # MPC.PR1PFS
REGADR_PR2PFS = REGADR_BASE + 0x02C2        # MPC.PR2PFS
REGADR_PR3PFS = REGADR_BASE + 0x02C3        # MPC.PR3PFS
REGADR_PR4PFS = REGADR_BASE + 0x02C4        # MPC.PR4PFS
REGADR_PR5PFS = REGADR_BASE + 0x02C5        # MPC.PR5PFS
REGADR_PR6PFS = REGADR_BASE + 0x02C6        # MPC.PR6PFS
REGADR_PR7PFS = REGADR_BASE + 0x02C7        # MPC.PR7PFS
REGADR_PORTP  = REGADR_BASE + 0x0097        # PORTP.PMR
REGADR_PORTR  = REGADR_BASE + 0x0098        # PORTR.PMR

# Jython regards any number with the upper bit set as a negative, so any 8-bit number bigger than 0x7F may cause problems.
JYTHON_NUMBER_C0 = -64                      # This number(0xFFFFFFC0) will be work as 0xC0
JYTHON_NUMBER_FF = -1                       # This number(0xFFFFFFFF) will be work as 0xFF


# Class to control a core with an associated CTI
# Handles CTI configuration synchronised start/stop with other cores
# Can optionally implement invasive config - core will be stopped while the CTI is configured
class CTICore(Device):
    def __init__(self, config, id, name, device, invasive):
        Device.__init__(self, config, id, name)
        self.config = config
        self.cti = device
        self.doXTrig = False
        self.doInvasive = False
        self.supportInvasive = invasive
        self.connected = False
        self.checkClock = False

    def get_core_state(self):
        state = zeros(1, 'i')
        self.getExecStatus(state, zeros(1, 'i'), zeros(1, 'l'), zeros(1, 'l'),
                           zeros(1, 'l'))
        return state[0]

    def is_stopped(self):
        state = self.get_core_state()

        if state == RDDI_EVENT_TYPE.RDDI_PROC_STATE_STOPPED.ordinal():
            return True

        return False

    def openConn(self, id, version, name):
        if self.checkClock:
            self.config.checkSecondaryCoreClock(self.getName())
        Device.openConn(self, id, version, name)
        self.connected = True

        if self.doXTrig:
            if self.doInvasive and not self.is_stopped():
                try:
                    self.stop()
                    self.configureCTI()
                finally:
                    Device.go(self)
            else:
                self.configureCTI()

    # If we've configured cross-triggering we need to unconfigure it when we disconnect
    def closeConn(self):
        if self.doXTrig:
            if self.doInvasive and not self.is_stopped():
                try:
                    self.stop()
                    self.disableCTI()
                finally:
                    Device.go(self)
            else:
                self.disableCTI()
        Device.closeConn(self)
        self.connected = False

    def clearTriggers(self):
        if self.isConnected():
            if self.doInvasive and not self.is_stopped():
                try:
                    self.stop()
                    self.cti.writeRegister(CTIINTACK, 0x01 << TRIG_STOP)
                    self.cti.writeRegister(CTIINTACK, 0x00)
                except:
                    pass
            else:
                self.cti.writeRegister(CTIINTACK, 0x01 << TRIG_STOP)
                self.cti.writeRegister(CTIINTACK, 0x00)

    def configureCTI(self):
        if not self.cti.isConnected():
            self.cti.connect()

        self.cti.writeRegister(CTICTRL, 0x00000001)
        self.cti.writeRegister(CTIINEN + TRIG_STOP, 0x01 << CTM_CHANNEL_SYNC_STOP)
        self.cti.writeRegister(CTIOUTEN + TRIG_STOP, 0x01 << CTM_CHANNEL_SYNC_STOP)
        self.cti.writeRegister(CTIOUTEN + TRIG_START, 0x01 << CTM_CHANNEL_SYNC_START)

    def disableCTI(self):
        self.cti.writeRegister(CTIINEN + TRIG_STOP, 0x00)
        self.cti.writeRegister(CTIOUTEN + TRIG_STOP, 0x00)
        self.cti.writeRegister(CTIOUTEN + TRIG_START, 0x00)
        self.cti.writeRegister(CTIINTACK, 0x01 << TRIG_STOP)
        self.cti.writeRegister(CTIINTACK, 0x00)

    def isConnected(self):
        return self.connected

    # Pass a go() instruction down to the parent, as this will need to configure & start other cores
    # If the parent says we are the only core connected, just start this core
    def go(self):
        if self.doXTrig:
            if not self.config.runCores():
                Device.go(self)
        else:
            Device.go(self)

    # For a step we need to unconfigure routing of start and stop events through the CTI
    # so that other cores don't run. Leave other events unaffected
    def step(self, count, flags):
        if self.doXTrig:
            result = 0
            origGate = self.cti.getChannelGate()

            newGate = origGate & ~((1 << CTM_CHANNEL_SYNC_STOP) | (1 << CTM_CHANNEL_SYNC_START));
            self.cti.setChannelGate(newGate)

            self.clearTriggers()

            try:
                result = Device.step(self, count, flags)
                return result
            except:
                pass
            finally:
                self.cti.setChannelGate(origGate)
        else:
            return Device.step(self, count, flags)

    def enableInvasive(self, enabled):
        self.doInvasive = enabled and self.supportInvasive

    def enableXTrig(self, enabled):
        self.doXTrig = enabled
        if self.isConnected():
            # need to update CTI registers when we have an active connection
            if enabled:
                self.configureCTI()
            else:
                self.disableCTI()

    # Invasive mode, stop the core while configuring the CTI
    # Only used if we are a core that might need it
    def enableInvasive(self, enabled):
        self.doInvasive = enabled and self.supportInvasive


class M_Class_ETMv3_4(ETMv3_4TraceSource):
    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False


class DtslScript_DSTREAM(DTSLv1):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB0", "On Chip Trace Buffer (ETB0)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript_DSTREAM.setTraceCaptureMethod),
                ]),
                DTSLv1.tabPage("cortexR4", "Cortex-R4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R4 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_R4_%d' % c, "Enable Cortex-R4 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_R4) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False) ] +
                            [ ETMv3_3TraceSource.cycleAccurateOption(DtslScript_DSTREAM.getETMsForCortexAR) ] +
                            [ ETMv3_3TraceSource.dataOption(DtslScript_DSTREAM.getETMsForCortexAR) ] +
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
                ]),
                DTSLv1.tabPage("itm", "ITM", childOptions=[
                    DTSLv1.booleanOption('ITM0', 'Enable ITM 0 trace', defaultValue=False)
                ]),
                DTSLv1.tabPage("auth", "AUTH", childOptions=[
                    DTSLv1.booleanOption('configAUTH', 'Configure the JTAG authentication',
                        defaultValue = False,
                        childOptions = [
                            DTSLv1.integerOption('key0', 'Key 0',
                                description='32-bit JTAG authentication key 0',
                                defaultValue=0x00000000,
                                display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('key1', 'Key 1',
                                description='32-bit JTAG authentication key 1',
                                defaultValue=0x00000000,
                                display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('key2', 'Key 2',
                                description='32-bit JTAG authentication key 2',
                                defaultValue=0x00000000,
                                display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('key3', 'Key 3',
                                description='32-bit JTAG authentication key 3',
                                defaultValue=0x00000000,
                                display=IIntegerOption.DisplayFormat.HEX),
                            ]
                        )
                ])
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []

        # Tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # Locate devices on the platform and create corresponding objects
        self.discoverDevices()

        # Only DAP device is managed by default - others will be added when enabling trace, SMP etc
        if self.dap not in self.mgdPlatformDevs:
            self.mgdPlatformDevs.append(self.dap)

        self.exposeCores()

        self.traceRangeIDs = {}

        traceComponentOrder = [ self.Funnel0 ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.ETB0 ]
        self.setupETBTrace(self.ETB0, "ETB0", traceComponentOrder, managedDevices)

        traceComponentOrder = [ self.Funnel0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(DSTREAM_PORTWIDTH, traceComponentOrder, managedDevices)

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+
    def configureAUTH(self):
        auth0 = self.getOptionValue("options.auth.configAUTH.key0")
        auth1 = self.getOptionValue("options.auth.configAUTH.key1")
        auth2 = self.getOptionValue("options.auth.configAUTH.key2")
        auth3 = self.getOptionValue("options.auth.configAUTH.key3")
        try:
            self.dap.writeMem(0, 0x00000000, auth0)
            self.dap.writeMem(0, 0x00000004, auth1)
            self.dap.writeMem(0, 0x00000008, auth2)
            self.dap.writeMem(0, 0x0000000C, auth3)
        except:
            # failed
            pass

    def get_core_state(self, core):
        try:
            state = zeros(1, 'i')
            core.getExecStatus(state, zeros(1, 'i'),
                                      zeros(1, 'l'),
                                      zeros(1, 'l'),
                                      zeros(1, 'l'))
        except:
            pass

        return state[0]

    def is_stopped(self, core):
        return self.get_core_state(core) == RDDI_EVENT_TYPE.RDDI_PROC_STATE_STOPPED

    def read8(self, core, address):
        # 1 byte read from physical address via core
        buffer = zeros(1, 'b')
        try:
            core.memRead(0, address, RDDI_ACC_SIZE.RDDI_ACC_BYTE, RDDI.RDDI_MRUL_NORMAL, 1, buffer)
        except:
            # failed
            pass
        return buffer

    def write8(self, core, address, value):
        # 1 byte write to physical address via core
        buffer = zeros(1, 'b')
        buffer[0] = value
        try:
            core.memWrite(0, address, RDDI_ACC_SIZE.RDDI_ACC_BYTE, RDDI.RDDI_MRUL_NORMAL, False, 1, buffer)
        except:
            # failed
            pass

    def setupPinmux(self, core):
        # Set up pinmuxing
        try:
            self.write8(core, REGADR_PWPR, 0x00)                # MPC.PWPR
            self.read8(core, REGADR_PWPR)
            self.write8(core, REGADR_PWPR, 0x40)
            self.write8(core, REGADR_PP6PFS, 0x27)              # MPC.PP6PFS : PSEL[5:0]=TRACECTL
            self.write8(core, REGADR_PP7PFS, 0x27)              # MPC.PP7PFS : PSEL[5:0]=TRACECLK
            self.write8(core, REGADR_PR0PFS, 0x27)              # MPC.PR0PFS : ISEL=OUTPUT PSEL[5:0]=TRACEDATA0
            self.write8(core, REGADR_PR1PFS, 0x27)              # MPC.PR1PFS : ISEL=OUTPUT PSEL[5:0]=TRACEDATA1
            self.write8(core, REGADR_PR2PFS, 0x27)              # MPC.PR2PFS : ISEL=OUTPUT PSEL[5:0]=TRACEDATA2
            self.write8(core, REGADR_PR3PFS, 0x27)              # MPC.PR3PFS : ISEL=OUTPUT PSEL[5:0]=TRACEDATA3
            self.write8(core, REGADR_PR4PFS, 0x27)              # MPC.PR4PFS : ISEL=OUTPUT PSEL[5:0]=TRACEDATA4
            self.write8(core, REGADR_PR5PFS, 0x27)              # MPC.PR5PFS : ISEL=OUTPUT PSEL[5:0]=TRACEDATA5
            self.write8(core, REGADR_PR6PFS, 0x27)              # MPC.PR6PFS : ISEL=OUTPUT PSEL[5:0]=TRACEDATA6
            self.write8(core, REGADR_PR7PFS, 0x27)              # MPC.PR7PFS : ISEL=OUTPUT PSEL[5:0]=TRACEDATA7
            self.write8(core, REGADR_PORTP, JYTHON_NUMBER_C0)   # PORTP.PMR  : PP6 and PP7 = Peripheral
            self.write8(core, REGADR_PORTR, JYTHON_NUMBER_FF)   # PORTR.PMR  : PR0 to PR7  = Peripheral
        except:
            pass

    def setCoreConfiguration(self):

        coreOpen = False
        coreStop = False

        coreTraceEnabled = self.getOptionValue("options.cortexR4.coreTrace")

        if coreTraceEnabled and self.TPIU.getEnabled():
            try:
                core = self.cortexR4cores[0]
                core.openConn(zeros(1, 'i'), zeros(1, 'i'), StringBuilder(1024))
                coreOpen = True
            except:
                pass

        if coreOpen:
            try:
                if not self.is_stopped(core):
                    try:
                        core.stop()
                        coreStop = True
                    except:
                        pass
            except:
                pass

        if coreTraceEnabled and coreOpen:
            if self.TPIU.getEnabled():
                self.setupPinmux(core)    # pinmuxing via Core w/ core state check

        if coreStop:
            try:
                core.go()
            except:
                pass

        if coreOpen:
            try:
                core.closeConn()
            except:
                pass

    def connectManagedDevices(self):
        auth = self.getOptionValue("options.auth.configAUTH")

        if auth:
            self.dap.connect()
            self.configureAUTH()
            self.dap.disconnect()

        # connect to other managed devices
        DTSLv1.connectManagedDevices(self)

    def postConnect(self):
        self.setCoreConfiguration()

        DTSLv1.postConnect(self)

    def discoverDevices(self):
        '''Find and create devices'''

        self.dap = CSDAP(self, 1, "DAP")

        cortexR4coreDevs = [8]
        self.cortexR4cores = []

        streamID = 1

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, 3, "OutCTI0")

        coreCTIDevs = [9]
        self.CoreCTIs = []

        etmDevs = [10, 13]
        self.ETMs = []
        self.cortexARetms = []

        # ITM 0
        self.ITM0 = self.createITM(6, streamID, "ITM0")
        streamID += 1

        # ITM 1
        self.ITM1 = self.createITM(12, streamID, "ITM1")
        streamID += 1

        # Create core
        for i in range(0, NUM_CORES_CORTEX_R4):
            # Create core
            core = Device(self, cortexR4coreDevs[i], "Cortex-R4")
            self.cortexR4cores.append(core)

        for i in range(0, len(coreCTIDevs)):
            # Create CTI
            coreCTI = CSCTI(self, coreCTIDevs[i], "CoreCTIs[%d]" % i)
            self.CoreCTIs.append(coreCTI)

        for i in range(0, len(etmDevs)):
            # Create ETM
            etm = self.createETM(etmDevs[i], streamID, "ETMs[%d]" % i)
            streamID += 1

        # ETB 0
        self.ETB0 = ETBTraceCapture(self, 2, "ETB0")

        # DSTREAM
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

        # TPIU
        self.TPIU = self.createTPIU(4, "TPIU")

        # Funnel 0
        self.Funnel0 = self.createFunnel(5, "Funnel0")

    def exposeCores(self):
        for core in self.cortexR4cores:
            self.addDeviceInterface(self.createDAPWrapper(core))

    def setupETBTrace(self, etb, name, traceComponentOrder, managedDevices):
        '''Setup ETB trace capture'''
        # Use continuous mode
        etb.setFormatterMode(FormatterMode.CONTINUOUS)

        # Register other trace components with ETB and register ETB with configuration
        etb.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etb)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)

    def setupDSTREAMTrace(self, portwidth, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU for continuous mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        self.TPIU.setPortSize(portwidth)

        # Configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.DSTREAM.setPortWidth(portwidth)

        # Register other trace components
        self.DSTREAM.setTraceComponentOrder(traceComponentOrder)

        # Register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", managedDevices)

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sources to CTIs
        sourceCTIMap = {}
        sourceCTIMap[self.ETMs[0]] = (self.CoreCTIs[0], 6, CTM_CHANNEL_TRACE_TRIGGER)

        return sourceCTIMap.get(source, (None, None, None))

    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''

        # Build map of trace sinks to CTIs
        sinkCTIMap = {}
        sinkCTIMap[self.ETB0] = (self.OutCTI0, 1, CTM_CHANNEL_TRACE_TRIGGER)
        sinkCTIMap[self.DSTREAM] = (self.OutCTI0, 3, CTM_CHANNEL_TRACE_TRIGGER)

        return sinkCTIMap.get(sink, (None, None, None))

    def getTMForCore(self, core):
        '''Get trace macrocell for core'''

        # Build map of cores to trace macrocells
        coreTMMap = {}
        coreTMMap[self.cortexR4cores[0]] = self.ETMs[0]

        return coreTMMap.get(core, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def createETM(self, etmDev, streamID, name):
        '''Create ETM of correct version'''
        if etmDev == 10:
            etm = ETMv3_3TraceSource(self, etmDev, streamID, name)
            # Disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            self.cortexARetms.append(etm)
            return etm
        if etmDev == 13:
            etm = M_Class_ETMv3_4(self, etmDev, streamID, name)
            # Disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            return etm

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu

    def setETBTraceEnabled(self, etb, enabled):
        '''Enable/disable ETB trace capture'''
        self.enableCTIsForSink(etb, enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_R4):
            coreTM = self.getTMForCore(self.cortexR4cores[c])
            if coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, self.cortexR4cores[c], coreTM)

        self.registerTraceSource(traceCapture, self.ITM0)
        self.registerTraceSource(traceCapture, self.ITM1)

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
        funnelMap[self.ITM0] = (self.Funnel0, 3)
        funnelMap[self.ITM1] = (self.Funnel0, 4)
        funnelMap[self.ETMs[0]] = (self.Funnel0, 0)
        funnelMap[self.ETMs[1]] = (self.Funnel0, 5)

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

        traceMode = self.getOptionValue("options.trace.traceCapture")

        coreTraceEnabled = self.getOptionValue("options.cortexR4.coreTrace")
        for i in range(0, NUM_CORES_CORTEX_R4):
            thisCoreTraceEnabled = self.getOptionValue("options.cortexR4.coreTrace.Cortex_R4_%d" % i)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.cortexR4cores[i])
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "cortexR4")
            self.setTriggerGeneratesDBGRQ(coreTM, self.getOptionValue("options.cortexR4.coreTrace.triggerhalt"))

        itmEnabled = self.getOptionValue("options.itm.ITM0")
        self.setTraceSourceEnabled(self.ITM0, itmEnabled)

        # Register trace sources for each trace sink
        self.registerTraceSources(self.ETB0)
        self.registerTraceSources(self.DSTREAM)

        self.setManagedDeviceList(self.getManagedDevices(traceMode))

    def updateDynamicOptions(self):
        '''Update the dynamic options'''

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def setTraceCaptureMethod(self, method):
        if method == "none":
            self.setETBTraceEnabled(self.ETB0, False)
            self.setDSTREAMTraceEnabled(False)
        elif method == "ETB0":
            self.setETBTraceEnabled(self.ETB0, True)
            self.setDSTREAMTraceEnabled(False)
        elif method == "DSTREAM":
            self.setETBTraceEnabled(self.ETB0, False)
            self.setDSTREAMTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def getETMsForCortexAR(self):
        '''Get the ETMs for Cortex-A and Cortex-R cores only'''
        return self.cortexARetms

    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+

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

    def createDAPWrapper(self, core):
        '''Add a wrapper around a core to allow access to AHB and APB via the DAP'''
        return MemoryRouter(
            [DapMemoryAccessor("AHB", self.dap, 0, "AHB bus accessed via AP_0 on DAP_0"),
             DapMemoryAccessor("APB", self.dap, 3, "APB bus accessed via AP_3 on DAP_0")],
            core)

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

    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, itmDev, streamID, name)
        # Disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

class DtslScript_ULINK(DtslScript_DSTREAM):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("ETB0", "On Chip Trace Buffer (ETB0)")],
                        setter=DtslScript_ULINK.setTraceCaptureMethod),
                ]),
                DTSLv1.tabPage("cortexR4", "Cortex-R4", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-R4 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex_R4_%d' % c, "Enable Cortex-R4 %d trace" % c, defaultValue=True)
                            for c in range(0, NUM_CORES_CORTEX_R4) ] +
                            [ DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable the ETM triggers to halt execution", defaultValue=False) ] +
                            [ ETMv3_3TraceSource.cycleAccurateOption(DtslScript_ULINK.getETMsForCortexAR) ] +
                            [ ETMv3_3TraceSource.dataOption(DtslScript_ULINK.getETMsForCortexAR) ] +
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
                ]),
                DTSLv1.tabPage("itm", "ITM", childOptions=[
                    DTSLv1.booleanOption('ITM0', 'Enable ITM 0 trace', defaultValue=False)
                ]),
                DTSLv1.tabPage("auth", "AUTH", childOptions=[
                    DTSLv1.booleanOption('configAUTH', 'Configure the JTAG authentication',
                        defaultValue = False,
                        childOptions = [
                            DTSLv1.integerOption('key0', 'Key 0',
                                description='32-bit JTAG authentication key 0',
                                defaultValue=0x00000000,
                                display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('key1', 'Key 1',
                                description='32-bit JTAG authentication key 1',
                                defaultValue=0x00000000,
                                display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('key2', 'Key 2',
                                description='32-bit JTAG authentication key 2',
                                defaultValue=0x00000000,
                                display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('key3', 'Key 3',
                                description='32-bit JTAG authentication key 3',
                                defaultValue=0x00000000,
                                display=IIntegerOption.DisplayFormat.HEX),
                            ]
                        )
                ])
            ])
        ]


# These are simple wrapper classes to the base DtslScript_ULINK class.
# For each platform, Arm DS creates a folder named after the DTSL Class to store
# the DTSL options file.
# Forcing each target connection to use a different class means that
# different DTSL options files are created for each connection type.
# If you want to have a shared options file, then use the same class name for
# each connection type
class DtslScript_ULINKpro(DtslScript_ULINK):
    pass

class DtslScript_CMSIS(DtslScript_ULINK):
    def discoverDevices(self):
        '''Find and create devices'''

        self.dap = CSDAP(self, 1, "DAP")

        cortexR4coreDevs = [8]
        self.cortexR4cores = []

        streamID = 1

        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, 3, "OutCTI0")

        coreCTIDevs = [9]
        self.CoreCTIs = []

        etmDevs = [10, 13]
        self.ETMs = []
        self.cortexARetms = []

        # ITM 0
        self.ITM0 = self.createITM(6, streamID, "ITM0")
        streamID += 1

        # ITM 1
        self.ITM1 = self.createITM(12, streamID, "ITM1")
        streamID += 1

        for i in range(0, NUM_CORES_CORTEX_R4):
            # Create core
            core = Device(self, cortexR4coreDevs[i], "Cortex-R4")
            self.cortexR4cores.append(core)

        for i in range(0, len(coreCTIDevs)):
            # Create CTI
            coreCTI = CSCTI(self, coreCTIDevs[i], "CoreCTIs[%d]" % i)
            self.CoreCTIs.append(coreCTI)

        for i in range(0, len(etmDevs)):
            # Create ETM
            etm = self.createETM(etmDevs[i], streamID, "ETMs[%d]" % i)
            streamID += 1

        # ETB 0
        self.ETB0 = ETBTraceCapture(self, 2, "ETB0")

        # DSTREAM
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

        # TPIU
        self.TPIU = self.createTPIU(4, "TPIU")

        # Funnel 0
        self.Funnel0 = self.createFunnel(5, "Funnel0")

class DtslScript_RVI(DtslScript_ULINK):
    pass
