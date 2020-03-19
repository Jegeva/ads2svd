from jarray import zeros, array

from jtag import *

import time
import struct

import logging

logger = logging.getLogger(__name__)
#logger.setLevel(logging.info)


# JTAG-AP registers
CSDAP_AP_REG_BASE = 0x1800

CSW     = 0
CSW_TRST_OUT = (1 << 1)
PORTSEL = 1
PSTA    = 2
BFIFO1  = 4
BFIFO2  = 5
BFIFO3  = 6
BFIFO4  = 7

# JTAG-AP protocol
#   buffer sizes
AP_JTAG_BFIFO_W_SIZE = 4
AP_JTAG_BFIFO_R_SIZE = 7

#  maximum values for packets
AP_JTAG_MAX_TMS = 5
AP_JTAG_MAX_PACKED_BITS = 6
AP_JTAG_MAX_DATA_BITS = 128

#  packets
AP_JTAG_TMS_TDI     = 0x40
AP_JTAG_DEF_TDI_TDO = 0x80
AP_JTAG_UTDI_0      = 0x01
AP_JTAG_UTDI_1      = 0x03
AP_JTAG_SHIFT_TDI   = 0x04
AP_JTAG_TMS_EXIT1   = 0x08
AP_JTAG_TDO_PACKED  = 0x80


class PrePostBits:
    '''Holds pre/post bits for a JTAG-AP port'''

    def __init__(self, irPreBits, irPostBits, drPreBits, drPostBits):
        self.irPreBits  = irPreBits
        self.irPostBits = irPostBits
        self.drPreBits  = drPreBits
        self.drPostBits = drPostBits


