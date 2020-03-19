# Copyright (C) 2014-2019 Arm Limited (or its affiliates). All rights reserved.
from struct import pack, unpack

from com.arm.debug.dtsl import DTSLException
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor, APBAP, \
    AXIAP, AXIMemAPAccessor, AxBMemAPAccessor, CSCTI, CSFunnel, CSTMC, \
    CSTPIU, CTISyncSMPDevice, CortexM_AHBAP, ConnectableDevice, \
    DSTREAMTraceCapture, DSTREAMSTStoredTraceCapture, DSTREAMPTStoreAndForwardTraceCapture, \
    DSTREAMPTLiveStoredStreamingTraceCapture, Device, DeviceInfo, DeviceCluster, ETMv4TraceSource, \
    ETRTraceCapture, FormatterMode, ITMTraceSource, TMCETBTraceCapture, STMTraceSource, CSDAP\

from com.arm.debug.dtsl.components.CTISyncSMPDevice import DeviceCTIInfo
from com.arm.debug.dtsl.configurations import ConfigurationBase, DTSLv1
from com.arm.debug.dtsl.configurations import TimestampInfo

from com.arm.debug.dtsl.configurations.options import IIntegerOption

from com.arm.debug.dtsl.interfaces import IARMCoreTraceSource
from com.arm.rddi import RDDI_ACC_SIZE
from jarray import zeros
from java.lang import StringBuilder
from juno_constants import *
from m3 import *
from system_profile import SystemProfiler

NUM_A53_CORES = 4
NUM_A57_CORES = 2
NUM_M3_CORES = 1

TRACE_RANGE_DESCRIPTION = '''Limit capture to the specified address range'''
DSTREAM_PORTWIDTH = 16

CTM_CHAN_SYNC_STOP = 0  # use channel 0 for sync stop
CTM_CHAN_SYNC_START = 1  # use channel 1 for sync start
CTM_CHAN_TRACE_TRIGGER = 2  # use channel 2 for trace triggers

ITM_ATB_ID = 1
ATB_ID_BASE = 2

ITM_FUNNEL_PORT = 0
STM_FUNNEL_PORT = 2
SYS_PROFILER_FUNNEL_PORT = 4

A57_TRACE_OPTIONS = 0
A53_TRACE_OPTIONS = 1
M3_TRACE_OPTIONS = 2
HEX_INTEGER = IIntegerOption.DisplayFormat.HEX

# import core specific functions from Cores folder
import sys, os
sys.path.append(os.path.join('..', '..', '..', 'Cores'))
import a57_rams
import a53_rams

class ResetHookedA57Core(a57_rams.A57CoreDevice):
    def __init__(self, config, id, name):
        a57_rams.A57CoreDevice.__init__(self, config, id, name)
        self.parent = config

    def systemReset(self, resetType):
        # reset via reset controller
        self.parent.reset(self)

class ResetHookedA53Core(a53_rams.A53CoreDevice):
    def __init__(self, config, id, name):
        a53_rams.A53CoreDevice.__init__(self, config, id, name)
        self.parent = config

    def systemReset(self, resetType):
        # reset via reset controller
        self.parent.reset(self)

