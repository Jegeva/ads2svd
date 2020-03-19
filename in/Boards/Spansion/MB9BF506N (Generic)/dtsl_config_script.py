from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import ETMv3_4TraceSource
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import V7M_CSTPIU
from com.arm.debug.dtsl.components import AHBCortexMMemAPAccessor
from com.arm.debug.dtsl.components import CortexM_AHBAP
from com.arm.debug.dtsl.configurations import DTSLv1

ALL_CORES = -1
DEFAULT_PORT_SIZE = 4

class DTSLConfigurationFunctions(DTSLv1):
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
        self.mgdDevices.append(self.AHB)
        self.addTraceCaptureInterface(self.DSTREAM)
        self.DSTREAM.setTraceComponentOrder(self.traceComponentOrder)

    def createMClassETMsv3_4(self, sink, etmToUse):
        """
        This function creates all the ETMs or a
        specific ETM. It assumes linear mapping
        between the cores and the ETMs. This function might need adjustments
        in order to better match the hardware setup.
        """
        self.traceSources = []
        if etmToUse >= len(self.coreIndexList):
            etms = etmToUse + 1
        else:
            etms = len(self.coreIndexList)

        etmDev = 1
        for i in range(0, etms):
            etmDev = self.findDevice("CSETM", etmDev + 1)
            if (etmToUse == ALL_CORES) or (i == etmToUse):
                ETM = Cortex_M_ETM(self, etmDev, i + 1,"ETM%d" % i)
                self.traceSources.append(ETM)
                if etmToUse == ALL_CORES:
                    sink.addTraceSource(ETM, self.coreIndexList[i])
                else:
                    sink.addTraceSource(ETM, self.coreIndexList[0])

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
                coreDevice = Device(self, coreDev,"%s_%d" % (coreType, i))
                self.coreDevices = [ coreDevice ]
                coreDevice.registerAddressFilter(AHBCortexMMemAPAccessor("AHB", self.AHB, "AHB bus accessed via AP_0"))
                self.addDeviceInterface(coreDevice)

    def createMemAccessor(self):
        # MEMAP device
        ahbDev = self.findDevice("CSMEMAP")
        self.AHB = CortexM_AHBAP(self, ahbDev, "CSMEMAP")

    def createV7MTPIU(self, pw, enabled):
        """
        Creates a Cortex-M*-specific TPIU and configures it for DSTREAM trace.
        """
        tpiuDev = self.findDevice("CSTPIU")
        self.tpiu = V7M_CSTPIU(self, tpiuDev, "TPIU", self.AHB)
        if enabled == True:
            self.tpiu.setEnabled(True)
            self.tpiu.setPortSize(pw)
            self.traceComponentOrder = [ self.tpiu ]
        else:
            self.tpiu.setEnabled(False)
        self.mgdDevices = [ self.tpiu ]

    def determineFormatterMode(self):
        # Configures the TPIU for continuous mode.
        self.formatterMode = FormatterMode.CONTINUOUS

        # Configures the DSTREAM for continuous trace
        self.dstreamMode = DSTREAMTraceCapture.TraceMode.Continuous


class Cortex_M_ETM(ETMv3_4TraceSource):
    """
    Cortex-M*-specific ETM configuration.
    """

    # Disable trace triggers and start stop points as currently unsupported
    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False

class Cortex_M3_DSTREAM(DTSLConfigurationFunctions):
    def __init__(self, root):
        DTSLConfigurationFunctions.__init__(self, root)
        coreIndex = 0
        self.createMemAccessor()
        self.createSingleCore("Cortex-M3", coreIndex)
        self.determineFormatterMode()
        self.createV7MTPIU(DEFAULT_PORT_SIZE, True)
        self.createDSTREAM(DEFAULT_PORT_SIZE)
        self.createMClassETMsv3_4(self.DSTREAM, coreIndex)
        self.setManagedDevices(self.mgdDevices)

