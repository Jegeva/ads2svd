from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import SimpleSyncSMPDevice
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture

class blazemdp_SingleCoreETB(DTSLv1):
    def __init__(self, root, coreNo):
        DTSLv1.__init__(self, root)

        self.core = coreNo

        # disable the TPIU to allow ETB to work at full rate
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(False)

        # Enable port for self.core on the funnel.  PTM 0,1
        # are on funnel port 0, 1 respectively.
        funnelDev0 = self.findDevice("CSTFunnel")
        funnel0 = CSFunnel(self, funnelDev0, "Funnel_0")
        funnel0.setAllPortsDisabled()
        funnel0.setPortEnabled(self.core)

        # There's another funnel before the ETB.  Port 0
        # comes from the A9 subsystem. (Other port is an STM).
        funnelDev1 = self.findDevice("CSTFunnel", funnelDev0+1)
        funnel1 = CSFunnel(self, funnelDev1, "Funnel_1")
        funnel1.setAllPortsDisabled()
        funnel1.setPortEnabled(0)

        # find first core/PTM
        coreDev = self.findDevice("Cortex-A9")
        ptmDev = self.findDevice("CSPTM")

        # skip through list to desired core/PTM
        for i in range(0, coreNo):
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)

        self.PTM = PTMTraceSource(self, ptmDev, 1, "PTM")
        self.addDeviceInterface(Device(self, coreDev, "Cortex-A9_%d" % coreNo))

        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(FormatterMode.BYPASS)
        self.ETB.addTraceSource(self.PTM, coreDev)
        self.ETB.setTraceComponentOrder([ funnel1, funnel0 ])
        self.addTraceCaptureInterface(self.ETB)

        self.setManagedDevices([ self.PTM, funnel0, tpiu, funnel1, self.ETB ])

class blazemdp_A9_0_ETB(blazemdp_SingleCoreETB):
    def __init__(self, root):
        blazemdp_SingleCoreETB.__init__(self, root, 0)

class blazemdp_A9_1_ETB(blazemdp_SingleCoreETB):
    def __init__(self, root):
        blazemdp_SingleCoreETB.__init__(self, root, 1)

class blazemdp_A9_0_ETB_KernelOnly(blazemdp_SingleCoreETB):
    def __init__(self, root):
        blazemdp_SingleCoreETB.__init__(self, root, 0)
        self.PTM.addTraceRange(0xC0000000,0xFFFFFFFF)

class blazemdp_A9_1_ETB_KernelOnly(blazemdp_SingleCoreETB):
    def __init__(self, root):
        blazemdp_SingleCoreETB.__init__(self, root, 1)
        self.PTM.addTraceRange(0xC0000000,0xFFFFFFFF)

