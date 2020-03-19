# Copyright (C) 2018-2019 Arm Limited (or its affiliates). All rights reserved.

from com.arm.debug.dtsl import DTSLException
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import ConnectableDevice
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTLiveStoredStreamingTraceCapture
from com.arm.debug.dtsl.components import V7M_CSTPIU
from com.arm.debug.dtsl.components import V7M_ITMTraceSource
from m3etm import M3_ETM as V7M_ETMTraceSource
from com.arm.rddi import RDDI_ACC_SIZE
import sys
import os
dtslSearchPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '..', '..', '..', 'Scripts', 'DTSL')
sys.path.append(dtslSearchPath)

from struct import pack, unpack
from jarray import zeros

freq =  72000000
DSTREAM_PORTWIDTH = 4
DSTREAM_CAPTURE_NAMES = ["DSTREAM", "DSTREAM_PT_Store_and_Forward", "DSTREAM_PT_StreamingTrace"]

class ResetHookedDevice(ConnectableDevice):
    def __init__(self, root, devNo, name):
        ConnectableDevice.__init__(self, root, devNo, name)
        self.parent = root

    def systemReset(self, resetType):
        ConnectableDevice.systemReset(self, resetType)
        # Notify root configuration
        self.parent.postReset()

class uCProbeConfiguration(DTSLv1):
    '''A configuration class which has support for the uC/Probe connection'''

    @staticmethod
    def getucProbeOptionsPage():
        return DTSLv1.tabPage(
            name='ucProbe',
            displayName='uC/Probe',
            childOptions=[
                DTSLv1.booleanOption(
                    name='ucProbeEnabled',
                    displayName = 'Enable uC/Probe UDP Server',
                    defaultValue=False,
                    isDynamic=True,
                    childOptions = [
                        DTSLv1.integerOption(
                            name='PORT',
                            displayName = 'Server port number',
                            description = 'The UDP port number to listen on. Valid range: 1024..65535, default is 9930.',
                            minimum=1024,
                            maximum=65535,
                            defaultValue=9930,
                            display=IIntegerOption.DisplayFormat.DEC,
                            isDynamic=False
                        )
                    ]
                )
            ]
        )

    def __init__(self, root):
        '''The class constructor'''
        # base class construction
        DTSLv1.__init__(self, root)
        self.ucProbeServer = None
        # We assume our child classes will assign this for us
        # to reference a device object through which we are to
        # access memory
        self.ucMemoryAccessor = None

    def preDisconnect(self):
        '''Is called before we start target disconnect sequence'''
        # Must halt any ucProbeServer
        if self.ucProbeServer != None:
            self.ucProbeServer.stop()

    def setucProbeOptions(self, obase):
        '''Sets up the uC/Probe server
        Parameters:
            obase
                 the string 'path' to the ucProbe options
        '''
        isEnabled = self.getOptionValue(obase+".ucProbeEnabled")
        if isEnabled:
            if self.ucProbeServer == None and self.ucMemoryAccessor != None:
                from ucprobeserver import UCProbeServer
                port = self.getOptionValue(obase+".ucProbeEnabled.PORT")
                self.ucProbeServer = UCProbeServer(self.ucMemoryAccessor, port)
                self.ucProbeServer.start()
        else:
            if self.ucProbeServer != None:
                self.ucProbeServer.stop()
                self.ucProbeServer = None


