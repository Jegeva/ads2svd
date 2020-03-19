# Copyright (C) 2013-2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from com.arm.debug.dtsl.components import ETMv3_4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import GenericTraceDevice
from com.arm.debug.dtsl import DTSLException
from com.arm.debug.dtsl.nativelayer import NativeException
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
from com.arm.rddi import RDDI, RDDI_ACC_SIZE, RDDI_EVENT_TYPE
from jtagap import JTAGAP
import jtag

from struct import pack, unpack
from jarray import array, zeros

# Import core specific functions
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a5_rams


NUM_CORES_CORTEX_A5 = 1
NUM_CORES_CORTEX_M4 = 1
TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
CYCLE_ACCURATE_DESCRIPTION = '''Enable cycle accurate trace'''
CTM_CHANNEL_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHANNEL_SYNC_START = 1  # use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 2  # use channel 2 for trace triggers
ITMA5_ATB_ID = 1
ITMM4_ATB_ID = 2
ATB_ID_BASE = 3
CORTEX_A5_TRACE_OPTIONS = 0
CORTEX_M4_TRACE_OPTIONS = 1

CTICTRL  =  0x000
CTIINTACK = 0x004
CTIINEN  =  0x008
CTIOUTEN =  0x028

TRIG_STOP  = 0
TRIG_START = 7

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

    def memRead(self, page, address, size, rule, count, pDataOut):
        Device.memRead(self, page, address, size, rule, count, pDataOut)

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


class A5Core(CTICore):
    def __init__(self, config, id, name, device, invasive):
        CTICore.__init__(self, config, id, name, device, invasive)
        self.postConnectConfig = {}
        self.isConnectedA5Core = False

    def openConn(self, pId, pVersion, pMessage):
        CTICore.openConn(self, pId, pVersion, pMessage)
        for k, v in self.postConnectConfig.items():
            try:
                self.setConfig(k, v)
            except NativeException, e:
                # ignore missing config item on older firmware
                if e.getRDDIErrorCode() != RDDI.RDDI_ITEMNOTSUP:
                    raise
        self.isConnectedA5Core = True

    def addPostConnectConfigItem(self, name, value):
        self.postConnectConfig[name] = value

    def setConfigWhenConnected(self, name, value):
        self.addPostConnectConfigItem(name, value)
        if self.isConnectedA5Core:
            self.setConfig(name, value)


class SWO(GenericTraceDevice):
    def postConnect(self):
        GenericTraceDevice.postConnect(self)

        ITATBCTR0 = 0x03C0 # Integration Test ATB Control Register 0
        ITATBCTR2 = 0x03BC # Integration Test ATB Control Register 2
        self.writeRegister(ITATBCTR0, 0x00000001)
        self.writeRegister(ITATBCTR2, 0x00000001)


class M4_ETM(ETMv3_4TraceSource):
    # Disable trace triggers and start stop points as currently unsupported
    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False


class TraceRangeOptions:
    def __init__(self, coreTraceName = None, dtsl = None):
        if coreTraceName == None:
            self.defaultSetup()
        else:
            self.traceRangeEnable = dtsl.getOptionValue("%s.traceRange" % coreTraceName)
            self.traceRangeStart = dtsl.getOptionValue("%s.traceRange.start" % coreTraceName)
            self.traceRangeEnd = dtsl.getOptionValue("%s.traceRange.end" % coreTraceName)
            self.traceRangeIDs = None

    def defaultSetup(self):
        self.traceRangeEnable = False
        self.traceRangeStart = None
        self.traceRangeEnd = None
        self.traceRangeIDs = None


class CacheMaintCore(CTICore):
    def __init__(self, config, id, name, coreCTI, boolean):
        CTICore.__init__(self, config, id, name, coreCTI, boolean)

    def to_s8(self, val):
        return val > 127 and val - 256 or val

    def __clean_invalidate_caches(self, page):
        buf = zeros(4,'b')
        # Instruction clean invalidation
        CTICore.memRead(self, page, 0xE0082800, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)
        if buf[0] & 0x1:
            buf = array(map(self.to_s8, [buf[0] & 0xFF, 0x0, 0x0, 0x8F]), 'b')
            CTICore.memWrite(self, page,  0xE0082800, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)
        # Data clean invalidation
        CTICore.memRead(self, page, 0xE0082000, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, len(buf), buf)
        if buf[0] & 0x1:
            buf = array(map(self.to_s8, [buf[0] & 0xFF, 0x0, 0x0, 0x8F]), 'b')
            CTICore.memWrite(self, page,  0xE0082000, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, len(buf), buf)

    def setSWBreak(self, page, addr, flags):
        brkID = CTICore.setSWBreak(self, page, addr, flags)
        self.__clean_invalidate_caches(page)

        return brkID

    def memWrite(self, page, addr, size, rule, check, count, data):
        CTICore.memWrite(self, page, addr, size, rule, check, count, data)
        self.__clean_invalidate_caches(page)


