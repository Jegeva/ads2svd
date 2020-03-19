
# JTAG scan types
JTAGS_IR = 0
JTAGS_DR = 1

# JTAG state names
(JTAGS_TLR, JTAGS_RTI, JTAGS_PDR, JTAGS_PIR, JTAGS_SHD, JTAGS_SHI,
 JTAGS_SDR, JTAGS_CDR, JTAGS_E1D, JTAGS_E2D, JTAGS_UDR,
 JTAGS_SIR, JTAGS_CIR, JTAGS_E1I, JTAGS_E2I, JTAGS_UIR,
 JTAGS_LAST) = range(0, 17)
JTAGS_LAST_REST=JTAGS_SDR

# JTAG state names (for debug/logging)
JTAG_StateNames = [
    "TLR", "RTI", "PDR", "PIR",
    "SHD", "SHI", "SDR", "CDR",
    "E1D", "E2D", "UDR", "SIR",
    "CIR", "E1I", "E2I", "UIR",
    "???"
    ]

def JTAGStateName(state):
    if state >= len(JTAG_StateNames):
        return JTAG_StateNames[JTAGS_LAST]
    else:
        return JTAG_StateNames[state]


# JTAG state transition map
# for each starting state we have a (length, bit values) tuple for each
# destination state
# the bit values are clocked lsb first

trans_tlr = [
    (1, 0x01), # TLR
    (1, 0x00), # RTI
    (5, 0x0A), # PDR: 01010
    (6, 0x16), # PIR: 010110
    (4, 0x02), # SHD: 0010
    (5, 0x06), # SHI: 00110
    (2, 0x02), # SDR: 10
    ]

trans_rti = [
    (3, 0x07), # TLR: 111
    (1, 0x00), # RTI: 0
    (4, 0x05), # PDR: 0101
    (5, 0x0B), # PIR: 01011
    (3, 0x01), # SHD: 001
    (4, 0x03), # SHI: 0011
    (1, 0x01), # SDR: 1
    ]

trans_pdr = [
    (5, 0x1F), # TLR: 11111
    (3, 0x03), # RTI: 011
    (6, 0x17), # PDR: 010111
    (7, 0x2F), # PIR: 0101111
    (2, 0x01), # SHD: 01
    (6, 0x0F), # SHI: 001111
    (3, 0x07), # SDR: 111
    ]

trans_pir = [
    (5, 0x1F), # TLR: 11111
    (3, 0x03), # RTI: 011
    (6, 0x17), # PDR: 010111
    (7, 0x2F), # PIR: 0101111
    (5, 0x07), # SHD: 00111
    (2, 0x01), # SHI: 01
    (3, 0x07), # SDR: 111
    ]

trans_shd = [
    (5, 0x1F), # TLR: 11111
    (3, 0x03), # RTI: 011
    (2, 0x01), # PDR: 01
    (7, 0x2F), # PIR: 0101111
    (0, 0x00), # SHD: illegal
    (0, 0x00), # SHI: illegal
    (3, 0x07), # SDR: 111
    ]

trans_shi = [
    (5, 0x1F), # TLR: 11111
    (3, 0x03), # RTI: 011
    (6, 0x17), # PDR: 010111
    (2, 0x01), # PIR: 01
    (0, 0x00), # SHD: illegal
    (0, 0x00), # SHI: illegal
    (3, 0x07), # SDR: 111
    ]

trans_sdr = [
    (2, 0x03), # TLR: 11
    (3, 0x03), # RTI: 011
    (3, 0x02), # PDR: 010
    (4, 0x05), # PIR: 0101
    (2, 0x00), # SHD: 00
    (3, 0x01), # SHI: 001
    (0, 0x00), # SDR: 0
    ]

# top level state map
# usage: JTAG_TRANSITIONS[start][end] will produce (length, values) tuple
JTAG_TRANSITIONS = [
    trans_tlr,                    # from TestLogicReset
    trans_rti,                    # from RunTestIdle
    trans_pdr,                    # from PauseDR
    trans_pir,                    # from PauseIR
    trans_shd,                    # from ShiftDR
    trans_shi,                    # from ShiftIR
    trans_sdr,                    # from SelectDR
    ]


def GenerateTAPMoveData(curr, end):
    if curr > JTAGS_LAST_REST:
        # not a valid state
        return (0, 0)

    if end > JTAGS_LAST_REST:
        # not a valid resting state
        return (0, 0)

    # index into table
    trans = JTAG_TRANSITIONS[curr][end]
    return trans



def bytesToInt(data, bits):
    '''Pack a sequence of bytes into a little endian integer
    '''

    r = 0
    for i in range(0, bits/8):
        shift = (i * 8)
        if i < len(data):
            r |= (data[i] << shift) & (0xFF << shift)
    if (bits % 8) != 0:
        b = bits/8
        shift = (b * 8)
        mask = ((1 << (bits % 8)) - 1)
        if b < len(data):
            r |= (data[b] << shift) & (mask << shift)
    return r


def intToBytes(v, bits):
    '''Unpack a little endian integer into a sequence of bytes
    '''

    r = []
    for i in range(0, bits/8):
        r.append(v & 0xFF)
        v >>= 8
    if (bits % 8) != 0:
        mask = ((1 << (bits % 8)) - 1)
        r.append(v & mask)
    return r