class DSTREAMDebugAndTrace(uCProbeConfiguration):
    '''A top level configuration class which supports debug and trace'''

    @staticmethod
    def getOptionList():
        '''The method which specifies the configuration options which
           the user can edit via the launcher panel |Edit...| button
        '''
        return [
            DTSLv1.tabSet(
                name='options',
                displayName='Options',
                childOptions=[
                    DSTREAMDebugAndTrace.getTraceBufferOptionsPage(),
                    DSTREAMDebugAndTrace.getETMOptionsPage(),
                    DSTREAMDebugAndTrace.getITMOptionsPage(),
                    uCProbeConfiguration.getucProbeOptionsPage()
                ]
            )
        ]

    @staticmethod
    def getTraceBufferOptionsPage():
        # If you change the position or name of the traceCapture
        # device option you MUST modify the project_types.xml to
        # tell the debugger about the new location/name
        return DTSLv1.tabPage(
            name='traceBuffer',
            displayName='Trace Buffer',
            childOptions=[
                DTSLv1.enumOption(
                    name='traceCaptureDevice',
                    displayName='Trace capture method',
                    defaultValue='DSTREAM',
                    values=[
                        ('none', 'No trace capture device'),
                        ('DSTREAM', 'DSTREAM 4GB Trace Buffer')
                    ]
                ),
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

    @staticmethod
    def getETMOptionsPage():
        return DTSLv1.tabPage(
            name='ETM',
            displayName='Instruction Trace',
            childOptions=[
                DTSLv1.booleanOption(
                    name='cortexM3coreTraceEnabled',
                    displayName='Enable Cortex-M3 instruction trace',
                    defaultValue=False,
                    isDynamic=True
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
                    defaultValue=2
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
                DTSLv1.booleanOption(
                    name='DWTENA',
                    displayName = 'Enable DWT stimulus',
                    defaultValue=True,
                    isDynamic=True
                ),
                DTSLv1.integerOption(
                    name='STIMENA',
                    displayName = 'Stimulus port enables',
                    minimum=0x00000000,
                    maximum=0xFFFFFFFF,
                    defaultValue=0xFFFFFFFF,
                    display=IIntegerOption.DisplayFormat.HEX,
                    isDynamic=True
                ),
                DTSLv1.infoElement(
                    name='PRIVMASK',
                    displayName = 'PRIVMASK - Allow USER mode access',
                    childOptions=[
                        DTSLv1.booleanOption(
                            name='[7:0]',
                            displayName='Ports [7:0]',
                            defaultValue=True,
                            isDynamic=True
                        ),
                        DTSLv1.booleanOption(
                            name='[15:8]',
                            displayName='Ports [15:8]',
                            defaultValue=True,
                            isDynamic=True
                        ),
                        DTSLv1.booleanOption(
                            name='[23:16]',
                            displayName='Ports [23:16]',
                            defaultValue=True,
                            isDynamic=True
                        ),
                        DTSLv1.booleanOption(
                            name='[31:24]',
                            displayName='Ports [31:24]',
                            defaultValue=True,
                            isDynamic=True
                        )
                    ]
                )
            ]
        )

    @staticmethod
    def getITMOptionsPage():
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
                                ('Target', 'The target will setup the ITM', DSTREAMDebugAndTrace.getTargetITMOptions()),
                                ('Debugger', 'Arm Debugger will setup the ITM', DSTREAMDebugAndTrace.getDebuggerITMOptions())
                            ]
                        )
                    ]
                )
            ]
        )

    def __init__(self, root):
        '''The class constructor'''
        # base class construction
        uCProbeConfiguration.__init__(self, root)
        # create the devices in the platform
        self.cores = []
        self.traceSources = []
        self.reservedATBIDs = {}
        self.createDevices()
        for core in self.cores:
            self.addDeviceInterface(core)

    def createDevices(self):
        # create MEMAP
        devID = self.findDevice("CSMEMAP")
        self.AHB = CortexM_AHBAP(self, devID, "CSMEMAP")
        self.ucMemoryAccessor = self.AHB
        # create core
        devID = self.findDevice("Cortex-M3")
        self.cortexM3 = ResetHookedDevice(self, devID, "Cortex-M3")
        self.cortexM3.registerAddressFilters(
                [AHBCortexMMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0")])
        self.cores.append(self.cortexM3)

        # create the ETM disabled by default - will enable with option
        devID = self.findDevice("CSETM")
        self.ETM = V7M_ETMTraceSource(self, devID, 1, "ETM")
        self.ETM.setEnabled(False)
        self.traceSources.append(self.ETM)
        # ITM disabled by default - will enable with option
        devID = self.findDevice("CSITM")
        self.ITM = V7M_ITMTraceSource(self, devID, 2, "ITM")
        #self.ITM = M3_ITM(self, devID, 2, "ITM")
        self.ITM.setEnabled(False)
        self.traceSources.append(self.ITM)
        # TPIU
        devID = self.findDevice("CSTPIU")
        self.TPIU = V7M_CSTPIU(self, devID, "TPIU", self.AHB)

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def setPortWidth(self, portWidth):
        self.TPIU.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''
        # configure the DSTREAM for continuous trace
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.setPortWidth(DSTREAM_PORTWIDTH)
        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.TPIU ])
        # tell DSTREAM about its trace sources
        self.DSTREAM.addTraceSource(self.ETM, self.cortexM3.getID())
        self.DSTREAM.addTraceSource(self.ITM)
        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        # automatically handle connection/disconnection to trace components
        self.setManagedDevices( [self.AHB, self.ETM, self.ITM, self.TPIU, self.DSTREAM] )

    def setETMEnabled(self, enabled):
        '''Configuration option setter method to enable/disable the ETM trace source'''
        self.ETM.setEnabled(enabled)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Configuration option setter method to enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)

    def setTraceWrapMode(self, mode):
        '''Configuration option setter method for the buffer wrap mode'''
        if mode == "wrap":
            self.DSTREAM.setWrapOnFull(True)
        else:
            self.DSTREAM.setWrapOnFull(False)

    def setClearTraceOnConnect(self, enabled):
        '''Configuration option setter method to enable/disable clear trace buffer on connect'''
        self.DSTREAM.setClearOnConnect(enabled)

    def setStartTraceOnConnect(self, enabled):
        '''Configuration option setter method to enable/disable auto start trace buffer on connect only'''
        self.DSTREAM.setAutoStartTraceOnConnect(enabled)

    def writeMem(self, addr, value):
        self.cores[0].memWrite(0, addr, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0x10000, False, 4, pack('<I', value))

    def readMem(self, addr):
        buffer = zeros(4, 'b')
        self.cores[0].memRead(0, addr, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0x10000, 4, buffer)
        return unpack('<I', buffer)[0]

    def setupPinMUXForTrace(self):
        '''Sets up the IO Pin MUX to select 4 bit TPIU trace'''
        addrDBGMCU_CR = 0xE0042004
        value = self.readMem(addrDBGMCU_CR)
        value |=  0xE0 # TRACE_MODE=11 (4 bit port), TRACE_IOEN=1
        self.writeMem(addrDBGMCU_CR, value)

    def enableSystemTrace(self):
        '''Sets up the system to enable trace
           For a Cortex-M3 system we must make sure that the
           TRCENA bit (24) in the DEMCR registers is set.
           NOTE: This bit is normally set by the DSTREAM Cortex-M3
                 template - but we set it ourselves here in case
                 no one connects to the Cortex-M3 device.
        '''
        addrDEMCR = 0xE000EDFC
        bitTRCENA = 0x01000000
        value = self.readMem(addrDEMCR)
        value |= bitTRCENA
        self.writeMem(addrDEMCR, value)

    def setITMEnabled(self, enabled):
        '''Enable/disable the ITM trace source'''
        self.ITM.setEnabled(enabled)

    def setITMEnableTimestamps(self, enabled):
        '''Enable/disable the ITM timestamp'''
        self.ITM.setEnableTimestamps(enabled)

    def setITMTSPrescale(self, TSPrescale):
        '''Set the ITM timestamp prescale value'''
        psValue = {"none":0, "d4":1, "d16":2, "d64":3}
        self.ITM.setTSPrescale(psValue[TSPrescale])

    def setITMEnableDWT(self, enabled):
        '''Enable/disable ITM DWT output support'''
        self.ITM.setEnableDWT(enabled)

    def setITMPortEnables(self, portBitSet):
        '''Set the ITM port enable bitset'''
        self.ITM.setPortEnables(portBitSet)

    def setITMPortPrivileges(self, priv_7_0, priv_15_8, priv_23_16, priv_31_24):
        '''Set the ITM port privilage bits'''
        self.ITM.setPortPrivileges(priv_7_0, priv_15_8, priv_23_16, priv_31_24)

    def setITMOwnedByDebugger(self, state):
        self.ITM.setIsSetupByTarget(not state)

    # override
    def postConnect(self):
        if self.getOptionValue("options.traceBuffer.traceCaptureDevice") in DSTREAM_CAPTURE_NAMES:
            self.setupPinMUXForTrace()
            self.enableSystemTrace()

         # update the timestamp value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)
        DTSLv1.postConnect(self)

    def postReset(self):
        '''Makes sure the debug configuration is re-instated
           following a reset event
        '''
        if self.getOptionValue("options.traceBuffer.traceCaptureDevice") in DSTREAM_CAPTURE_NAMES:
            self.setupPinMUXForTrace()
            self.enableSystemTrace()

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
                source.setStreamID(self.reservedATBIDs[source.getName()])
            else:
                # Make sure the current ID is not on the reserved list
                while atbID in self.reservedATBIDs.values():
                    atbID = atbID + 1
                source.setStreamID(atbID)
                atbID = atbID + 1

    def traceDeviceIsDSTREAM(self, obase):
        ''' Indicates if the trace capture device is configured to be DSTREAM
            Param: obase the option path string to the trace buffer options
        '''
        return self.getOptionValue(obase+".traceBuffer.traceCaptureDevice") in DSTREAM_CAPTURE_NAMES

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
        self.setITMEnableDWT(self.getOptionValue(obase+".DWTENA"))
        self.setITMPortEnables(self.getOptionValue(obase+".STIMENA"))
        self.setITMPortPrivileges(
            self.getOptionValue(obase+".PRIVMASK.[7:0]"),
            self.getOptionValue(obase+".PRIVMASK.[15:8]"),
            self.getOptionValue(obase+".PRIVMASK.[23:16]"),
            self.getOptionValue(obase+".PRIVMASK.[31:24]"))
        self.ITM.setEnableSYNC(True)

    def setDSTREAMOptions(self, obase):
        '''Configures the DSTREAM options
           Param: obase the option path string to the DSTREAM options
        '''
        self.setTraceWrapMode(self.getOptionValue(obase+".traceWrapMode"))
        self.setClearTraceOnConnect(self.getOptionValue(obase+".clearTraceOnConnect"))
        self.setStartTraceOnConnect(self.getOptionValue(obase+".startTraceOnConnect"))


    def setInitialOptions(self, obase):
        '''Takes the configuration options and configures the
           DTSL objects prior to target connection
           Param: obase the option path string to top level options
        '''
        if self.traceDeviceIsDSTREAM(obase):
            self.createDSTREAM()
            self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)
            self.setDSTREAMTraceEnabled(True)
            self.setDSTREAMOptions(obase+".traceBuffer")
            obaseETM = obase+".ETM"
            obaseITM = obase+".ITM"
            self.setETMEnabled(self.getOptionValue(obaseETM+".cortexM3coreTraceEnabled"))
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
        else:
            self.setDSTREAMTraceEnabled(False)
            self.setETMEnabled(False)
            self.setITMEnabled(False)
        obaseUCProbe = obase+".ucProbe"
        self.setucProbeOptions(obaseUCProbe)

    def updateDynamicOptions(self, obase):
        '''Takes any changes to the dynamic options and
           applies them. Note that some trace options may
           not take effect until trace is (re)started
           Param: obase the option path string to top level options
        '''
        if self.traceDeviceIsDSTREAM(obase):
            obaseETM = obase+".ETM"
            self.setETMEnabled(self.getOptionValue(obaseETM+".cortexM3coreTraceEnabled"))
            obaseITM = obase+".ITM"
            if self.getOptionValue(obaseITM+".itmTraceEnabled"):
                self.setITMEnabled(True)
                obaseITMOwner = obaseITM+".itmTraceEnabled.itmowner"
                if self.debuggerOwnsITM(obaseITMOwner):
                    self.setITMOptions(obaseITMOwner+".debugger")
            else:
                self.setITMEnabled(False)
        obaseUCProbe = obase+".ucProbe"
        self.setucProbeOptions(obaseUCProbe)

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