class DtslScript_DSTREAM(DTSLv1):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("system", "System", childOptions=[
                    DTSLv1.booleanOption('wake', 'Start secondary core clock on connection', defaultValue=False,
                                         description="Set to ensure the secondary core clock is enabled when connecting.",
                                         setter=DtslScript_DSTREAM.wakeSecondary),
                    DTSLv1.booleanOption('xTrig', 'Cortex-A5 - Cortex-M4 synchronized start and stop', defaultValue=False, isDynamic=True,
                        setter=DtslScript_DSTREAM.EnableXTrig, childOptions =
                            [DTSLv1.booleanOption('invasive', 'Invasive configuration', defaultValue=False, isDynamic=True,
                                setter=DtslScript_DSTREAM.EnableInvasive,
                                description="If the Cortex-M4 is executing WFI, Arm DS will be unable to configure cross-triggering. Invasive configuration halts the Cortex-M4 while setting up cross-triggering"
                            )]
                    ),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            # Limit of 4 bit TPIU trace on this platform, even on DSTREAM
                            values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")], isDynamic=False),
                    ])
                ]),
                DTSLv1.tabPage("cortexA5", "Cortex-A5", childOptions=[
                    DTSLv1.booleanOption('cortexA5coreTrace', 'Cortex-A5 trace', defaultValue=False,
                                         description="Enable trace from the Cortex-A5 module",
                        childOptions =
                            [DTSLv1.enumOption('A5traceCapture', 'Trace capture method', defaultValue="none",
                                values = [("none", "None"), ("ETB_A5", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                                setter=DtslScript_DSTREAM.setA5TraceCaptureMethod)] +
                            ETMv3_5TraceSource.defaultOptions(DtslScript_DSTREAM.getA5ETM) +
                            [ #ETMv3_5TraceSource.timestampingOption(DtslScript_DSTREAM.getA5ETM),
                              DTSLv1.booleanOption('contextIDs', "ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                              ETMv3_5TraceSource.dataOption(DtslScript_DSTREAM.getA5ETM),
                              DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable ETM triggers to halt execution", defaultValue=False) ] +
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
                            ] +
                            [DTSLv1.booleanOption('itm', 'ITM trace', defaultValue=False,
                                                   description="Enable trace from the ITM",
                                                   setter=DtslScript_DSTREAM.setITMEnabledA5)]
                        )
                ]),
                DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('cortexM4coreTrace', 'Cortex-M4 trace', defaultValue=False,
                                         description="Enable trace from the Cortex-M4 module",
                        childOptions =
                            [DTSLv1.enumOption('M4traceCapture', 'Trace capture method', defaultValue="none",
                                values = [("none", "None"), ("ETB_M4", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                                setter=DtslScript_DSTREAM.setM4TraceCaptureMethod)] +
                            [DTSLv1.booleanOption('itm', 'ITM trace', defaultValue=False,
                                                   description="Enable trace from the ITM",
                                                   setter=DtslScript_DSTREAM.setITMEnabledM4) for c in range(0, NUM_CORES_CORTEX_M4)]
                        )
                ]),
                DtslScript_DSTREAM.getOptionSecureDebugTabPage(),
                DtslScript_DSTREAM.getOptionRAMTabPage()
            ])
        ]

    @staticmethod
    def getOptionSecureDebugTabPage():
        return DTSLv1.tabPage("sjc", "Secure Debug", childOptions=[
                  DTSLv1.booleanOption('sjcUnlock', 'Configure the SJC',
                      defaultValue = False,
                      setter=DtslScript_DSTREAM.setUnlockSJC,
                      childOptions = [
                          DTSLv1.integerOption('key', 'SJC key',
                              description='56-bit SJC unlock code',
                              defaultValue=0x123456789ABCDE,
                              display=IIntegerOption.DisplayFormat.HEX)
                          ]
                      )
              ])

    @staticmethod
    def getOptionRAMTabPage():
        return DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                  # Turn cache debug mode on/off
                  DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                       description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                       defaultValue=False, isDynamic=True)
              ])

    def setUnlockSJC(self, required):
        self.sjcUnlockReqd = required

    def wakeSecondary(self, enabled):
        self.enableSecondaryClock = enabled

    def __init__(self, root):
        DTSLv1.__init__(self, root)
        self.ctiConfigDone = False

        self.secondaryCore = 'Cortex-M4'
        self.enableSecondaryClock = False

        self.enableA5TraceClock = False
        self.enableA5TPIUPinmux = False
        self.enableM4TraceClock = False
        self.enableM4TPIUPinmux = False

        self.sjcUnlockReqd = False

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.mgdPlatformDevs = set()

        # tracks which devices are managed when a trace mode is enabled
        self.mgdTraceDevs = {}

        # only AHB/APB are managed by default - others will be added when enabling trace, SMP etc
        self.mgdPlatformDevs.add(self.AHB_A5)
        self.mgdPlatformDevs.add(self.APB_A5)
        self.mgdPlatformDevs.add(self.AHB_M4)

        self.exposeCores()

        self.setupETBTrace()

        self.setupDSTREAMTrace()

        # use internal trace range to limit trace to e.g. kernel
        self.traceRangeOptions = [
            TraceRangeOptions(), # Cortex-A5 trace options
            TraceRangeOptions(), # Cortex-M4 trace options
            ]

        self.setManagedDevices(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    # Sync-start all cores
    # If one of the cores isn't connected then we can't sync - tell the core to start itself
    def runCores(self):
        self.clearTriggers()
        usingXTrig = True
        for core in self.cortexA5cores + self.cortexM4cores:
            if not core.isConnected():
                usingXTrig = False

        if usingXTrig:
            self.getDebug().synchronize(2, [8, 12, 10]);
            return True

        return False

    # ACK all the stop triggers on the CTIs so that all cores can start
    # If we haven't yet configured the CTIs and cores for sync execution, do so now
    def clearTriggers(self):
        for core in self.cortexA5cores + self.cortexM4cores:
            core.clearTriggers()

        if not self.ctiConfigDone:
            if self.cortexA5cores[0].isConnected():
                self.getDebug().setConfig(8, "CTI_SYNCH_START", "1")
                self.getDebug().setConfig(10, "SYNCH_START_CHANNEL", "1")
                self.getDebug().setConfig(10, "SYNCH_START_ENABLE", "1")

            if self.cortexM4cores[0].isConnected():
                self.getDebug().setConfig(12, "CTI_SYNCH_START", "1")
                self.getDebug().setConfig(17, "SYNCH_START_CHANNEL", "1")
                self.getDebug().setConfig(17, "SYNCH_START_ENABLE", "1")
        self.ctiConfigDone = True

    def enableClocks(self):
        script = """from LDDI import *
import sys

A5_ID = 8
A5_OFFSET = 0xC0088000
A5_AP = 1

M4_ID = 12
M4_AP = 3

RVM_PROCBRK_INFO = 0
RVM_PROCBRK_ENA = 1
RVM_PROCBRK_DIS = 2
ResetVecEncoding = [0x54455352]  # 'RSET' in ASCII

POST_RST_STATE_RUN = 0
POST_RST_STATE_STOP = 1

targetConfigured = False

def HandleOpenConn(DevID,type,state):
    if type==1:
        configureTarget()
    return handleOpenConn(DevID,type,state)


def isCoreConnected(id):
    err, configTest = getConfig(id,'CONFIG_ITEMS')
    return err == 0

def dapPowerCheckBase(dapdev):
    # check DAP power status
    err, powerState = getConfig(dapdev, 'DAP_POWER_UP')
    if err == 0 and powerState != 1:
        # not powered - try to power up
        for t in range(10):
            # the DAP_POWER_UP state is reference counted, so try get it in sync with reality
            err = setConfig(dapdev, 'DAP_POWER_UP', 0)
            # power up the DAP
            err = setConfig(dapdev, 'DAP_POWER_UP', 1)
            # read status
            err, powerState = getConfig(dapdev, 'DAP_POWER_UP')
            if powerState == 1:
                break
            if t < 9:
                print 'Failed to power up DAP: Retrying'
            else:
                print 'Failed to power up DAP'
                err = 9 # EMUERR_TARGSTATE
    return err

def configureTarget(force=False):
    global targetConfigured
    if targetConfigured and not force:
        # already setup
        return 0

    err, id, version, message = Debug_OpenConn(1)
    if err == 0x101: # already open
        dapOpened = False
    elif err != 0:
        print >> sys.stderr, "Failed to open DAP: %04x" % err
        return err
    else:
        dapOpened = True
    err = dapPowerCheckBase(1)
    if err != 0:
        print >> sys.stderr, "Failed to powerup DAP: %04x" % err
        if dapOpened:
            Debug_CloseConn(1)
        return err
"""
        if self.enableSecondaryClock:
            script = script + """
    Debug_MemWrite(1,0x4300,0x4006B08C,4,0x0320,0,[0x5A,0x5A,0x01,0x00])"""
        if self.enableA5TraceClock or self.enableM4TraceClock:
            script = script + """
    value = [ 0, 0, 0, 0 ]
    err = Debug_MemRead(1, 0x4300, 0x4006B01C, 4, 0x320, 4, value)
    if err == 0:
        value[3] |= 0x04
        Debug_MemWrite(1,0x4300,0x4006B01C,4,0x0320,0,value)
"""
        if self.enableA5TPIUPinmux or self.enableM4TPIUPinmux:
            script = script + """
    for address in range(0x40048014, 0x40048058, 4):
        Debug_MemWrite(1,0x4300,address,4,0x0320,0,[0xC2, 0x31, 0x10, 0x00])
    Debug_MemWrite(1,0x4300,0x40048058,4,0x0320,0,[0xC2, 0x31, 0x30, 0x00])
"""

        script = script + """
    if dapOpened:
        Debug_CloseConn(1)
    targetConfigured = True
    return 0

def UnknownStateRecovery():
    configureTarget(force=True)

def HandleExeReset(flags):
    A5SavedBrkPointInfo = [ '0' ]
    M4SavedBrkPointInfo = [ '0' ]
    # Handle stop for A5
    if isCoreConnected(A5_ID):
        Err, postRstState = getConfig(A5_ID, 'POST_RESET_STATE')
        if postRstState == POST_RST_STATE_STOP:
            Err, A5SavedBrkPointInfo = Debug_BrkProcessor(A5_ID, RVM_PROCBRK_INFO, ResetVecEncoding)
            Err = Debug_BrkProcessor(A5_ID, RVM_PROCBRK_ENA, ResetVecEncoding)
        handleExeGo(A5_ID)

    # Handle stop for M4
    if isCoreConnected(M4_ID):
        Err, postRstState = getConfig(M4_ID, 'POST_RESET_STATE')
        if postRstState == POST_RST_STATE_STOP:
            Err, M4SavedBrkPointInfo = Debug_BrkProcessor(M4_ID, RVM_PROCBRK_INFO, ResetVecEncoding)
            Err = Debug_BrkProcessor(M4_ID, RVM_PROCBRK_ENA, ResetVecEncoding)

    err, id, version, message = Debug_OpenConn(1)
    # Write the reset
    Debug_MemWrite(1,0x4300,0x4006e000,4,0x0320,0,[ 0x0A, 0x15, 0, 0 ])
    if err == 0:
        Debug_CloseConn(1)

    configureTarget(force=True)

    if A5SavedBrkPointInfo[0] == '-':
        Debug_BrkProcessor(A5_ID, RVM_PROCBRK_DIS, ResetVecEncoding)
    if M4SavedBrkPointInfo[0] == '-':
        Debug_BrkProcessor(M4_ID, RVM_PROCBRK_DIS, ResetVecEncoding)
    return False
"""
        self.getDebug().setConfig(0, "PythonScript", script)


    def connectManagedDevices(self):
        self.enableClocks()
        self.secondaryCoreClockChecked = False

        # First, connect to the DAP
        self.dap.connect()

        # Unlock debug if required
        if self.sjcUnlockReqd:
            self.unlockSJC()

        self.determineSecondaryCore()

        # reconfigure trace based on which core is secondary
        if self.secondaryCore == 'Cortex-A5':
            secondaryCore = self.cortexA5cores[0]
            secondaryTraceDevs = self.a5TraceClkDevs
        else:
            secondaryCore = self.cortexM4cores[0]
            secondaryTraceDevs = self.m4TraceClkDevs

        self.reconfigureDSTREAMTrace()
        self.updateManagedDevices()

        mgdDevs = set(self.getManagedComponents())

        # check clock state now if any devices in secondary core domain are enabled
        if mgdDevs & secondaryTraceDevs:
            self.checkSecondaryCoreClock("%s trace components" % self.secondaryCore)
        else:
            # otherwise defer until core is connected to
            secondaryCore.checkClock = True

        # connect to other managed devices
        DTSLv1.connectManagedDevices(self)

    def unlockSJC(self):
        # Create JTAG-AP handler
        jtagAP = JTAGAP(self.dap, 2)

        jtagAP.setPort(0)
        jtagAP.tapReset(jtag.JTAGS_RTI)

        # Scan out challenge value
        SJC_CHALLENGE = [ 0x0C ]
        challenge = [ 0 ] * 8
        jtagAP.scanIO(jtag.JTAGS_IR, 5, SJC_CHALLENGE, None, jtag.JTAGS_PIR, 1)
        jtagAP.scanIO(jtag.JTAGS_DR, 63, None, challenge, jtag.JTAGS_RTI, 1)
        #print 'SJC challenge', challenge

        # Get response value from options
        response = []
        keySJC = self.getOptionValue("options.sjc.sjcUnlock.key")
        for i in range(7):
            x = keySJC & 0xFF
            response.append(x)
            keySJC = keySJC >> 8
        #print 'SJC response', response

        # Scan in response value
        SJC_RESPONSE = [ 0x0D ]
        jtagAP.scanIO(jtag.JTAGS_IR, 5, SJC_RESPONSE, None, jtag.JTAGS_PIR, 1)
        jtagAP.scanIO(jtag.JTAGS_DR, 56, response, None, jtag.JTAGS_RTI, 1)

        # read MDM AP STATUS Register - expect Debug Enabled and Secure DEbug bits to be set
        # check MDM-AP status
        mdmStat = self.dap.readAPRegister(4, 0)
        #print 'MDM status %08x' % mdmStat
        if (mdmStat & 0x08) != 0x08:
            challStr = '0x' + ''.join([ '%02x' % i for i in reversed(challenge) ])
            raise DTSLException("""Secure debug is not enabled.
Please reconfigure connection with correct response for challenge %s and reset target before reconnecting
MDM-AP status = 0x%08X""" % (challStr, mdmStat))


    def discoverDevices(self):
        '''find and create devices'''

        dapDev = self.findDevice("ARMCS-DP")
        self.dap = CSDAP(self, dapDev, "DAP")

        ahbDev = self.findDevice("CSMEMAP")
        self.AHB_A5 = AHBAP(self, ahbDev, "CSMEMAP")

        apbDev = self.findDevice("CSMEMAP", ahbDev+1)
        self.APB_A5 = APBAP(self, apbDev, "CSMEMAP")

        ahbM4Dev = self.findDevice("CSMEMAP", apbDev+1)
        self.AHB_M4 = CortexM_AHBAP(self, ahbM4Dev, "CSMEMAP")

        cortexA5coreDev = 0
        self.cortexA5cores = []

        cortexM4coreDev = 0
        self.cortexM4cores = []

        streamID = ATB_ID_BASE

        coreCTIDev = 1
        self.CTIs  = []
        self.cortexA5ctiMap = {} # map cores to associated CTIs
        self.cortexM4ctiMap = {} # map cores to associated CTIs

        etmDev = 1
        self.ETMs  = []

        # track which devices are in each core's trace clock domain
        self.m4TraceClkDevs = set()
        self.a5TraceClkDevs = set()

        for i in range(0, NUM_CORES_CORTEX_A5):
            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)

            # create core
            cortexA5coreDev = self.findDevice("Cortex-A5", cortexA5coreDev+1)
            dev = A5Core(self, cortexA5coreDev, "Cortex-A5_%d" % i, coreCTI, False)
            self.cortexA5cores.append(dev)
            self.cortexA5ctiMap[dev] = coreCTI

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev+1)
            etm = ETMv3_5TraceSource(self, etmDev, streamID, "ETM_A5_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            self.a5TraceClkDevs.add(etm)

        for i in range(0, NUM_CORES_CORTEX_M4):
            # create CTI for this core
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)
            self.m4TraceClkDevs.add(coreCTI)

            # create core
            cortexM4coreDev = self.findDevice("Cortex-M4", cortexM4coreDev+1)
            dev = CacheMaintCore(self, cortexM4coreDev, "Cortex-M4_%d" % i, coreCTI, True)
            self.cortexM4cores.append(dev)
            self.cortexM4ctiMap[dev] = coreCTI

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev+1)
            etm = M4_ETM(self, etmDev, streamID, "ETM_M4_%d_%d" % (i, streamID))
            streamID += 1
            # disabled by default - will enable with option
            etm.setEnabled(False)
            self.ETMs.append(etm)
            self.m4TraceClkDevs.add(etm)

        # ETB
        etbDevA5 = self.findDevice("CSETB")
        self.ETBA5 = ETBTraceCapture(self, etbDevA5, "ETB_A5")
        self.a5TraceClkDevs.add(self.ETBA5)

        etbDevM4 = self.findDevice("CSETB", etbDevA5 + 1)
        self.ETBM4 = ETBTraceCapture(self, etbDevM4, "ETB_M4")
        self.m4TraceClkDevs.add(self.ETBM4)

        # DSTREAM
        self.createDSTREAM()

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = self.createTPIU(tpiuDev, "TPIU")

        # Funnel 0
        # This is the master funnel that serves the TPIU
        funnelDevMaster = self.findDevice("CSTFunnel")
        self.funnelMaster = self.createFunnel(funnelDevMaster, "Funnel_0")

        # Funnel 1
        # A5 funnel
        funnelDevA5 = self.findDevice("CSTFunnel", funnelDevMaster+1)
        self.funnelA5 = self.createFunnel(funnelDevA5, "Funnel_1")
        self.a5TraceClkDevs.add(self.funnelA5)

        # Funnel 2
        # M4 funnel
        funnelDevM4 = self.findDevice("CSTFunnel", funnelDevA5+1)
        self.funnelM4 = self.createFunnel(funnelDevM4, "Funnel_2")
        self.m4TraceClkDevs.add(self.funnelM4)

        # ITM
        itmDevA5 = self.findDevice("CSITM")
        self.ITMA5 = self.createITM(itmDevA5, ITMA5_ATB_ID, "ITM_A5")
        self.a5TraceClkDevs.add(self.ITMA5)

        itmDevM4 = self.findDevice("CSITM", itmDevA5 + 1)
        self.ITMM4 = self.createITM(itmDevM4, ITMM4_ATB_ID, "ITM_M4")
        self.m4TraceClkDevs.add(self.ITMM4)

        # SWO
        swoDev = self.findDevice("CSSWO")
        self.swo = SWO(self, swoDev, "SWO")


    def exposeCores(self):
        for core in self.cortexA5cores:
            self.registerA5Filters(core)
            self.addDeviceInterface(core)
            a5_rams.registerInternalRAMs(core)
        for core in self.cortexM4cores:
            self.registerM4Filters(core)
            self.addDeviceInterface(core)

    def setupETBTrace(self):
        '''Setup ETB trace capture'''

        # Do A5 subsystem first
        # use continuous mode
        self.ETBA5.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETB and register ETB with configuration
        self.ETBA5.setTraceComponentOrder([ self.funnelMaster, self.funnelA5 ])
        self.addTraceCaptureInterface(self.ETBA5)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETB_A5", [ self.funnelA5, self.funnelMaster, self.tpiu, self.ETBA5 ])

        # register trace sources
        self.registerA5TraceSources(self.ETBA5)

        # Now do M4
        # use continuous mode
        self.ETBM4.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETB and register ETB with configuration
        self.ETBM4.setTraceComponentOrder([ self.funnelMaster, self.funnelM4 ])
        self.addTraceCaptureInterface(self.ETBM4)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETB_M4", [ self.swo, self.funnelM4, self.funnelMaster, self.tpiu, self.ETBM4 ])

        # register trace sources
        self.registerM4TraceSources(self.ETBM4)

    def setupDSTREAMTrace(self):
        '''Setup DSTREAM trace capture'''
        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)

        # configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.tpiu, self.funnelMaster, self.funnelM4, self.funnelA5 ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.funnelA5, self.funnelM4, self.funnelMaster, self.tpiu, self.swo, self.DSTREAM ])

    def setPortWidth(self, portWidth):
        self.tpiu.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

