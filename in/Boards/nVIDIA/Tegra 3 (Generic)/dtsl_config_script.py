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

def getFunnelPort(core):
    # select port for desired core
    port = -1
    if core == 3:
        # core 3 isn't on port 3, but on port 4!
        port = 4
    else:
        # otherwise core n is on port n
        port = core
    return port

class DTSLConfigurationFunctions(DTSLv1):

    def createCTIsWithSeparateTraceCTI(self):
        self.ctis = []
        self.ctiMap = {}
        outCTIDev = self.createOutCTI()
        coreCTIDev = outCTIDev
        for i in range(0, len(self.coreDevices)):
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev + 1)
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            coreCTI.enableInputEvent(0, 0) # use channel 0 for sync stop
            coreCTI.enableInputEvent(6, 2) # use channel 2 for macrocell trigger
            coreCTI.enableOutputEvent(0, 0)
            coreCTI.enableOutputEvent(7, 1) # use channel 1 for sync start
            self.ctis.append(coreCTI)
            coreDev = self.coreDevices[i]
            self.ctiMap[coreDev] = coreCTI

    def createCores(self, coreType, numberOfCores):
        self.coreIndexList = []
        self.coreDevices = []
        coreDev = 0
        for i in range (0, numberOfCores):
            coreDev = self.findDevice(coreType, coreDev + 1)
            self.coreIndexList.append(coreDev)
            self.coreDevices.append(Device(self, coreDev, "%s_%d" % (coreType, i)))

    def createDSTREAM(self, pw):
        if (hasattr(self, 'traceSources')) != True:
            self.traceSources = []
        self.DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        self.DSTREAM.setTraceMode(self.dstreamMode)
        self.DSTREAM.setPortWidth(pw)
        self.traceSources.append(self.DSTREAM)
        self.addTraceCaptureInterface(self.DSTREAM)
        self.DSTREAM.setTraceComponentOrder(self.traceComponentOrder)

    def createDisabledTPIU(self):
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = CSTPIU(self, tpiuDev, "TPIU")
        self.tpiu.setEnabled(False)
        self.traceSources = [ self.tpiu ]


    def createEnabledTPIU(self, pw):
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = CSTPIU(self, tpiuDev, "TPIU")
        self.tpiu.setEnabled(True)
        self.tpiu.setFormatterMode(self.formatterMode)
        self.tpiu.setPortSize(pw)
        self.traceSources = [ self.tpiu ]
        self.traceComponentOrder = [ self.tpiu ]

    def createEtb(self):
        if (hasattr(self, 'traceSources')) != True:
            self.traceSources = []
        if (hasattr(self, 'traceComponentOrder')) != True:
            self.traceComponentOrder = []
        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(self.formatterMode)
        self.traceSources.append(self.ETB)
        self.addTraceCaptureInterface(self.ETB)
        self.ETB.setTraceComponentOrder(self.traceComponentOrder)

    def createOutCTI(self):
        outCTIDev = self.findDevice("CSCTI")
        outCTI = CSCTI(self, outCTIDev, "CTI_out")
        if (hasattr(self, 'ETB')) == True:
            outCTI.enableOutputEvent(1, 2) # ETB trigger input is CTI out 1
        else:
            if (hasattr(self, 'DSTREAM')) == True:
                outCTI.enableOutputEvent(3, 2) # TPIU trigger input is CTI out 3
        self.ctis = [ outCTI ]
        return outCTIDev

    def createPTM(self, sink, ptmToUse):
        self.macrocells = []
        if ptmToUse >= len(self.coreIndexList):
            ptms = ptmToUse + 1
        else:
            ptms = len(self.coreIndexList)

        ptmDev = 1
        for i in range(0, ptms):
            ptmDev = self.findDevice("CSPTM", ptmDev + 1)
            if (ptmToUse == ALL_CORES) or (i == ptmToUse):
                PTM = PTMTraceSource(self, ptmDev, i + 1,"PTM%d" % i)
                self.macrocells.append(PTM)
                if ptmToUse == ALL_CORES:
                    sink.addTraceSource(PTM, self.coreIndexList[i])
                else:
                    sink.addTraceSource(PTM, self.coreIndexList[0])

        self.traceSources = self.macrocells + self.traceSources


    def createSingleCore(self, coreType, desiredCoreIndex):
        coreDev = 0
        for i in range (0, desiredCoreIndex + 1):
            coreDev = self.findDevice(coreType, coreDev + 1)
            if i == desiredCoreIndex:
                self.coreIndexList = [ coreDev ]
                self.coreDevices = [ Device(self, coreDev,"%s_%d" % (coreType, i)) ]

    def createSingleFunnel(self, portToOpen):
        if (hasattr(self, 'traceComponentOrder')) != True:
            self.traceComponentOrder = []
        funnelDev = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev, "Funnel")
        funnel.setAllPortsDisabled()
        if (portToOpen == -1):
            for i in range(0, len(self.coreDevices)):
                funnel.setPortEnabled(getFunnelPort(i))
        else:
            funnel.setPortEnabled(getFunnelPort(portToOpen))

        self.traceSources.append(funnel)
        self.traceComponentOrder = [ funnel ] + self.traceComponentOrder

    def determineFormatterMode(self):
        self.formatterMode = FormatterMode.CONTINUOUS
        self.dstreamMode = DSTREAMTraceCapture.TraceMode.Continuous


class Cortex_A9_0_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 0
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTM(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources)

