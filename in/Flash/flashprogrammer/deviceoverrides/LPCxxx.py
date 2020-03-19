# Copyright (C) 2019 Arm Limited (or its affiliates). All rights reserved.

# Utility function to generate user-signature checksum for LPCxxx targets.
# See section 4.3.4 in the LPC5411x User Manual for further information.

from com.arm.debug.flashprogrammer.data import ByteArrayDataSource;

import struct

ByteArrayDataSource

DEVICES_REQUIRING_CHECKSUM = [
    "LPC17",
    "LPC15",
    "LPC13",
    "LPC12",
    "LPC11",
    "LPC8",
    "LPC54" ]

def requiresChecksum(deviceName):
    for sourceDevice in DEVICES_REQUIRING_CHECKSUM:
        if deviceName.startswith(sourceDevice):
            return True

    return False

def makeSignedByte(val):
    if val & (1<<7) != 0:
        val = val - (1<<8)
    return val

def generateChecksum(data):
    data.seek(0)
    rawData = data.getData(data.getSize())
    data.seek(0)
    # Generate 2's complement checksum of the first 7 entries in the vector table
    n = 0
    for i in range(0, 7):
        dat = data.getData(4)
        intDat = struct.unpack_from('<I', dat.tostring())[0]
        n = (n + intDat) & 0xFFFFFFFF
    n = 0 - n + (1 << 32)

    # Pack 32bit checksum at 0x1C (vector location 7)
    rawData[0x1F] = makeSignedByte((n >> 24) & 0xFF)
    rawData[0x1E] = makeSignedByte((n >> 16) & 0xFF)
    rawData[0x1D] = makeSignedByte((n >> 8) & 0xFF)
    rawData[0x1C] = makeSignedByte(n & 0xFF)

    return ByteArrayDataSource(rawData)