#    def getCTIForSink(self, sink):
#        '''Get the CTI and input/channel associated with a trace sink
#        return (None, None, None) if no associated CTI
#        '''
#        if sink == self.ETB:
#            # ETB trigger input is CTI out 1
#            return (self.outCTI, 1, CTM_CHANNEL_TRACE_TRIGGER)
#        if sink == self.DSTREAM:
#            # TPIU trigger input is CTI out 3
#            return (self.outCTI, 3, CTM_CHANNEL_TRACE_TRIGGER)
#        # no associated CTI
#        return (None, None, None)

#    def getCTIForSource(self, source):
#        '''Get the CTI and input/channel associated with a source
#        return (None, None, None) if no associated CTI
#        '''
#        if source in self.ETMs:
#            coreNum = self.ETMs.index(source)
#            # ETM trigger is on input 6
#            if coreNum < len(self.CTIs):
#                return (self.CTIs[coreNum], 6, CTM_CHANNEL_TRACE_TRIGGER)
#
#        # no associated CTI
#        return (None, None, None)

    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
#        self.enableCTIsForSource(source, enabled)

    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, tpiuDev, name)
        # disable the TPIU by default to allow ETB to work at full rate
        tpiu.setEnabled(False)
        return tpiu

    def setETBTraceEnabled(self, source, enabled):
        '''Enable/disable ETB trace capture'''
