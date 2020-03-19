# Copyright (C) 2017-2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AxBMemAPAccessor
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import AXIMemAPAccessor
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import ETRTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import DSTREAMSTStoredTraceCapture
from com.arm.debug.dtsl.components import DSTREAMPTStoreAndForwardTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import CSATBReplicator
from com.arm.debug.dtsl.components import STMTraceSource
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
from com.arm.debug.dtsl import DTSLException

from com.arm.rddi import RDDI_ACC_SIZE

from struct import pack, unpack
from jarray import array, zeros

coreNames = ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]
dapIndices = [0, 0, 0, 0]
ctiNames = ["CSCTI_4", "CSCTI_5", "CSCTI_6", "CSCTI_7"]
ctiCoreTriggers = [1, 1, 1, 1]
ctiMacrocellTriggers = [6, 6, 6, 6]
macrocellNames = ["CSETM_0", "CSETM_1", "CSETM_2", "CSETM_3", "CSSTM"]
funnelNames = ["CSTFunnel", "CSTFunnel", "CSTFunnel", "CSTFunnel", "CSTFunnel"]
funnelPorts = [0, 1, 2, 3, 4]
clusterNames = ["Cortex-A53_SMP_0"]
clusterCores = [["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]]
coreNames_cortexA53 = ["Cortex-A53_0", "Cortex-A53_1", "Cortex-A53_2", "Cortex-A53_3"]

TRACE_RANGE_DESCRIPTION = '''Limit trace capture to the specified range. This is useful for restricting trace capture to an OS (e.g. Linux kernel)'''
CTM_CHANNEL_SYNC_STOP = 2  # Use channel 2 for sync stop
CTM_CHANNEL_SYNC_START = 1  # Use channel 1 for sync start
CTM_CHANNEL_TRACE_TRIGGER = 3  # Use channel 3 for trace triggers

TRIG_STOP = 0
FPGA_CTI_ADDR = 0x80007000

CTICTRL   = 0x00
CTIINTACK = 0x04
CTIINEN   = 0x08
CTIOUTEN  = 0x28

# Import core specific functions
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a53_rams


# Cross-triggering with a CTI in the FPGA
# Override of the Device class for Cortex-A53 that also knows how to configure CTIs for sync start and stop
# Controls two CTIs - the one bound to the core and the one in the FPGA
# Only touches the CTI if cross-triggering has been enabled
# De-configures CTI on disconnect

class CTICore(a53_rams.A53CoreDevice):
    def __init__(self, config, id, name, cti1, cti2):
        a53_rams.A53CoreDevice.__init__(self, config, id, name)
        self.myCTI = cti1
        self.fpgaCTI = cti2
        self.xTrigFPGA = False
        self.xTrigHPS = False
        self.connected = False
        self.safeToAccessCTIs = False

    def setCrossTrigFPGA(self, enabled):
        self.enableTrigFPGA(enabled)

    def setCrossTrigHPS(self, enabled):
        self.enableTrigHPS(enabled)

    def openConn(self, id, version, name):
        Device.openConn(self, id, version, name)
        self.connected = True
        self.configureCTIs()

    def closeConn(self):
        self.unconfigureCTIs()
        self.connected = False
        Device.closeConn(self)

    def configureCTIs(self):
        if self.safeToAccessCTIs:
            if self.xTrigFPGA or self.xTrigHPS:
                self.ensureCTIsConnected()
                self.enableCTIs()

            self.enableTrigFPGA(self.xTrigFPGA)
            self.enableTrigHPS(self.xTrigHPS)

    def unconfigureCTIs(self):
        self.enableTrigFPGA(False)
        self.enableTrigHPS(False)

    def enableTrigFPGA(self, enabled):
        if self.connected and self.safeToAccessCTIs:
            if enabled:
                self.ensureCTIsConnected()
                self.enableCTIs()
                self.enableCTIStopChannel(self.myCTI, self.fpgaCTI, True)
            else:
                if self.xTrigFPGA:
                    self.clearTriggers()
                    self.enableCTIStopChannel(self.myCTI, self.fpgaCTI, False)

        self.xTrigFPGA = enabled

    def enableTrigHPS(self, enabled):
        if self.connected and self.safeToAccessCTIs:
            if enabled:
                self.ensureCTIsConnected()
                self.enableCTIs()
                self.enableCTIStopChannel(self.fpgaCTI, self.myCTI, True)
            else:
                if self.xTrigHPS:
                    self.enableCTIStopChannel(self.fpgaCTI, self.myCTI, False)

        self.xTrigHPS = enabled

    def ensureCTIsConnected(self):
        # if enable the trigger sometime after connection then need to connect to CTI
        if not self.myCTI.isConnected():
            self.myCTI.connect()
        if not self.fpgaCTI.isConnected():
            self.fpgaCTI.connect()

    def enableCTIs(self):
        self.myCTI.writeRegister(CTICTRL, 0x00000001)
        self.fpgaCTI.writeRegister(CTICTRL, 0x00000001)

    def enableCTIStopChannel(self, outCTI, inCTI, enable):
        if enable:
            val = (0x01 << CTM_CHANNEL_SYNC_STOP)
        else:
            val = 0
        inCTI.writeRegister(CTIINEN + TRIG_STOP, val)
        outCTI.writeRegister(CTIOUTEN + TRIG_STOP, val)

    def clearTriggers(self):
        if self.xTrigFPGA and self.myCTI.isConnected():
            self.myCTI.writeRegister(CTIINTACK, 0x01 << TRIG_STOP)
            self.myCTI.writeRegister(CTIINTACK, 0x00)

    def go(self):
        self.clearTriggers()
        Device.go(self)

    def step(self, count, flags):
        self.clearTriggers()
        return Device.step(self, count, flags)

''' Because of slow connection with USB-Blaster, replace download with simple memWrites '''
class CTICoreNoDownload(CTICore):
    def __init__(self, config, id, name, cti1, cti2):
        CTICore.__init__(self, config, id, name, cti1, cti2)
        self.downloading = False
        self.dlStart = 0
        #self.dlError = null
        self.dlErrorEncountered = False

    def memDownload(self, page, address, size, rule, check, count, data):
        try:
            if (self.downloading == False):
                self.dlStart = address
                self.downloading = True
            self.memWrite( page, address, size, rule, check, count, data)
        except NativeException, e:
            if (self.dlErrorEncountered == False):
                self.dlError = e
                self.dlErrorEncountered = True

    def memDownloadEnd(self, values, pages, addresses, offsets):
        self.downloading = False
        if (self.dlErrorEncountered == True):
            self.dlErrorEncountered = False
            values[0] = self.dlError.getRDDIErrorCode()
            #pages[0] = self.dlPage
            #addresses[0] = self.dlAddress
            #offsets[0] = self.dlOffset
            raise self.dlError
        else:
            values[0] = 0

# A very simple implementation of a CTI
# This knows about just one input and one output trigger
# It makes no access to the CTI device outside of the flushConfig() method
# To ensure this, access to the CTI registers is via MemAP memory writes - we don't use the CTI template

class RegisterDevice:
    def __init__(self, dev, address):
        self.inputEnabled = False
        self.device = dev
        self.baseAddr = address

    def flushConfig(self):
        if self.inputEnabled:
            self.writeRegister(CTICTRL, 1)

            register = CTIINEN + FPGA_TRIG_STOP
            value = 1 << CTM_CHANNEL_SYNC_STOP
            self.writeRegister(register, value)

            register = CTIOUTEN + FPGA_TRIG_ACK
            value = 1 << CTM_CHANNEL_SYNC_STOP
            self.writeRegister(register, value)
        else:
            register = CTIINEN + FPGA_TRIG_STOP
            self.writeRegister(register, 0)
            register = CTIOUTEN + FPGA_TRIG_STOP
            self.writeRegister(register, 0)

    def enableInputTrigger(self):
        self.inputEnabled = True

    def disableAllInputs(self):
        self.inputEnabled = False

    def disableAllOutputs(self):
        pass

    def writeRegister(self, register, value):
        # Access via AP 1
        address = self.baseAddr + register * 4
        self.device.memWrite(APB_AP, address, RDDI_ACC_SIZE.RDDI_ACC_DEF, self.apToRule(APB_AP), False, 4, pack('<I', value))


# CTI Sync handler that can optionally deal with an additional CTI
# No access is made to the CTI unless cross-trigger for that CTI has been enabled
# To simplify other scripting and DTSL options dialog, only one method call is needed to enable/disable cross trigger
class AlteraCTISyncSMPDevice(CTISyncSMPDevice):

    def __init__(self, configuration, name, id, devs, startChannel, stopChannel):
        self.cti = RegisterDevice(self, FPGA_CTI_ADDR)
        self.xTrig = False
        CTISyncSMPDevice.__init__(self, configuration, name, id, devs, startChannel, stopChannel)

    def setCrossTrig(self, enabled):
        if enabled:
            # Wire up the STOP triggers on the FPGA
            self.cti.enableInputTrigger()
            # If we are connected, flush the config through to the CTI
            # Otherwise this must be done at connect time
            if self.isConnected():
                self.cti.flushConfig()
        else:
            # Only touch the CTI if we have previously enabled it
            if self.xTrig == True:
                self.cti.disableAllInputs()
                self.cti.disableAllOutputs()
                if self.isConnected():
                    self.cti.flushConfig()

        self.xTrig = enabled

    def startCores(self, stoppedCores):
        if self.xTrig:
            # Clear the trigger acks
            self.cti.writeRegister(CTIINTACK, 0x01 << FPGA_TRIG_STOP)
            self.cti.writeRegister(CTIINTACK, 0x00)
        self.super__startCores(stoppedCores)

    def openConn(self, id, version, message):
        CTISyncSMPDevice.openConn(self, id, version, message)
        if self.xTrig:
            self.cti.flushConfig()

# Device Handler can optionally deal with an additional CTI
# No access is made to the CTI unless cross-trigger for that CTI has been enabled
# To simplify other scripting and DTSL options dialog, only one method call is needed to enable/disable cross trigger
class coreCTIDevice(Device):

    def __init__(self, configuration, name, id, devs, startChannel, stopChannel):
        self.cti = RegisterDevice(self, FPGA_CTI_ADDR)
        self.xTrig = False

    def setCrossTrig(self, enabled):
        if enabled:
            # Wire up the STOP triggers on the FPGA
            self.cti.enableInputTrigger()
            # If we are connected, flush the config through to the CTI
            # Otherwise this must be done at connect time
            if self.isConnected():
                self.cti.flushConfig()
        else:
            # Only touch the CTI if we have previously enabled it
            if self.xTrig == True:
                self.cti.disableAllInputs()
                self.cti.disableAllOutputs()
                if self.isConnected():
                    self.cti.flushConfig()

        self.xTrig = enabled

    def startCores(self, stoppedCores):
        if self.xTrig:
            # Clear the trigger acks
            self.cti.writeRegister(CTIINTACK, 0x01 << FPGA_TRIG_STOP)
            self.cti.writeRegister(CTIINTACK, 0x00)
        self.super__startCores(stoppedCores)

    def openConn(self, id, version, message):
        CTISyncSMPDevice.openConn(self, id, version, message)
        if self.xTrig:
            self.cti.flushConfig()


class DtslScript(DTSLv1):

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "System Memory Trace Buffer (CSTMC_1/ETR)"), ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                            values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False),
                    ])
                ])

    @staticmethod
    def getOptionCortexA53TabPage():
        return DTSLv1.tabPage("Cortex-A53_SMP_0", "Cortex-A53", childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A53 core trace', defaultValue=False,
                        childOptions =
                            # Allow each source to be enabled/disabled individually
                            [ DTSLv1.booleanOption('Cortex-A53_SMP_0_%d' % core, "Enable " + clusterCores[0][core] + " trace", defaultValue=True)
                            for core in range(len(clusterCores[0])) ] +
                            [ DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True) ] +
                            [ DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True)
                            ] +
                            [ ETMv4TraceSource.cycleAccurateOption(DtslScript.getTraceMacrocellsForCluster("Cortex-A53_SMP_0"))] +
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
                        )
                ])

    @staticmethod
    def getOptionCrossTriggerTabPage():
        XTRIG_INFO = '''The Cross Trigger interface can only be accessed if the system clocks
have been initialized.  If the Cross Trigger interface is accessed
prior to the clock initialization, then the target may lock up.
The following option should only be set if you are sure that the system
clocks have been initialized prior to connecting to the target system.'''

        return DTSLv1.tabPage("xTrig", "Cross Trigger", childOptions=[
                    DTSLv1.booleanOption('xtrigFPGA0', 'Enable FPGA -> HPS Cross Trigger (Cortex-A53_0) ', defaultValue=False, isDynamic=True,
                        setter=DtslScript.setXTrigFPGAEnabled0, description="Trigger events in the FPGA can halt only Cortex-A53_0 core"),
                    DTSLv1.booleanOption('xtrigFPGA1', 'Enable FPGA -> HPS Cross Trigger (Cortex-A53_1)', defaultValue=False, isDynamic=True,
                        setter=DtslScript.setXTrigFPGAEnabled1, description="Trigger events in the FPGA can halt only Cortex-A53_1 core"),
                    DTSLv1.booleanOption('xtrigFPGA2', 'Enable FPGA -> HPS Cross Trigger (Cortex-A53_2) ', defaultValue=False, isDynamic=True,
                        setter=DtslScript.setXTrigFPGAEnabled2, description="Trigger events in the FPGA can halt only Cortex-A53_2 core"),
                    DTSLv1.booleanOption('xtrigFPGA3', 'Enable FPGA -> HPS Cross Trigger (Cortex-A53_3)', defaultValue=False, isDynamic=True,
                        setter=DtslScript.setXTrigFPGAEnabled3, description="Trigger events in the FPGA can halt only Cortex-A53_3 core"),
                    DTSLv1.booleanOption('xtrigHPS', 'Enable HPS -> FPGA Cross Trigger', defaultValue=False, isDynamic=True,
                        setter=DtslScript.setXTrigHPSEnabled, description="Trigger events in the FPGA can be caused when Cortex-A53 cores halt"),
                    DTSLv1.optionGroup('access', 'Cross Trigger initialization', childOptions=[
                        DTSLv1.infoElement('info', XTRIG_INFO),
                        DTSLv1.booleanOption('canAccess', 'Assume Cross Triggers can be accessed',
                                             description=XTRIG_INFO,
                                             setter=DtslScript.setCTIAccess,
                                             defaultValue=False, isDynamic=True),
                        ])
                ])

    @staticmethod
    def getOptionETRTabPage():
        return DTSLv1.tabPage("ETR", "ETR", childOptions=[
                    DTSLv1.booleanOption('etrBuffer0', 'Configure the system memory trace buffer to be used by the CSTMC_1/ETR device', defaultValue=False,
                        childOptions = [
                            DTSLv1.integerOption('start', 'Start address',
                            description='Start address of the system memory trace buffer to be used by the CSTMC_1/ETR device',
                            defaultValue=0x00100000,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.integerOption('size', 'Size in bytes',
                            description='Size of the system memory trace buffer in bytes',
                            defaultValue=0x8000,
                            isDynamic=True,
                            display=IIntegerOption.DisplayFormat.HEX),
                            DTSLv1.booleanOption('scatterGather', 'Enable scatter-gather mode',
                            defaultValue=False,
                            description='When enabling scatter-gather mode, the start address of the on-chip trace buffer must point to a configured scatter-gather table')
                        ]
                    ),
                ])

    @staticmethod
    def getOptionSTMTabPage():
        return DTSLv1.tabPage("stm", "STM", childOptions=[
                    DTSLv1.booleanOption('CSSTM', 'Enable CSSTM trace', defaultValue=False),
                ])

    @staticmethod
    def getOptionRAMTabPage():
        return DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ])

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCrossTriggerTabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionRAMTabPage()
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
        
        self.exposeCores()
        
        self.traceRangeIDs = {}
        
        traceComponentOrder = [ self.Funnel0 ]
        managedDevices = [ self.Funnel0, self.OutCTI0, self.TPIU, self.ETF0Trace ]
        self.setupETFTrace(self.ETF0Trace, "CSTMC_0", traceComponentOrder, managedDevices)
        
        traceComponentOrder = [ self.Funnel0, self.ETF0 ]
        managedDevices = [ self.Funnel0, self.ETF0, self.OutCTI0, self.TPIU, self.ETR0 ]
        self.setupETRTrace(self.ETR0, "CSTMC_1", traceComponentOrder, managedDevices)
        
        traceComponentOrder = [ self.Funnel0, self.ETF0, self.TPIU ]
        managedDevices = [ self.Funnel0, self.ETF0, self.OutCTI0, self.TPIU, self.DSTREAM ]
        self.setupDSTREAMTrace(traceComponentOrder, managedDevices)
        
        self.setupCTISyncSMP()
        
        self.setManagedDeviceList(self.mgdPlatformDevs)
        
        self.setETFTraceEnabled(self.ETF0Trace, False)
        self.setETRTraceEnabled(self.ETR0, False)
        self.setDSTREAMTraceEnabled(False)
    
    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+
    
    def discoverDevices(self):
        '''Find and create devices'''
        
        self.APBs = []
        self.AXIs = []
        
        ap = APBAP(self, self.findDevice("CSMEMAP_0"), "APB_0")
        self.mgdPlatformDevs.append(ap)
        self.APBs.append(ap)
        
        ap = AXIAP(self, self.findDevice("CSMEMAP_1"), "AXI_0")
        self.mgdPlatformDevs.append(ap)
        self.AXIs.append(ap)
        
        # Trace start/stop CTI 0
        self.OutCTI0 = CSCTI(self, self.findDevice("CSCTI_0"), "CSCTI_0")
        self.CTIs  = []
        self.cortexA53ctiMap = {} # map cores to associated CTIs
        
        # FPGA CTI
        fpgaCTIDev = self.findDevice("CSCTI_1", self.findDevice("CSCTI_1"))
        self.fpgaCTI = CSCTI(self, fpgaCTIDev, "CSCTI_1")
        
        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        # STM -- CSSTM
        self.STM0 = self.createSTM("CSSTM", streamID, "CSSTM")
        streamID += 1
        
        # For future use, store a map of core types and cluster names against created devices
        self.macrocells = {}
        self.macrocells["cortexA53"] = []
        self.macrocells["Cortex-A53_SMP_0"] = []
        
        cortexA53CoreDev = 0
        self.cortexA53cores = []
        # Ensure that macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for i in range(len(coreNames)):
            # create CTI for this core
            coreCTI = CSCTI(self, self.findDevice(ctiNames[i]), ctiNames[i])
            self.CTIs.append(coreCTI)

            # Automatically handle connection to CTIs
            self.mgdPlatformDevs.append(coreCTI)

            # Create core
            cortexA53CoreDev = self.findDevice(coreNames[i], cortexA53CoreDev+1)
            coreDevice = self.ctiCoreFactory(cortexA53CoreDev, "Cortex-A53_%d" % i, coreCTI, self.fpgaCTI)
            self.cortexA53cores.append(coreDevice)
            self.cortexA53ctiMap[coreDevice] = coreCTI
            
            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmDev = self.getMacrocellNameForCore(coreNames[i])
            if not tmDev == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmDev), streamID, tmDev)
                streamID += 2
                tm.setEnabled(False)
                self.macrocells["cortexA53"].append(tm)
                self.addMacrocellsToClusterList(coreNames[i], tm)
            
        # Create all the CTIs which are associated with cores
        for i in range (len(ctiNames)):
            if not ctiNames[i] is None:
                coreCTI = CSCTI(self, self.findDevice(ctiNames[i]), ctiNames[i])
                # Automatically handle connection to CTIs
                self.mgdPlatformDevs.append(coreCTI)
        
        # ETF 0
        self.ETF0 = CSTMC(self, self.findDevice("CSTMC_0"), "CSTMC_0")
        
        # ETF 0 trace capture
        self.ETF0Trace = TMCETBTraceCapture(self, self.ETF0, "CSTMC_0")
        
        # ETR 0
        self.ETR0 = ETRTraceCapture(self, self.findDevice("CSTMC_1"), "CSTMC_1")
        
        # DSTREAM
        self.createDSTREAM()
        
        # TPIU
        self.TPIU = self.createTPIU("CSTPIU", "TPIU")
        
        # Funnel 0
        self.Funnel0 = self.createFunnel("CSTFunnel", "CSTFunnel")
        
        # Replicator 0
        self.Replicator0 = CSATBReplicator(self, self.findDevice("CSATBReplicator"), "CSATBReplicator")
        
    def registerFilters(self, core, dap):
        '''Register MemAP filters to allow access to the APs for the device'''
        if dap == 0:
            core.registerAddressFilters([
                AxBMemAPAccessor("APB_0", self.APBs[0], "APB bus accessed via AP 0 (CSMEMAP_0)"),
                AXIMemAPAccessor("AXI_0", self.AXIs[0], "AXI bus accessed via AP 1 (CSMEMAP_1)", 64),
            ])
    
    def exposeCores(self):
        '''Ensure that cores have access to memory'''
        for i in range(len(coreNames)):
            core = self.getDeviceInterface(coreNames[i])
            self.registerFilters(core, dapIndices[i])
            self.addDeviceInterface(core)
        for core in self.cortexA53cores:
            a53_rams.registerInternalRAMs(core)
    
    def setupETFTrace(self, etfTrace, name, traceComponentOrder, managedDevices):
        '''Setup ETF trace capture'''
        # Use continuous mode
        etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)
        
        # Register other trace components with ETF and register ETF with configuration
        etfTrace.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etfTrace)
        
        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)
    
    def setupETRTrace(self, etr, name, traceComponentOrder, managedDevices):
        '''Setup ETR trace capture'''
        # Use continuous mode
        etr.setFormatterMode(FormatterMode.CONTINUOUS)
        
        # Register other trace components with ETR and register ETR with configuration
        etr.setTraceComponentOrder(traceComponentOrder)
        self.addTraceCaptureInterface(etr)
        
        # Automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(name, managedDevices)
    
    def setupDSTREAMTrace(self, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        
        # Configure the DSTREAM for trace
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
    
    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/Disable all pertinent funnel ports for a trace source'''
        sourceName = source.getName()
        for i in range(len(macrocellNames)):
            if sourceName == macrocellNames[i]:
                '''We may have a list of funnels to which the source is connected.'''
                if isinstance(funnelNames[i], list):
                    for j in range(len(funnelNames[i])):
                        '''Enable/Disable multiple connected funnel ports for this trace source.'''
                        self.setFunnelPortEnabled(funnelNames[i][j], funnelPorts[i][j], enabled)
                else:
                    '''Enable/Disable a single connected funnel port for this trace source.'''
                    self.setFunnelPortEnabled(funnelNames[i], funnelPorts[i], enabled)
    
    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a trace source
        return (None, None, None) if no associated CTI
        '''
        sourceName = source.getName()
        for i in range(len(coreNames)):
            if sourceName == macrocellNames[i]:
                if ctiMacrocellTriggers[i] is not None:
                    return (self.getDeviceInterface(ctiNames[i]), ctiMacrocellTriggers[i], CTM_CHANNEL_TRACE_TRIGGER)
        
        return (None, None, None)
    
    def getCTIForSink(self, sink):
        '''Get the CTI and output/channel associated with a trace sink
        return (None, None, None) if no associated CTI
        '''
        sinkNames = ["CSTMC_0", "CSTPIU", "CSTMC_1"]
        ctiNames = ["CSCTI_0", "CSCTI_0", "CSCTI_0"]
        ctiTriggers = [1, 3, 1]
        
        sinkName = sink.getName()
        for i in range(len(sinkNames)):
            if sinkName == sinkNames[i]:
                return (self.getDeviceInterface(ctiNames[i]), ctiTriggers[i], CTM_CHANNEL_TRACE_TRIGGER)
        
        return (None, None, None)
    
    def setTraceSourceEnabled(self, source, enabled):
        '''Enable/disable a trace source'''
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)
    
    def createTPIU(self, tpiuDev, name):
        tpiu = CSTPIU(self, self.findDevice(tpiuDev), name)
        # Disabled by default - will enable with option
        tpiu.setEnabled(False)
        return tpiu
    
    def setupCTISyncSMP(self):
        '''Create SMP device using CTI synchronization'''
        # Setup CTIs for synch start/stop
        # Cortex-A53 CTI SMP setup
        ctiInfo = {}
        ctiInfo = self.getCTIInfoForCores(clusterCores[0])

        self.smp = AlteraCTISyncSMPDevice(self, clusterNames[0], self.cortexA53cores, ctiInfo, CTM_CHANNEL_SYNC_START, CTM_CHANNEL_SYNC_STOP)
        self.registerFilters(self.smp, self.getDapIndex(clusterNames[0]))
        self.addDeviceInterface(self.smp)

    
    def setETFTraceEnabled(self, etfTrace, enabled):
        '''Enable/disable ETF trace capture'''
        if enabled:
            # Put the ETF in ETB mode
            etfTrace.getTMC().setMode(CSTMC.Mode.ETB)
        else:
            # Put the ETF in FIFO mode
            etfTrace.getTMC().setMode(CSTMC.Mode.ETF)
        
        self.enableCTIsForSink(etfTrace, enabled)
    
    def setETRTraceEnabled(self, etr, enabled):
        '''Enable/disable ETR trace capture'''
        if enabled:
            # Ensure TPIU is disabled
            self.TPIU.setEnabled(False)
        self.enableCTIsForSink(etr, enabled)
    
    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.TPIU.setEnabled(enabled)
        self.enableCTIsForSink(self.DSTREAM, enabled)
    
    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for i in range(len(coreNames)):
            core = self.getDeviceInterface(coreNames[i])
            coreTM = self.getTMForCore(core)
            if coreTM is not None and coreTM.isEnabled():
                self.registerCoreTraceSource(traceCapture, core, coreTM)
        
        i=len(coreNames)
        for macrocell in range(i, len(macrocellNames)):
            TM = self.getDeviceInterface(macrocellNames[macrocell])
            if TM is not None:
                self.registerTraceSource(traceCapture, TM)
        
    
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
        
        coreTraceEnabled = self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace")
        for core in range(len(clusterCores[0])):
            thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.Cortex-A53_SMP_0_%d" % core)
            enableSource = coreTraceEnabled and thisCoreTraceEnabled
            coreTM = self.getTMForCore(self.getDeviceInterface(clusterCores[0][core]))
            self.setTraceSourceEnabled(coreTM, enableSource)
            self.setInternalTraceRange(coreTM, "Cortex-A53_SMP_0")
            self.setTimestampingEnabled(coreTM, self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.timestamp"))
            self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.Cortex-A53_SMP_0.coreTrace.contextIDs"),
                                     "32")
        
        portWidthOpt = self.getOptions().getOption("options.trace.offChip.tpiuPortWidth")
        if portWidthOpt:
            portWidth = self.getOptionValue("options.trace.offChip.tpiuPortWidth")
            self.setPortWidth(int(portWidth))
        
        traceBufferOpt = self.getOptions().getOption("options.trace.offChip.traceBufferSize")
        if traceBufferOpt:
            traceBufferSize = self.getOptionValue("options.trace.offChip.traceBufferSize")
            self.setTraceBufferSize(traceBufferSize)
        
        stmEnabled = self.getOptionValue("options.stm.CSSTM")
        self.setTraceSourceEnabled(self.STM0, stmEnabled)
        
        # Register trace sources for each trace sink
        self.registerTraceSources(self.ETF0Trace)
        self.registerTraceSources(self.ETR0)
        self.registerTraceSources(self.DSTREAM)
        
        self.setManagedDeviceList(self.getManagedDevices(traceMode))
        
    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        
        # Set up the ETR 0 buffer
        configureETRBuffer = self.getOptionValue("options.ETR.etrBuffer0")
        if configureETRBuffer:
            scatterGatherMode = self.getOptionValue("options.ETR.etrBuffer0.scatterGather")
            bufferStart = self.getOptionValue("options.ETR.etrBuffer0.start")
            bufferSize = self.getOptionValue("options.ETR.etrBuffer0.size")
            self.ETR0.setBaseAddress(bufferStart)
            self.ETR0.setTraceBufferSize(bufferSize)
            self.ETR0.setScatterGatherModeEnabled(scatterGatherMode)
            
        for core in range(len(self.cortexA53cores)):
            a53_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA53cores[core])
            a53_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA53cores[core])
        
    def getManagedDevices(self, traceKey):
        '''Get the required set of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)
        
        return deviceList
    
    def setTraceCaptureMethod(self, method):
        if method == "CSTMC_0":
            self.setETFTraceEnabled(self.ETF0Trace, True)
        if method == "CSTMC_1":
            self.setETRTraceEnabled(self.ETR0, True)
        if method == "DSTREAM":
            self.setDSTREAMTraceEnabled(True)
    
    @staticmethod
    def getTraceMacrocellsForCluster(cluster):
        '''Get the Trace Macrocells for a given coreType
           Use parameter-binding to ensure that the correct Macrocells
           are returned for the core type and cluster passed only'''
        def getMacrocellsForCluster(self):
            return self.macrocells[cluster]
        return getMacrocellsForCluster
    
    def setXTrigFPGAEnabled0(self, enabled):
        self.cortexA53cores[0].setCrossTrigFPGA(enabled)

    def setXTrigFPGAEnabled1(self, enabled):
        self.cortexA53cores[1].setCrossTrigFPGA(enabled)

    def setXTrigFPGAEnabled2(self, enabled):
        self.cortexA53cores[2].setCrossTrigFPGA(enabled)

    def setXTrigFPGAEnabled3(self, enabled):
        self.cortexA53cores[3].setCrossTrigFPGA(enabled)

    def setXTrigHPSEnabled(self, enabled):
        for core in self.cortexA53cores:
            core.setCrossTrigHPS(enabled)

    def setCTIAccess(self, access):
        # check whether CTIs should be configured on connection
        for core in self.cortexA53cores:
            core.safeToAccessCTIs = access
            if self.isConnected():
                core.configureCTIs()

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
    
    def getTMForCore(self, core):
        '''Get trace macrocell for core'''
        coreName = core.getName()
        for i in range(len(coreNames)):
            if coreName == coreNames[i]:
                return self.getDeviceInterface(macrocellNames[i])
        
        return None
    
    def setInternalTraceRange(self, coreTM, coreName):
        
        traceRangeEnable = self.getOptionValue("options.%s.coreTrace.traceRange" % coreName)
        traceRangeStart = self.getOptionValue("options.%s.coreTrace.traceRange.start" % coreName)
        traceRangeEnd = self.getOptionValue("options.%s.coreTrace.traceRange.end" % coreName)
        
        if coreTM in self.traceRangeIDs:
            coreTM.clearTraceRange(self.traceRangeIDs[coreTM])
            del self.traceRangeIDs[coreTM]
        
        if traceRangeEnable:
            self.traceRangeIDs[coreTM] = coreTM.addTraceRange(traceRangeStart, traceRangeEnd)
    
    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
    
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
    
    def getMacrocellNameForCore(self, coreName):
        '''Get the index of the dap with which this core is associated'''
        for index in range(len(coreNames)):
            if coreNames[index] == coreName:
                return macrocellNames[index]
        return None
    
    def addMacrocellsToClusterList(self, coreName, tm):
        '''Add the macrocell to the cluster map'''
        for i in range(len(clusterNames)):
            clusterCoreNames = clusterCores[i];
            if coreName in clusterCoreNames:
                self.macrocells[clusterNames[i]].append(tm)
    
    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, self.findDevice(funnelDev), name)
        funnel.setAllPortsDisabled() # Will enable for each source later
        return funnel
    
    def setFunnelPortEnabled(self, funnelName, port, enabled):
        '''Enable/disable a funnel port'''
        funnel = self.getDeviceInterface(funnelName)
        if funnel:
            if enabled:
                funnel.setPortEnabled(port)
            else:
                funnel.setPortDisabled(port)
    
    def createSTM(self, stmDev, streamID, name):
        stm = STMTraceSource(self, self.findDevice(stmDev), streamID, name)
        # Disabled by default - will enable with option
        stm.setEnabled(False)
        return stm
    
    def getDapIndex(self, coreName):
        '''Get the index of the dap with which this core is associated'''
        for index in range(len(coreNames)):
            if coreNames[index] == coreName:
                return dapIndices[index]
        return 0
    
    def getDevicesFromNameList(self, devNames):
        devs = []
        for devName in devNames:
            dev = self.getDeviceInterface(devName)
            if not dev is None:
                devs.append(dev)
        
        return devs
    
    def getCTIInfoForCores(self, cores):
        '''Get the CTI info for the given cores - return a map of CTI info against core'''
        ctiInfo = {}
        for coreName in cores:
            for i in range(len(coreNames)):
                if coreName == coreNames[i] and ctiNames[i] is not None:
                    ctiInfoForDevice =  CTISyncSMPDevice.DeviceCTIInfo(self.getDeviceInterface(ctiNames[i]), CTISyncSMPDevice.DeviceCTIInfo.NONE, ctiCoreTriggers[i], 0, 0)
                    core = self.getDeviceInterface(coreName)
                    ctiInfo[core] = ctiInfoForDevice
        
        return ctiInfo
    
    def postConnect(self):
        DTSLv1.postConnect(self)
        
        try:
            freq = self.getOptionValue("options.trace.traceOpts.timestampFrequency")
        except:
            return
        
        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)
    
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
            
            
    def verify(self):
        mask = [ 0xF, 0x0, 0x0, 0x0, 0xFF, 0xFF, 0xF, 0x0 ]
        expectedROMTable = [ 0L, 0L, 0L, 0L, 3L, 224L, 14L, 0L ]
        addrROMTable = 0x80000FD0
 
        return (self.confirmValue(addrROMTable, expectedROMTable, mask) and (self.countDevices("Cortex-A53_") == 4))

    def confirmValue(self, addr, expected, mask):
        actual = zeros(len(expected), 'l')
        for i in range(0,len(expected)-1) :
            j = i*4
            buffer = zeros(4, 'b')
            try:
                self.APBs[0].readMem(addr+j, 4, buffer)
            except DTSLException:
                return False
            value = unpack('<I', buffer)[0]
            actual[i] = value
            if ((actual[i] & mask[i]) != (expected[i] & mask[i])):
                return False
        return True

    def countDevices(self, deviceName):
        count = 0
        for d in self.getDevices() :
            name = d.getName()
            if deviceName in name and "SMP" not in name:
                count += 1
  
        return count

    def ctiCoreFactory(self, dev, label, coreCTI, fpgaCTI):
        return CTICore(self, dev, label, coreCTI, fpgaCTI)

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, traceComponentOrder, managedDevices):
        '''Setup DSTREAM trace capture'''
        # Configure the TPIU mode
        self.TPIU.setFormatterMode(FormatterMode.CONTINUOUS)
        
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
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCrossTriggerTabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionRAMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "System Memory Trace Buffer (CSTMC_1/ETR)"), ("DSTREAM", "DSTREAM-ST Streaming Trace")],
                        setter=DtslScript_DSTREAM_ST.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="4",
                            values = [("4", "4 bit")], isDynamic=False),
                        DTSLv1.enumOption('traceBufferSize', 'Trace Buffer Size', defaultValue="4GB",
                            values = [("64MB", "64MB"), ("128MB", "128MB"), ("256MB", "256MB"), ("512MB", "512MB"), ("1GB", "1GB"), ("2GB", "2GB"), ("4GB", "4GB"), ("8GB", "8GB"), ("16GB", "16GB"), ("32GB", "32GB"), ("64GB", "64GB"), ("128GB", "128GB")], isDynamic=False)
                    ])
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMSTStoredTraceCapture(self, "DSTREAM")
    
    def setTraceBufferSize(self, mode):
        '''Configuration option setter method for the trace buffer size'''
        bufferSize = 64*1024*1024
        if (mode == "64MB"):
            bufferSize = 64*1024*1024
        if (mode == "128MB"):
            bufferSize = 128*1024*1024
        if (mode == "256MB"):
            bufferSize = 256*1024*1024
        if (mode == "512MB"):
            bufferSize = 512*1024*1024
        if (mode == "1GB"):
            bufferSize = 1*1024*1024*1024
        if (mode == "2GB"):
            bufferSize = 2*1024*1024*1024
        if (mode == "4GB"):
            bufferSize = 4*1024*1024*1024
        if (mode == "8GB"):
            bufferSize = 8*1024*1024*1024
        if (mode == "16GB"):
            bufferSize = 16*1024*1024*1024
        if (mode == "32GB"):
            bufferSize = 32*1024*1024*1024
        if (mode == "64GB"):
            bufferSize = 64*1024*1024*1024
        if (mode == "128GB"):
            bufferSize = 128*1024*1024*1024
        
        self.DSTREAM.setMaxCaptureSize(bufferSize)

class DtslScript_DSTREAM_PT(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_PT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCrossTriggerTabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionRAMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "System Memory Trace Buffer (CSTMC_1/ETR)"), ("DSTREAM", "DSTREAM-PT 8GB Trace Buffer")],
                        setter=DtslScript_DSTREAM_PT.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                    DTSLv1.infoElement("offChip", "Off-Chip Trace", childOptions=[
                        DTSLv1.enumOption('tpiuPortWidth', 'TPIU Port Width', defaultValue="16",
                            values = [("4", "4 bit"), ("8", "8 bit"), ("16", "16 bit")], isDynamic=False)
                    ])
                ])

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM")

class DtslScript_USBBlaster(DtslScript):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_USBBlaster.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCrossTriggerTabPage(),
                DtslScript.getOptionETRTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionRAMTabPage()
            ])
        ]

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "System Memory Trace Buffer (CSTMC_1/ETR)")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ])
                ])

    def resetTarget(self, resetType, targetDevice):
        pass

    def ctiCoreFactory(self, dev, label, coreCTI, fpgaCTI):
        return CTICoreNoDownload(self, dev, label, coreCTI, fpgaCTI)
