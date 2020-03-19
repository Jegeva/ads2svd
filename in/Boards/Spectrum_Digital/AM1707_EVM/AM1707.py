from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import ETMv1TraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import FormatterMode


class AM1707ETB(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        coreDev = self.findDevice("ARM926EJ-S")
        etmDev = self.findDevice("ETM")
        self.ETM = ETMv1TraceSource(self, etmDev, "ETM")

        etbDev = self.findDevice("ETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(FormatterMode.BYPASS)
        self.ETB.addTraceSource(self.ETM, coreDev)
        self.addTraceCaptureInterface(self.ETB)

        self.setManagedDevices([self.ETM, self.ETB])


class AM1707ETBKernelOnly(AM1707ETB):
    def __init__(self, root):
        AM1707ETB.__init__(self, root)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)