class DtslScript(DTSLv1):

    @staticmethod
    def getOptionTraceBufferTabPage():
        return DTSLv1.tabPage("traceBuffer", "Trace Buffer", childOptions=[
                    DTSLv1.enumOption(
                        'traceCapture',
                        'Trace capture method',
                        defaultValue="none",
                        values=[("none", "None"),
                                ("ETR", "System Memory Trace Buffer (ETR)"),
                                ("ETF", "On Chip Trace Buffer (ETF)"),
                                ("DSTREAM", "DSTREAM 4GB Trace Buffer")],
                        setter=DtslScript.setTraceCaptureMethod)
        ])

    @staticmethod
    def getOptionCortexA57TabPage():
        return DTSLv1.tabPage("cortexA57", "Cortex-A57", childOptions=[
                DTSLv1.booleanOption(
                    'cortexA57coreTrace',
                    'Enable Cortex-A57 core trace',
                    defaultValue=False,
                    childOptions=[
                        DTSLv1.booleanOption(
                            'Cortex_A57_%d' % c,
                            "Enable Cortex-A57 %d trace" % c,
                            defaultValue=True)
                            for c in range(0, NUM_A57_CORES)] + [
                        DTSLv1.booleanOption(
                            'triggerhalt',
                            "ETM Triggers halt execution",
                            description='Enable the ETM triggers to halt '
                                        'execution',
                            defaultValue=False)] + [
                        DTSLv1.booleanOption(
                            'timestamp',
                            "Enable ETM Timestamps",
                            description="Controls the output of timestamps "
                                        "into the ETM output streams",
                            defaultValue=True,
                            isDynamic=True)] + [
                        DTSLv1.booleanOption(
                            'contextIDs',
                            "Enable ETM Context IDs",
                            description="Controls the output of context ID "
                                        "values into the ETM output streams",
                                        defaultValue=True)] + [
                        ETMv4TraceSource.cycleAccurateOption(DtslScript.getA57ETMs)] + [
                            # Trace range selection (e.g. for linux kernel)
                        DTSLv1.booleanOption(
                            'traceRange',
                            'Trace capture range',
                            description=TRACE_RANGE_DESCRIPTION,
                            defaultValue=False,
                            childOptions=[
                                DTSLv1.integerOption(
                                    'start',
                                    'Start address',
                                    description='Start address for capture',
                                    defaultValue=0,
                                    display=IIntegerOption.DisplayFormat.HEX),
                                DTSLv1.integerOption(
                                    'end',
                                    'End address',
                                    description='End address for capture',
                                    defaultValue=0xFFFFFFFF,
                                    display=IIntegerOption.DisplayFormat.HEX)])
                        ]
            )
        ])

    @staticmethod
    def getOptionCortexA53TabPage():
        return DTSLv1.tabPage("cortexA53", "Cortex-A53", childOptions=[
                    DTSLv1.booleanOption(
                        'cortexA53coreTrace',
                        'Enable Cortex-A53 core trace',
                        defaultValue=False,
                        childOptions=[
                            DTSLv1.booleanOption(
                                'Cortex_A53_%d' % c,
                                "Enable Cortex-A53 %d trace" % c,
                                defaultValue=True)
                                for c in range(0, NUM_A53_CORES)] + [
                            DTSLv1.booleanOption(
                                'triggerhalt',
                                "ETM Triggers halt execution",
                                description="Enable the ETM triggers to "
                                            "halt execution",
                                defaultValue=False)] + [
                            DTSLv1.booleanOption(
                                'timestamp',
                                "Enable ETM Timestamps",
                                description="Controls the output of "
                                            "timestamps into the ETM "
                                            "output streams",
                                defaultValue=True)] + [
                            DTSLv1.booleanOption(
                                'contextIDs',
                                "Enable ETM Context IDs",
                                description="Controls the output of "
                                            "context ID values into "
                                            "the ETM output streams",
                                defaultValue=True)] + [
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getA53ETMs)] + [
                            DTSLv1.booleanOption(
                                'traceRange',
                                'Trace capture range',
                                description=TRACE_RANGE_DESCRIPTION,
                                defaultValue=False,
                                childOptions=[
                                    DTSLv1.integerOption(
                                        'start',
                                        'Start address',
                                        description='Start address for '
                                                    'trace capture',
                                        defaultValue=0,
                                        display=HEX_INTEGER),
                    DTSLv1.integerOption('end', 'End address',
                        description='End address for trace capture',
                        defaultValue=0xFFFFFFFF,
                        display=IIntegerOption.DisplayFormat.HEX)
                ])
            ])
        ])

    @staticmethod
    def getOptionCortexM3TabPage():
        return DTSLv1.tabPage("cortexM3", "Cortex-M3", childOptions=[
                    DTSLv1.booleanOption(
                        'itm',
                        'Enable Cortex-M3 ITM trace',
                        defaultValue=False,
                        setter=DtslScript.setITMEnabled),
                    DTSLv1.booleanOption(
                        'cortexM3coreTrace',
                        'Enable Cortex-M3 core trace',
                        defaultValue=False,
                        childOptions=[
                            DTSLv1.booleanOption(
                                    'Cortex_M3_%d' % c,
                                    "Enable Cortex-M3 %d trace" % c,
                                    defaultValue=True)
                                    for c in range(0, NUM_M3_CORES)] + [
                            DTSLv1.booleanOption(
                                    'timestamp',
                                    "Enable ETM Timestamps",
                                    description="Controls the output of "
                                                "timestamps into the ETM "
                                                "output streams",
                                    defaultValue=True)] + [
                            DTSLv1.integerOption(
                                     'freq',
                                     'Timestamp Period',
                                     defaultValue=4000,
                                     isDynamic=False,
                                     description="This value will be used "
                                                 "to vary the period "
                                                 "between timestamps "
                                                 "appearing in the trace "
                                                 "stream.\nIt represents "
                                                 "the number of cycles, "
                                                 "so a lower value gives "
                                                 "more frequent timestamps.")]
                    )
            ])

    @staticmethod
    def getOptionETRandETFTabPage():
        return DTSLv1.tabPage("ETR", "ETR/ETF", childOptions=[
            DTSLv1.booleanOption(
                'syncBuffer',
                'Halt Cortex-A57/A53 SMP cluster(s) when ETR/ETF buffer full',
                defaultValue=False,
                isDynamic=True),
            DTSLv1.booleanOption(
                'etrBuffer', 'Configure the ETR system memory trace buffer',
                defaultValue=False,
                childOptions=[
                    DTSLv1.integerOption('start', 'Start address',
                        description='Start address of the on-chip buffer',
                        defaultValue=DEFAULT_ETR_BUFFER_ADDRESS,
                        display=IIntegerOption.DisplayFormat.HEX),
                    DTSLv1.integerOption('size', 'Size in bytes',
                        description='Size of the on-chip trace buffer in bytes',
                        defaultValue=0x8000,
                        display=IIntegerOption.DisplayFormat.HEX),
                    DTSLv1.booleanOption('scatterGather',
                        'Enable scatter-gather mode',
                        defaultValue=False,
                        description='When enabling scatter-gather mode, the '
                                    'start address of the on-chip trace '
                                    'buffer must point to a configured '
                                    'scatter-gather table')
                ]
            )
        ])

    @staticmethod
    def getOptionSTMTabPage():
        return DTSLv1.tabPage("STM",
                              "STM",
                              childOptions=[
                                    DTSLv1.booleanOption(
                                            'stm',
                                            'Enable STM trace',
                                            defaultValue=False,
                                            setter=DtslScript.setSTMEnabled)])

    @staticmethod
    def getOptionSystemProfilerTabPage():
        return DTSLv1.tabPage(
                "profiler",
                "System Profiler",
                childOptions=[
                    DTSLv1.booleanOption(
                            'enable',
                            'Enable System Profiler trace generation',
                            defaultValue=False,
                                childOptions=[
                                    DTSLv1.optionGroup(
                                        'config',
                                        'Trigger Configuration',
                                        description='Configure triggering',
                        childOptions=[
                        DTSLv1.booleanOption(
                            "win",
                            "Enable Window Timer (Timer will trigger capture)",
                            defaultValue=True,
                            childOptions=[
                                DTSLv1.integerOption(
                                    'duration',
                                    'Window Time Duration',
                                    description='Durations of 0x1-80000000',
                                    defaultValue=0x40000000,
                                    display=IIntegerOption.DisplayFormat.HEX),
                        ]),
                    ]),

                    DTSLv1.optionGroup('monitors',
                                       'Monitor and Count Configuration',
                                       description='Configure monitor options',
                                       childOptions=[
                        DTSLv1.booleanOption(
                            "secure",
                            "Count Secure Events",
                            defaultValue=True),
                        DTSLv1.booleanOption(
                            "mon_0",
                            "Monitor 0 (ABM attached to Cortex-A57)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_1",
                            "Monitor 1 (ABM attached to Cortex-A53)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_2",
                            "Monitor 2 (ABM attached to T6XX)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_3",
                            "Monitor 3 (ABM attached to CCI S1 port)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_4",
                            "Monitor 4 (ABM attached to PCIe -> CCI I/F)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_5",
                            "Monitor 5 (ABM attached to CCI -> PCIe I/F)",
                             defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_6",
                            "Monitor 6 (ABM attached to Sys Peripheral)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_7",
                            "Monitor 7 (ABM attached to DMC S0 port)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_8",
                            "Monitor 8 (ABM attached to DMC S1 port)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_9",
                            "Monitor 9 (ABM attached to DMC S2 port)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_10",
                            "Monitor 10 (ABM attached to DMC S3 port)",
                            defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_11",
                            "Monitor 11 (CPM)",
                             defaultValue=False),
                        DTSLv1.booleanOption(
                            "mon_12",
                            "Monitor 12 (MPM)",
                            defaultValue=False)
                    ]),
                ]
            )
        ])

    @staticmethod
    def getOptionStopClockTabPage():
        return DTSLv1.tabPage("stopclock", "Stop Clock", childOptions=[
            DTSLv1.booleanOption(
                name='enable',
                displayName='Enable Stop clock debug configuration',
                defaultValue=False,
                isDynamic=True,
                childOptions=[
                    DTSLv1.stringOption(
                        name='scanDSTREAM',
                        displayName='JTAG Scan DSTREAM',
                        description='The DSTREAM unit connected to J76. '
                                    'Set this to DS to use the same DSTREAM '
                                    'Arm DS is using. Otherwise set it to the '
                                    'connection address of the other DSTREAM '
                                    'unit e.g. TCP:scandstream',
                        defaultValue="DS",
                        isDynamic=True
                    ),
                    DTSLv1.infoElement(
                        name='triggers',
                        displayName='Stop clock triggers',
                        description='These are the stop clock triggers i.e. '
                                    'the target events which cause stop clock '
                                    'mode to be triggered',
                        childOptions=[
                            DTSLv1.booleanOption(
                                name="manual",
                                displayName="Manual (NOW!)",
                                description='Take care with this option. As '
                                            'soon as this gets configured in '
                                            'the target it will enter stop '
                                            'mode and you will loose the '
                                            'debug connection! You are '
                                            'advised NOT to persist this '
                                            'setting enabled/checked.',
                                defaultValue=False,
                                isDynamic=True
                            ),
                            DTSLv1.booleanOption(
                                name="watchdog",
                                displayName="Watchdog timeout",
                                description='Trusted Watchdog or SCP Watchdog '
                                            'timeout',
                                defaultValue=False,
                                isDynamic=True
                            ),
                            DTSLv1.booleanOption(
                                name="cortex-a57_0",
                                displayName="Cortex-A57_0 enters debug state",
                                description='Debug state is entered when the '
                                            'core hits a breakpoint or when '
                                            'the use manually halts it',
                                defaultValue=False,
                                isDynamic=True
                            ),
                            DTSLv1.booleanOption(
                                name="cortex-a57_1",
                                displayName="Cortex-A57_1 enters debug state",
                                description='Debug state is entered when the '
                                            'core hits a breakpoint or when '
                                            'the use manually halts it',
                                defaultValue=False,
                                isDynamic=True
                            ),
                            DTSLv1.booleanOption(
                                name="cortex-a53_0",
                                displayName="Cortex-A53_0 enters debug state",
                                description='Debug state is entered when the '
                                            'core hits a breakpoint or when '
                                            'the use manually halts it',
                                defaultValue=False,
                                isDynamic=True
                            ),
                            DTSLv1.booleanOption(
                                name="cortex-a53_1",
                                displayName="Cortex-A53_1 enters debug state",
                                description='Debug state is entered when the '
                                            'core hits a breakpoint or when '
                                            'the use manually halts it',
                                defaultValue=False,
                                isDynamic=True
                            ),
                            DTSLv1.booleanOption(
                                name="cortex-a53_2",
                                displayName="Cortex-A53_2 enters debug state",
                                description='Debug state is entered when the '
                                            'core hits a breakpoint or when '
                                            'the use manually halts it',
                                defaultValue=False,
                                isDynamic=True
                            ),
                            DTSLv1.booleanOption(
                                name="cortex-a53_3",
                                displayName="Cortex-A53_3 enters debug state",
                                description='Debug state is entered when the '
                                            'core hits a breakpoint or when '
                                            'the use manually halts it',
                                defaultValue=False,
                                isDynamic=True
                            )
                        ]
                    )
                ]
            )
        ]
    )

    @staticmethod
    def getRAMOptions():
        return DTSLv1.tabPage("rams", "Cache RAMs", childOptions =[
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
                DtslScript.getOptionCortexA57TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCortexM3TabPage(),
                DtslScript.getOptionETRandETFTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionStopClockTabPage(),
                DtslScript.getOptionSystemProfilerTabPage(),
                DtslScript.getRAMOptions()
            ])
        ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        ''' Track which devices are managed by
            DTSL(all managed devices will be connected)'''
        self.mgdTraceDevs = {}
        self.mgdPlatformDevs = []

        ''' Only MEMAP devices are managed by default.
            Others will be added when enabling trace, SMP etc'''
        self.mgdPlatformDevs.append(self.axi)
        self.mgdPlatformDevs.append(self.apb)
        self.mgdPlatformDevs.append(self.AHB_M)
        self.mgdPlatformDevs.append(self.sysCtrl)

        ''' ensure core memory access '''
        for core in self.cortexA57cores:
            a57_rams.registerInternalRAMs(core)
        for core in self.cortexA53cores:
            a53_rams.registerInternalRAMs(core)
        cores = self.cortexA53cores + self.cortexA57cores + self.cortexM3cores
        for core in cores:
            self.registerFilters(core)
            self.addDeviceInterface(core)

        self.traceRangeIDs = {}

        ''' SMP and bigLITTLE '''
        self.setupCTISyncSMP()
        self.setupBigLittle()

        self.setManagedDeviceList(self.mgdPlatformDevs)

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+
    def discoverDevices(self):
        '''find and create devices'''
        # MEMAP devices...
        memAPDev = self.findDevice("CSMEMAP")
        self.axi = AXIAP(self, memAPDev, "AXIAP")
        memAPDev = self.findDevice("CSMEMAP", memAPDev + 1)
        self.apb = APBAP(self, memAPDev, "APBAP")
        memAPDev = self.findDevice("CSMEMAP", memAPDev + 1)
        self.AHB_M = CortexM_AHBAP(self, memAPDev, "AHBAP_M")

        self.sysCtrl = ConnectableDevice(self,
                                         self.findDevice("JunoSystemControl"),
                                         "JunoSystemControl")

        # The system CTI for TPIU, ETR, ETF, STM
        sysCTIDev = self.findDevice("CSCTI")
        self.sysCTI0 = CSCTI(self, sysCTIDev, "CTI_out")

        # The system CTI for profiler, generic counter, watchdog timer
        sysCTIDev = self.findDevice("CSCTI", sysCTIDev + 1)
        self.sysCTI1 = CSCTI(self, sysCTIDev, "CTI_sys")

        # map cores/ETMs to associated CTIs
        self.cortexA57ctiMap = {}
        self.cortexA53ctiMap = {}
        self.cortexM3ctiMap = {}

        self.ETMs = []
        self.A57ETMs = []
        self.A53ETMs = []
        self.CTIs = []

        ''' Calls to findDevice will start looking for the requested
            device from these indices'''
        etmDev = 0
        coreDev = 0
        ctiDev = sysCTIDev

        streamID = ATB_ID_BASE
        self.cortexA57cores = []

        for i in range(0, NUM_A57_CORES):
            # create core
            coreDev = self.findDevice("Cortex-A57", coreDev + 1)
            dev = ResetHookedA57Core(self, coreDev, "Cortex-A57_%d" % i)
            deviceInfo = DeviceInfo("core", "Cortex-A57")
            dev.setDeviceInfo(deviceInfo)
            self.cortexA57cores.append(dev)

            # create CTI for this core
            ctiDev = self.findDevice("CSCTI", ctiDev + 1)
            coreCTI = CSCTI(self, ctiDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)
            self.cortexA57ctiMap[dev] = coreCTI

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev + 1)
            etm = ETMv4TraceSource(self, etmDev, streamID,
                                   "ETM_%d_%d" % (i, streamID))
            etm.setEnabled(False)
            self.ETMs.append(etm)
            self.A57ETMs.append(etm)

            streamID += 2

        coreDev = 0
        self.cortexA53cores = []
        for i in range(0, NUM_A53_CORES):
            # create core
            coreDev = self.findDevice("Cortex-A53", coreDev + 1)
            dev = ResetHookedA53Core(self, coreDev, "Cortex-A53_%d" % i)
            deviceInfo = DeviceInfo("core", "Cortex-A53")
            dev.setDeviceInfo(deviceInfo)
            self.cortexA53cores.append(dev)

            # create CTI for this core
            ctiDev = self.findDevice("CSCTI", ctiDev + 1)
            coreCTI = CSCTI(self, ctiDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(coreCTI)
            self.cortexA53ctiMap[dev] = coreCTI

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev + 1)
            etm = ETMv4TraceSource(self, etmDev, streamID,
                                   "ETM_%d_%d" % (i, streamID))
            etm.setEnabled(False)
            self.ETMs.append(etm)
            self.A53ETMs.append(etm)

            streamID += 2

        coreDev = 0
        self.cortexM3cores = []
        for i in range(0, NUM_M3_CORES):
            # create CTI for this core
            ctiDev = self.findDevice("CSCTI", ctiDev + 1)
            ctiM3 = CSCTI(self, ctiDev, "CTI_%d_%d" % (i, streamID))
            self.CTIs.append(ctiM3)
            self.cortexM3ctiMap[dev] = ctiM3

            # create core
            coreDev = self.findDevice("Cortex-M3", coreDev + 1)
            dev = Device(self, coreDev, "Cortex-M3")
            deviceInfo = DeviceInfo("core", "Cortex-M3")
            dev.setDeviceInfo(deviceInfo)
            self.cortexM3cores.append(dev)

            # create the ETM for this core
            etmDev = self.findDevice("CSETM", etmDev + 1)
            etm = M3_ETM(self, etmDev, streamID, "ETM_%d_%d" % (i, streamID))
            etm.setEnabled(False)
            self.ETMs.append(etm)

            streamID += 2

        # TPIU
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = CSTPIU(self, tpiuDev, "TPIU")
        self.tpiu.setEnabled(False)

        # TMCs
        tmcDev = self.findDevice("CSTMC")
        self.ETF = CSTMC(self, tmcDev, "ETF")

        # Reserve this TMC for use as an ETR
        self.etrTmcDev = self.findDevice("CSTMC", tmcDev + 1)

        # Master output funnel
        funnelDev = self.findDevice("CSTFunnel")
        self.funnelMaster = self.createFunnel(funnelDev, "Funnel_master")

        #Master funnel enabled for all core trace as this is controlled via
        #cluster funnels
        self.funnelMaster.setPortEnabled(0)  # A57 trace.
        self.funnelMaster.setPortEnabled(1)  # A53 trace.
        self.funnelMaster.setPortEnabled(3)  # M3 trace.

        #Individual cluster funnels
        funnelDev = self.findDevice("CSTFunnel", funnelDev + 1)
        self.funnelA57 = self.createFunnel(funnelDev, "Funnel_A57")
        funnelDev = self.findDevice("CSTFunnel", funnelDev + 1)
        self.funnelA53 = self.createFunnel(funnelDev, "Funnel_A53")
        funnelDev = self.findDevice("CSTFunnel", funnelDev + 1)
        self.funnelM3 = self.createFunnel(funnelDev, "Funnel_M3")

        # create STM and ITM
        stmDev = self.findDevice("CSSTM")
        self.STM = STMTraceSource(self, stmDev, streamID, "STM")
        streamID += 2

        self.create_ITM()

        self.sysProf = SystemProfiler(self, self.axi, SYS_PROF_BASE,
                                      streamID, "SystemProfiler")

    def createDSTREAM(self):
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

    def createETR(self):
        self.ETR = ETRTraceCapture(self, self.etrTmcDev, "ETR")

    def createETFTrace(self):
        self.etfTrace = TMCETBTraceCapture(self, self.ETF, "ETF")

    def createFunnel(self, funnelDev, name):
        funnel = CSFunnel(self, funnelDev, name)
        funnel.setAllPortsDisabled()  # Will enable for each source later
        return funnel

    def create_ITM(self):
        itmDev = self.findDevice("CSITM")
        TSPrescale = 0
        DWTEn = 0
        SYNCEn = 1
        TSSEn = 1
        channelMask = 0xFFFFFFFF
        self.ITM = ITMTraceSource(self, itmDev, ITM_ATB_ID, "ITM", TSPrescale,
                                  DWTEn, SYNCEn, TSSEn, channelMask)

    def setupDSTREAMTrace(self, portWidth):
        '''Setup DSTREAM trace capture'''
        # configure the TPIU and DSTREAM for continuous trace
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        self.DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        self.setPortWidth(portWidth)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder(
                         [self.funnelA57, self.funnelA53, self.funnelM3,
                          self.funnelMaster, self.ETF, self.tpiu])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("DSTREAM",
                 [self.funnelMaster, self.funnelA57, self.funnelA53,
                  self.funnelM3, self.sysCTI0, self.tpiu,
                  self.DSTREAM, self.ETF])

    def setPortWidth(self, portWidth):
        self.tpiu.setPortSize(portWidth)
        self.DSTREAM.setPortWidth(portWidth)

    def setupETRTrace(self):
        self.ETR.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETR and register ETR with config
        self.ETR.setTraceComponentOrder([self.funnelM3, self.funnelA57,
                                         self.funnelA53, self.funnelMaster,
                                         self.ETF])
        self.addTraceCaptureInterface(self.ETR)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices("ETR", [self.funnelMaster, self.funnelA57,
                 self.funnelA53, self.funnelM3, self.sysCTI0, self.tpiu,
                 self.ETR, self.ETF])

    def setupETFTrace(self):
        self.etfTrace.setFormatterMode(FormatterMode.CONTINUOUS)

        # register other trace components with ETF and register ETF with config
        self.etfTrace.setTraceComponentOrder([self.funnelM3, self.funnelA57,
                          self.funnelA53, self.funnelMaster, self.ETF])
        self.addTraceCaptureInterface(self.etfTrace)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(
            "ETF", [self.funnelM3, self.funnelA57, self.funnelA53,
                    self.funnelMaster, self.sysCTI0, self.tpiu, self.etfTrace])

    def setupCTISyncSMP(self):
        # Cortex-A57 CTI SMP setup
        ctiInfo = {}
        for c in self.cortexA57cores:
            # use V8 Cortex event mapping : in/out on trigger 0 for stop,
            # out on trigger 1 for start
            ctiInfo[c] = CTISyncSMPDevice.DeviceCTIInfo(
                            self.cortexA57ctiMap[c],
                            CTISyncSMPDevice.DeviceCTIInfo.NONE, 1, 0, 0)

        smpA57 = CTISyncSMPDevice(self,
                                  "Cortex-A57 SMP",
                                  self.cortexA57cores,
                                  ctiInfo,
                                  CTM_CHAN_SYNC_START,
                                  CTM_CHAN_SYNC_STOP)
        self.registerFilters(smpA57)
        self.addDeviceInterface(smpA57)

        # Cortex-A53 CTI SMP setup
        ctiInfo = {}
        for c in self.cortexA53cores:
            # use V8 Cortex event mapping : in/out on trigger 0 for stop,
            #out on trigger 1 for start

            ctiInfo[c] = CTISyncSMPDevice.DeviceCTIInfo(
                            self.cortexA53ctiMap[c],
                            CTISyncSMPDevice.DeviceCTIInfo.NONE, 1, 0, 0)

        smpA53 = CTISyncSMPDevice(self,
                                  "Cortex-A53 SMP",
                                  self.cortexA53cores,
                                  ctiInfo,
                                  CTM_CHAN_SYNC_START,
                                  CTM_CHAN_SYNC_STOP)
        self.registerFilters(smpA53)
        self.addDeviceInterface(smpA53)

        # automatically handle connection to CTIs
        for c in self.CTIs:
            self.mgdPlatformDevs.append(c)

    def setupBigLittle(self):
        '''use V8 Cortex event mapping : in/out on trigger 0 for stop,
            out on trigger 1 for start'''
        ctiInf = {}
        for c in self.cortexA57cores:
            ctiInf[c] = CTISyncSMPDevice.DeviceCTIInfo(
                            self.cortexA57ctiMap[c],
                            CTISyncSMPDevice.DeviceCTIInfo.NONE,
                            1, 0, 0)
        for c in self.cortexA53cores:
            ctiInf[c] = CTISyncSMPDevice.DeviceCTIInfo(
                            self.cortexA53ctiMap[c],
                            CTISyncSMPDevice.DeviceCTIInfo.NONE,
                            1, 0, 0)

        big = DeviceCluster("big", self.cortexA57cores)
        LITTLE = DeviceCluster("LITTLE", self.cortexA53cores)
        bigLITTLE = CTISyncSMPDevice(
                        self, "big.LITTLE", [big, LITTLE], ctiInf,
                        CTM_CHAN_SYNC_START, CTM_CHAN_SYNC_STOP
                        )
        self.registerFilters(bigLITTLE)
        self.addDeviceInterface(bigLITTLE)

    # Trace Enable/Disable functions...
    def setTriggerGeneratesDBGRQ(self, xtm, state):
        pass  # Currently disabled until DTSL support is released.
        # xtm.setTriggerGeneratesDBGRQ(state)

    def setTimestampingEnabled(self, xtm, state):
        xtm.setTimestampingEnabled(state)

    def setContextIDEnabled(self, xtm, state):
        if state == False:
            xtm.setContextIDs(False,
                              IARMCoreTraceSource.ContextIDSize.NONE)
        else:
            xtm.setContextIDs(True,
                              IARMCoreTraceSource.ContextIDSize.BITS_31_0)

    def setSTMEnabled(self, enabled):
        self.setTraceSourceEnabled(self.STM, enabled)

    def setITMEnabled(self, enabled):
        self.setTraceSourceEnabled(self.ITM, enabled)

    def setTraceSourceEnabled(self, source, enabled):
        source.setEnabled(enabled)
        self.enableFunnelPortForSource(source, enabled)
        self.enableCTIsForSource(source, enabled)

    def setTraceCaptureMethod(self, method):
        self.traceCaptureMethod = method
        if method == "none":
            self.ETF.setMode(CSTMC.Mode.ETF)
            self.setDSTREAMTraceEnabled(False)
            self.setETRTraceEnabled(False)
            self.setETFTraceEnabled(False)
        elif method in ["DSTREAM", "DSTREAM_PT_Store_and_Forward", "DSTREAM_PT_StreamingTrace"]:
            self.ETF.setMode(CSTMC.Mode.ETF)
            self.setETRTraceEnabled(False)
            self.setETFTraceEnabled(False)
            self.setDSTREAMTraceEnabled(True)
        elif method == "ETR":
            self.ETF.setMode(CSTMC.Mode.ETF)
            self.setDSTREAMTraceEnabled(False)
            self.setETRTraceEnabled(True)
            self.setETFTraceEnabled(False)
        elif method == "ETF":
            self.ETF.setMode(CSTMC.Mode.ETB)
            self.setDSTREAMTraceEnabled(False)
            self.setETFTraceEnabled(True)
            self.setETRTraceEnabled(False)

    def setDSTREAMTraceEnabled(self, enabled):
        '''Enable/disable DSTREAM trace capture'''
        self.dstreamTraceEnabled = enabled
        self.tpiu.setEnabled(enabled)
        self.enableCTIsForSink("TPIU", enabled)

    def setETRTraceEnabled(self, enabled):
        '''Enable/disable ETR trace capture'''
        self.etrTraceEnabled = enabled
        if enabled:
            # ensure TPIU is disabled
            self.tpiu.setEnabled(False)
        self.enableCTIsForSink("ETR", enabled)

    def setETFTraceEnabled(self, enabled):
        '''Enable/disable ETF trace capture'''
        self.etfTraceEnabled = enabled
        if enabled:
            # ensure TPIU is disabled
            self.tpiu.setEnabled(False)
        self.enableCTIsForSink("etfTrace", enabled)

    def enableCTIsForSink(self, sink, enabled):
        '''Enable/disable triggers using CTI associated with sink'''
        cti, output, channel = self.getCTIForSink(sink)
        if cti:
            if enabled:
                cti.enableOutputEvent(output, channel)
            else:
                cti.disableOutputEvent(output, channel)

    def enableCTIsForSource(self, source, enabled):
        '''Enable/disable triggers using CTI associated with source'''
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            if enabled:
                cti.enableInputEvent(input, channel)
            else:
                cti.disableInputEvent(input, channel)

    def getCTIForSink(self, sink):
        '''Get the CTI and input/channel associated with a trace sink
            TPIU trigger is CTITRIGOUT[3]
            ETR  trigger is CTITRIGOUT[1]
            ETF  trigger is CTITRIGOUT[7]'''
        if sink == "TPIU":
            return (self.sysCTI0, 3, CTM_CHAN_TRACE_TRIGGER)
        elif sink == "ETR":
            return (self.sysCTI0, 1, CTM_CHAN_TRACE_TRIGGER)
        elif sink == "etfTrace":
            return (self.sysCTI0, 7, CTM_CHAN_TRACE_TRIGGER)
        return (None, None, None)  # no associated CTI

    def getCTIForSource(self, source):
        '''Get the CTI and input/channel associated with a source.
            Return (None, None, None) if no associated CTI'''
        if source in self.ETMs:
            coreNum = self.ETMs.index(source)
            # ETM trigger is on input 6
            if coreNum < len(self.CTIs):
                return (self.CTIs[coreNum], 6, CTM_CHAN_TRACE_TRIGGER)
        return (None, None, None)  # no associated CTI

    def enableFunnelPortForSource(self, source, enabled):
        '''Enable/disable the funnel port for a trace source'''
        port = self.getFunnelPortForSource(source)
        funnel = self.getFunnelForSource(source)
        if enabled:
            funnel.setPortEnabled(port)
        else:
            funnel.setPortDisabled(port)

    ''' Cores 0 and 1 (A57s) are on the A57 funnel ports 0 & 1
        Cores 2, 3, 4 & 5 (A53s) are on the A53 funnel ports 0, 1, 2 & 3
        Core 6 (M3) is on M3 funnel port 0'''
    def getFunnelPortForCore(self, core):
        ''' Funnel port-to-core mapping can be customized here'''
        port = core
        if core >= NUM_A57_CORES:
            port = core - NUM_A57_CORES
        if core >= (NUM_A57_CORES + NUM_A53_CORES):
            port = (core - (NUM_A57_CORES + NUM_A53_CORES)) + 1
        return port

    def getFunnelForSource(self, source):
        funnelMap = {self.STM: self.funnelMaster}
        funnelMap[self.ITM] = self.funnelM3
        funnelMap[self.sysProf] = self.funnelMaster
        totalCores = NUM_A53_CORES + NUM_A57_CORES + NUM_M3_CORES
        for i in range(0, totalCores):
            funnel = self.funnelA57
            if i >= NUM_A57_CORES:
                funnel = self.funnelA53
            if i >= (NUM_A53_CORES + NUM_A57_CORES):
                funnel = self.funnelM3
            funnelMap[self.ETMs[i]] = funnel
        return funnelMap.get(source, None)

    def getFunnelPortForSource(self, source):
        '''Get the funnel port number for a trace source'''
        # Build map of sources to funnel ports
        portMap = {self.STM: STM_FUNNEL_PORT}
        portMap[self.ITM] = ITM_FUNNEL_PORT
        portMap[self.sysProf] = SYS_PROFILER_FUNNEL_PORT
        for i in range(0, NUM_A57_CORES + NUM_A53_CORES + NUM_M3_CORES):
            portMap[self.ETMs[i]] = self.getFunnelPortForCore(i)
        return portMap.get(source, None)

    def getManagedDevices(self, traceKey):
        '''Get the required list of managed devices for this configuration'''
        deviceList = self.mgdPlatformDevs[:]
        for d in self.mgdTraceDevs.get(traceKey, []):
            if d not in deviceList:
                deviceList.append(d)

        return deviceList

    def addManagedTraceDevices(self, traceKey, devs):
        '''Add devices to the set of devices managed by
            the configuration for this trace mode'''
        traceDevs = self.mgdTraceDevs.get(traceKey)
        if not traceDevs:
            traceDevs = set()
            self.mgdTraceDevs[traceKey] = traceDevs
        for d in devs:
            traceDevs.add(d)

    def registerTraceSource(self, traceCapture, source):
        '''Register trace source with trace capture device'''
        traceCapture.addTraceSource(source)
        self.addManagedTraceDevices(traceCapture.getName(), [source])

    def registerTraceSources(self, traceCapture):
        '''Register all trace sources with trace capture device'''
        for coreIndex in range(0, NUM_A57_CORES):
            if self.ETMs[coreIndex].isEnabled():
                self.registerCoreTraceSource(traceCapture,
                                             self.cortexA57cores[coreIndex],
                                             self.ETMs[coreIndex])

        for coreIndex in range(0, NUM_A53_CORES):
            etmIndex = NUM_A57_CORES + coreIndex
            if self.ETMs[etmIndex].isEnabled():
                self.registerCoreTraceSource(traceCapture,
                                             self.cortexA53cores[coreIndex],
                                             self.ETMs[etmIndex])

        for coreIndex in range(0, NUM_M3_CORES):
            etmIndex = NUM_A57_CORES + NUM_A53_CORES + coreIndex
            if self.ETMs[etmIndex].isEnabled():
                self.registerCoreTraceSource(traceCapture,
                                             self.cortexM3cores[coreIndex],
                                             self.ETMs[etmIndex])

        self.registerTraceSource(traceCapture, self.ITM)
        self.registerTraceSource(traceCapture, self.STM)
        self.registerTraceSource(traceCapture, self.sysProf)

    def registerCoreTraceSource(self, traceCapture, core, source):
        '''Register a trace source with capture device and enable triggers'''
        # Register with trace capture, associating with core
        traceCapture.addTraceSource(source, core.getID())

        # source is managed by the configuration
        self.addManagedTraceDevices(traceCapture.getName(), [source])

        # CTI (if present) is also managed by the configuration
        cti, input, channel = self.getCTIForSource(source)
        if cti:
            self.addManagedTraceDevices(traceCapture.getName(), [cti])

    def registerFilters(self, core):
        '''Add a wrapper around a core to allow access to AHB and APB
            via the DAP'''
        core.registerAddressFilters(
            [AXIMemAPAccessor("AXI", self.axi, "AXI bus accessed via AP0", 64),
             AxBMemAPAccessor("APB", self.apb, "APB bus accessed via AP1"),
             AHBCortexMMemAPAccessor("AHB", self.AHB_M,
                                     "Cortex-M AHB bus accessed via AP0")])

    def setupStopClockTriggers(self, obase):
        '''Installs the stop clock triggers for single chain debug mode.
            When one of the triggers fires it will sets the DFT Bist JTAG port
            into single chain debug mode which allows the flop chains to be
            scanned out. If the triggerSources[] has TRIG_MANUAL set, this will
            cause an immediate entry into stop clock mode.
            NOTE: The DFT Bist JTAG port is _not_ the DAP debug JTAG port
        Params:
            obase the option path string to our options
        '''
        if self.getOptionValue(obase):
            assert isinstance(self.AHB_M, CortexM_AHBAP)
            # Read the existing register value
            cfgreg = self.AHB_M.readMem(SCC_APB_BASE +
                                        SCC_APB_SCAN_DEBUG_CTRL_REG)
            # Clear the master enable
            cfgreg = cfgreg & ~SCDBG_MASTER_EN
            # Now inspect each source and if found enabled we enable the
            # source and set the master enable
            triggerBase = obase + ".triggers"
            if self.getOptionValue(triggerBase + ".manual"):
                cfgreg = cfgreg | (SCDBG_MASTER_EN |
                         SCDBG_TRIG_MANUAL | SCDBG_TRIGGER)
                # Note: There is no point in an else: clause here because if
                # the SCDBG_TRIG_MANUAL bit was set previously the system would
                # already be halted!
            if self.getOptionValue(triggerBase + ".watchdog"):
                cfgreg = cfgreg | (SCDBG_MASTER_EN |
                                   SCDBG_TRIG_WDOG)
            else:
                cfgreg = cfgreg & ~SCDBG_TRIG_WDOG
            if self.getOptionValue(triggerBase + ".cortex-a57_0"):
                cfgreg = cfgreg | (SCDBG_MASTER_EN |
                                   SCDBG_TRIG_DBGACK_ATL0)
            else:
                cfgreg = cfgreg & ~SCDBG_TRIG_DBGACK_ATL0
            if self.getOptionValue(triggerBase + ".cortex-a57_1"):
                cfgreg = cfgreg | (SCDBG_MASTER_EN |
                                   SCDBG_TRIG_DBGACK_ATL1)
            else:
                cfgreg = cfgreg & ~SCDBG_TRIG_DBGACK_ATL1
            if self.getOptionValue(triggerBase + ".cortex-a53_0"):
                cfgreg = cfgreg | (SCDBG_MASTER_EN |
                                   SCDBG_TRIG_DBGACK_APL0)
            else:
                cfgreg = cfgreg & ~SCDBG_TRIG_DBGACK_APL0
            if self.getOptionValue(triggerBase + ".cortex-a53_1"):
                cfgreg = cfgreg | (SCDBG_MASTER_EN |
                                   SCDBG_TRIG_DBGACK_APL1)
            else:
                cfgreg = cfgreg & ~SCDBG_TRIG_DBGACK_APL1
            if self.getOptionValue(triggerBase + ".cortex-a53_2"):
                cfgreg = cfgreg | (SCDBG_MASTER_EN |
                                   SCDBG_TRIG_DBGACK_APL2)
            else:
                cfgreg = cfgreg & ~SCDBG_TRIG_DBGACK_APL2
            if self.getOptionValue(triggerBase + ".cortex-a53_3"):
                cfgreg = cfgreg | (SCDBG_MASTER_EN |
                                   SCDBG_TRIG_DBGACK_APL3)
            else:
                cfgreg = cfgreg & ~SCDBG_TRIG_DBGACK_APL3
            try:
                self.AHB_M.writeMem(SCC_APB_BASE + SCC_APB_SCAN_DEBUG_CTRL_REG,
                                    False,  # Do not attempt to verify write!
                                    cfgreg)
            except DTSLException:
                # We ignore a write failure because if TRIG_MANUAL was
                # specified, the write will be reported as failing
                pass
            # NOTE: If TRIG_MANUAL was enabled the DAP is now dead

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+
    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are
            changed.
            This will be called:
                *after construction but before device connection
                *during a debug session should the user change the DTSL options
        '''
        obase = "options"
        if not self.isConnected():
            self.setInitialOptions(obase)
        self.updateDynamicOptions(obase)



    def setInitialOptions(self, obase):
        '''Takes the configuration options and configures the
            DTSL objects prior to target connection
        Param: obase the option path string to top level options
        '''

        ''' Setup whichever trace capture device was selected (if any) '''
        if self.dstreamTraceEnabled:
            self.createDSTREAM()
            self.setupDSTREAMTrace(DSTREAM_PORTWIDTH)
        elif self.etrTraceEnabled:
            self.createETR()
            self.setupETRTrace()
        elif self.etfTraceEnabled:
            self.createETFTrace()
            self.setupETFTrace()

        obase = "options.cortexA57.cortexA57coreTrace"
        coreTraceEnabled = self.getOptionValue(obase)
        for i in range(0, NUM_A57_CORES):
            traceThisCore = self.getOptionValue(obase + ".Cortex_A57_%d" % i)
            enableSource = coreTraceEnabled and traceThisCore
            self.setTraceSourceEnabled(self.ETMs[i], enableSource)
            self.setInternalTraceRange(self.ETMs[i], "cortexA57")
            val = self.getOptionValue(obase + ".triggerhalt")
            self.setTriggerGeneratesDBGRQ(self.ETMs[i], val)
            val = self.getOptionValue(obase + ".timestamp")
            self.setTimestampingEnabled(self.ETMs[i], val)
            val = self.getOptionValue(obase + ".contextIDs")
            self.setContextIDEnabled(self.ETMs[i], val)

        obase = "options.cortexA53.cortexA53coreTrace"
        coreTraceEnabled = self.getOptionValue(obase)
        for i in range(0, NUM_A53_CORES):
            traceThisCore = self.getOptionValue(obase + ".Cortex_A53_%d" % i)
            curIndex = i + NUM_A57_CORES
            enableSource = coreTraceEnabled and traceThisCore
            self.setTraceSourceEnabled(self.ETMs[curIndex], enableSource)
            self.setInternalTraceRange(self.ETMs[curIndex], "cortexA53")
            val = self.getOptionValue(obase + ".triggerhalt")
            self.setTriggerGeneratesDBGRQ(self.ETMs[curIndex], val)
            val = self.getOptionValue(obase + ".timestamp")
            self.setTimestampingEnabled(self.ETMs[curIndex], val)
            val = self.getOptionValue(obase + ".contextIDs")
            self.setContextIDEnabled(self.ETMs[curIndex], val)

        obase = "options.cortexM3.cortexM3coreTrace"
        coreTraceEnabled = self.getOptionValue(obase)
        for i in range(0, NUM_M3_CORES):
            traceThisCore = self.getOptionValue(obase + ".Cortex_M3_%d" % i)
            curIndex = i + NUM_A57_CORES + NUM_A53_CORES
            enableSource = coreTraceEnabled and traceThisCore
            self.setTraceSourceEnabled(self.ETMs[curIndex], enableSource)
            val = self.getOptionValue(obase + ".timestamp")
            self.setTimestampingEnabled(self.ETMs[curIndex], val)
            val = self.getOptionValue(obase + ".freq")
            self.ETMs[curIndex].setTimestampFrequency(val)

        # Set up the ETR buffer
        if self.etrTraceEnabled:
            obase = "options.ETR.etrBuffer"
            configureETRBuffer = self.getOptionValue(obase)
            if configureETRBuffer:
                scatterGatherMode = self.getOptionValue(obase + ".scatterGather")
                bufferStart = self.getOptionValue(obase + ".start")
                bufferSize = self.getOptionValue(obase + ".size")
                self.ETR.setBaseAddress(bufferStart)
                self.ETR.setTraceBufferSize(bufferSize)
                self.ETR.setScatterGatherModeEnabled(scatterGatherMode)

        # register trace sources
        if self.etrTraceEnabled:
            self.registerTraceSources(self.ETR)
        elif self.dstreamTraceEnabled:
            self.registerTraceSources(self.DSTREAM)
        elif self.etfTraceEnabled:
            self.registerTraceSources(self.etfTrace)

        traceMode = self.getOptionValue("options.traceBuffer.traceCapture")
        self.setManagedDeviceList(self.getManagedDevices(traceMode))

        if self.dstreamTraceEnabled:
            dstream_opts = "options.traceBuffer.traceCapture." + self.getDstreamOptionString() + "."

            portWidthOpt = self.getOptions().getOption(dstream_opts + "tpiuPortWidth")
            if portWidthOpt:
               portWidth = self.getOptionValue(dstream_opts + "tpiuPortWidth")
               self.setPortWidth(int(portWidth))

            traceBufferSizeOpt = self.getOptions().getOption(dstream_opts + "traceBufferSize")
            if traceBufferSizeOpt:
                traceBufferSize = self.getOptionValue(dstream_opts + "traceBufferSize")
                self.setTraceBufferSize(traceBufferSize)

        # System Profiler config
        obase = "options.profiler.enable"
        optVal = self.getOptionValue(obase + ".config.win")
        self.sysProf.setWindowTimerEnabled(optVal)
        optVal = self.getOptionValue(obase + ".config.win.duration")
        self.sysProf.setWindowDuration(optVal)
        optVal = self.getOptionValue(obase + ".monitors.secure")
        self.sysProf.setCountSecure(optVal)

        sp_monitors = 0
        for monitor in range(13):
            option = "options.profiler.enable.monitors.mon_%d" % monitor
            selected = self.getOptionValue(option)
            if selected:
                sp_monitors |= (1 << monitor)
        self.sysProf.setMonitors(sp_monitors)
        self.setTraceSourceEnabled(self.sysProf, self.getOptionValue(obase))

    def getDstreamOptionString(self):
        return "dstream"

    def updateDynamicOptions(self, obase):
        '''Takes any changes to the dynamic options and
            applies them. Note that some trace options may
            not take effect until trace is (re)started
        Param: obase the option path string to top level options
        '''
        stopClockOBase = obase + '.stopclock.enable'
        self.setupStopClockTriggers(stopClockOBase)

        for i in range(0, NUM_A57_CORES):
            a57_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA57cores[i])
            a57_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA57cores[i])
        for i in range(0, NUM_A53_CORES):
            a53_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA53cores[i])
            a53_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA53cores[i])


    def setInternalTraceRange(self, coreTM, coreName):
        obase = "options.%s.%scoreTrace.traceRange" % (coreName, coreName)
        traceRangeEnable = self.getOptionValue(obase)
        traceRangeStart = self.getOptionValue(obase + ".start")
        traceRangeEnd = self.getOptionValue(obase + ".end")

        if coreTM in self.traceRangeIDs:
            coreTM.clearTraceRange(self.traceRangeIDs[coreTM])
            if traceRangeEnable:
                self.traceRangeIDs[coreTM] = coreTM.addTraceRange(
                                                        traceRangeStart,
                                                        traceRangeEnd)
            else:
                del self.traceRangeIDs[coreTM]

    def postConnect(self):
        self.powerUpClusters()
        DTSLv1.postConnect(self)
        self.enableTimeStamper(self.AHB_M, TIMESTAMP_BASE)
        # Ensure that the sys CTI is configured to halt the cores on ETR/ETF
        # full if needed
        self.setHaltOnEtfEtrFull(self.getOptionValue("options.ETR.syncBuffer"))
        obase = "options"
        # Setup any stop clock support
        stopClockOBase = obase + '.stopclock.enable'
        self.setupStopClockTriggers(stopClockOBase)

        # Set the fixed timestamp frequency value so that timestamp decode works
        tsInfo = TimestampInfo(50000000)
        self.setTimestampInfo(tsInfo)

    def traceStart(self, traceCapture):
        DTSLv1.traceStart(self, traceCapture)
        # set up the System Profiler
        if self.getOptionValue("options.profiler.enable"):
            self.sysProf.traceStart(None)
            self.funnelMaster.setPortEnabled(SYS_PROFILER_FUNNEL_PORT)

    def setHaltOnEtfEtrFull(self, halt):
        '''configure sysCTI halting behaviour when on-chip trace is full...'''
        ETF_FULL = 0
        ETR_FULL = 2

        if self.sysCTI0.isConnected():
            if halt:
                self.sysCTI0.writeRegister(CTICTRL, 1)
                self.sysCTI0.writeRegister(CTIINEN + ETR_FULL,
                                           1 << CTM_CHAN_SYNC_STOP)
                self.sysCTI0.writeRegister(CTIINEN + ETF_FULL,
                                           1 << CTM_CHAN_SYNC_STOP)
            else:
                self.sysCTI0.writeRegister(CTIINEN + ETR_FULL, 0)
                self.sysCTI0.writeRegister(CTIINEN + ETF_FULL, 0)

    def enableTimeStamper(self, memap, config_reg_address):
        # Enable the global timestamper
        buffer = zeros(4, 'b')
        memap.readMem(config_reg_address, 4, buffer)
        value = unpack('<I', buffer)[0]
        value &= 0xFFFFF000
        value |= 0x00000001

        memap.memWrite(0x4300, config_reg_address, RDDI_ACC_SIZE.RDDI_ACC_DEF,
                       0x320, False, 4, pack('<I', value))

    def getA57ETMs(self):
        return self.A57ETMs

    def getA53ETMs(self):
        return self.A53ETMs

    def reset(self, device):
        self.preTraceStop(None)
        if self.etfTraceEnabled:
            self.etfTrace.stop()
        elif self.etrTraceEnabled:
            self.ETR.stop()
        elif self.dstreamTraceEnabled:
            self.DSTREAM.stop()
        Device.systemReset(device, 0);
        self.powerUpClusters()
        DTSLv1.postConnect(self)

    def powerUpClusters(self):
        dapDev  = self.findDevice("ARMCS-DP", 1)
        dapDev  = self.findDevice("ARMCS-DP", dapDev +1)
        dapM3 = CSDAP(self, dapDev, "DAP_M3")
        self.powerUpDap(dapM3);
        dapM3.writeMem(0, 0x44020300, 0x10)
        dapM3.writeMem(0, 0x44020320, 0x10)
        dapM3.writeMem(0, 0x44020080, 0x10)
        dapM3.writeMem(0, 0x44020180, 0x10)
        dapM3.closeConn()

    def powerUpDap(self, dap):
        DP_OFFSET = 0x2080;
        DP_CTRL_STAT   = DP_OFFSET + 1

        if not dap.isConnected():
            dap.openConn(None,None,None)

        value = dap.readRegister(DP_CTRL_STAT)

        if not (value & 0x20000000):
            value |= 0x50000000
            dap.writeRegister(DP_CTRL_STAT, value)

            for i in range(100):
                value = dap.readRegister(DP_CTRL_STAT)
                if (value & 0x20000000):
                    break
                # DAP powered

class DtslScript_DSTREAM_ST_Family(DtslScript):

    def setupDSTREAMTrace(self, portWidth):
        # configure the TPIU and DSTREAM for continuous trace
        self.tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        self.setPortWidth(portWidth)

        # register other trace components
        self.DSTREAM.setTraceComponentOrder(
                         [self.funnelA57, self.funnelA53, self.funnelM3,
                          self.funnelMaster, self.ETF, self.tpiu])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(self.DSTREAM)
        self.addStreamTraceCaptureInterface(self.DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.addManagedTraceDevices(self.getOptionValue("options.traceBuffer.traceCapture"),
                 [self.funnelMaster, self.funnelA57, self.funnelA53,
                  self.funnelM3, self.sysCTI0, self.tpiu,
                  self.DSTREAM, self.ETF])

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

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_ST.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA57TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCortexM3TabPage(),
                DtslScript.getOptionETRandETFTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionStopClockTabPage(),
                DtslScript.getOptionSystemProfilerTabPage(),
                DtslScript.getRAMOptions()
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
                                ("ETR", "System Memory Trace Buffer (ETR)"),
                                ("ETF", "On Chip Trace Buffer (ETF)"),
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

class DtslScript_DSTREAM_PT(DtslScript_DSTREAM_ST_Family):

    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=[
                DtslScript_DSTREAM_PT.getOptionTraceBufferTabPage(),
                DtslScript.getOptionCortexA57TabPage(),
                DtslScript.getOptionCortexA53TabPage(),
                DtslScript.getOptionCortexM3TabPage(),
                DtslScript.getOptionETRandETFTabPage(),
                DtslScript.getOptionSTMTabPage(),
                DtslScript.getOptionStopClockTabPage(),
                DtslScript.getOptionSystemProfilerTabPage(),
                DtslScript.getRAMOptions()
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
                                ("ETR", "System Memory Trace Buffer (ETR)"),
                                ("ETF", "On Chip Trace Buffer (ETF)"),
                                DtslScript_DSTREAM_PT.getStoreAndForwardOptions(),
                                DtslScript_DSTREAM_PT.getStreamingTraceOptions()],
                        setter=DtslScript.setTraceCaptureMethod)
        ])

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
        if self.getOptionValue("options.traceBuffer.traceCapture") == "DSTREAM_PT_Store_and_Forward":
            return "dpt_storeandforward"
        if self.getOptionValue("options.traceBuffer.traceCapture") == "DSTREAM_PT_StreamingTrace":
            return "dpt_streamingtrace"

    def createDSTREAM(self):
        if self.getOptionValue("options.traceBuffer.traceCapture") == "DSTREAM_PT_Store_and_Forward":
            self.DSTREAM = DSTREAMPTStoreAndForwardTraceCapture(self, "DSTREAM_PT_Store_and_Forward")
        elif self.getOptionValue("options.traceBuffer.traceCapture") == "DSTREAM_PT_StreamingTrace":
            self.DSTREAM = DSTREAMPTLiveStoredStreamingTraceCapture(self, "DSTREAM_PT_StreamingTrace")

