
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from juno_constants import *


class M3_ETM(ETMv3_5TraceSource):
    def __init__(self, config, device, stream, name):
        self.tsFrequency = DEFAULT_JUNO_TS_FREQ
        ETMv3_5TraceSource.__init__(self, config, device, stream, name)

    # Disable trace triggers and start stop points as currently unsupported
    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False

    def setTimestampFrequency(self, freq):
        self.tsFrequency = freq