class JTAGAP:
    '''Peforms JTAG scans on scanchains connected to a JTAG-AP

    Scans are performed by writing/reading the AP's registers as described in
    ARM Debug Interface v5 Architecture Specification
    (http://infocenter.arm.com/help/topic/com.arm.doc.ihi0031a/index.html)

    '''


    def __init__(self, dap, ap):
        '''Create a JTAGAP instance

        dap:  The DAP device (com.arm.debug.dtsl.components.CSDAP) to access
        ap:   The AP number of the JTAG-AP
        port: The JTAG-AP port to scan on
        '''

        # dap/port selection
        self.dap = dap
        self.ap = ap

        self.curPort = -1

        # per-port data:
        #   pre/post bits
        self.prePostBits = {}

        #   current tap state
        self.curState = {}

        # current JTAG-AP bytecode buffer
        self.txBuf = []


    def setPort(self, port):
        '''Set the port to peform scans on

        port: The new port number (0 based)
        '''
        if port != self.curPort:
            if not port in self.curState:
                # assume RTI if we haven't seen this port before
                self.curState[port] = JTAGS_RTI
            self.curPort = port
            self.__selectPort(self.curPort)


    def configScanChain(self, irPreBits, irPostBits, drPreBits, drPostBits):
        '''Configure the pre/post IR/DR bits for the device to communicate
        with.

        The terms pre/post are taken to apply to the jtag data entering the AP
        (i.e. leaving the target system via TDO). Thus, for the following scan
        chain:

        TDI -> IR.3 -> IR.5 -> IR.4 -> IR.4 -> TDO

        to communicate with the IR.5 device we would set irPreBits=8,
        irPostBits=3, drPreBits=2, drPostBits=1

        pre/post bits for IR scans are 1s to put the other devices into BYPASS mode
        pre/post bits for DR scans are 1s

        irPreBits:  The number of bits scanned out before the IR for the selected device
        irPostBits: The number of bits scanned out after the IR for the selected device
        drPreBits:  The number of bits scanned out before the DR for the selected device
        drPostBits: The number of bits scanned out after the DR for the selected device
        '''
        self.prePost[self.curPort] = PrePostBits(irPreBits, irPostBits, drPreBits, drPostBits)


    def scanIO(self, scanType, scanLen, scanOut, scanIn, rest, flush):
        '''Perform an IR or DR scan

        The tap state is moved to SHIFT-IR/SHIFT-DR, the bits are read
        from/written to the IR/DR register and then state is moved to the
        resting state.  Pre/post bits specified by configScanChain() are
        inserted.

        scanType: The type of scan to perform: JTAGS_IR for IR scan, JTAGS_DR for
                  DR scan
        scanLen:  The number of bits to scan
        scanOut:  Data to scan out of the AP into the scan chain.  The LSB of
                  scanOut[0] is sent first.  If scanOut is None, the data
                  transmitted will be 1s
        scanIn:   Buffer to receive data scanned into AP from the scan chain.
                  scanIn[0] holds the 1st bit received. If scanIn is None, no
                  data will be read back
        rest:     The JTAG state to move to after the scan
        flush:    Whether to perform scan immediately.  Only used if scanIn is
                  None.
        '''

        # sanity check number of scan bits
        if scanLen <= 0:
            logger.warn("scanIO: Invalid scan length %d", scanLen)
            raise RuntimeError, "scanIO: Invalid scan length %d" % scanLen

        preBits = 0
        postBits = 0

        prePostBits = self.prePostBits.get(self.curPort)
        if scanType == JTAGS_IR:
            shift = JTAGS_SHI
            if prePostBits:
                preBits = prePostBits.irPreBits
                postBits = prePostBits.irPostBits
        else:
            shift = JTAGS_SHD
            if prePostBits:
                preBits = prePostBits.drPreBits
                postBits = prePostBits.drPostBits

        scanBits = preBits + scanLen + postBits

        # Generate bitstream for tap move to shift
        toLen, SeqBitsTo = GenerateTAPMoveData(self.curState[self.curPort], shift)
        if toLen == 0:
            errMsg = "scanIO: Invalid entry transition from %s to %s" % (
                JTAGStateName(self.curState[self.curPort]), JTAGStateName(shift)
                )
            logger.warn(errMsg)
            raise RuntimeError, errMsg

        # Generate bitstream for tap move from shift to rest
        fromLen, SeqBitsFrom = GenerateTAPMoveData(shift, rest)
        if fromLen == 0:
            errMsg = "scanIO: Invalid exit transition from %s to %s" % (
                JTAGStateName(shift), JTAGStateName(rest)
                )
            logger.warn(errMsg)
            raise RuntimeError, errMsg

        if logger.isEnabledFor(logging.info):
            logger.info("scanIO: move from %s, to %s, scan %d bits In:%s Out:%s, move to %s",
                        JTAGStateName(self.curState[self.curPort]),
                        JTAGStateName(shift),
                        scanBits,
                        scanOut != None,
                        scanIn != None,
                        JTAGStateName(rest)
                        )
        # we're not shifting data as part of the 'from' TMS packet so we can move
        # to E1xR on the last bit of the data shift
            bExit1 = True

        # we will actually move from the exit state so...
        fromLen -= 1        # Length one less than calculated
        SeqBitsFrom >>= 1   # Dump the transition from Sh to Ex

        if (scanOut is not None) and ((preBits > 0) or (postBits > 0)):
            # create a data stream incorporating any pre or post bits, which we
            # can manipulate to remove any data bits scanned as spare TMS bits.
            # Note : this is pre/post bits for the current JTAG-AP scan chain
            outBuffer = self.__InsertPrePostBits(scanOut, scanLen, preBits, postBits)
        else:
            outBuffer = scanOut

        if ((preBits > 0) or (postBits > 0)) and (scanIn is not None):
            # setup to scan in to the internal buffer, so that we can later remove pre/post bits
            # allocate incoming buffer
            inBuffer = [ 0 ] * ((scanBits+7)/8)
        else:
            inBuffer = scanIn

        # tap move to the start of the shift (with TDI=0)
        self.__AP_JTAG_TMSOut(toLen, SeqBitsTo, False)

        # shift the data
        if (scanBits > 0):
            # This assumes that if there is no outData then TDI will always be 1, needed for pre/post bits.
            # This is currently the default implementation (see __AP_JTAG_ShiftData())
            self.__AP_JTAG_ShiftData(scanBits, outBuffer, inBuffer, bExit1)

        if ((preBits > 0) or (postBits > 0)) and (scanIn is not None):
            # remove any pre and post bits from the captured data
            self.__ExtractDataBits(inBuffer, scanIn, scanLen, preBits)

        # Tap move to the final state (with TDI=0)
        self.__AP_JTAG_TMSOut(fromLen, SeqBitsFrom, False)

        # force flush of the sequence out to hardware, if not already
        if flush or scanIn is not None:
            self.__AP_JTAG_FlushSequence()

        # Assume we have arrived where we expected
        self.curState[self.curPort] = rest


    def stateMove(self, rest):
        '''Moves the tap state to requested resting state by clocking TMS sequences
        into the TAP controller.

        rest: The state to move to

        '''
        seqLen, seqBits = GenerateTAPMoveData(self.curState[self.curPort], rest)
        if seqLen == 0:
            errMsg = "stateMove: invalid move from %s to %s" % (
                JTAGStateName(self.curState[self.curPort]), JTAGStateName(rest)
                )
            logger.warn(errMsg)
            raise RuntimeError, errMsg

        logger.info("stateMove: move from %s to %s",
                    JTAGStateName(self.curState[self.curPort]),
                    JTAGStateName(rest))

        # tap move to the start of the shift
        self.__AP_JTAG_TMSOut(seqLen, seqBits, False)

        self.__AP_JTAG_FlushSequence()

        # update TAP state indicator
        self.curState[self.curPort] = rest


    def stateJump(self, rest):
        '''Sets the internal tap state to requested state

        Call when an external influence has changed tap state (e.g. reset)

        rest: The state to jump to

        '''
        logger.info("stateJump: %s", JTAGStateName(rest))
        self.curState[self.curPort] = rest


    def tapReset(self, rest):
        '''Perform a tap reset

        The TRST line is asserted for 50ms and then a seqence of TMS bits
        is scanned to ensure TLR is entered and then moves to the requested
        rest state

        rest: The tap state to move to after TLR
        '''
        logger.info("tapReset: rest=%s", JTAGStateName(rest))

        # assert TRST via CSW for 50mS
        csw = self.__readAPReg(CSW)
        self.__writeAPReg(CSW, csw | CSW_TRST_OUT)

        # TAP state machine on target(s) should now be reset, but force
        # to the rest state via TLR anyway to make absolutely sure.
        # TMS = 11111111
        seqBits = 0xff
        self.__AP_JTAG_TMSOut(8, seqBits, False)

        self.__AP_JTAG_FlushSequence()

        time.sleep(0.050)
        self.__writeAPReg(CSW, csw)

        tmsLen, seqBits = GenerateTAPMoveData(JTAGS_TLR, rest)
        self.__AP_JTAG_TMSOut(tmsLen, seqBits, False)

        # Assume we have arrived where we expected
        self.curState[self.curPort] = rest


    # generate TMS sequence on active JTAG-AP port
    def __AP_JTAG_TMSOut(self, numBits, tmsStream, bTDI):

        # sanity check the number of bits? Must be 32 or less
        if numBits > 32:
            raise RuntimeError, "Invalid TMS scan length %d" % numBits

        bitsLeft = numBits
        bitVal = tmsStream
        outBytes = []
        while bitsLeft > 0:
            if bitsLeft < AP_JTAG_MAX_TMS:
                bitsToClock = bitsLeft
            else:
                bitsToClock = AP_JTAG_MAX_TMS

            # write the current output byte
            curByte = ((1<<bitsToClock) | (bitVal & ((1<<bitsToClock)-1)))
            if bTDI:
                curByte |= AP_JTAG_TMS_TDI
            outBytes.append(curByte)

            if len(outBytes) == AP_JTAG_BFIFO_W_SIZE:
                # FIFO full: flush to BFIFO
                self.__WriteJtagFifo(outBytes, False, 0)
                outBytes = []

            bitsLeft -= bitsToClock
            if bitsLeft > 0:
                # move along the bitstream
                bitVal >>= bitsToClock

        # write out any remaining bytes
        if len(outBytes) > 0:
            self.__WriteJtagFifo(outBytes, False, 0)


    # scan data bits on active JTAG-AP port
    def __AP_JTAG_ShiftData(self, numBits, pOutData, pInData, bExit1=True):
        logger.debug("__AP_JTAG_ShiftData: %d %s %s", numBits, pOutData, pInData)

        # build TDI_TDO byte
        tdi_tdo = AP_JTAG_DEF_TDI_TDO
        if pOutData is None:
            # no output data, so tie TDI to 1
            tdi_tdo |= AP_JTAG_UTDI_1
            bWrite = False
        else:
            bWrite = True

        if pInData:
            # we want to shift return data into our read FIFO
            tdi_tdo |= AP_JTAG_SHIFT_TDI
            # we'll need to check there is sufficient room in the read FIFO
            bRead = True
        else:
            bRead = False

        if bExit1:
            # clock last TMS as 1 to leave us in Exit1-xR
            tdi_tdo |= AP_JTAG_TMS_EXIT1

        # output data bytes
        txFifo = []
        if numBits <= AP_JTAG_MAX_PACKED_BITS:
            # its a packed packet, so 2nd byte is data
            txFifo.append(tdi_tdo)
            if bWrite:
                txFifo.append((1<<numBits) | (pOutData[0] & ((1<<numBits)-1)) | AP_JTAG_TDO_PACKED)
            else:
                # we're 'using TDI', so data bits are don't care
                txFifo.append((1<<numBits) | AP_JTAG_TDO_PACKED)

            # write packed packet to write FIFO
            self.__WriteJtagFifo(txFifo, bRead, 1)

            if bRead:
                # if we expect return data from this sequence then we must make sure
                # its flushed out before attempting the read
                self.__AP_JTAG_FlushSequence()

                # read back the resulting byte from read FIFO
                rxData = self.__ReadJtagFifo(1)
                pInData[0] = (uint8)(rxData & ((1<<numBits)-1))

        else:
            # non packed
            bitPos = 0
            txBytePos = 0
            rxBytePos = 0
            bitsLeft = numBits
            fifoIdx = 0
            dataBits = 0

            while bitPos < numBits:
                if (bitPos == 0) or (bitPos%AP_JTAG_MAX_DATA_BITS == 0):
                    # write the header bytes
                    if bitsLeft <= AP_JTAG_MAX_DATA_BITS:
                        bitsToClock = bitsLeft
                    else:
                        bitsToClock = AP_JTAG_MAX_DATA_BITS

                    txFifo.append(tdi_tdo)
                    txFifo.append(bitsToClock - 1)

                    # do the write. If the write will cause a read then first check
                    # there is sufficient room in the read FIFO for the number of
                    # bytes to be read. This will be 4 or less as we read the FIFO
                    # every 4th byte
                    if bRead:
                        if bitsToClock > 32:
                            checkBytes = 4
                        else:
                            checkBytes = (bitsToClock+7)/8

                        self.__WriteJtagFifo(txFifo, True, checkBytes)
                    else:
                        # write won't cause a read, no need to check anything
                        self.__WriteJtagFifo(txFifo, False, 0)

                    # update counter
                    bitsLeft -= bitsToClock
                    txFifo = [] # clear FIFO

                # fill Tx FIFO
                if bWrite:
                    if (numBits - bitPos) < 8:
                        # last byte, so we only want to write the remaining bits
                        remBits = (numBits - bitPos)
                        txFifo.append(pOutData[txBytePos] & ((1<<remBits)-1))
                        dataBits += remBits
                    else:
                        # add the output data
                        txFifo.append(pOutData[txBytePos])
                        dataBits += 8
                    txBytePos += 1

                fifoIdx += 1

                # check for a full Tx FIFO
                if fifoIdx == AP_JTAG_BFIFO_W_SIZE:
                    # write the data out
                    if bWrite:
                        self.__WriteJtagFifo(txFifo, False, 0)
                        txFifo = []

                    if bRead:
                        # if we expect return data from this sequence then we must make sure
                        # its flushed out before attempting the read
                        self.__AP_JTAG_FlushSequence()

                        # get the corresponding read data
                        rxBytes = self.__ReadJtagFifo(4)
                        pInData[rxBytePos:rxBytePos+4] = rxBytes
                        rxBytePos += 4

                    # reset the index
                    fifoIdx = 0
                    dataBits = 0

                # update bit index
                bitPos += 8

            # deal with any remaining data
            if fifoIdx > 0:
                if bWrite:
                    self.__WriteJtagFifo(txFifo, False, 0)
                    txFifo = []

                if bRead:
                    # if we expect return data from this sequence then we must make sure
                    # its flushed out before attempting the read
                    self.__AP_JTAG_FlushSequence()

                    # get the corresponding read data
                    rxBytes = self.__ReadJtagFifo(fifoIdx)
                    pInData[rxBytePos:rxBytePos+4] = rxBytes


    # bytes to be written to the JTAG-AP are buffered until we have a full 32 bits
    # to minimise access to the JTAG-DP. This routine forces a flush of this buffer
    def __AP_JTAG_FlushSequence(self):
        # flush internal buffer out to the hardware
        if len(self.txBuf) > 0:
            buf = (self.txBuf + [ 0 ] * 4)[:4]
            outVal = buf[0] | (buf[1] << 8) | (buf[2] << 16) | (buf[3] << 24)
            self.__writeAPReg(BFIFO1 + len(self.txBuf)-1, outVal)

            # reset buffer index
            self.txBuf = []


    def __WriteJtagFifo(self, data, bCheckSpace=False, rxBytes=0):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("__WriteJtagFifo: %s", map(hex, data))

        if bCheckSpace:
            # this write will cause data to be captured in the read FIFO, so first ensure there
            # is sufficient space in the read FIFO

            # read the JTAG-AP CSW
            csw = self.__readAPReg(CSW)

            if (AP_JTAG_BFIFO_R_SIZE - ((csw>>24) & 0x00000007)) < rxBytes:
                # there's not enough room, something is out of step!
                raise RuntimeError, "Not enough room in JTAG-AP FIFO"

        # write the FIFO
        for b in data:
            self.txBuf.append(b)

            if len(self.txBuf) >= 4:
                # flush sequence out to hardware
                self.__AP_JTAG_FlushSequence()


    # read from the JTAG-AP FIFO
    def __ReadJtagFifo(self, bytes):
        rxBytes = []

        # read the FIFO
        bytesLeft = bytes
        while bytesLeft > 0:
            if bytesLeft <= 4:
                bytesToRead = bytesLeft
            else:
                bytesToRead = 4

            csw = self.__readAPReg(CSW)
            logger.debug("__ReadJtagFifo: %d / %d bytes available", (csw >> 24) & 0x7, bytesLeft)

            rxData = self.__readAPReg(BFIFO1+bytesToRead-1)
            for i in range(0, bytesToRead):
                rxBytes.append((rxData >> 8*i) & 0xFF)

            #update counter
            bytesLeft -= bytesToRead

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("__ReadJtagFifo: %s", map(hex, rxBytes))

        return rxBytes


    # ! Inserts the pre & post bits around the supplied data and stores the
    #  resultant bit stream within the m_ScanOutBuffer data member.
    #
    #  i.e. if we had data of  01100, dataBits = 5, preBits = 10, postBits = 4,
    # then the resultant bit stream would be :
    #   *
    #          1111 01100 11111 11111
    #           ^     ^     ^     ^
    #           |     |     |     |
    #        postBits |    prebits (10 bits)
    #                 |
    #     the 5 bits destined for the core we require
    #
    # Note that the required number of bits to be now scanned is 5+10+4=19 bits
    #
    # @param pData - the data stream that is to scanned out
    # @param dataBits - the number of databits in the data stream
    # @param preBits - the number of prebits to insert
    # @param postBits - the number of post-bits to insert
    #
    def __InsertPrePostBits(pData, dataBits, preBits, postBits):

        ulTotalBits = dataBits + preBits + postBits
        scanOutBuffer = []
        bitPos=0

        # start with any pre bits
        if preBits > 0:
            preBitsLeft = preBits

            # Insert the prebits a byte at a time, until we have less
            # than 8 bits to insert....
            while preBitsLeft >= 8:
                scanOutBuffer.append(0xff)
                preBitsLeft -= 8

            # insert the remaining prebits at the current bytePos
            scanOutBuffer.append((1<<preBitsLeft) - 1)
            bitPos += preBits

        # prebits now dealt with, so lets insert the data destined for
        # our connection
        if (bitPos == 0) or (bitPos%8 == 0):
            # either there were no pre-bits or inserting them has left
            # our bit position byte aligned, which makes things easier
            bytesToCopy = (dataBits+7)/8
            scanOutBuffer += pData[:bytesToCopy]

        else:
            # here is where we are inserting the data to be scanned to a given core
            # the data is not byte aligned and so we must do some jigging around to insert
            # the data correctly.

            # bitOffset - this is the bit position within the byte where the data is to go
            # bitGap - is just used to deduce how many bits are left in the current byte
            dataBitsLeft = dataBits
            bitOffset  = (bitPos%8)
            bitGap = (8 - bitPos%8)
            i = 0

            while dataBitsLeft > 0:
                scanOutBuffer[-1] |= pData[i] << bitOffset
                if (dataBitsLeft > bitGap):
                    # stick the remaining bitGap bits of data in the next byte up
                    # Note : bitOffset + bitGap = 8.
                    scanOutBuffer.append(pData[i] >> bitGap)
                    dataBitsLeft -= 8
                elif (dataBitsLeft == bitGap):
                    # then all the bits fit in exactly with no room left, just inc bytepos
                    # so we know to start inserting the post-bits in the next byte
                    dataBitsLeft = 0
                else:
                    # dataBitsLeft < bitGap so all the bits will fit into this
                    # current byte so set dataBitsLeft=0
                    dataBitsLeft = 0
                i += 1

        bitPos += dataBits

        # Now append the post bits to the buffer
        if postBits > 0:
            postBitsLeft = postBits

        if (bitPos % 8) == 0:
            # we're byte aligned, which makes things easier
            while postBitsLeft >= 8:
                scanOutBuffer.append(0xff)
                postBitsLeft -= 8
            scanOutBuffer.append((1<<postBitsLeft) - 1)
        else:
            bitOffset = (bitPos%8)
            bitGap = (8 - bitPos%8)

            while postBitsLeft > 0:
                scanOutBuffer[-1] |= 0xff << bitOffset
                scanOutBuffer.append(0xff >> bitGap)
                postBitsLeft -= 8


    def __ExtractDataBits(self, scanInBuffer, scanData, dataBits, preBits):
        bitPos = preBits

        for pos in range(0, dataBits):
            if (scanInBuffer[bitPos/8] & (1 << (bitPos & 7))):
                scanData[pos/8] |= 1 << (pos & 7)
            else:
                scanData[pos/8] &= ~(1 << (pos & 7))
            bitPos += 1


    def __read_PORTSEL(self):
        # get the currently selected port bits
        return self.__readAPReg(PORTSEL)


    def __selectPort(self, port):
        # select a port
        self.__writeAPReg(PORTSEL, (1 << port))


    def __read_PSTA(self):
        return self.__readAPReg(PSTA)


    def __getJTAGAP_RegID(self, reg):
        return CSDAP_AP_REG_BASE | ((self.ap & 0xFF) << 3) | reg


    def __readAPReg(self, reg):
        v = self.dap.readRegister(self.__getJTAGAP_RegID(reg))
        logger.debug('R %d: %08x', reg, v)
        return v


    def __writeAPReg(self, reg, val):
        logger.debug('W %d: %08x', reg, val)
        return self.dap.writeRegister(self.__getJTAGAP_RegID(reg), val)

    def writeAPReg(self, reg, val):
        return self.writeAPReg(self, reg, val)

