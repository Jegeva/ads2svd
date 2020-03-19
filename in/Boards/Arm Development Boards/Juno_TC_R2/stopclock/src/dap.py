# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

from jtag import JTAG
from dapexception import DAPException
from jarray import zeros
import struct
import array
from com.arm.rddi import IJTAG
from com.arm.rddi import RDDI_ACC_SIZE
from com.arm.rddi import RDDIException
from com.arm.debug.dtsl.interfaces import IDevice
from com.arm.debug.dtsl import DTSLException
import math


class DAPRegAccess:
    """ Base class for DAP register access
    All physical DAP register access classes should be derived from this class
    and should implement methods used in this class but not declared here.
    """

    # DP Reg definitions
    DP_REG_DPIDR     = 0x00                                       # @IgnorePep8
    DP_REG_CTRL_STAT = 0x04                                       # @IgnorePep8
    DP_REG_CTRL_STAT_CSYSPWRUPACK = 0x80000000                    # @IgnorePep8
    DP_REG_CTRL_STAT_CSYSPWRUPREQ = 0x40000000                    # @IgnorePep8
    DP_REG_CTRL_STAT_CDBGPWRUPACK = 0x20000000                    # @IgnorePep8
    DP_REG_CTRL_STAT_CDBGPWRUPREQ = 0x10000000                    # @IgnorePep8
    DP_REG_DLCR      = 0x04 # SWD only                            # @IgnorePep8
    DP_REG_TARGETID  = 0x04 # SWD only                            # @IgnorePep8
    DP_REG_DLPIDR    = 0x04 # SWD only                            # @IgnorePep8
    DP_REG_SELECT    = 0x08                                       # @IgnorePep8
    DP_REG_RDBUFF    = 0x0C                                       # @IgnorePep8

    # AP Reg definitions
    AP_REG_CSW = 0x00                                             # @IgnorePep8
    AP_REG_CSW_SIZE_MASK         = 0x00000007                     # @IgnorePep8
    AP_REG_CSW_SIZE_8            =        0x0                     # @IgnorePep8
    AP_REG_CSW_SIZE_16           =        0x1                     # @IgnorePep8
    AP_REG_CSW_SIZE_32           =        0x2                     # @IgnorePep8
    AP_REG_CSW_ADDRINC_MASK      = 0x00000030                     # @IgnorePep8
    AP_REG_CSW_ADDRINC_OFF       =       0x00                     # @IgnorePep8
    AP_REG_CSW_ADDRINC_SINGLE    =       0x10                     # @IgnorePep8
    AP_REG_CSW_ADDRINC_PACKED    =       0x20                     # @IgnorePep8
    AP_REG_CSW_MODE_MASK         = 0x007FF000                     # @IgnorePep8
    AP_REG_CSW_SPIDEN_MASK       = 0x00800000                     # @IgnorePep8
    AP_REG_CSW_PROT_MASK         = 0x7F000000                     # @IgnorePep8
    AP_REG_CSW_PROT_HPROT0       = 0x01000000                     # @IgnorePep8
    AP_REG_CSW_PROT_HPROT1       = 0x02000000                     # @IgnorePep8
    AP_REG_CSW_PROT_HPROT2       = 0x04000000                     # @IgnorePep8
    AP_REG_CSW_PROT_HPROT3       = 0x08000000                     # @IgnorePep8
    AP_REG_CSW_PROT_HPROT4       = 0x10000000                     # @IgnorePep8
    AP_REG_CSW_PROT_HPROT5       = 0x20000000                     # @IgnorePep8
    AP_REG_CSW_PROT_HPROT6       = 0x40000000                     # @IgnorePep8
    AP_REG_CSW_PROT_SPROT        = 0x40000000                     # @IgnorePep8
    AP_REG_CSW_MASTERTYPE_MASK   = 0x20000000                     # @IgnorePep8
    AP_REG_CSW_MASTERTYPE_CORE   = 0x00000000                     # @IgnorePep8
    AP_REG_CSW_MASTERTYPE_DEBUG  = 0x20000000                     # @IgnorePep8
    AP_REG_CSW_DBGSWEN_MASK      = 0x80000000                     # @IgnorePep8
    AP_REG_CSW_DBGSWEN           = 0x80000000                     # @IgnorePep8

    AP_REG_TAR = 0x04
    AP_REG_DRW = 0x0C
    AP_REG_BD0 = 0x10
    AP_REG_BD1 = 0x14
    AP_REG_BD2 = 0x18
    AP_REG_BD3 = 0x1C
    AP_REG_CFG = 0xF4
    AP_REG_BASE = 0xF8
    AP_REG_IDR = 0xFC

    RETRY_COUNT = 5
    OKorFAULT = 2
    WAIT = 1

    def toHex32(self, rVal):
        """ Converts an integer value to a hex string
        Returns a string of the form 0xhhhhhhhh which is the hex
        value of rVal
        Parameters:
            rVal - the integer value to be converted
        """
        return "0x%s" % ("00000000%X" % (rVal & 0xffffffff))[-8:]

    def toHex64(self, rVal):
        """ Converts an long value to a hex string
        Returns a string of the form 0xhhhhhhhhhhhhhhhh which is the hex
        value of rVal
        Parameters:
            rVal - the long value to be converted
        """
        return "0x%s" % ("0000000000000000%X" %
                         (rVal & 0xffffffffffffffff))[-16:]

    def toHex(self, rVal, bitLength=32):
        """ Converts an value to a hex string
        Returns a string of the form 0xhhhh which is the hex value of rVal
        using as many nibble values required for the bitLength
        Parameters:
            rVal - the long value to be converted
            bitLength - number of bits to display (defaults to 32)
        """
        if bitLength == 64:
            return self.toHex64(rVal)
        if bitLength == 32:
            return self.toHex32(rVal)
        nibbleLength = int((bitLength + 3) / 4)
        mask = int(math.floor(math.ldexp(1, 4 * nibbleLength) - 1))
        lStr = ("%s%X" % ("0" * nibbleLength, rVal & mask))
        hStr = lStr[-nibbleLength:]
        return "0x%s" % (hStr)

    def readDAP_CtrlStat(self):
        """ Reads the DAP Ctrl/Stat register
        Returns:
            32 bit register value
        """
        self.writeDAP_SELECT(0, 0, 0)
        return self.readDAPReg(DAPRegAccess.DP_REG_CTRL_STAT)

    def readDAP_DLCR(self):
        """ Reads the DAP DLCR (The Data Link Control Register) register
        Returns:
            32 bit register value
        """
        self.writeDAP_SELECT(0, 0, 1)
        return self.readDAPReg(DAPRegAccess.DP_REG_DLCR)

    def readDAP_TARGETID(self):
        """ Reads the DAP TARGETID register
        Returns:
            32 bit register value
        """
        self.writeDAP_SELECT(0, 0, 2)
        return self.readDAPReg(DAPRegAccess.DP_REG_TARGETID)

    def readDAP_DLPIDR(self):
        """ Reads the DAP DLPIDR (Data Link Protocol Identification) register
        Returns:
            32 bit register value
        """
        self.writeDAP_SELECT(0, 0, 3)
        return self.readDAPReg(DAPRegAccess.DP_REG_DLPIDR)

    def readDAP_DPIDR(self):
        """ Reads the DAP DPIDR (The Debug Port ID) register
        Returns:
            32 bit register value
        """
        return self.readDAPReg(DAPRegAccess.DP_REG_DPIDR)

    def readAP_CSW(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_CSW)

    def writeAP_CSW(self, apIdx, value):
        return self.writeAPReg(apIdx, DAPRegAccess.AP_REG_CSW, value)

    def readAP_TAR(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_TAR)

    def writeAP_TAR(self, apIdx, value):
        return self.writeAPReg(apIdx, DAPRegAccess.AP_REG_TAR, value)

    def readAP_DRW(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_DRW)

    def writeAP_DRW(self, apIdx, value):
        return self.writeAPReg(apIdx, DAPRegAccess.AP_REG_DRW, value)

    def readAP_DRWn(self, apIdx, count):
        return self.readAPDRWn(apIdx, count)

    def writeAP_DRWn(self, apIdx, values):
        return self.writeAPDRWn(apIdx, values)

    def readAP_BD0(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_BD0)

    def writeAP_BD0(self, apIdx, value):
        return self.writeAPReg(apIdx, DAPRegAccess.AP_REG_BD0, value)

    def readAP_BD1(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_BD1)

    def writeAP_BD1(self, apIdx, value):
        return self.writeAPReg(apIdx, DAPRegAccess.AP_REG_BD1, value)

    def readAP_BD2(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_BD2)

    def writeAP_BD2(self, apIdx, value):
        return self.writeAPReg(apIdx, DAPRegAccess.AP_REG_BD2, value)

    def readAP_BD3(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_BD3)

    def writeAP_BD3(self, apIdx, value):
        return self.writeAPReg(apIdx, DAPRegAccess.AP_REG_BD3, value)

    def readAP_BD1234(self, apIdx):
        return self.readAPBDRegs(apIdx)

    def writeAP_BD1234(self, apIdx, values):
        return self.writeAPBDRegs(apIdx, values)

    def readAP_CFG(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_CFG)

    def readAP_BASE(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_BASE)

    def readAP_IDR(self, apIdx):
        return self.readAPReg(apIdx, DAPRegAccess.AP_REG_IDR)

    def readAPMemBlock32(self, apIdx, address, nWords, csw):
        """ Reads a block of 32 bit word memory from a MEM-AP
        Params:
            apIdx - the AP (0..255)
            address - the address to read from (b[1:0]=0)
            nWords - the number of 32 bit words to read
            csw - bits 6 and above of the CSW value to use when making the
                  access
        Returns:
            an array of nWords x 32 bit values
        """
        blockBoundary = 1024
        address = address & 0xFFFFFFFC
        cswValue = (DAPRegAccess.AP_REG_CSW_SIZE_32 |
                    DAPRegAccess.AP_REG_CSW_ADDRINC_SINGLE |
                    (csw & ~0x0000002F))
        self.writeAP_CSW(apIdx, cswValue)
        # MEM-AP may only support 1K access blocks and may not support
        # incrementing TAR across a 1K boundary. So we split the block read
        # up into possibly 3 parts:
        #
        # +-----+   +----------+   +-----+
        # | sub | + | 1K block | + | sub |
        # | 1K  |   |  reads   |   | 1k  |
        # +-----+   +----------+   +-----+
        data = None
        # Do first sub block (if any) to get us to blockBoundary
        if address & (blockBoundary - 1) != 0:
            self.writeAP_TAR(apIdx, address)
            wCount = min(
                nWords,
                (blockBoundary - (address & (blockBoundary - 1))) >> 2)
            data = self.readAP_DRWn(apIdx, wCount)
            nWords = nWords - wCount
            address = address + 4 * wCount
        # Now do all remaining blocks
        while nWords > 0:
            self.writeAP_TAR(apIdx, address)
            wCount = min(nWords, blockBoundary / 4)
            if data is None:
                data = self.readAP_DRWn(apIdx, wCount)
            else:
                data.extend(self.readAP_DRWn(apIdx, wCount))
            nWords = nWords - wCount
            address = address + 4 * wCount
        return data

    def writeAPMemBlock32(self, apIdx, address, data32, csw):
        """ Writes a block of 32 bit word memory to a MEM-AP
        Params:
            apIdx - the AP (0..255)
            address - the address to write to (b[1:0]=0)
            data32 - the data to write as an array of 32 bit words
            csw - bits 6 and above of the CSW value to use when making the
                  access
        """
        blockBoundary = 1024
        address = address & 0xFFFFFFFC
        nWords = len(data32)
        cswValue = (DAPRegAccess.AP_REG_CSW_SIZE_32 |
                    DAPRegAccess.AP_REG_CSW_ADDRINC_SINGLE |
                    (csw & ~0x0000002F))
        self.writeAP_CSW(apIdx, cswValue)
        # MEM-AP may only support 1K access blocks and may not support
        # incrementing TAR across a 1K boundary. So we split the block write
        # up into possibly 3 parts:
        #
        # +-----+   +----------+   +-----+
        # | sub | + | 1K block | + | sub |
        # | 1K  |   |  writes  |   | 1k  |
        # +-----+   +----------+   +-----+
        subBlockStart = 0
        # Do first sub block (if any) to get us to blockBoundary
        if address & (blockBoundary - 1) != 0:
            self.writeAP_TAR(apIdx, address)
            wCount = min(
                nWords,
                (blockBoundary - (address & (blockBoundary - 1))) >> 2)
            subBlock = data32[subBlockStart:subBlockStart + wCount]
            self.writeAP_DRWn(apIdx, subBlock)
            nWords = nWords - wCount
            address = address + 4 * wCount
            subBlockStart = subBlockStart + wCount
        # Now do all remaining blocks
        while nWords > 0:
            self.writeAP_TAR(apIdx, address)
            wCount = min(nWords, blockBoundary / 4)
            subBlock = data32[subBlockStart:subBlockStart + wCount]
            self.writeAP_DRWn(apIdx, subBlock)
            nWords = nWords - wCount
            address = address + 4 * wCount
            subBlockStart = subBlockStart + wCount

    def isPoweredUp(self):
        ctrlStatVal = self.readDAP_CtrlStat()
        powerUpAcks = (DAPRegAccess.DP_REG_CTRL_STAT_CSYSPWRUPACK |
                       DAPRegAccess.DP_REG_CTRL_STAT_CDBGPWRUPACK)
        return ((ctrlStatVal & powerUpAcks) == powerUpAcks)

    def powerUp(self):
        if self.isPoweredUp():
            return True
        powerUpReqs = (DAPRegAccess.DP_REG_CTRL_STAT_CSYSPWRUPREQ |
                       DAPRegAccess.DP_REG_CTRL_STAT_CDBGPWRUPREQ)
        self.writeDAP_CtrlStat(powerUpReqs)
        return self.isPoweredUp()

    def showROMTable(self, apIdx, base):
        if base & 1 == 0:
            print "AP does not have a ROM table"
            return
        if base & 2 == 0:
            print "AP does not have a ROM table in a recognized format"
            return
        baseAddress = base & 0xFFFFF000
        romTable = self.readAPMemBlock32(
            apIdx,
            baseAddress, 4096 / 4,
            DAPRegAccess.AP_REG_CSW_PROT_HPROT1)
        print "AP %d ROM table" % (apIdx)
        self.showDump32(baseAddress, romTable, skipZeroLines=True)

    def showDump32(self, baseAddress, data32, skipZeroLines):
        count = len(data32)
        start = 0
        while count > 0:
            nwords = min(8, count)
            strList = [self.toHex(baseAddress) + ':']
            allZero = True
            for idx in range(start, start + nwords):
                if data32[idx] != 0:
                    allZero = False
                strList.append(self.toHex(data32[idx]))
            start = start + nwords
            count = count - nwords
            baseAddress = baseAddress + nwords * 4
            if not (skipZeroLines and allZero):
                print ' '.join(strList)

    def showAPInfo(self, apIdx):
        value = self.readAP_CSW(apIdx)
        if value == 0:
            return
        print "AP[%d] CTRL/STAT = %s" % (apIdx, self.toHex(value))
        value = self.readAP_IDR(apIdx)
        print "AP[%d]       IDR = %s" % (apIdx, self.toHex(value))
        base = self.readAP_BASE(apIdx)
        print "AP[%d]      BASE = %s" % (apIdx, self.toHex(base))
        value = self.readAP_CFG(apIdx)
        print "AP[%d]       CFG = %s" % (apIdx, self.toHex(value))
        self.showROMTable(apIdx, base)

    def showDAP(self):
        print "DAP IDCODE    = %s" % (self.toHex(self.readDAPIDCODE()))
        value = self.readDAP_CtrlStat()
        print "DAP CTRL/STAT = %s" % (self.toHex(value))
        value = self.readDAP_DLCR()
        print "DAP DLCR      = %s" % (self.toHex(value))
        value = self.readDAP_TARGETID()
        print "DAP TARGETID  = %s" % (self.toHex(value))
        value = self.readDAP_DLPIDR()
        print "DAP DLPIDR    = %s" % (self.toHex(value))
        value = self.readDAP_DPIDR()
        print "DAP DPIDR     = %s" % (self.toHex(value))
        self.showAPInfo(apIdx=0)


