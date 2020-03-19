from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import RDDISyncSMPDevice


class Samsung_Exynos_4210_SingleCoreETB(DTSLv1):
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

        # find first core/PTM
        coreDev = self.findDevice("Cortex-A9")
        ptmDev = self.findDevice("CSPTM")

        # skip through list to desired core/PTM
        for i in range(0, coreNo):
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)

        # Create the PTM and device interfaces
        self.PTM = PTMTraceSource(self, ptmDev, 1, "PTM")
        self.addDeviceInterface(Device(self, coreDev, "Cortex-A9_%d" % coreNo))

        # Create the ETB trace capture
        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(FormatterMode.BYPASS)
        self.ETB.addTraceSource(self.PTM, coreDev)
        self.ETB.setTraceComponentOrder([ funnel0 ])
        self.addTraceCaptureInterface(self.ETB)

        self.setManagedDevices([ self.PTM, funnel0, tpiu, self.ETB ])



class Samsung_Exynos_4210_A9_0_ETB(Samsung_Exynos_4210_SingleCoreETB):
    def __init__(self, root):
        Samsung_Exynos_4210_SingleCoreETB.__init__(self, root, 0)


class Samsung_Exynos_4210_A9_1_ETB(Samsung_Exynos_4210_SingleCoreETB):
    def __init__(self, root):
        Samsung_Exynos_4210_SingleCoreETB.__init__(self, root, 1)


class Samsung_Exynos_4210_A9_0_ETB_KernelOnly(Samsung_Exynos_4210_SingleCoreETB):
    def __init__(self, root):
        Samsung_Exynos_4210_SingleCoreETB.__init__(self, root, 0)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)


class Samsung_Exynos_4210_A9_1_ETB_KernelOnly(Samsung_Exynos_4210_SingleCoreETB):
    def __init__(self, root):
        Samsung_Exynos_4210_SingleCoreETB.__init__(self, root, 1)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)



class Samsung_Exynos_4210_SMP(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)
        # find each core and build list of Devices
        coreDev = 1
        coreDevices= []
        for i in range(0, 2):
            # create Device representation for the core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            coreDevices.append(Device(self, coreDev, "Cortex-A9_%d" % i))
        # create SMP device and expose from configuration
        self.addDeviceInterface(RDDISyncSMPDevice(self, "Exynos SMP", 1, coreDevices))



class Samsung_Exynos_4210_SMP_ETB(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # disable the TPIU to allow ETB to work at full rate
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(False)

        funnelDev0 = self.findDevice("CSTFunnel")
        funnel0 = CSFunnel(self, funnelDev0, "Funnel")
        funnel0.setAllPortsDisabled()

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
        ETB.setTraceComponentOrder([ funnel0 ])
        self.addTraceCaptureInterface(ETB)

        # automatically handle connection/disconnection to trace components
        self.setManagedDevices(self.PTMs + [ funnel0, tpiu, ETB ])

        # create SMP device and expose from configuration
        self.addDeviceInterface(RDDISyncSMPDevice(self, "Exynos SMP", 1, coreDevices))

class Samsung_Exynos_4210_SMP_ETB_KernelOnly(Samsung_Exynos_4210_SMP_ETB):
    def __init__(self, root):
        Samsung_Exynos_4210_SMP_ETB.__init__(self, root)
        for ptm in self.PTMs:
            ptm.addTraceRange(0xBF000000,0xFFFFFFFF)