#        source.setEnabled(enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.tpiu.setEnabled(enabled)

    def registerA5TraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_A5):
            self.registerCoreTraceSource(traceCapture, self.cortexA5cores[c], self.ETMs[c])
        self.registerTraceSource(traceCapture, self.ITMA5)

    def registerM4TraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for c in range(0, NUM_CORES_CORTEX_M4):
            self.registerCoreTraceSource(traceCapture, self.cortexM4cores[c], self.ETMs[NUM_CORES_CORTEX_A5+c])
        self.registerTraceSource(traceCapture, self.ITMM4)

    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with trace capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [ source ])

#        # CTI (if present) is also managed by the configuration
#        cti, input, channel = self.getCTIForSource(source)
#        if cti:
#            self.addManagedTraceDevices(traceCapture.getName(), [ cti ])

    def getFunnelForSource(self, source):
        if (source == self.ETMs[0]):
            return self.funnelA5
        return self.funnelM4

    def getTPIUportForSource(self, source):
        if (source == self.ETMs[0]):
            return 1
        return 0



    def EnableInvasive(self, enabled):
        for core in self.cortexA5cores + self.cortexM4cores:
            core.enableInvasive(enabled)

    def EnableXTrig(self, enabled):
        for core in self.cortexA5cores + self.cortexM4cores:
            core.enableXTrig(enabled)

    def setTriggerGeneratesDBGRQ(self, xtm, state):
        xtm.setTriggerGeneratesDBGRQ(state)

    def setTimestampingEnabled(self, xtm, state):
        xtm.setTimestampingEnabled(state)

    def setContextIDEnabled(self, xtm, state, size):
        if state == False:
            xtm.setContextIDs(False, IARMCoreTraceSource.ContextIDSize.NONE)
        else:
            contextIDSizeMap = {
                 "8":IARMCoreTraceSource.ContextIDSize.BITS_7_0,
                "16":IARMCoreTraceSource.ContextIDSize.BITS_15_0,
                "32":IARMCoreTraceSource.ContextIDSize.BITS_31_0 }
            xtm.setContextIDs(True, contextIDSizeMap[size])

    def reconfigureDSTREAMTrace(self):
        '''Callback to update the configuration state after options are changed'''
        # re-register trace components used for DSTREAM depending on whether secondary core trace is enabled
        if self.secondaryCore == 'Cortex-M4':
            secondaryTraceEnabled = self.getOptionValue("options.cortexM4.cortexM4coreTrace")
            etmM4 = self.ETMs[-1]
            secondaryTraceDevs = set([self.funnelM4, self.ITMM4, etmM4])
        else:
            secondaryTraceEnabled = self.getOptionValue("options.cortexA5.cortexA5coreTrace")
            etmA5 = self.ETMs[0]
            secondaryTraceDevs = set([self.funnelA5, self.ITMA5, etmA5])

        dstreamTraceComponentOrder = [ self.tpiu, self.funnelMaster, self.funnelM4, self.funnelA5 ]
        if secondaryTraceEnabled:
            self.mgdTraceDevs["DSTREAM"] |= secondaryTraceDevs
        else:
            # secondary core not enabled - remove devices
            self.mgdTraceDevs["DSTREAM"] -= secondaryTraceDevs
            dstreamTraceComponentOrder = [ d for d in dstreamTraceComponentOrder if not d in secondaryTraceDevs ]
        self.DSTREAM.setTraceComponentOrder(dstreamTraceComponentOrder)

        A5traceMode = self.getOptionValue("options.cortexA5.cortexA5coreTrace.A5traceCapture")
        if A5traceMode == 'DSTREAM':
            self.registerA5TraceSources(self.DSTREAM)
        M4traceMode = self.getOptionValue("options.cortexM4.cortexM4coreTrace.M4traceCapture")
        if M4traceMode == 'DSTREAM':
            self.registerM4TraceSources(self.DSTREAM)


    def updateManagedDevices(self):
        A5traceMode = self.getOptionValue("options.cortexA5.cortexA5coreTrace.A5traceCapture")
        M4traceMode = self.getOptionValue("options.cortexM4.cortexM4coreTrace.M4traceCapture")
        managedDevs = self.getManagedDevices(A5traceMode) | self.getManagedDevices(M4traceMode)
        self.setManagedDevices(managedDevs)

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+

    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''

        self.updateManagedDevices()

        for core in range(0, len(self.cortexA5cores)):
            a5_rams.applyCacheDebug(configuration = self,
                                    optionName = "options.rams.cacheDebug",
                                    device = self.cortexA5cores[core])

        coreTraceEnabled = self.getOptionValue("options.cortexA5.cortexA5coreTrace")
        A5traceMode = self.getOptionValue("options.cortexA5.cortexA5coreTrace.A5traceCapture")
        for i in range(0, NUM_CORES_CORTEX_A5):
            etm = self.ETMs[i]
            self.setTraceSourceEnabled(etm, coreTraceEnabled)
            self.enableMasterFunnelPort(etm, (A5traceMode == 'DSTREAM'))

            self.setTriggerGeneratesDBGRQ(self.ETMs[i], self.getOptionValue("options.cortexA5.cortexA5coreTrace.triggerhalt"))
            self.setContextIDEnabled(self.ETMs[i],
                                     self.getOptionValue("options.cortexA5.cortexA5coreTrace.contextIDs"),
                                     self.getOptionValue("options.cortexA5.cortexA5coreTrace.contextIDs.contextIDsSize"))

        coreTraceEnabled = self.getOptionValue("options.cortexM4.cortexM4coreTrace")
        M4traceMode = self.getOptionValue("options.cortexM4.cortexM4coreTrace.M4traceCapture")
        for i in range(0, NUM_CORES_CORTEX_M4):
            etm = self.ETMs[NUM_CORES_CORTEX_A5+i]
            self.setTraceSourceEnabled(etm, coreTraceEnabled)
            self.enableMasterFunnelPort(etm, (M4traceMode == 'DSTREAM'))

        etmStartIndex = 0
        etmEndIndex = 0

        etmEndIndex += NUM_CORES_CORTEX_A5
        self.setInternalTraceRange(self.traceRangeOptions[CORTEX_A5_TRACE_OPTIONS], TraceRangeOptions("options.cortexA5.cortexA5coreTrace", self), self.ETMs[etmStartIndex:etmEndIndex])
        etmStartIndex += NUM_CORES_CORTEX_A5

        etmEndIndex += NUM_CORES_CORTEX_M4
        etmStartIndex += NUM_CORES_CORTEX_M4

        portWidthOpt = self.getOptions().getOption("options.system.offChip.tpiuPortWidth")
        if portWidthOpt:
            portWidth = self.getOptionValue("options.system.offChip.tpiuPortWidth")
            self.setPortWidth(int(portWidth))

        traceBufferOpt = self.getOptions().getOption("options.system.offChip.traceBufferSize")
        if traceBufferOpt:
            traceBufferSize = self.getOptionValue("options.system.offChip.traceBufferSize")
            self.setTraceBufferSize(traceBufferSize)

    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        return self.mgdPlatformDevs | self.mgdTraceDevs.get(traceKey, set())

    def setA5TraceCaptureMethod(self, method):
        if method == "none":
            self.enableA5TraceClock = False
            self.enableA5TPIUPinmux = False
