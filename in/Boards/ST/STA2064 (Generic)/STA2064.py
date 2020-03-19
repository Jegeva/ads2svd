from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import ETMv3_3TraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import DSTREAMTraceCapture

class STA2064_ETB(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # disable the TPIU to allow ETB to work at full rate
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "CSTPIU")
        tpiu.setEnabled(False)

        coreDev = self.findDevice("ARM1176JZF-S_JTAG-AP")
        etmDev = self.findDevice("CSETM")
        self.ETM = ETMv3_3TraceSource(self, etmDev, 1, "ETM")

        etbDev = self.findDevice("CSETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(FormatterMode.BYPASS)
        self.ETB.addTraceSource(self.ETM, coreDev)
        self.addTraceCaptureInterface(self.ETB)

        self.setManagedDevices([self.ETM, self.ETB, tpiu])


class STA2064_ETB_CA(STA2064_ETB):
    def __init__(self, root):
        STA2064_ETB.__init__(self, root)
        self.ETM.setCycleAccurate(True)


class STA2064_ETB_Kernel_Only(STA2064_ETB):
    def __init__(self, root):
        STA2064_ETB.__init__(self, root)
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)


class STA2064_ETB_Kernel_Only_CA(STA2064_ETB_Kernel_Only):
    def __init__(self, root):
        STA2064_ETB_Kernel_Only.__init__(self, root)
        self.ETM.setCycleAccurate(True)


class STA2064_Single_Core_DSTREAM(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # configure the TPIU for continuous mode, 16 bit
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(True)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        tpiu.setPortSize(16)

        # find first core/PTM
        coreDev = self.findDevice("ARM1176JZF-S_JTAG-AP")

        self.addDeviceInterface(Device(self, coreDev, "ARM1176JZF-S_JTAG-AP"))
        etmDev = self.findDevice("CSETM")
        self.ETM = ETMv3_3TraceSource(self, etmDev, 1, "ETM")

        # configure the DSTREAM for 16 bit continuous trace
        DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        DSTREAM.setPortWidth(16)

        # register the trace source with the DSTREAM
        DSTREAM.addTraceSource(self.ETM, coreDev)

        # register other trace components
        DSTREAM.setTraceComponentOrder([ tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(DSTREAM)

        # automatically handle connection/disconnection
        self.setManagedDevices([ self.ETM, tpiu, DSTREAM ])


class STA2064_DSTREAM(STA2064_Single_Core_DSTREAM):
    def __init__(self, root):
        STA2064_Single_Core_DSTREAM.__init__(self, root)


class STA2064_DSTREAM_CA(STA2064_DSTREAM):
    def __init__(self, root):
        STA2064_DSTREAM.__init__(self, root)
        self.ETM.setCycleAccurate(True)


class STA2064_DSTREAM_Kernel_Only(STA2064_Single_Core_DSTREAM):
    def __init__(self, root):
        STA2064_Single_Core_DSTREAM.__init__(self, root)
        self.ETM.addTraceRange(0xC0000000,0xFFFFFFFF)


class STA2064_DSTREAM_Kernel_Only_CA(STA2064_DSTREAM_Kernel_Only):
    def __init__(self, root):
        STA2064_DSTREAM_Kernel_Only.__init__(self, root)
        self.ETM.setCycleAccurate(True)