class DebugOnly(uCProbeConfiguration):

    @staticmethod
    def getOptionList():
        '''The method which specifies the configuration options which
           the user can edit via the launcher panel |Edit...| button
        '''
        return [
            DTSLv1.tabSet(
                name='options',
                displayName='Options',
                childOptions=[
                    uCProbeConfiguration.getucProbeOptionsPage()
                ]
            )
        ]


    '''A top level configuration class which only supports debug (no trace)'''
    def __init__(self, root):
        uCProbeConfiguration.__init__(self, root)
        # create the devices in the platform
        self.cores = []
        self.createDevices()
        for core in self.cores:
            self.addDeviceInterface(core)

    # Target dependent functions
    def createDevices(self):
        # create core
        devID = self.findDevice("Cortex-M3")
        self.cortexM3 = ConnectableDevice(self, devID, "Cortex-M3")
        devID = self.findDevice("CSMEMAP")
        self.AHB = CortexM_AHBAP(self, devID, "CSMEMAP")
        self.ucMemoryAccessor = self.AHB
        self.cortexM3.registerAddressFilters(
            [AHBCortexMMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0")])
        self.cores.append(self.cortexM3)
        self.setManagedDevices([self.AHB])

    def updateDynamicOptions(self, obase):
        '''Takes any changes to the dynamic options and
           applies them. Note that some trace options may
           not take effect until trace is (re)started
           Param: obase the option path string to top level options
        '''
        obaseUCProbe = obase+".ucProbe"
        self.setucProbeOptions(obaseUCProbe)

    def setInitialOptions(self, obase):
        '''Takes the configuration options and configures the
           DTSL objects prior to target connection
           Param: obase the option path string to top level options
        '''
        obaseUCProbe = obase+".ucProbe"
        self.setucProbeOptions(obaseUCProbe)

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

class DSTREAM_ST_FAMILY(DSTREAMDebugAndTrace):

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''
        # register other trace components
        self.DSTREAM.setTraceComponentOrder([ self.TPIU ])
        #Set dstream/tpiu port width
        self.setPortWidth(portWidth)
        # tell DSTREAM about its trace sources
        self.DSTREAM.addTraceSource(self.ETM, self.cortexM3.getID())
        self.DSTREAM.addTraceSource(self.ITM)
        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)
        # automatically handle connection/disconnection to trace components
        self.setManagedDevices( [self.AHB, self.ETM, self.ITM, self.TPIU, self.DSTREAM])

    def setDSTREAMOptions(self, obase):
        '''Configures the DSTREAM options
           Param: obase the option path string to the DSTREAM options
        '''
        dstream_opts = obase + ".traceCaptureDevice." + self.getDstreamOptionString()
        portWidthOpt = self.getOptions().getOption(dstream_opts + ".tpiuPortWidth")
        if portWidthOpt:
           portWidth = self.getOptionValue(dstream_opts + ".tpiuPortWidth")
           self.setPortWidth(int(portWidth))

        traceBufferSizeOpt = self.getOptions().getOption(dstream_opts + ".traceBufferSize")
        if traceBufferSizeOpt:
            traceBufferSize = self.getOptionValue(dstream_opts + ".traceBufferSize")
            self.setTraceBufferSize(traceBufferSize)

    def getDstreamOptionString(self):
        return "dstream"

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

class DSTREAMSTDebugAndTrace(DSTREAM_ST_FAMILY):
    '''A top level configuration class which supports debug and trace'''

    @staticmethod
    def getOptionList():
        '''The method which specifies the configuration options which
           the user can edit via the launcher panel |Edit...| button
        '''
        return [
            DTSLv1.tabSet(
                name='options',
                displayName='Options',
                childOptions=[
                    DSTREAMSTDebugAndTrace.getTraceBufferOptionsPage(),
                    DSTREAMDebugAndTrace.getETMOptionsPage(),
                    DSTREAMDebugAndTrace.getITMOptionsPage(),
                    uCProbeConfiguration.getucProbeOptionsPage()
                ]
            )
        ]

    @staticmethod
    def getTraceBufferOptionsPage():
        # If you change the position or name of the traceCapture
        # device option you MUST modify the project_types.xml to
        # tell the debugger about the new location/name
        return DTSLv1.tabPage(
            name='traceBuffer',
            displayName='Trace Buffer',
            childOptions=[
                    DTSLv1.radioEnumOption(
                    name='traceCaptureDevice',
                    displayName = 'Trace capture method',
                    description="Specify how trace data is to be collected",
                    defaultValue="none",
                    values = [
                        ("none", "No trace capture device"),
                        DSTREAMSTDebugAndTrace.getDSTREAMOptions()
                        ]),
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
                                  ("32GB", "32GB"), ("64GB", "64GB"), ("128GB",
                                      "128GB")], isDynamic=False),
                ]
            )
        )

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMSTStoredTraceCapture(self, "DSTREAM")