#            self.setETBTraceEnabled(self.ETM_A5, False)
#            self.setETBTraceEnabled(self.ETM_M4, False)
            self.setDSTREAMTraceEnabled(self.enableM4TPIUPinmux)
        elif method == "ETB_A5":
            self.enableA5TraceClock = True
            self.enableA5TPIUPinmux = False
#            self.setETBTraceEnabled(self.ETM_A5, True)
#            self.setETBTraceEnabled(self.ETM_M4, False)
            self.setDSTREAMTraceEnabled(self.enableM4TPIUPinmux)
        elif method == "DSTREAM":
            self.enableA5TraceClock = True
            self.enableA5TPIUPinmux = True
#            self.setETBTraceEnabled(self.ETM_A5, False)
#            self.setETBTraceEnabled(self.ETM_M4, False)
            self.setDSTREAMTraceEnabled(True)

    def setM4TraceCaptureMethod(self, method):
        if method == "none":
            self.enableM4TraceClock = False
            self.enableM4TPIUPinmux = False
#            self.setETBTraceEnabled(self.ETM_A5, False)
#            self.setETBTraceEnabled(self.ETM_M4, False)
            self.setDSTREAMTraceEnabled(self.enableA5TPIUPinmux)
        elif method == "ETB_M4":
            self.enableM4TraceClock = True
            self.enableM4TPIUPinmux = False