class JTAGAPChain:
    '''Performs scans on one scan chain of a JTAG-AP

    Ensures the correct port is selected before each operation
    '''

    def __init__(self, jtagap, port):
        '''Create a JTAG-AP chain

        jtagap: The JTAGAP object to access
        port:   The port to select for each operation
        '''
        self.jtagap = jtagap
        self.port = port


        # pre/post bits
        self.irPreBits = 0
        self.irPostBits = 0
        self.drPreBits = 0
        self.drPostBits = 0


    def configScanChain(self, irPreBits, irPostBits, drPreBits, drPostBits):
        '''Configure the pre/post IR/DR bits for the device to communicate
        with.

        The terms pre/post are taken to apply to the jtag data entering the AP
        (i.e. leaving the target system via TDO). Thus, for the following scan
        chain:

        TDI -> IR.3 -> IR.5 -> IR.4 -> IR.4 -> TDO

        to communicate with the IR.5 device we would set irPreBits=8,
        irPostBits=3, drPreBits=2, drPostBits=1

        pre/post bits for IR scans are 1s to put the other devices into BYPASS mode
        pre/post bits for DR scans are 1s

        irPreBits:  The number of bits scanned out before the IR for the selected device
        irPostBits: The number of bits scanned out after the IR for the selected device
        drPreBits:  The number of bits scanned out before the DR for the selected device
        drPostBits: The number of bits scanned out after the DR for the selected device
        '''
        self.jtagap.configScanChain(irPreBits, irPostBits, drPreBits, drPostBits)


    def scanIO(self, scanType, scanLen, scanOut, scanIn, rest, flush):
        '''Perform an IR or DR scan

        The tap state is moved to SHIFT-IR/SHIFT-DR, the bits are read
        from/written to the IR/DR register and then state is moved to the
        resting state.  Pre/post bits specified by configScanChain() are
        inserted.

        scanType: The type of scan to perform: JTAGS_IR for IR scan, JTAGS_DR for
        DR scan
        scanLen:  The number of bits to scan
        scanOut:  Data to scan out of the AP into the scan chain.  The LSB of
        scanOut[0] is sent first.  If scanOut is None, the data
        transmitted will be 1s
        scanIn:   Buffer to receive data scanned into AP from the scan chain.
        scanIn[0] holds the 1st bit received. If scanIn is None, no
        data will be read back
        rest:     The JTAG state to move to after the scan
        flush:    Whether to perform scan immediately.  Only used if scanIn is
        None.
        '''
        self.__ensurePortSelected()
        self.jtagap.scanIO(scanType, scanLen, scanOut, scanIn, rest, flush)


    def stateMove(self, rest):
        '''Moves the tap state to requested resting state by clocking TMS sequences
        into the TAP controller.

        rest: The state to move to

        '''
        self.__ensurePortSelected()
        self.jtagap.stateMove(rest)


    def stateJump(self, rest):
        '''Sets the internal tap state to requested state

        Call when an external influence has changed tap state (e.g. reset)

        rest: The state to jump to

        '''
        self.__ensurePortSelected()
        self.jtagap.stateJump(rest)


    def tapReset(self, rest):
        '''Perform a tap reset

        The TRST line is asserted for 50ms and then a seqence of TMS bits
        is scanned to ensure TLR is entered and then moves to the requested
        rest state

        rest: The tap state to move to after TLR
        '''
        self.__ensurePortSelected()
        self.jtagap.tapReset(rest)


    def __ensurePortSelected(self):
        self.jtagap.setPort(self.port)
