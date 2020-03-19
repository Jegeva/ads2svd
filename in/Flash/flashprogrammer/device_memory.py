
from com.arm.rddi.RDDI_ACC_SIZE import RDDI_ACC_DEF
from com.arm.rddi.RDDI_ACC_SIZE import RDDI_ACC_WORD
from com.arm.rddi.RDDI import *

from jarray import zeros
import struct

def writeToTarget(dev, start, data, length=None, CHUNK_SIZE=4096):
    '''Writes data to a device.  The chunk size is the point where the code
    transitions from being performed using a single write to being performed as a
    download.

    dev - a DTSL device to which the data is written
    start - The start address of the write operation
    data - a byte buffer of data to write to the target device
    length - The number of bytes to be written, if null the whole buffer is written'''
    if length is None:
        length = len(data)

    if length < CHUNK_SIZE:
        dev.memWrite(0, start, RDDI_ACC_DEF, RDDI_MRUL_NORMAL, False, length, data)
    else:
        currentAddress = start
        bytesLeft = len(data)
        chunkSize = min([CHUNK_SIZE, bytesLeft])
        pos = 0

        while bytesLeft > 0:
            bytesToCopy = data[pos : pos + chunkSize]
            dev.memDownload(0L, currentAddress, RDDI_ACC_DEF, 0, False, chunkSize, bytesToCopy)
            currentAddress += chunkSize
            pos += chunkSize
            bytesLeft -= chunkSize
            chunkSize = min([CHUNK_SIZE, bytesLeft])

        val    = zeros(1, 'i')
        page   = zeros(1, 'l')
        addr   = zeros(1, 'l')
        offset = zeros(1, 'l')
        dev.memDownloadEnd(val, page, addr, offset)


def readFromTarget(dev, start, size):
    '''Reads data from a device

    dev - The DTSL Device that the data should be read from
    start - The start address
    size - The number of bytes to be read

    return an array of bytes containing the read data'''
    readBuf = zeros(size, 'b')
    dev.memRead(0, start, RDDI_ACC_DEF, RDDI_MRUL_NORMAL, size, readBuf)
    return readBuf


def compareBuffers(a, b):
    '''Compare two buffers

    return buffer size if equal, index of first difference if not
    '''
    if a != b:
        # compare each element of a and b (map(cmd, a, b))
        #   and locate the index (enumerate) of the first non-zero element
        for i, d in enumerate(map(cmp, a, b)):
            if d != 0:
                return i
        return -1
    return len(a)


def intToBytes(a):
    '''Convert a integer to a 4 byte buffer (little endian)

    Data is written to target as a byte array

    a - The integer to convert

    return a byte array
    '''
    return list(struct.unpack('4b', struct.pack('<I', a)))


def intFromBytes(buf):
    '''Convert 4 bytes (little endian) to an integer

    Data is read from target as a byte array

    buf - The byte array (4 bytes) to convert

    return an integer unpacked from buf
    '''
    return struct.unpack('<I', buf)[0]