#            self.setETBTraceEnabled(self.ETM_A5, False)
#            self.setETBTraceEnabled(self.ETM_M4, True)
            self.setDSTREAMTraceEnabled(self.enableA5TPIUPinmux)
        elif method == "DSTREAM":
            self.enableM4TraceClock = True
            self.enableM4TPIUPinmux = True
#            self.setETBTraceEnabled(self.ETM_A5, False)
#            self.setETBTraceEnabled(self.ETM_M4, False)
            self.setDSTREAMTraceEnabled(True)

    def getETMs(self):
        '''Get the ETMs'''
        return self.ETMs

    def getA5ETM(self):
        return self.ETMs[0]

    def setITMEnabledA5(self, enabled):
        '''Enable/disable the ITM trace source'''
        self.ITMA5.setEnabled(enabled)
        if (enabled == True):
            self.funnelA5.setPortEnabled(1)
        else:
            self.funnelA5.setPortDisabled(1)

    def setITMEnabledM4(self, enabled):
        '''Enable/disable the ITM trace source'''
        self.ITMM4.setEnabled(enabled)
        if (enabled == True):
            self.funnelM4.setPortEnabled(1)
        else:
            self.funnelM4.setPortDisabled(1)

    def verify(self):
        # The DAP may be disconnected, connect to it now
        if not self.dap.isConnected():
            self.dap.connect()

        expectedROMTable = [ 0, 0, 0, 0, 0x80, 0xE9, 0x08, 0x01 ]
        mask = [ 0xF, 0x0, 0x0, 0x0, 0xFF, 0xFF, 0xF, 0x0 ]
        if not self.confirmValue(0, 0x40087FD0, expectedROMTable, mask):
            return False

        if self.secondaryCore == 'Cortex-M4':
            expectedA5 = [ 0x04, 0, 0, 0, 0x05, 0xBC, 0x1B, 0x00 ]
            if not self.confirmValue(1, 0xC0088FD0, expectedA5, mask):
                return False
        else:
            expectedM4 = [ 0x04, 0, 0, 0, 0x0C, 0xB0, 0x0B, 0x00 ]
            if not self.confirmValue(3, 0xE000EFD0, expectedM4, mask):
                return False

        # We can disconnect from the DAP now
        self.dap.disconnect()

        return True

    def confirmValue(self, ap, addr, expected, mask):
        actual = self.readDAPWords(ap, addr, len(expected))
        for e, m, a in zip(expected, mask, actual):
            if ((a & m) != (e & m)):
                print "Expected %08x but read %08x (with mask %08x)" % (e, a, m)
                return False
        return True


    def determineSecondaryCore(self):
        # The DAP may be disconnected, connect to it now
        if not self.dap.isConnected():
            self.dap.connect()

        # Read CP0TYPE from MSCM to get primary core
        ptype = self.readDAPWords(0, 0x40001020, 1)[0]
        # type is encoded in bits [31:8]
        ptype = (ptype >> 8) & 0x00FFFFFF
        if ptype == 0x434135: # 'CA5'
            self.secondaryCore = 'Cortex-M4'
        else:
            self.secondaryCore = 'Cortex-A5'

        # We can disconnect from the DAP now
        self.dap.disconnect()


    def readDAPWords(self, ap, addr, count):
        buffer = zeros(4 * count, 'b')
        self.dap.readMem(ap, addr, 4 * count, buffer)
        return [ unpack('<I', buffer[i:i+4])[0] for i in range(0, len(buffer), 4) ]


    def checkSecondaryCoreClock(self, connectingTo):
        # The DAP may be disconnected, connect to it now
        if not self.dap.isConnected():
            self.dap.connect()

        if not self.secondaryCoreClockChecked:
            if not self.confirmValue(0, 0x4006B08C, [0x00010000], [0x00010000]):
                raise DTSLException, "Secondary core clock must be enabled before connecting to %s" % connectingTo
            self.secondaryCoreClockChecked = True

        # We can disconnect from the DAP now
        self.dap.disconnect()


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

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def registerA5Filters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB_A5, "A5 AHB bus accessed via AP_0"),
             AxBMemAPAccessor("APB", self.APB_A5, "A5 APB bus accessed via AP_1")])

    def registerM4Filters(self, core):
        '''Register MemAP filters to allow access to the AHB/APB for the device'''
        core.registerAddressFilters(
            [AxBMemAPAccessor("AHB", self.AHB_M4, "M4 AHB bus accessed via AP_0")])

    def enableCTIInput(self, cti, input, channel, enabled):
        skip = 1
