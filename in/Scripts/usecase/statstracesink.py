from com.arm.debug.dtsl.impl import PipelineStageBase


class StatsTraceSink(PipelineStageBase):

    def __init__(self, dtslTraceSource):
        self.dtslTraceSource = dtslTraceSource

    def setDTSLTraceSource(self, dtslTraceSource):
        self.dtslTraceSource = dtslTraceSource

    def getDTSLTraceSource(self):
        return self.dtslTraceSource

    def consume(self, count):
        pass

    def flush(self):
        pass
