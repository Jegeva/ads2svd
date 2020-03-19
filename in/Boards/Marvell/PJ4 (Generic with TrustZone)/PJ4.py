from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import FormatterMode


class PJ4ETB(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        coreDev = self.findDevice("88SV581x-v7_PJ4_TZ")
        etmDev = self.findDevice("CSETM")
        self.ETM = ETMv3_3TraceSource(self, etmDev, 1, "ETM")

        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(FormatterMode.BYPASS)
        self.ETB.addTraceSource(self.ETM, coreDev)
        #self.ETB.setTraceComponentOrder([ funnel ])
        self.addTraceCaptureInterface(self.ETB)

        self.setManagedDevices([self.ETM, self.ETB])



class PJ4ETBKernelOnly(PJ4ETB):
    def __init__(self, root):
        PJ4ETB.__init__(self, root)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)
