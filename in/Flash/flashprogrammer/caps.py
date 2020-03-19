from jarray import zeros
from struct import pack

from com.arm.rddi import RDDI_CAP_ID
from com.arm.rddi import RDDI

from com.arm.debug.dtsl.nativelayer import NativeException

def _to_u32(val):
    return val + 0x100000000 if val < 0 else val


def _get_capability_size(core, id):
    num_bytes = zeros(1, 'i')
    try:
        core.getCapabilities(id, None, num_bytes)
    except NativeException, e:
        err = e.getRDDIErrorCode()
        if err != RDDI.RDDI_BUFFER_OVERFLOW:
            raise
    return num_bytes[0]


def _get_capability(core, id):
    num_bytes = zeros(1, 'i')
    # initial guess at block size - should be enough for most blocks
    block = zeros(0x400, 'i')
    try:
        core.getCapabilities(id, block, num_bytes)
    except NativeException, e:
        err = e.getRDDIErrorCode()
        if err != RDDI.RDDI_BUFFER_OVERFLOW:
            raise
        else:
            # retry with actual block size
            block = zeros((num_bytes[0]+3) / 4, 'i')
            core.getCapabilities(id, block, num_bytes)
    block = block[:(num_bytes[0]+3)/4] # trim trailing unused data
    return map(_to_u32, block)


def _c_string_at(s, offset):
    return s[offset:s.find('\0', offset)]


# RDDI_CAP_REGINFO block is 3 word header followed by chunks of 5 words.
def _gen_reginfo_chunks(block):
    for i in range(3, len(block), 5):
        yield block[i:i + 5]


def reg_map(core):
    r_caps = _get_capability(core, RDDI_CAP_ID.RDDI_CAP_REGINFO)
    s_caps = _get_capability(core, RDDI_CAP_ID.RDDI_CAP_STRINGS)

    # RDDI_CAP_STRINGS block as one long string
    strings = ''.join([pack('<I', x) for x in s_caps])

    # Build the name->address map
    regmap = dict((_c_string_at(strings, rec[0]).upper(), rec[4])
                  for rec in _gen_reginfo_chunks(r_caps))

    # PC is special
    if 'PC' not in regmap:
        regmap['PC'] = r_caps[2]

    return regmap


