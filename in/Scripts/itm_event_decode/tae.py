from com.arm.debug.trace.events.itm import ITMCustomDecoder

import struct

class TAE(ITMCustomDecoder):

    def __init__(self, sink):
        self.sink = sink
        self.remaining = None
        self.buf = None
        self.escape = False


    def notifyStart(self): pass
    def notifyEnd(self): pass


    def initialState(self, i):
        if (i & 0x808080ff) == 0x8080807e:
            self.remaining = ((i & 0x7f0000) >> 16) | ((i & 0x7f000000) >> 17)
            self.buf = bytearray()
            self.state = self.buildingMessage


    @staticmethod
    def fmt(msg):
        timestamp = struct.unpack('<I', str(msg[:4]))[0]
        text = msg[6:].decode('utf-8')
        return 'Time %d: %s' % (timestamp, text)


    def buildingMessage(self, i):
        for b in struct.pack('<I', i):
            if self.remaining > 0:
                self.remaining -= 1
                self.processByte(ord(b))
            if self.remaining == 0:
                self.sink.accept(TAE.fmt(self.buf))
                self.state = self.initialState
                break


    def processByte(self, b):
        if self.escape:
            self.escape = False
            if b == 0x5e:
                self.buf.append(0x7e)
            elif b == 0x5d:
                self.buf.append(0x7d)
        elif b == 0x7d:
            self.escape = True
        else:
            self.buf.append(b)


    def notifyInt(self, i):
        self.state(i)


    state = initialState

    notifyByte = notifyShort = notifyInt


