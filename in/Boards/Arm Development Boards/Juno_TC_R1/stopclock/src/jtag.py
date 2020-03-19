from com.arm.rddi import RDDI_JTAGS_IR_DR
from com.arm.rddi import RDDI_JTAGS_STATE
from jarray import zeros, array
import struct


class JTAGIDCODE:
    def __init__(self, idcode):
        self.idcode = idcode

    def getCompany(self):
        return (self.idcode >> 1) & 0x7FF

    def getPart(self):
            return (self.idcode >> 12) & 0xFFFF

    def getRev(self):
        return (self.idcode >> 28) & 0xF


class JTAG:
    """Wraps a Java RDDI JTAG object to make access to is slightly easier
    """
    # Some of the JTAG constants we use
    DR = RDDI_JTAGS_IR_DR.RDDI_JTAGS_DR.swigValue()
    IR = RDDI_JTAGS_IR_DR.RDDI_JTAGS_IR.swigValue()
    RTI = RDDI_JTAGS_STATE.RDDI_JTAGS_RTI.swigValue()
    PAUSE_DR = RDDI_JTAGS_STATE.RDDI_JTAGS_PDR.swigValue()
    PAUSE_IR = RDDI_JTAGS_STATE.RDDI_JTAGS_PIR.swigValue()

    def __init__(self, jtag, connectionAddress):
        '''Construction from an IJTAG instance
        Parameters:
            jtag - an instance of an IJTAG class
            connectionAddress - the connection string for the JTAG device
        '''
        self.jtag = jtag
        self.connectionAddress = connectionAddress
        self.connected = False
        self.version = 0

    def connect(self):
        version = zeros(1, 'i')
        self.jtag.connect(version)
        self.version = version[0]
        self.connected = True

    def disconnect(self):
        self.jtag.disconnect()
        self.connected = True

    def isConnected(self):
        return self.connected

    def rddiJTAG(self):
        if not self.connected:
            self.connect()
        return self.jtag

    def getConnectionAddress(self):
        return self.connectionAddress

    def getVersionStr(self):
        if self.version == 0:
            return "Unknown"
        d1 = ""
        if self.version >> 12 != 0:
            d1 = chr(ord('0') + ((self.version >> 12) & 0x000F))
        d2 = chr(ord('0') + ((self.version >> 8) & 0x000F))
        d3 = chr(ord('0') + ((self.version >> 4) & 0x000F))
        d4 = chr(ord('0') + (self.version & 0x000F))
        return "V%s%s.%s%s" % (d1, d2, d3, d4)

    def getMaxJTAGBlockSize(self):
        maxJTAGBlockSize = 4096
        if self.version > 0x0100:
            maxJTAGBlockSize = 32768
        return maxJTAGBlockSize

    def tapReset(self):
        """ Performs a soft tap reset
        Params:
            jtag - the JTAG object we use to perform JTAG scans
        """
        tmsData = struct.pack("<B", 0xFF)
        self.jtag.TMS(7, tmsData)

    def countJTAGDevices(self):
        """ Counts the JTAG devices on the chain
            To do this we fill all IR with 1s - which is a predefined JTAG
            instruction BYPASS. This forces all JTAG devices to present a
            single 0 bit in their DR chain. We then scan out the DR chain by
            pushing 1s in and capturing the output. The output will contain a
            0 bit for each device on the chain followed by the 1s we pushed in.
            So we can count the 0s as the number of devices on the chain.
            NOTE: The current implementation is limited to the total IR length
                  < 128
        Params:
            jtag - the JTAG object we use to perform JTAG scans
        Returns:
            0.. the number of JTAG devices on the scan chain
        """
        # map an 8 bit value to number of 0 bits
        bitsClear = {0: 8, 0x80: 7, 0xC0: 6, 0xE0: 5, 0xF0: 4,
                     0xF8: 3, 0xFC: 2, 0xFE: 1, 0xFF: 0}
        # 128 bits of 1s
        oneBits = struct.pack('<BBBBBBBBBBBBBBBB',
                              0xFF, 0xFF, 0xFF, 0xFF,
                              0xFF, 0xFF, 0xFF, 0xFF,
                              0xFF, 0xFF, 0xFF, 0xFF,
                              0xFF, 0xFF, 0xFF, 0xFF)
        scanOutBits = zeros(8, 'b')
        # Set all IR to BYPASS (all ones). This sets all DRs to 1 bit of 0.
        # Scan out these 0s by pushing 1s in.
        self.jtag.scanIRDR(128, oneBits, 64, oneBits, scanOutBits,
                           JTAG.RTI, True)
        # Now count the 0s - there is one 0 bit per device on the chain
        oneCount = 0
        for offset in range(len(scanOutBits)):
            v = scanOutBits[offset] & 0xFF
            if v == 0xFF:
                break
            if v in bitsClear:
                oneCount = oneCount + bitsClear[v]
            else:
                raise RuntimeError('Received bad JTAG data whilst '
                                   'counting devices')
        return oneCount

    def measureIRChainLength(self):
        self.tapReset()
        blockBitCount = 4096
        txBits = zeros(blockBitCount / 8, 'B')
        for idx in range(256, 511):
            txBits[idx] = 0xFF
        txBits = txBits.tostring()
        rxBits = zeros(blockBitCount / 8, 'b')
        self.jtag.scanIO(JTAG.IR, blockBitCount, txBits, rxBits,
                         JTAG.PAUSE_IR, True)
        zCount = 0
        for idx in range(256, 511):
            if rxBits[idx] == 0:
                zCount += 8
            elif rxBits[idx] == -1:
                break
            else:
                val = rxBits[idx]
                while val & 1 == 0:
                    zCount += 1
                    val = val >> 1
        self.tapReset()
        return zCount

    def readIDCodes(self, tapCount):
        """ Returns an array of JTAG IDCODES with one entry per device on
            the chain
        Params:
            tapCount - the number of devices on the chain
        Returns:
            array of JTAG IDCODES. If an entry holds 0 this means the device
            does not have an IDCODE (all valid IDCODES have b0 = 1)
        """
        self.tapReset()
        data = zeros(4 * tapCount, 'b')
        self.jtag.scanIO(JTAG.DR, 32 * tapCount, None, data, JTAG.RTI, True)
        # we need to process the data as a bit stream, so convert the binary
        # array # to a string of '0'/'1' characters
        bits = array(['0'], 'c') * (32 * tapCount)
        bitIdx = 0
        for idx in range(4 * tapCount):
            v = data[idx]
            for b in range(8):
                if v & (1 << b) != 0:
                    bits[bitIdx] = '1'
                bitIdx = bitIdx + 1
        # extract the IDCODES
        idCodes = zeros(tapCount, 'i')  # preset to 0s
        bitIdx = 0
        for idx in range(tapCount):
            if bits[bitIdx] == '0':
                # device does not have an IDCODE
                bitIdx = bitIdx + 1
            else:
                # pre-set bit 0 and extract the rest
                idBit = 0x80000000
                for offs in range(1, 32):
                    idBit = idBit >> 1
                    if bits[bitIdx + offs] == '1':
                        idBit = idBit | 0x80000000
                idCodes[idx] = idBit
                bitIdx = bitIdx + 32
        return idCodes