#        '''Enable/disable cross triggering between an input and a channel'''
#        if enabled:
#            cti.enableInputEvent(input, channel)
#        else:
#            cti.disableInputEvent(input, channel)

    def enableCTIsForSink(self, sink, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, output, channel = self.getCTIForSink(sink)
#        if cti:
#            self.enableCTIOutput(cti, output, channel, enabled)

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
#        if cti:
#            self.enableCTIInput(cti, input, channel, enabled)

    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, funnelDev, name)
        funnel.setAllPortsDisabled() # Will enable for each source later
        return funnel

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        # Both cores are on port 0 of their respective funnels
        funnel = self.getFunnelForSource(source)
        if enabled:
            funnel.setPortEnabled(0)
        else:
            funnel.setPortDisabled(0)

    def enableMasterFunnelPort(self, source, enabled):
        '''If we've enabled TPIU trace then we also have to open some funnel ports'''
        port = self.getTPIUportForSource(source)
        if enabled:
            self.funnelMaster.setPortEnabled(port)
        else:
            self.funnelMaster.setPortDisabled(port)


    def getFunnelPortForCore(self, core):
        ''' Both cores are on port 0 of their respective funnels'''
        return 0

    def createITM(self, itmDev, streamID, name):
        itm = ITMTraceSource(self, itmDev, streamID, name)
        # disabled by default - will enable with option
        itm.setEnabled(False)
        return itm

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

class DtslScript_DSTREAM_ST_Family(DtslScript_DSTREAM):

    def setupDSTREAMTrace(self):
        '''Setup DSTREAM trace capture'''
        # configure the TPIU for continuous mode
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.tpiu, self.funnelMaster, self.funnelM4, self.funnelA5 ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM", [ self.funnelA5, self.funnelM4, self.funnelMaster, self.tpiu, self.swo, self.DSTREAM ])

class DtslScript_DSTREAM_ST(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("system", "System", childOptions=[
                    DTSLv1.booleanOption('wake', 'Start secondary core clock on connection', defaultValue=False,
                                         description="Set to ensure the secondary core clock is enabled when connecting.",
                                         setter=DtslScript_DSTREAM.wakeSecondary),
                    DTSLv1.booleanOption('xTrig', 'Cortex-A5 - Cortex-M4 synchronized start and stop', defaultValue=False, isDynamic=True,
                        setter=DtslScript_DSTREAM.EnableXTrig, childOptions =
                            [DTSLv1.booleanOption('invasive', 'Invasive configuration', defaultValue=False, isDynamic=True,
                                setter=DtslScript_DSTREAM.EnableInvasive,
                                description="If the Cortex-M4 is executing WFI, Arm DS will be unable to configure cross-triggering. Invasive configuration halts the Cortex-M4 while setting up cross-triggering"
                            )]
                    ),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            values = [("1", "1 bit"), ("2", "2 bit"), ("4", "4 bit")], isDynamic=False),
                        DTSLv1.enumOption('traceBufferSize', 'Trace Buffer Size', defaultValue="4GB",
                            values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"), ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"), ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                    ]),
                ]),
                DTSLv1.tabPage("cortexA5", "Cortex-A5", childOptions=[
                    DTSLv1.booleanOption('cortexA5coreTrace', 'Cortex-A5 trace', defaultValue=False,
                                         description="Enable trace from the Cortex-A5 module",
                        childOptions =
                            [DTSLv1.enumOption('A5traceCapture', 'Trace capture method', defaultValue="none",
                                values = [("none", "None"), ("ETB_A5", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM-ST Streaming Trace")],
                                setter=DtslScript_DSTREAM.setA5TraceCaptureMethod)] +
                            ETMv3_5TraceSource.defaultOptions(DtslScript_DSTREAM.getA5ETM) +
                            [ #ETMv3_5TraceSource.timestampingOption(DtslScript_DSTREAM.getA5ETM),
                              DTSLv1.booleanOption('contextIDs', "ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                              ETMv3_5TraceSource.dataOption(DtslScript_DSTREAM.getA5ETM),
                              DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable ETM triggers to halt execution", defaultValue=False) ] +
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
                            ] +
                            [DTSLv1.booleanOption('itm', 'ITM trace', defaultValue=False,
                                                   description="Enable trace from the ITM",
                                                   setter=DtslScript_DSTREAM.setITMEnabledA5)]
                        ),
                ]),
                DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('cortexM4coreTrace', 'Cortex-M4 trace', defaultValue=False,
                                         description="Enable trace from the Cortex-M4 module",
                        childOptions =
                            [DTSLv1.enumOption('M4traceCapture', 'Trace capture method', defaultValue="none",
                                values = [("none", "None"), ("ETB_M4", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM-ST Streaming Trace")],
                                setter=DtslScript_DSTREAM.setM4TraceCaptureMethod)] +
                            [DTSLv1.booleanOption('itm', 'ITM trace', defaultValue=False,
                                                   description="Enable trace from the ITM",
                                                   setter=DtslScript_DSTREAM.setITMEnabledM4) for c in range(0, NUM_CORES_CORTEX_M4)]
                        ),
                ]),
                DtslScript_DSTREAM.getOptionSecureDebugTabPage(),
                DtslScript_DSTREAM.getOptionRAMTabPage()
            ])
        ]

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
                DTSLv1.tabPage("system", "System", childOptions=[
                    DTSLv1.booleanOption('wake', 'Start secondary core clock on connection', defaultValue=False,
                                         description="Set to ensure the secondary core clock is enabled when connecting.",
                                         setter=DtslScript_DSTREAM.wakeSecondary),
                    DTSLv1.booleanOption('xTrig', 'Cortex-A5 - Cortex-M4 synchronized start and stop', defaultValue=False, isDynamic=True,
                        setter=DtslScript_DSTREAM.EnableXTrig, childOptions =
                            [DTSLv1.booleanOption('invasive', 'Invasive configuration', defaultValue=False, isDynamic=True,
                                setter=DtslScript_DSTREAM.EnableInvasive,
                                description="If the Cortex-M4 is executing WFI, Arm DS will be unable to configure cross-triggering. Invasive configuration halts the Cortex-M4 while setting up cross-triggering"
                            )]
                    ),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False)                    ]),
                ]),
                DTSLv1.tabPage("cortexA5", "Cortex-A5", childOptions=[
                    DTSLv1.booleanOption('cortexA5coreTrace', 'Cortex-A5 trace', defaultValue=False,
                                         description="Enable trace from the Cortex-A5 module",
                        childOptions =
                            [DTSLv1.enumOption('A5traceCapture', 'Trace capture method', defaultValue="none",
                                values = [("none", "None"), ("ETB_A5", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer")],
                                setter=DtslScript_DSTREAM.setA5TraceCaptureMethod)] +
                            ETMv3_5TraceSource.defaultOptions(DtslScript_DSTREAM.getA5ETM) +
                            [ #ETMv3_5TraceSource.timestampingOption(DtslScript_DSTREAM.getA5ETM),
                              DTSLv1.booleanOption('contextIDs', "ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                              ETMv3_5TraceSource.dataOption(DtslScript_DSTREAM.getA5ETM),
                              DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable ETM triggers to halt execution", defaultValue=False) ] +
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
                            ] +
                            [DTSLv1.booleanOption('itm', 'ITM trace', defaultValue=False,
                                                   description="Enable trace from the ITM",
                                                   setter=DtslScript_DSTREAM.setITMEnabledA5)]
                        ),
                ]),
                DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('cortexM4coreTrace', 'Cortex-M4 trace', defaultValue=False,
                                         description="Enable trace from the Cortex-M4 module",
                        childOptions =
                            [DTSLv1.enumOption('M4traceCapture', 'Trace capture method', defaultValue="none",
                                values = [("none", "None"), ("ETB_M4", "On Chip Trace Buffer (ETB)"), ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer")],
                                setter=DtslScript_DSTREAM.setM4TraceCaptureMethod)] +
                            [DTSLv1.booleanOption('itm', 'ITM trace', defaultValue=False,
                                                   description="Enable trace from the ITM",
                                                   setter=DtslScript_DSTREAM.setITMEnabledM4) for c in range(0, NUM_CORES_CORTEX_M4)]
                        ),
                ]),
                DtslScript_DSTREAM.getOptionSecureDebugTabPage(),
                DtslScript_DSTREAM.getOptionRAMTabPage()
            ])
        ]

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")

