from com.arm.debug.trace.events.itm import ITMCustomDecoder

import struct
import string

# Don't expand forever if no newlines in the stream.
MAX_LEN=4096

class Text(ITMCustomDecoder):

    def __init__(self, sink):
        self.sink = sink
        self.buf = bytearray()

    def notifyStart(self): pass
    def notifyEnd(self): pass

    def notifyInt(self, i):
        for b in struct.pack('<I', i):
            if b != '\0' and b != '\r':
                self.buf.append(b)
            if b == '\n' or len(self.buf) == MAX_LEN:
                self.sink.accept(self.buf.decode('utf-8'))
                self.buf = bytearray()

    notifyByte = notifyShort = notifyInt