#
# DSTREAM trace is waiting on a suitable connector.
# All of these blazemdp_.*DSTREAM.* configurations are untested.
#
class blazemdp_SingleCoreDSTREAM(DTSLv1):
    def __init__(self, root, coreNo):
        DTSLv1.__init__(self, root)

        self.core = coreNo

        # configure the TPIU for continuous mode, 16 bit
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(True)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        tpiu.setPortSize(16)

        # Enable port for self.core on the funnel.  PTM 0,1
        # are on funnel port 0, 1 respectively.
        funnelDev0 = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev0, "Funnel_0")
        funnel.setAllPortsDisabled()
        funnel.setPortEnabled(self.core)

        # find first core/PTM
        coreDev = self.findDevice("Cortex-A9")
        ptmDev = self.findDevice("CSPTM")

        # skip through list to desired core/PTM
        for i in range(0, coreNo):
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)

        self.addDeviceInterface(Device(self, coreDev, "Cortex-A9_%d" % coreNo))
        self.PTM = PTMTraceSource(self, ptmDev, 1, "PTM")

        # configure the DSTREAM for 16 bit continuous trace
        DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        DSTREAM.setPortWidth(16)

        # register the trace source with the DSTREAM
        DSTREAM.addTraceSource(self.PTM, coreDev)

        # register other trace components
        DSTREAM.setTraceComponentOrder([ funnel, tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(DSTREAM)

        # automatically handle connection/disconnection
        self.setManagedDevices([ self.PTM, funnel, tpiu, DSTREAM ])

class blazemdp_A9_0_DSTREAM(blazemdp_SingleCoreDSTREAM):
    def __init__(self, root):
        blazemdp_SingleCoreDSTREAM.__init__(self, root, 0)

class blazemdp_A9_1_DSTREAM(blazemdp_SingleCoreDSTREAM):
    def __init__(self, root):
        blazemdp_SingleCoreDSTREAM.__init__(self, root, 1)

class blazemdp_A9_0_DSTREAM_KernelOnly(blazemdp_SingleCoreDSTREAM):
    def __init__(self, root):
        blazemdp_SingleCoreDSTREAM.__init__(self, root, 0)
        self.PTM.addTraceRange(0xC0000000,0xFFFFFFFF)

class blazemdp_A9_1_DSTREAM_KernelOnly(blazemdp_SingleCoreDSTREAM):
    def __init__(self, root):
        blazemdp_SingleCoreDSTREAM.__init__(self, root, 1)
        self.PTM.addTraceRange(0xC0000000,0xFFFFFFFF)

class blaze_SMP(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # find each core
        coreDev = 1
        self.coreDevices= []
        for i in range(0, 2):
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            self.coreDevices.append(Device(self, coreDev, "Cortex-A9_%d" % i))
        self.addDeviceInterface(SimpleSyncSMPDevice(self, "blaze SMP",1,self.coreDevices))

class blaze_SMP_ETB(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # disable the TPIU to allow ETB to work at full rate
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(False)

        # enable ports for each core on the funnel
        funnelDev0 = self.findDevice("CSTFunnel")
        funnel0 = CSFunnel(self, funnelDev0, "Funnel")
        funnel0.setAllPortsDisabled()

        # There's another funnel before the ETB.  Port 0
        # comes from the A9 subsystem. (Other port is an STM).
        funnelDev1 = self.findDevice("CSTFunnel", funnelDev0+1)
        funnel1 = CSFunnel(self, funnelDev1, "Funnel_1")
        funnel1.setAllPortsDisabled()
        funnel1.setPortEnabled(0)

        # Create ETB and put into CONTINUOUS mode
        etbDev = self.findDevice("CSETB")
        ETB = ETBTraceCapture(self, etbDev, "ETB")
        ETB.setFormatterMode(FormatterMode.CONTINUOUS)

        # find each core/PTM and enable trace
        coreDev = 1
        ptmDev = 1
        coreDevices= []
        self.PTMs = []
        for i in range(0, 2):
            # find the next core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)

            # create the PTM for this core
            streamID = i+1
            PTM = PTMTraceSource(self, ptmDev, streamID, "PTM%d" % i)
            self.PTMs.append(PTM)

            # enable the funnel for this core
            funnel0.setPortEnabled(i)

            # register trace source with ETB
            ETB.addTraceSource(PTM, coreDev)

            # create Device representation for the core
            coreDevices.append(Device(self, coreDev, "Cortex-A9_%d" % i))

        # register other trace components with ETB and register ETB with configuration
        ETB.setTraceComponentOrder([ funnel1, funnel0 ])
        self.addTraceCaptureInterface(ETB)

        # automatically handle connection/disconnection to trace components
        self.setManagedDevices(self.PTMs + [ funnel0, tpiu, funnel1, ETB ])

        # create SMP device and expose from configuration
        self.addDeviceInterface(SimpleSyncSMPDevice(self, "blaze SMP", 1, coreDevices))

class blaze_SMP_ETB_KernelOnly(blaze_SMP_ETB):
    def __init__(self, root):
        blaze_SMP_ETB.__init__(self, root)
        for ptm in self.PTMs:
            ptm.addTraceRange(0xC0000000,0xFFFFFFFF)


class blaze_SMP_DSTREAM(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # configure the TPIU for continuous mode, 16 bit
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(True)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        tpiu.setPortSize(16)

        # enable ports for each core on the funnel
        funnelDev0 = self.findDevice("CSTFunnel")
        funnel0 = CSFunnel(self, funnelDev0, "Funnel")
        funnel0.setAllPortsDisabled()

        # There's another funnel before the TPIU.  Port 0
        # comes from the A9 subsystem. (Other port is an STM).
        funnelDev1 = self.findDevice("CSTFunnel", funnelDev0+1)
        funnel1 = CSFunnel(self, funnelDev1, "Funnel_1")
        funnel1.setAllPortsDisabled()
        funnel1.setPortEnabled(0)

        # configure the DSTREAM for 16 bit continuous trace
        DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        DSTREAM.setPortWidth(16)

        # find each core/PTM and enable trace
        coreDev = 1
        ptmDev = 1
        coreDevices= []
        self.PTMs = []
        for i in range(0, 2):
            # find the next core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)

            # create the PTM for this core
            streamID = i+1
            PTM = PTMTraceSource(self, ptmDev, streamID, "PTM%d" % i)
            self.PTMs.append(PTM)

            # enable the funnel for this core
            funnel0.setPortEnabled(i)

            # register trace source with DSTREAM
            DSTREAM.addTraceSource(PTM, coreDev)

            # create Device representation for the core
            coreDevices.append(Device(self, coreDev, "Cortex-A9_%d" % i))

        # register other trace components with DSTREAM and register DSTREAM with configuration
        DSTREAM.setTraceComponentOrder([ tpiu, funnel1, funnel0 ])
        self.addTraceCaptureInterface(DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.setManagedDevices(self.PTMs + [ funnel0, tpiu, funnel1, DSTREAM ])

        # create SMP device and expose from configuration
        self.addDeviceInterface(SimpleSyncSMPDevice(self, "blaze SMP", 1, coreDevices))





