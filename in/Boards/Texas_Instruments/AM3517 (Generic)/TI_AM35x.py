from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import FormatterMode


class TI_AM35xETB(DTSLv1):
    @staticmethod
    def getOptionList():
        return [ DTSLv1.booleanOption('addresses', 'Enable data address trace',
                description='Enable trace of data access addresses in addition to instruction trace', defaultValue=False,
                setter=TI_AM35xETB.setDataAddressTraceEnabled) ]

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # disable the TPIU to allow ETB to work at full rate
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(False)

        coreDev = self.findDevice("Cortex-A8")
        etmDev = self.findDevice("CSETM")
        self.ETM = ETMv3_3TraceSource(self, etmDev, 1, "ETM")

        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(FormatterMode.BYPASS)
        self.ETB.addTraceSource(self.ETM, coreDev)
        self.addTraceCaptureInterface(self.ETB)

        self.setManagedDevices([self.ETM, self.ETB, tpiu])

    def setDataAddressTraceEnabled(self, enable):
        self.ETM.setDataTraceEnabled(enable)
        self.ETM.setDataAddressTraceEnabled(enable)


class TI_AM35xETBKernelOnly(TI_AM35xETB):
    def __init__(self, root):
        TI_AM35xETB.__init__(self, root)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)
