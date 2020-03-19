from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import ETMv3_1TraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import FormatterMode


class iMX35ETB(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        coreDev = self.findDevice("ARM1136JF-S")
        etmDev = self.findDevice("ETM")
        self.ETM = ETMv3_1TraceSource(self, etmDev, "ETM")

        etbDev = self.findDevice("ETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(FormatterMode.BYPASS)
        self.ETB.addTraceSource(self.ETM, coreDev)
        self.addTraceCaptureInterface(self.ETB)

        self.setManagedDevices([self.ETM, self.ETB])

class iMX35ETBKernelOnly(iMX35ETB):
    def __init__(self, root):
        iMX35ETB.__init__(self, root)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)
