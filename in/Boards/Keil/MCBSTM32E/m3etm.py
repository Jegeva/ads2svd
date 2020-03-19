from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import ETMv3_4TraceSource

class M3_ETM(ETMv3_4TraceSource):
    '''A Cortex-M3 specific ETM which requires the unlock register setting'''
    def __init__(self, root, deviceID, streamID, deviceName):
        ETMv3_4TraceSource.__init__(self, root, deviceID, streamID, deviceName)

    # Disable trace triggers and start stop points as currently unsupported
    def hasTriggers(self):
        return False

    def hasTraceStartPoints(self):
        return False

    def hasTraceStopPoints(self):
        return False

    def hasTraceRanges(self):
        return False

    def setStreamID(self, streamID):
        pass

