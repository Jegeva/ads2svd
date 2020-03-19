from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import ITMTraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import FormatterMode

class SwitchableETM(ETMv3_3TraceSource):
    procSel = 0

    def getControlRegValue(self):
        crVal = ETMv3_3TraceSource.getControlRegValue(self)
        crVal |= (self.procSel & 0x7) << 25
        return crVal

    def postConnect(self):
        ETMv3_3TraceSource.postConnect(self)

        # switch the selected PTM using procedure documented in PTM arch spec

        ETMCR = 0
        ETMCR_POWER_DOWN = (1 << 0)

        #  base class has left us in programming mode
        crVal = self.readRegister(ETMCR)

        #  Set ETMCR bit [0], PowerDown, to b1. - power down to sync to new core
        crVal |= ETMCR_POWER_DOWN
        self.writeRegister(ETMCR, crVal)

        #  Change ETMCR processor select
        crVal |= (self.procSel & 0x7) << 25
        self.writeRegister(ETMCR, crVal)

        #  Clear ETMCR bit [0], PowerDown, to b0. - power up again
        crVal &= ~ETMCR_POWER_DOWN
        self.writeRegister(ETMCR, crVal)



class CortexR5Board(DTSLv1):
    def __init__(self, root, cores):
        """
        Constructor which creates the self.core_associations_map[]
        """
        DTSLv1.__init__(self, root)
        self.core_list = cores
        self.trace_sources = []

    def create_funnel(self):
        """
        Create the funnel device and set all ports disabled
        """
        funnelDev = self.findDevice("CSTFunnel")
        self.funnel = CSFunnel(self, funnelDev, "Funnel")
        self.funnel.setAllPortsDisabled()
        self.trace_sources = self.trace_sources + [ self.funnel ]

    def create_disabled_TPIU(self):
        """
        Create a disabled TPIU
        """
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = CSTPIU(self, tpiuDev, "TPIU")
        self.tpiu.setEnabled(False)
        self.trace_sources = self.trace_sources + [ self.tpiu ]

    def create_enabled_TPIU(self, pw, mode):
        """
        Create enabled TPIU with given port width
        """
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = CSTPIU(self, tpiuDev, "TPIU")
        self.tpiu.setEnabled(True)
        self.tpiu.setFormatterMode(mode)
        self.tpiu.setPortSize(pw)
        self.trace_sources = self.trace_sources + [ self.tpiu ]

    def create_ETB(self, formatter_mode):
        """
        Create ETB and set its formatter mode
        """
        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(formatter_mode)
        self.trace_sources = self.trace_sources + [ self.ETB ]


    def create_ETM(self, coreDev, sink, coreNum):
        """
        Creates self.ETM components
        """
        etmDev = self.findDevice("CSETM")

        self.ETM = SwitchableETM(self, etmDev, 1, "ETM")
        self.ETM.procSel = coreNum
        sink.addTraceSource(self.ETM, coreDev)
        self.trace_sources = self.trace_sources + [ self.ETM ]

    #
    # May need customizing for different targets
    #
    def get_ETM_funnel_port(self, coreNo):
        """
        Find the funnel port assigned to a ETM trace source
        for the passed coreNo
        """
        return 0

    def get_funnel_port_list_for_core_list(self, core_list):
        """
        Returns a list of funnel port IDs, one for each coreNo within
        the passed core_list
        """
        port_list=[]
        for coreNo in core_list:
            port_list.append(self.get_ETM_funnel_port(coreNo))
        return port_list

    def enable_funnel_ports_for_core_list(self, core_list):
        """
        Enables the funnel ports for each coreNo contained within
        the passed core_list
        """
        self.enable_funnel_ports(self.get_funnel_port_list_for_core_list(core_list))

    def enable_funnel_ports(self, port_list):
        """
        Enable the funnel ports contained within the passed port_list
        """
        for port in port_list:
            self.funnel.setPortEnabled(port)

    def determine_formatter_mode(self, core_list):
        """
        Decide the appropriate formatter and trace modes for the core list
        """
        if (len(core_list) > 1):
            self.formatter_mode = FormatterMode.CONTINUOUS
            self.dstream_mode = DSTREAMTraceCapture.TraceMode.Continuous
        else:
            self.formatter_mode = FormatterMode.BYPASS
            self.dstream_mode = DSTREAMTraceCapture.TraceMode.Raw

    def setup_for_ETM_ETB_trace(self, coreNum):
        """
        Sets up the trace components to generate trace for each of the
        coreNo within self.core_list into the ETB.
        """
        #
        # Create ETB component in the requested mode
        #
        self.determine_formatter_mode(self.core_list)
        coreDev = self.findDevice("Cortex-R5")

        # skip through list to desired core
        for i in range(0, coreNum):
            coreDev = self.findDevice("Cortex-R5", coreDev+1)

        self.create_ETB(self.formatter_mode)

        # Create the funnel component
        self.create_funnel()
        self.enable_funnel_ports_for_core_list(self.core_list)
        self.ETB.setTraceComponentOrder([ self.funnel ])

        #
        # create TPIU and disable to allow ETB to work at full rate
        #
        self.create_disabled_TPIU()
        #
        # Create ETM component for the core
        #
        self.create_ETM(coreDev, self.ETB, coreNum)
        #
        # Tell DTSL about the created trace component
        #
        self.addTraceCaptureInterface(self.ETB)
        #
        # automatically handle connection/disconnection & trace start/stop
        #
        self.setManagedDevices( self.trace_sources )

    def setup_for_DSTREAM_trace(self, pw, coreNum):
        """
        Sets up the trace components to generate trace for each of the
        coreNo within self.core_list to DSTREAM
        """

        #
        # Create and configure the DSTREAM component
        #
        self.determine_formatter_mode(self.core_list)
        coreDev = self.findDevice("Cortex-R5")

        # skip through list to desired core
        for i in range(0, coreNum):
            coreDev = self.findDevice("Cortex-R5", coreDev+1)

        DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")

        DSTREAM.setTraceMode(self.dstream_mode)
        DSTREAM.setPortWidth(pw)

        # Create the funnel component (must be created before any attempt
        # to enable funnel ports)
        #
        self.create_funnel()

        #
        # create TPIU, setup with desired port width and formatter mode
        #
        self.create_enabled_TPIU(pw, self.formatter_mode)
        #
        # Create ETM component for the core and enable its path
        # through the funnel
        #
        self.create_ETM(coreDev, DSTREAM, coreNum)
        self.enable_funnel_ports_for_core_list(self.core_list)

        # Tell DTSL about the created trace component
        DSTREAM.setTraceComponentOrder([ self.funnel, self.tpiu ])
        self.addTraceCaptureInterface(DSTREAM)

        #
        # automatically handle connection/disconnection & trace start/stop
        #
        self.setManagedDevices( self.trace_sources + [DSTREAM] )

