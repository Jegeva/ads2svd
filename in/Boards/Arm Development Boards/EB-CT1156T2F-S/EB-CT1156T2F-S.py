from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import ETMv3_1TraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import FormatterMode

class TargetBoard(DTSLv1):
    def __init__(self, root, cores):
        DTSLv1.__init__(self, root)
        self.core_list = cores
        self.trace_sources = []

    def create_ETB(self, formatter_mode):
        etbDev = self.findDevice("ETB")
        self.ETB = ETBTraceCapture(self, etbDev, "ETB")
        self.ETB.setFormatterMode(formatter_mode)
        self.trace_sources = self.trace_sources + [ self.ETB ]

    def create_ETM(self, coreDev, sink):
        etmDev = self.findDevice("ETM")
        self.ETM = ETMv3_1TraceSource(self, etmDev, "ETM")
        sink.addTraceSource(self.ETM, coreDev)
        self.trace_sources = self.trace_sources + [ self.ETM ]

    def determine_formatter_mode(self, core_list):
        self.formatter_mode = FormatterMode.BYPASS
        self.dstream_mode = DSTREAMTraceCapture.TraceMode.Raw

    def setup_for_ETM_ETB_trace(self):
        self.determine_formatter_mode(self.core_list)
        coreDev = self.findDevice("ARM1156T2F-S")
        self.create_ETB(self.formatter_mode)
        self.create_ETM(coreDev, self.ETB)
        self.addTraceCaptureInterface(self.ETB)
        self.setManagedDevices( self.trace_sources )

class Target_ETB(TargetBoard):
    def __init__(self, root):
        core = 0
        TargetBoard.__init__(self, root, [core])
        self.setup_for_ETM_ETB_trace()

class Target_ETB_KernelOnly(TargetBoard):
    def __init__(self, root):
        core = 0
        TargetBoard.__init__(self, root, [core])
        self.setup_for_ETM_ETB_trace()
        self.ETM.addTraceRange(0xBF000000,0xFFFFFFFF)