class DAPRegAccessDAPTemplate(DAPRegAccess):
    """ Class which does DAP accesses via the DSTREAM JTAG-DP template
    The DSTREAM device list can contain a JTAG-DP template (which Arm DS will
    not normally connect to). We make use of this template to perform the
    DAP accesses.
    """

    # These are JTAG-DP template memory access rule flags which indicate
    # whether the page field contains the prot access fields
    CSDAP_PAGESPEC = 0x100
    CSDAP_USEHPROT = 0x200

    def __init__(self, device):
        """ Construction from a Java RDDI-DEBUG object
        Params:
            device - the RDDI-DEBUG object we use to perform the DAP access
        """
        assert isinstance(device, IDevice)
        self.debug = device

    def writeDAP_CtrlStat(self, value):
        """ Writes the DAP CTRL/STAT register
        Params:
            value - the value to write
        """
        # regID = 00100000 100000rr
        regID = 0x2080 | ((DAPRegAccess.DP_REG_CTRL_STAT >> 2) & 0x03)
        try:
            self.debug.writeRegister(regID, value)
        except DTSLException, eDTSL:
            raise DAPException("Failed to write DAP CTRL/STAT register", eDTSL)

    def writeDAP_SELECT(self, apIdx, apbanksel=0, dpbanksel=0):
        """ Writes the DAP SELECT register
        Params:
            apIdx - the AP index 0..255
            apbanksel - the AP bank select 0..15
            dpbanksel - the AP bank select 0..15 (arch 2 onwards)
        """
        # regID = 00100000 100000rr
        regValue = (((apIdx & 0xFF) << 24) |
                    ((apbanksel & 0x0F) << 4) |
                    (dpbanksel & 0x0F))
        regID = 0x2080 | ((DAPRegAccess.DP_REG_SELECT >> 2) & 0x03)
        try:
            self.debug.writeRegister(regID, regValue)
        except DTSLException, eDTSL:
            raise DAPException("Failed to write DAP SELECT register", eDTSL)

    def readDAPReg(self, reg):
        """ Reads a DAP register
        Params:
            reg  - 0x00 (DPIDR),
                   0x04 (CTRL/STAT),
                   0x08 (SELECT),
                   0x0C (RDBUFF)
        Returns:
            32 bit register value
        """
        # regID = 00100000 100000rr
        regID = 0x2080 | ((reg >> 2) & 0x03)
        try:
            return self.debug.readRegister(regID)
        except DTSLException, eDTSL:
            raise DAPException("Failed to read DAP register [0x%02X]" % (reg),
                               eDTSL)

    def formAPRegID(self, apIdx, reg):
        """ Forms a DAP template register ID for access to an AP register
        Params:
            apIdx - the AP (0..255)
            reg  - one of the AP_REG_xxxx values
        Returns:
            16 bit register id value
        """
        # regID = 00011ppp ppppprrr
        return 0x1800 | (((apIdx & 0xFF) << 3)) | ((reg >> 2) & 0x07)

    def readAPReg(self, apIdx, reg):
        """ Reads a MEM-AP register
        Params:
            apIdx - the AP (0..255)
            reg  - one of the AP_REG_xxxx values
        Returns:
            32 bit register value
        """
        try:
            return self.debug.readRegister(self.formAPRegID(apIdx, reg))
        except DTSLException, eDTSL:
            raise DAPException(
                "Failed to read AP register [ap=%d, reg=0x%02X]" % (
                    apIdx, reg),
                eDTSL)

    def writeAPReg(self, apIdx, reg, value):
        """ Writes a MEM-AP register
        Params:
            apIdx - the AP (0..255)
            reg  - one of the AP_REG_xxxx values
            value - the 32 bit value to write
        """
        try:
            self.debug.writeRegister(self.formAPRegID(apIdx, reg), value)
        except DTSLException, eDTSL:
            raise DAPException(
                "Failed to write AP register [ap=%d, reg=0x%02X]" % (
                    apIdx, reg),
                eDTSL)

    def readAPBDRegs(self, apIdx):
        """ Reads the MEM-AP BD0..BD4 registers
        Params:
            apIdx - the AP (0..255)
        Returns:
            an array of 4 x 32 bit register values
        """
        bdValues = zeros(4, 'i')
        try:
            self.debug.regReadBlock(self.formAPRegID(apIdx,
                                                     DAPRegAccess.AP_REG_BD0),
                                    4, bdValues)
        except DTSLException, eDTSL:
            raise DAPException(
                "Failed to read AP BD registers [ap=%d]" % (apIdx),
                eDTSL)
        return bdValues

    def writeAPBDRegs(self, apIdx, values):
        """ Writes the BD MEM-AP registers
        Params:
            apIdx - the AP (0..255)
            value - array of 4 x 32 bit values to write
        """
        try:
            self.debug.regWriteBlock(self.formAPRegID(apIdx,
                                                      DAPRegAccess.AP_REG_BD0),
                                     4, values)
        except DTSLException, eDTSL:
            raise DAPException(
                "Failed to write AP BD registers [ap=%d]" % (apIdx),
                eDTSL)

    def readAPDRWn(self, apIdx, count):
        """ Reads the MEM-AP DRW register a number of times
        Params:
            apIdx - the AP (0..255)
            count - the number of times to read the register
        Returns:
            an array of count x 32 bit register values
        """
        # The only way we have to read the same register multiple times
        # is to use the regReadlist call where we give it a register list
        # which is a repeated reg ID.
        regListSize = min(32, count)  # the max size of the read list per call
        regID = self.formAPRegID(apIdx, DAPRegAccess.AP_REG_DRW)
        # Create list of regIDs all entries holding the same ID
        regIDs = zeros(regListSize, 'i')
        for idx in range(regListSize):
            regIDs[idx] = regID
        # Read the register in blocks of regListSize
        data = None
        subData = zeros(regListSize, 'i')
        try:
            while count > 0:
                subCount = min(regListSize, count)
                self.debug.regReadList(regIDs[0:subCount], subData)
                if data is None:
                    data = subData[0:subCount]
                else:
                    data.extend(subData[0:subCount])
                count = count - subCount
        except DTSLException, eDTSL:
            raise DAPException(
                "Failed to read AP DRW register [ap=%d]" % (apIdx),
                eDTSL)
        return data

    def writeAPDRWn(self, apIdx, values):
        """ Writes the MEM-AP DRW register a number of times
        Params:
            apIdx - the AP (0..255)
            value - array of 32 bit values to write
        """
        # The only way we have to write the same register multiple times
        # is to use the regWritelist call where we give it a register list
        # which is a repeated reg ID.
        count = len(values)
        regListSize = min(32, count)  # the max size of the write list per call
        regID = self.formAPRegID(apIdx, DAPRegAccess.AP_REG_DRW)
        # Create list of regIDs all entries holding the same ID
        regIDs = zeros(regListSize, 'i')
        for idx in range(regListSize):
            regIDs[idx] = regID
        # Write the register in blocks of regListSize
        idx = 0
        try:
            while count > 0:
                subCount = min(regListSize, count)
                self.debug.regWriteList(regIDs[0:subCount],
                                        values[idx:idx + subCount])
                count = count - subCount
                idx = idx + subCount
        except DTSLException, eDTSL:
            raise DAPException(
                "Failed to write AP DRW register [ap=%d]" % (apIdx),
                eDTSL)

    def readAPMemBlock32Opt(self, apIdx, address, nWords, csw):
        """ Reads a block of 32 bit word memory from a MEM-AP. This makes
            use of the template's read memory API and so should be faster
            than readAPMemBlock32() - but at the expense of transparency of
            target operations.
        Params:
            apIdx - the AP (0..255)
            address - the address to read from (b[1:0]=0)
            nWords - the number of 32 bit words to read
            csw - bits 6 and above of the CSW value to use when making the
                  access
            NOTE: currently, only the top 8 bits of csw are used
        Returns:
            an array of nWords x 32 bit values
        """
        page = ((apIdx & 0xFF) |
                ((csw & DAPRegAccess.AP_REG_CSW_PROT_MASK) >> 16))
        memData = zeros(4 * nWords, 'b')
        try:
            rule = (DAPRegAccessDAPTemplate.CSDAP_PAGESPEC |
                    DAPRegAccessDAPTemplate.CSDAP_USEHPROT)
            self.debug.memRead(page, address, RDDI_ACC_SIZE.RDDI_ACC_WORD,
                               rule, 4 * nWords, memData)
            rVals = zeros(nWords, 'i')
            memDataStr = memData.tostring()
            for wIdx in range(nWords):
                rVals[wIdx] = struct.unpack_from(
                    '<l', memDataStr, wIdx * 4)[0]
            return rVals
        except DTSLException, eDTSL:
            addrRange = "0x%08X..0x%08X" % (address, address + 4 * nWords - 1)
            msg = ("Failed to read from MEM-AP "
                   "[dev=%d, ap=%d, page=0x%04X, rule=0x%04X, address=%s]") % (
                       self.debug.getID(), apIdx, page, rule, addrRange)
            raise DAPException(msg, eDTSL)

    def writeAPMemBlock32Opt(self, apIdx, address, data32, csw):
        """ Writes a block of 32 bit word memory to a MEM-AP. This makes
            use of the template's write memory API and so should be faster
            than writeAPMemBlock32() - but at the expense of transparency of
            target operations.
        Params:
            apIdx - the AP (0..255)
            address - the address to write to (b[1:0]=0)
            data32 - the data to write as an array of 32 bit words
            csw - bits 6 and above of the CSW value to use when making the
                  access
            NOTE: currently, only the top 8 bits of csw are used
        """
        page = ((apIdx & 0xFF) |
                ((csw & DAPRegAccess.AP_REG_CSW_PROT_MASK) >> 16))
        nWords = len(data32)
        byteData = array.array('c', '\0' * (nWords * 4))
        for idx in range(nWords):
            struct.pack_into('<I', byteData, idx * 4, data32[idx])
        try:
            rule = (DAPRegAccessDAPTemplate.CSDAP_PAGESPEC |
                    DAPRegAccessDAPTemplate.CSDAP_USEHPROT)
            self.debug.memWrite(page, address, RDDI_ACC_SIZE.RDDI_ACC_DEF,
                                rule, False, 4 * nWords, byteData.tostring())
        except DTSLException, eDTSL:
            addrRange = "0x%08X..0x%08X" % (address, address + 4 * nWords - 1)
            msg = ("Failed to write to MEM-AP "
                   "[dev=%d, ap=%d, page=0x%04X, rule=0x%04X, address=%s]") % (
                       self.debug.getID(), apIdx, page, rule, addrRange)
            raise DAPException(msg, eDTSL)


