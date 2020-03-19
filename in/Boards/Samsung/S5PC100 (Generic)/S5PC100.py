from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import FormatterMode


class S5PC100ETB(DTSLv1):
    @staticmethod
    def getOptionList():
        return [ DTSLv1.booleanOption('addresses', 'Enable data address trace',
                description='Enable trace of data access addresses in addition to instruction trace', defaultValue=False,
                setter=S5PC100ETB.setDataAddressTraceEnabled) ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # enable port for self. core on the funnel
        funnelDev = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev, "Funnel")
        funnel.setAllPortsDisabled()
        funnel.setPortEnabled(0)

        coreDev = self.findDevice("Cortex-A8")
        etmDev = self.findDevice("CSETM")
        self.ETM = ETMv3_3TraceSource(self, etmDev, 1, "ETM")

        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(FormatterMode.BYPASS)
        self.ETB.addTraceSource(self.ETM, coreDev)
        self.ETB.setTraceComponentOrder([ funnel ])
        self.addTraceCaptureInterface(self.ETB)

        self.setManagedDevices([self.ETM, self.ETB, funnel])

    def setDataAddressTraceEnabled(self, enable):
        self.ETM.setDataTraceEnabled(enable)
        self.ETM.setDataAddressTraceEnabled(enable)

class S5PC100ETBKernelOnly(S5PC100ETB):
    def __init__(self, root):
        S5PC100ETB.__init__(self, root)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)