class DtslScript_NoDSTREAM(DtslScript_DSTREAM):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DTSLv1.tabPage("system", "System", childOptions=[
                    DTSLv1.booleanOption('wake', 'Start secondary core clock on connection', defaultValue=False,
                                         description="Set to ensure the secondary core clock is enabled when connecting.",
                                         setter=DtslScript_DSTREAM.wakeSecondary),
                    DTSLv1.booleanOption('xTrig', 'Cortex-A5 - Cortex-M4 synchronized start and stop', defaultValue=False, isDynamic=True,
                        setter=DtslScript_DSTREAM.EnableXTrig, childOptions =
                            [DTSLv1.booleanOption('invasive', 'Invasive configuration', defaultValue=False, isDynamic=True,
                                setter=DtslScript_DSTREAM.EnableInvasive,
                                description="If the Cortex-M4 is executing WFI, Arm DS will be unable to configure cross-triggering. Invasive configuration halts the Cortex-M4 while setting up cross-triggering"
                            )]
                    ),
                ]),
                DTSLv1.tabPage("cortexA5", "Cortex-A5", childOptions=[
                    DTSLv1.booleanOption('cortexA5coreTrace', 'Cortex-A5 trace', defaultValue=False,
                                         description="Enable trace from the Cortex-A5 module",
                        childOptions =
                            [DTSLv1.enumOption('A5traceCapture', 'Trace capture method', defaultValue="none",
                                values = [("none", "None"), ("ETB_A5", "On Chip Trace Buffer (ETB)")],
                                setter=DtslScript_DSTREAM.setA5TraceCaptureMethod)] +
                            ETMv3_5TraceSource.defaultOptions(DtslScript_DSTREAM.getA5ETM) +
                            [ #ETMv3_5TraceSource.timestampingOption(DtslScript_DSTREAM.getA5ETM),
                              DTSLv1.booleanOption('contextIDs', "ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True,
                                childOptions = [
                                    DTSLv1.enumOption('contextIDsSize', 'Context ID Size', defaultValue="32",
                                        values = [("8", "8 bit"), ("16", "16 bit"), ("32", "32 bit")])
                                    ]),
                              ETMv3_5TraceSource.dataOption(DtslScript_DSTREAM.getA5ETM),
                              DTSLv1.booleanOption('triggerhalt', "ETM Triggers halt execution", description="Enable ETM triggers to halt execution", defaultValue=False) ] +
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
                            ] +
                            [DTSLv1.booleanOption('itm', 'ITM trace', defaultValue=False,
                                                   description="Enable trace from the ITM",
                                                   setter=DtslScript_DSTREAM.setITMEnabledA5)]
                        ),
                ]),
                DTSLv1.tabPage("cortexM4", "Cortex-M4", childOptions=[
                    DTSLv1.booleanOption('cortexM4coreTrace', 'Cortex-M4 trace', defaultValue=False,
                                         description="Enable trace from the Cortex-M4 module",
                        childOptions =
                            [DTSLv1.enumOption('M4traceCapture', 'Trace capture method', defaultValue="none",
                                values = [("none", "None"), ("ETB_M4", "On Chip Trace Buffer (ETB)")],
                                setter=DtslScript_DSTREAM.setM4TraceCaptureMethod)] +
                            [DTSLv1.booleanOption('itm', 'ITM trace', defaultValue=False,
                                                   description="Enable trace from the ITM",
                                                   setter=DtslScript_DSTREAM.setITMEnabledM4) for c in range(0, NUM_CORES_CORTEX_M4)]
                        ),
                ]),
                DtslScript_DSTREAM.getOptionSecureDebugTabPage(),
                DtslScript_DSTREAM.getOptionRAMTabPage()
            ])
        ]


# Simple wrapper class to the base DtslScript_CMSIS class.
# For each platform, Arm DS creates a folder named after the DTSL Class to store
# the DTSL options file.
# Forcing each target connection to use a different class means that
# different DTSL options files are created for each connection type.
# If you want to have a shared options file, then use the same class name for
# each connection type

class DtslScript_ULINKpro(DtslScript_NoDSTREAM):
    @staticmethod
    def dummy():
        #dummy function to prevent error
        return

class DtslScript_ULINKproD(DtslScript_NoDSTREAM):
    @staticmethod
    def dummy():
        #dummy function to prevent error
        return

class DtslScript_CMSIS(DtslScript_NoDSTREAM):
    @staticmethod
    def dummy():
        #dummy function to prevent error
        return

class DtslScript_RVI(DtslScript_NoDSTREAM):
    @staticmethod
    def dummy():
        #dummy function to prevent error
        return

