from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import RDDISyncSMPDevice
from com.arm.debug.dtsl.configurations import DTSLv1

ALL_CORES = -1
DEFAULT_PORT_SIZE = 16
KERNEL_RANGE_END = 0xFFFFFFFF
KERNEL_RANGE_START = 0x7F000000

class DTSLConfigurationFunctions(DTSLv1):
    def createCTIsWithSeparateTraceCTI(self):
        """
        This function creates all CTIs, including a CTI for ETB/TPIU.
        The first CTI is assumed to be used for ETB/TPIU, the rest are assumed to be associated with
        the cores in a linear fassion. This function might need adjustments
        in order to better match the hardware setup.
        """
        self.ctis = []
        self.ctiMap = {}
        outCTIDev = self.createOutCTI()
        coreCTIDev = outCTIDev
        for i in range(0, len(self.coreDevices)):
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev + 1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            coreCTI.enableInputEvent(0, 0) # use channel 0 for sync stop
            coreCTI.enableInputEvent(6, 2) # use channel 2 for ETM/PTM trigger
            coreCTI.enableOutputEvent(0, 0)
            coreCTI.enableOutputEvent(7, 1) # use channel 1 for sync start
            self.ctis.append(coreCTI)
            coreDev = self.coreDevices[i]
            self.ctiMap[coreDev] = coreCTI

    def createCores(self, coreType, numberOfCores):
        """
        Creates two lists: one containing the core indexes, the other - the core Device objects.
        Those will be used by other functions that set up the current activity.
        """
        self.coreIndexList = []
        self.coreDevices = []
        coreDev = 0
        for i in range (0, numberOfCores):
            coreDev = self.findDevice(coreType, coreDev + 1)
            self.coreIndexList.append(coreDev)
            self.coreDevices.append(Device(self, coreDev, "%s_%d" % (coreType, i)))

    def createDSTREAM(self, pw):
        """
        Creates and sets up the DSTREAM for DSTREAM trace.
        """
        if (hasattr(self, 'mgdDevices')) != True:
            self.mgdDevices = []
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        self.DSTREAM.setTraceMode(self.dstreamMode)
        self.DSTREAM.setPortWidth(pw)
        self.mgdDevices.append(self.DSTREAM)
        self.addTraceCaptureInterface(self.DSTREAM)
        self.DSTREAM.setTraceComponentOrder(self.traceComponentOrder)

    def createDisabledTPIU(self):
        """
        Disables the TPIU to allow ETB to run at full rate.
        """
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = CSTPIU(self, tpiuDev, "TPIU")
        self.tpiu.setEnabled(False)
        self.mgdDevices = [ self.tpiu ]


    def createEnabledTPIU(self, pw):
        """
        Creates a TPIU and configures it for DSTREAM trace.
        """
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = CSTPIU(self, tpiuDev, "TPIU")
        self.tpiu.setEnabled(True)
        self.tpiu.setFormatterMode(self.formatterMode)
        self.tpiu.setPortSize(pw)
        self.mgdDevices = [ self.tpiu ]
        self.traceComponentOrder = [ self.tpiu ]

    def createEtb(self):
        """
        Creates and sets up the ETB for ETB trace.
        """
        if (hasattr(self, 'mgdDevices')) != True:
            self.mgdDevices = []
        if (hasattr(self, 'traceComponentOrder')) != True:
            self.traceComponentOrder = []
        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(self.formatterMode)
        self.mgdDevices.append(self.ETB)
        self.addTraceCaptureInterface(self.ETB)
        self.ETB.setTraceComponentOrder(self.traceComponentOrder)

    def createOutCTI(self):
        """
        This function creates the cross trigger CTI for ETB/TPIU.
        This function might need adjustments
        in order to better match the hardware setup.
        """
        outCTIDev = self.findDevice("CSCTI")
        outCTI = CSCTI(self, outCTIDev, "CTI_out")
        if (hasattr(self, 'ETB')) == True:
            outCTI.enableOutputEvent(1, 2) # ETB trigger input is CTI out 1
        else:
            if (hasattr(self, 'DSTREAM')) == True:
                outCTI.enableOutputEvent(3, 2) # TPIU trigger input is CTI out 3
        self.ctis = [ outCTI ]
        return outCTIDev

    def createPTMs(self, sink, ptmToUse):
        """
        This function creates all the PTMs or a
        specific PTM. It assumes linear mapping
        between the cores and the PTMs. This function might need adjustments
        in order to better match the hardware setup.
        """
        self.traceSources = []
        if ptmToUse >= len(self.coreIndexList):
            ptms = ptmToUse + 1
        else:
            ptms = len(self.coreIndexList)

        ptmDev = 1
        for i in range(0, ptms):
            ptmDev = self.findDevice("CSPTM", ptmDev + 1)
            if (ptmToUse == ALL_CORES) or (i == ptmToUse):
                PTM = PTMTraceSource(self, ptmDev, i + 1,"PTM%d" % i)
                self.traceSources.append(PTM)
                if ptmToUse == ALL_CORES:
                    sink.addTraceSource(PTM, self.coreIndexList[i])
                else:
                    sink.addTraceSource(PTM, self.coreIndexList[0])

        self.mgdDevices = self.traceSources + self.mgdDevices


    def createSingleCore(self, coreType, desiredCoreIndex):
        """
        Creates two lists: one containing the core index, the other - the core Device object.
        Those will be used by other functions that set up the current activity.
        """
        coreDev = 0
        for i in range (0, desiredCoreIndex + 1):
            coreDev = self.findDevice(coreType, coreDev + 1)
            if i == desiredCoreIndex:
                self.coreIndexList = [ coreDev ]
                self.coreDevices = [ Device(self, coreDev,"%s_%d" % (coreType, i)) ]

    def createSingleFunnel(self, portToOpen):
        """
        Creates and sets up a single funnel, assuming linear mapping between
        the ETMs/PTMs and the funnel ports. This function might need adjustments
        in order to better match the hardware setup.
        """
        if (hasattr(self, 'traceComponentOrder')) != True:
            self.traceComponentOrder = []
        funnelDev = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev, "Funnel")
        funnel.setAllPortsDisabled()
        if (portToOpen == -1):
            for i in range(0, len(self.coreDevices)): # opens all ports
                funnel.setPortEnabled(self.getFunnelPort(i))
        else:
            funnel.setPortEnabled(self.getFunnelPort(portToOpen))  # opens a specific port

        self.mgdDevices.append(funnel)
        self.traceComponentOrder = [ funnel ] + self.traceComponentOrder

    def determineFormatterMode(self):
        # Configures the TPIU for continuous mode.
        self.formatterMode = FormatterMode.CONTINUOUS

        # Configures the DSTREAM for continuous trace
        self.dstreamMode = DSTREAMTraceCapture.TraceMode.Continuous

    def getFunnelPort(self, core):
        return core # can be changed in case the order of the funnel ports
                    # does not correspond to the order of the cores