class Cortex_R5_Data_Trace(CortexR5Board):
    @staticmethod
    def getOptionList():
        return [ DTSLv1.booleanOption('data', 'Data Trace',
                 description='Enable trace of data accesses', defaultValue=False,
                 setter=Cortex_R5_Data_Trace.setDataTraceEnabled,
                 childOptions = [
                    DTSLv1.booleanOption('addresses', 'Addresses',
                        description='Enable trace of data access addresses', defaultValue=True,
                        setter=Cortex_R5_Data_Trace.setDataAddressTraceEnabled),

                    DTSLv1.booleanOption('values', 'Values',
                        description='Enable trace of data access values', defaultValue=True,
                        setter=Cortex_R5_Data_Trace.setDataValueTraceEnabled),

                    DTSLv1.booleanOption('dataOnly', 'Enable data-only trace mode',
                        description='Enable data-only trace',
                        defaultValue = False,
                        setter=Cortex_R5_Data_Trace.setDataOnlyEnabled)
                    ]

                 )]

    def __init__(self, root, cores):
        CortexR5Board.__init__(self, root, cores)


    def setDataTraceEnabled(self, enable):
        self.ETM.setDataTraceEnabled(enable)

    def setDataAddressTraceEnabled(self, enable):
        self.ETM.setDataAddressTraceEnabled(enable)

    def setDataValueTraceEnabled(self, enable):
        self.ETM.setDataValueTraceEnabled(enable)

    def setDataOnlyEnabled(self, enable):
        self.ETM.setDataOnly(enable)

class Cortex_R5_0_ETB(Cortex_R5_Data_Trace):
    def __init__(self, root):
        core = 0
        Cortex_R5_Data_Trace.__init__(self, root, [core])
        self.setup_for_ETM_ETB_trace(core)

class Cortex_R5_0_ETB_KernelOnly(Cortex_R5_Data_Trace):
    def __init__(self, root):
        core = 0
        Cortex_R5_Data_Trace.__init__(self, root, [core])
        self.setup_for_ETM_ETB_trace(core)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)

class Cortex_R5_0_DSTREAM(Cortex_R5_Data_Trace):
    def __init__(self, root):
        # populate the core list for a single core system
        core = 0
        Cortex_R5_Data_Trace.__init__(self, root, [core])
        self.setup_for_DSTREAM_trace(16,core) # portwidth 16

class Cortex_R5_0_DSTREAM_KernelOnly(Cortex_R5_Data_Trace):
    def __init__(self, root):
        # populate the core list for a single core system
        core = 0
        Cortex_R5_Data_Trace.__init__(self, root, [core])
        self.setup_for_DSTREAM_trace(16,core)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)

class Cortex_R5_1_ETB(Cortex_R5_Data_Trace):
    def __init__(self, root):
        core = 1
        Cortex_R5_Data_Trace.__init__(self, root, [core])
        self.setup_for_ETM_ETB_trace(core)

class Cortex_R5_1_ETB_KernelOnly(Cortex_R5_Data_Trace):
    def __init__(self, root):
        core = 1
        Cortex_R5_Data_Trace.__init__(self, root, [core])
        self.setup_for_ETM_ETB_trace(core)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)

class Cortex_R5_1_DSTREAM(Cortex_R5_Data_Trace):
    def __init__(self, root):
        # populate the core list for a single core system
        core = 1
        Cortex_R5_Data_Trace.__init__(self, root, [core])
        self.setup_for_DSTREAM_trace(16,core) # portwidth 16

class Cortex_R5_1_DSTREAM_KernelOnly(Cortex_R5_Data_Trace):
    def __init__(self, root):
        # populate the core list for a single core system
        core = 1
        Cortex_R5_Data_Trace.__init__(self, root, [core])
        self.setup_for_DSTREAM_trace(16,core)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)