class DAPRegAccessJTAG(DAPRegAccess):
    """ Class to provide DAP register access via us performing JTAG scans
        using the RDDI-JTAG interface
    """
    # DAP IR/DR definitions
    IR_LEN = 4
    IR_ABORT = struct.pack('<B', 8)
    DR_ABORT_LEN = 35
    IR_DPACC = struct.pack('<B', 10)
    DR_DPACC_LEN = 35
    IR_APACC = struct.pack('<B', 11)
    DR_APACC_LEN = 35
    IR_IDCODE = struct.pack('<B', 14)
    DR_IDCODE_LEN = 32
    IR_BYPASS = struct.pack('<B', 15)
    DR_BYPASS_LEN = 1

    def __init__(self, jtag):
        """ Construction from a Java RDDI JTAG object
        Params:
            jtag - the JTAG object we use to perform JTAG scans
        """
        self.jtag = jtag
        assert isinstance(self.jtag.rddiJTAG(), IJTAG)

    def readDAPIDCODE(self):
        """ Reads the JTAG-DP IDCODE. You can use this to verify the DAP
            is present and responding. The format for the IDCODE is:
                [31:28] Version Version code
                [27:12] Part Number for the DP. Current DPs designed by ARM
                        Limited have the following PARTNO values:
                            JTAG-DP  0xBA00
                            SW-DP  0xBA10
                 [11:1] JEDEC Designer ID, an 11-bit JEDEC code that identifies
                        the designer of the ADI implementation, see The JEDEC
                        Designer ID. The ARM Limited default value for this
                        field, 0x23B.
                    [0] Always 1.
        Returns:
            32 bit IDCODE value (probably 0x3ba00477)
        """
        idcode = zeros(4, 'b')
        self.jtag.rddiJTAG().scanIRDR(
            DAPRegAccessJTAG.IR_LEN,
            DAPRegAccessJTAG.IR_IDCODE,
            DAPRegAccessJTAG.DR_IDCODE_LEN, None, idcode,
            JTAG.RTI, True)
        return struct.unpack('<' + 'I', idcode)[0]

    def waitForDAP(self, outdata, indata):
        """ Waits for the DAP to have accepted a request
        Params:
            outdata - the data set containing the read request
            indata - the data set containing the output of a previously
                     performed read request. This is updated with the
                     result of any scan we do whilst waiting for the
                     DAP to accept the request
        """
        # Check response from previous request
        for _ in range(DAPRegAccessJTAG.RETRY_COUNT):
            ack, _ = struct.unpack('<BI', indata)
            if ack & 3 == DAPRegAccess.OKorFAULT:
                # Previous request is complete _and_ our request has
                # been accepted
                return
            # Re-issue our read request until accepted
            self.jtag.rddiJTAG().scanIO(
                JTAG.DR,
                DAPRegAccessJTAG.DR_DPACC_LEN, outdata, indata,
                JTAG.RTI, True)
        # if we get here we have tried too many times to get the DAP to
        # accept our request
        raise DAPException("Timeout waiting for DAP to accept request")

    def extractD32FromScan35(self, scandata):
        """ Reads a D32 data value from a returned 35 bit DP/AP scan
        Params:
            scandata - a 35 bit scan as 5 bytes
        Returns:
            a 32 bit data value extracted from the scan data
        """
        ack, v_hi = struct.unpack('<BI', scandata)
        v_low = ack >> 3
        return ((v_hi << 5) | (v_low & 0x1F)) & 0xFFFFFFFF

    def form35bitRegReadScan(self, reg):
        """ Forms a DP or AP 35 bit register read scan
        Params:
            reg - one of the DP_REG_xxxx or AP_REG_xxxx values
        Returns:
            a 5 byte array containing the 35 bit scan
        """
        # outdata = 00000000 00000000 00000000 00000000 00000rr1
        # is a read request for rr = reg[3:2]
        outdata = zeros(5, 'b')
        outdata[0] = ((reg & 0x0C) >> 1) | 1
        return outdata

    def form35bitRegWriteScan(self, reg, value):
        """ Forms a DP or AP 35 bit register write scan
        Params:
            reg - one of the DP_REG_xxxx or AP_REG_xxxx values
            value - the 32 bit value to write
        Returns:
            a 5 character string containing the 35 bit scan
        """
        # 333 33222222 22221111 11111100 00000000
        # 432 10987654 32109876 54321098 76543210
        # ddd dddddddd dddddddd dddddddd dddddrr0
        return struct.pack(
            '<BI',
            ((value << 3) | ((reg & 0x0C) >> 1)) & 0xFF,
            value >> 5)

    def readDAPReg(self, reg):
        """ Reads a JTAG-DP register
        Params:
            reg  - 0x00 (DPIDR),
                   0x04 (CTRL/STAT),
                   0x08 (SELECT),
                   0x0C (RDBUFF)
        Returns:
            32 bit register value
        """
        try:
            # outdata = 00000000 00000000 00000000 00000000 00000rr1
            # is a read request for rr = reg[3:2]
            outdata = self.form35bitRegReadScan(reg)
            indata = zeros(5, 'b')
            # Write DPACC to IR and the read req to DR
            self.jtag.rddiJTAG().scanIRDR(
                DAPRegAccessJTAG.IR_LEN,
                DAPRegAccessJTAG.IR_DPACC,
                DAPRegAccessJTAG.DR_DPACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForDAP(outdata, indata)
            # Now issue a read of RDBUFF (0x0C) request
            # outdata = 00000000 00000000 00000000 00000000 00000111
            outdata[0] = ((DAPRegAccess.DP_REG_RDBUFF & 0x0C) >> 1) | 1
            self.jtag.rddiJTAG().scanIO(
                JTAG.DR,
                DAPRegAccessJTAG.DR_DPACC_LEN, outdata, indata,
                JTAG.RTI, True)
            self.waitForDAP(outdata, indata)
            # Returned data is now original reg read data, with a read of
            # RDBUFF left outstanding
            return self.extractD32FromScan35(indata)
        except RDDIException, eRDDI:
            raise DAPException("Failed to read DAP register [0x%02X]" % (reg),
                               eRDDI)

    def writeDAP_CtrlStat(self, value):
        """ Writes the DAP CTRL/STAT register
        Params:
            value - the value to write
        """
        # 333 33222222 22221111 11111100 00000000
        # 432 10987654 32109876 54321098 76543210
        # ddd dddddddd dddddddd dddddddd ddddd010
        try:
            outdata = self.form35bitRegWriteScan(
                DAPRegAccessJTAG.DP_REG_CTRL_STAT,
                value)
            indata = zeros(5, 'b')
            self.jtag.rddiJTAG().scanIRDR(
                DAPRegAccessJTAG.IR_LEN,
                DAPRegAccessJTAG.IR_DPACC,
                DAPRegAccessJTAG.DR_DPACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForDAP(outdata, indata)
        except RDDIException, eRDDI:
            raise DAPException("Failed to write DAP CTRL/STAT register", eRDDI)

    def writeDAP_SELECT(self, apIdx, apbanksel=0, dpbanksel=0):
        """ Writes the JTAG-DP SELECT register
        Params:
            apIdx - the AP index 0..255
            apbanksel - the AP bank select 0..15
            dpbanksel - the AP bank select 0..15 (arch 2 onwards)
        """
        # 333 33222222 22221111 11111100 00000000
        # 432 10987654 32109876 54321098 76543210
        # aaa aaaaa000 00000000 00000bbb bdddd100
        try:
            outdata = struct.pack(
                '<BI',
                0x04 | ((dpbanksel & 0x0F) << 3) | ((apbanksel & 0x01) << 7),
                ((apbanksel >> 1) & 0x07) | ((apIdx & 0xFF) << 19))
            indata = zeros(5, 'b')
            self.jtag.rddiJTAG().scanIRDR(
                DAPRegAccessJTAG.IR_LEN,
                DAPRegAccessJTAG.IR_DPACC,
                DAPRegAccessJTAG.DR_DPACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForDAP(outdata, indata)
        except RDDIException, eRDDI:
            raise DAPException("Failed to write DAP SELECT register", eRDDI)

    def waitForAP(self, outdata, indata):
        """ Waits for the AP to have accepted a request
        Params:
            outdata - the data set containing the 35 bit APACC request
            indata - the data set containing the 35 bit output of a previously
                     performed request. This is updated with the
                     result of any scan we do whilst waiting for the
                     AP to accept the request
        """
        try:
            # Check response from previous request
            for _ in range(DAPRegAccessJTAG.RETRY_COUNT):
                ack, _ = struct.unpack('<BI', indata)
                if ack & 3 == DAPRegAccess.OKorFAULT:
                    # Previous request is complete _and_ our request has
                    # been accepted
                    return
                # Re-issue our read request until accepted
                self.jtag.rddiJTAG().scanIO(
                    JTAG.DR,
                    DAPRegAccessJTAG.DR_APACC_LEN,
                    outdata, indata,
                    JTAG.RTI, True)
        except RDDIException, eRDDI:
            raise DAPException("Failed to perform scan on APACC register",
                               eRDDI)
        # if we get here we have tried too many times to get the AP to accept
        # our request
        raise DAPException("Timeout waiting for AP to accept command")

    def readAPReg(self, apIdx, reg):
        """ Reads a MEM-AP register
        Params:
            apIdx - the AP (0..255)
            reg  - one of the AP_REG_xxxx values
        Returns:
            32 bit register value
        """
        try:
            self.writeDAP_SELECT(apIdx, (reg >> 4) & 0xFF)
            # outdata = 00000000 00000000 00000000 00000000 00000rr1
            # is a read request for rr = reg[3:2]
            outdata = self.form35bitRegReadScan(reg)
            indata = zeros(5, 'b')
            # Write APACC to IR and the read req to DR
            self.jtag.rddiJTAG().scanIRDR(
                DAPRegAccessJTAG.IR_LEN,
                DAPRegAccessJTAG.IR_APACC,
                DAPRegAccessJTAG.DR_APACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForAP(outdata, indata)
            # Now issue a read of RDBUFF (0x0C) request
            # outdata = 00000000 00000000 00000000 00000000 00000111
            outdata[0] = ((DAPRegAccess.DP_REG_RDBUFF & 0x0C) >> 1) | 1
            self.jtag.rddiJTAG().scanIRDR(
                DAPRegAccessJTAG.IR_LEN,
                DAPRegAccessJTAG.IR_DPACC,
                DAPRegAccessJTAG.DR_DPACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForDAP(outdata, indata)
            # Returned data is now original reg read data, with a read of
            # RDBUFF left outstanding
            return self.extractD32FromScan35(indata)
        except RDDIException, eRDDI:
            raise DAPException(
                "Failed to read AP register [ap=%d, reg=0x%02X]" % (
                    apIdx, reg),
                eRDDI)

    def writeAPReg(self, apIdx, reg, value):
        """ Writes a MEM-AP register
        Params:
            apIdx - the AP (0..255)
            reg  - one of the AP_REG_xxxx values
            value - the 32 bit value to write
        """
        try:
            self.writeDAP_SELECT(apIdx, (reg >> 4) & 0xFF)
            # 333 33222222 22221111 11111100 00000000
            # 432 10987654 32109876 54321098 76543210
            # ddd dddddddd dddddddd dddddddd dddddrr0
            outdata = self.form35bitRegWriteScan(reg, value)
            indata = zeros(5, 'b')
            self.jtag.rddiJTAG().scanIRDR(
                DAPRegAccessJTAG.IR_LEN,
                DAPRegAccessJTAG.IR_APACC,
                DAPRegAccessJTAG.DR_APACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForAP(outdata, indata)
        except RDDIException, eRDDI:
            raise DAPException(
                "Failed to write AP register [ap=%d, reg=0x%02X]" % (
                    apIdx, reg),
                eRDDI)

    def readAPBDRegs(self, apIdx):
        """ Reads the MEM-AP BD0..BD4 registers
        Params:
            apIdx - the AP (0..255)
        Returns:
            an array of 4 x 32 bit register values
        """
        self.writeDAP_SELECT(apIdx, 1)
        # outdata = 00000000 00000000 00000000 00000000 00000001
        # outdata = 00000000 00000000 00000000 00000000 00000011
        # outdata = 00000000 00000000 00000000 00000000 00000101
        # outdata = 00000000 00000000 00000000 00000000 00000111
        # is a read request for rr = 00,01,10,11
        regIDs = [DAPRegAccess.AP_REG_BD0,
                  DAPRegAccess.AP_REG_BD1,
                  DAPRegAccess.AP_REG_BD2,
                  DAPRegAccess.AP_REG_BD3]
        bdValues = zeros(4, 'l')
        indata = zeros(5, 'b')
        outdata = self.form35bitRegReadScan(regIDs[0])
        try:
            # Select APACC in DR chain and issue request to read BD0
            self.jtag.rddiJTAG().scanIRDR(
                DAPRegAccessJTAG.IR_LEN,
                DAPRegAccessJTAG.IR_APACC,
                DAPRegAccessJTAG.DR_APACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForAP(outdata, indata)

            for reg in range(1, 4):
                outdata[0] = ((regIDs[reg] & 0x0C) >> 1) | 1
                self.jtag.rddiJTAG().scanIO(
                    JTAG.DR,
                    DAPRegAccessJTAG.DR_APACC_LEN,
                    outdata, indata,
                    JTAG.RTI, True)
                self.waitForAP(outdata, indata)
                bdValues[reg - 1] = self.extractD32FromScan35(indata)

            outdata[0] = ((DAPRegAccess.DP_REG_RDBUFF & 0x0C) >> 1) | 1
            self.jtag.rddiJTAG().scanIRDR(
                DAPRegAccessJTAG.IR_LEN,
                DAPRegAccessJTAG.IR_DPACC,
                DAPRegAccessJTAG.DR_DPACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForDAP(outdata, indata)
            bdValues[3] = self.extractD32FromScan35(indata)
            return bdValues
        except RDDIException, eRDDI:
            raise DAPException(
                "Failed to read AP BD registers [ap=%d]" % (apIdx),
                eRDDI)

    def writeAPBDRegs(self, apIdx, values):
        """ Writes the BD MEM-AP registers
        Params:
            apIdx - the AP (0..255)
            value - array of 4 x 32 bit values to write
        Returns:
            2 bit response code (OKorFAULT or WAIT)
        """
        self.writeDAP_SELECT(apIdx, 1)
        # 333 33222222 22221111 11111100 00000000
        # 432 10987654 32109876 54321098 76543210
        # ddd dddddddd dddddddd dddddddd ddddd000
        # ddd dddddddd dddddddd dddddddd ddddd010
        # ddd dddddddd dddddddd dddddddd ddddd100
        # ddd dddddddd dddddddd dddddddd ddddd110
        regIDs = [DAPRegAccess.AP_REG_BD0,
                  DAPRegAccess.AP_REG_BD1,
                  DAPRegAccess.AP_REG_BD2,
                  DAPRegAccess.AP_REG_BD3]
        outdata = self.form35bitRegWriteScan(regIDs[0], values[0])
        indata = zeros(5, 'b')
        try:
            self.jtag.rddiJTAG().scanIRDR(
                DAPRegAccessJTAG.IR_LEN,
                DAPRegAccessJTAG.IR_APACC,
                DAPRegAccessJTAG.DR_APACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForAP(outdata, indata)

            for reg in range(1, 4):
                outdata = self.form35bitRegWriteScan(regIDs[reg], values[reg])
                self.jtag.rddiJTAG().scanIO(
                    JTAG.DR,
                    DAPRegAccessJTAG.DR_APACC_LEN,
                    outdata, indata,
                    JTAG.RTI, True)
                self.waitForAP(outdata, indata)
        except RDDIException, eRDDI:
            raise DAPException(
                "Failed to write AP BD registers [ap=%d]" % (apIdx),
                eRDDI)

    def readAPDRWn(self, apIdx, count):
        """ Reads the MEM-AP DRW register a number of times
        Params:
            apIdx - the AP (0..255)
            count - the number of times to read the register
        Returns:
            an array of count x 32 bit register values
        """
        # Select AP bank for DRW
        self.writeDAP_SELECT(apIdx, DAPRegAccess.AP_REG_DRW >> 4)
        # outdata = 00000000 00000000 00000000 00000000 00000111
        # is a read request for rr = AP_REG_DRW
        drwValues = zeros(count, 'l')
        indata = zeros(5, 'b')
        outdata = self.form35bitRegReadScan(DAPRegAccess.AP_REG_DRW)
        # Select APACC in DR chain and issue request to read DRW
        self.jtag.rddiJTAG().scanIRDR(
            DAPRegAccessJTAG.IR_LEN,
            DAPRegAccessJTAG.IR_APACC,
            DAPRegAccessJTAG.DR_APACC_LEN, outdata, indata,
            JTAG.RTI, True)
        self.waitForAP(outdata, indata)

        drwIdx = 0
        while count > 1:
            self.jtag.rddiJTAG().scanIO(
                JTAG.DR,
                DAPRegAccessJTAG.DR_APACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForAP(outdata, indata)
            drwValues[drwIdx] = self.extractD32FromScan35(indata)
            drwIdx = drwIdx + 1
            count = count - 1

        outdata[0] = ((DAPRegAccess.DP_REG_RDBUFF & 0x0C) >> 1) | 1
        self.jtag.rddiJTAG().scanIRDR(
            DAPRegAccessJTAG.IR_LEN,
            DAPRegAccessJTAG.IR_DPACC,
            DAPRegAccessJTAG.DR_DPACC_LEN, outdata, indata,
            JTAG.RTI, True)
        self.waitForDAP(outdata, indata)
        drwValues[drwIdx] = self.extractD32FromScan35(indata)
        return drwValues

    def writeAPDRWn(self, apIdx, values):
        """ Writes the MEM-AP DRW register a number of times
        Params:
            apIdx - the AP (0..255)
            value - array of 4 x 32 bit values to write
        """
        count = len(values)
        if count == 0:
            return
        # Select AP bank for DRW
        self.writeDAP_SELECT(apIdx, DAPRegAccess.AP_REG_DRW >> 4)
        # scan out data looks like:
        # 333 33222222 22221111 11111100 00000000
        # 432 10987654 32109876 54321098 76543210
        # ddd dddddddd dddddddd dddddddd ddddd110
        outdata = self.form35bitRegWriteScan(DAPRegAccess.AP_REG_DRW,
                                             values[0])
        indata = zeros(5, 'b')
        # Select APACC and send initial write request
        self.jtag.rddiJTAG().scanIRDR(
            DAPRegAccessJTAG.IR_LEN,
            DAPRegAccessJTAG.IR_APACC,
            DAPRegAccessJTAG.DR_APACC_LEN,
            outdata, indata,
            JTAG.RTI, True)
        self.waitForAP(outdata, indata)
        count = count - 1
        vIdx = 1
        while count > 0:
            outdata = self.form35bitRegWriteScan(DAPRegAccess.AP_REG_DRW,
                                                 values[vIdx])
            self.jtag.rddiJTAG().scanIO(
                JTAG.DR,
                DAPRegAccessJTAG.DR_APACC_LEN,
                outdata, indata,
                JTAG.RTI, True)
            self.waitForAP(outdata, indata)
            count = count - 1
            vIdx = vIdx + 1


class APBAPMemAccess:
    """Class used to access memory via an APB-AP
    """
    def __init__(self, dapRegAccess, apIdx):
        """ Construction from an object which gives us DAP register accesses
        Params:
            dapRegAccess - an object derived from DAPRegAccess
            apIdx - the AP index number
        """
        self.dapRegAccess = dapRegAccess
        self.apIdx = apIdx

    def readAPMemBlock32(self, address, nWords, csw=0):
        return self.dapRegAccess.readAPMemBlock32(
            self.apIdx, address, nWords,
            csw | DAPRegAccess.AP_REG_CSW_MASTERTYPE_DEBUG)

    def writeAPMemBlock32(self, address, data32, csw=0):
        return self.dapRegAccess.writeAPMemBlock32(
            self.apIdx, address, data32,
            csw | DAPRegAccess.AP_REG_CSW_MASTERTYPE_DEBUG)


class AHBAPMemAccess:
    """Class used to access memory via an (non-Cortex-M system) AHB-AP
    """
    def __init__(self, dapRegAccess, apIdx):
        """ Construction from an object which gives us DAP register accesses
        Params:
            dapRegAccess - an object derived from DAPRegAccess
            apIdx - the AP index number
        """
        self.dapRegAccess = dapRegAccess
        self.apIdx = apIdx

    def readAPMemBlock32(self, address, nWords, csw=0x43000000):
        return self.dapRegAccess.readAPMemBlock32(
            self.apIdx, address, nWords,
            csw)

    def writeAPMemBlock32(self, address, data32, csw=0x43000000):
        return self.dapRegAccess.writeAPMemBlock32(
            self.apIdx, address, data32,
            csw)


class AHBAPCortexMMemAccess:
    """Class used to access memory via a Cortex-M system AHB-AP
    """
    def __init__(self, dapRegAccess, apIdx):
        """ Construction from an object which gives us DAP register accesses
        Params:
            dapRegAccess - an object derived from DAPRegAccess
            apIdx - the AP index number
        """
        self.dapRegAccess = dapRegAccess
        self.apIdx = apIdx

    def readAPMemBlock32(self, address, nWords, csw=0):
        return self.dapRegAccess.readAPMemBlock32(
            self.apIdx, address, nWords,
            csw | DAPRegAccess.AP_REG_CSW_PROT_HPROT1)

    def writeAPMemBlock32(self, address, data32, csw=0):
        return self.dapRegAccess.writeAPMemBlock32(
            self.apIdx, address, data32,
            csw | DAPRegAccess.AP_REG_CSW_PROT_HPROT1)


class AXIAPMemAccess:
    """Class used to access memory via an AXI-AP
    """
    def __init__(self, dapRegAccess, apIdx):
        """ Construction from an object which gives us DAP register accesses
        Params:
            dapRegAccess - an object derived from DAPRegAccess
            apIdx - the AP index number
        """
        self.dapRegAccess = dapRegAccess
        self.apIdx = apIdx

    def readAPMemBlock32(self, address, nWords, csw=0):
        return self.dapRegAccess.readAPMemBlock32(
            self.apIdx, address, nWords,
            csw)

    def writeAPMemBlock32(self, address, data32, csw=0):
        return self.dapRegAccess.writeAPMemBlock32(
            self.apIdx, address, data32,
            csw)