class Cortex_A9_0_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 0
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTMs(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

    def postReset(self):
        call_some_function_which_doesnt_exist()

class Cortex_A9_1_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 1
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTMs(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)

class Cortex_A9_CTI_SYNC_SMP(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 2)
        self.createCTIsWithSeparateTraceCTI()
        self.setManagedDevices(self.ctis)
        self.addDeviceInterface(CTISyncSMPDevice(self, "Cortex-A9_CTI_SYNC_SMP", 1, self.coreDevices, self.ctiMap, 1, 0))

class Cortex_A9_CTI_SYNC_SMP_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 2)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(ALL_CORES)
        self.createEtb()
        self.createPTMs(self.ETB, ALL_CORES)
        self.createCTIsWithSeparateTraceCTI()
        self.setManagedDevices(self.mgdDevices + self.ctis)
        self.addDeviceInterface(CTISyncSMPDevice(self, "Cortex-A9_CTI_SYNC_SMP_ETB", 1, self.coreDevices, self.ctiMap, 1, 0))

class Cortex_A9_0_ETB_KernelOnly(Cortex_A9_0_ETB):
    def __init__(self, root):
        Cortex_A9_0_ETB.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_1_ETB_KernelOnly(Cortex_A9_1_ETB):
    def __init__(self, root):
        Cortex_A9_1_ETB.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_CTI_SYNC_SMP_ETB_KernelOnly(Cortex_A9_CTI_SYNC_SMP_ETB):
    def __init__(self, root):
        Cortex_A9_CTI_SYNC_SMP_ETB.__init__(self, root)
        for traceSource in self.traceSources:
            traceSource.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

