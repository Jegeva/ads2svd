from com.arm.debug.trace.events.itm import ITMCustomDecoder

class Binary(ITMCustomDecoder):

    def __init__(self, sink):
        self.sink = sink

    def notifyStart(self): pass
    def notifyEnd(self): pass

    def notifyInt(self, i):
        self.sink.accept('0x%08x' % (i & 0xffffffff))

    def notifyShort(self, s):
        self.sink.accept('0x%04x' % (s & 0xffff))

    def notifyByte(self, b):
        self.sink.accept('0x%02x' % (b & 0xff))