class DSTREAMPTDebugAndTrace(DSTREAM_ST_FAMILY):
    '''A top level configuration class which supports debug and trace'''

    @staticmethod
    def getOptionList():
        '''The method which specifies the configuration options which
           the user can edit via the launcher panel |Edit...| button
        '''
        return [
            DTSLv1.tabSet(
                name='options',
                displayName='Options',
                childOptions=[
                    DSTREAMPTDebugAndTrace.getTraceBufferOptionsPage(),
                    DSTREAMDebugAndTrace.getETMOptionsPage(),
                    DSTREAMDebugAndTrace.getITMOptionsPage(),
                    uCProbeConfiguration.getucProbeOptionsPage()
                ]
            )
        ]

    @staticmethod
    def getTraceBufferOptionsPage():
        # If you change the position or name of the traceCapture
        # device option you MUST modify the project_types.xml to
        # tell the debugger about the new location/name
        return DTSLv1.tabPage(
            name='traceBuffer',
            displayName='Trace Buffer',
            childOptions=[
                    DTSLv1.radioEnumOption(
                    name='traceCaptureDevice',
                    displayName = 'Trace capture method',
                    description="Specify how trace data is to be collected",
                    defaultValue="none",
                    values = [
                        ("none", "No trace capture device"),
                        DSTREAMPTDebugAndTrace.getStoreAndForwardOptions(),
                        DSTREAMPTDebugAndTrace.getStreamingTraceOptions()
                        ]),
            ]
        )

    @staticmethod
    def getStoreAndForwardOptions():
        return (
            "DSTREAM_PT_Store_and_Forward", "DSTREAM-PT 8GB Trace Buffer",
            DTSLv1.infoElement(
                "dpt_storeandforward", "", "",
                childOptions=[
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False)
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
                    DTSLv1.enumOption('tpiuPortWidth', 'TPIU port width', defaultValue="4",
                        values = [("1", "1 bit"), ("2", "2 bit"), ("3", "3 bit"), ("4", "4 bit")], isDynamic=False),
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