class Cortex_A9_0_DSTREAM(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 0
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(coreIndex)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTM(self.DSTREAM, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources + self.ctis)

class Cortex_A9_1_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 1
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTM(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources)

class Cortex_A9_1_DSTREAM(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 1
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(coreIndex)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTM(self.DSTREAM, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources + self.ctis)

class Cortex_A9_2_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 2
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTM(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources)

class Cortex_A9_2_DSTREAM(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 2
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(coreIndex)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTM(self.DSTREAM, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources + self.ctis)

class Cortex_A9_3_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 3
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(coreIndex)
        self.createEtb()
        self.createPTM(self.ETB, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources)

class Cortex_A9_3_DSTREAM(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 3
        self.createSingleCore("Cortex-A9", coreIndex)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(coreIndex)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTM(self.DSTREAM, coreIndex)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources + self.ctis)

class Cortex_A9_SMP(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 4)
        self.addDeviceInterface(RDDISyncSMPDevice(self, "Cortex-A9_SMP", 1, self.coreDevices))

class Cortex_A9_SMP_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 4)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(ALL_CORES)
        self.createEtb()
        self.createPTM(self.ETB, ALL_CORES)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources)
        self.addDeviceInterface(RDDISyncSMPDevice(self, "Cortex-A9_SMP_ETB", 1, self.coreDevices))

class Cortex_A9_SMP_DSTREAM(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 4)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(ALL_CORES)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTM(self.DSTREAM, ALL_CORES)
        self.createOutCTI()
        self.setManagedDevices(self.traceSources + self.ctis)
        self.addDeviceInterface(RDDISyncSMPDevice(self, "Cortex-A9_SMP_DSTREAM", 1, self.coreDevices))

class Cortex_A9_CTI_SYNC_SMP(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 4)
        self.createCTIsWithSeparateTraceCTI()
        self.setManagedDevices(self.ctis)
        self.addDeviceInterface(CTISyncSMPDevice(self, "Cortex-A9_CTI_SYNC_SMP", 1, self.coreDevices, self.ctiMap, 1, 0))

class Cortex_A9_CTI_SYNC_SMP_ETB(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 4)
        self.determineFormatterMode()
        self.createDisabledTPIU()
        self.createSingleFunnel(ALL_CORES)
        self.createEtb()
        self.createPTM(self.ETB, ALL_CORES)
        self.createCTIsWithSeparateTraceCTI()
        self.setManagedDevices(self.traceSources + self.ctis)
        self.addDeviceInterface(CTISyncSMPDevice(self, "Cortex-A9_CTI_SYNC_SMP_ETB", 1, self.coreDevices, self.ctiMap, 1, 0))

class Cortex_A9_CTI_SYNC_SMP_DSTREAM(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        self.createCores("Cortex-A9", 4)
        self.determineFormatterMode()
        self.createEnabledTPIU(DEFAULT_PORT_SIZE)
        self.createSingleFunnel(ALL_CORES)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createPTM(self.DSTREAM, ALL_CORES)
        self.createCTIsWithSeparateTraceCTI()
        self.setManagedDevices(self.traceSources + self.ctis)
        self.addDeviceInterface(CTISyncSMPDevice(self, "Cortex-A9_CTI_SYNC_SMP_DSTREAM", 1, self.coreDevices, self.ctiMap, 1, 0))

class Cortex_A9_0_ETB_KernelOnly(Cortex_A9_0_ETB):
    def __init__(self, root):
        Cortex_A9_0_ETB.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_0_DSTREAM_KernelOnly(Cortex_A9_0_DSTREAM):
    def __init__(self, root):
        Cortex_A9_0_DSTREAM.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_1_ETB_KernelOnly(Cortex_A9_1_ETB):
    def __init__(self, root):
        Cortex_A9_1_ETB.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_1_DSTREAM_KernelOnly(Cortex_A9_1_DSTREAM):
    def __init__(self, root):
        Cortex_A9_1_DSTREAM.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_2_ETB_KernelOnly(Cortex_A9_2_ETB):
    def __init__(self, root):
        Cortex_A9_2_ETB.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_2_DSTREAM_KernelOnly(Cortex_A9_2_DSTREAM):
    def __init__(self, root):
        Cortex_A9_2_DSTREAM.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_3_ETB_KernelOnly(Cortex_A9_3_ETB):
    def __init__(self, root):
        Cortex_A9_3_ETB.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_3_DSTREAM_KernelOnly(Cortex_A9_3_DSTREAM):
    def __init__(self, root):
        Cortex_A9_3_DSTREAM.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_SMP_ETB_KernelOnly(Cortex_A9_SMP_ETB):
    def __init__(self, root):
        Cortex_A9_SMP_ETB.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_SMP_DSTREAM_KernelOnly(Cortex_A9_SMP_DSTREAM):
    def __init__(self, root):
        Cortex_A9_SMP_DSTREAM.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_CTI_SYNC_SMP_ETB_KernelOnly(Cortex_A9_CTI_SYNC_SMP_ETB):
    def __init__(self, root):
        Cortex_A9_CTI_SYNC_SMP_ETB.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

class Cortex_A9_CTI_SYNC_SMP_DSTREAM_KernelOnly(Cortex_A9_CTI_SYNC_SMP_DSTREAM):
    def __init__(self, root):
        Cortex_A9_CTI_SYNC_SMP_DSTREAM.__init__(self, root)
        for macrocell in self.macrocells:
            macrocell.addTraceRange(KERNEL_RANGE_START, KERNEL_RANGE_END)

