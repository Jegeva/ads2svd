from com.arm.debug.dtsl.components import PVCacheMemoryAccessor
from com.arm.debug.dtsl.components import PVCacheMemoryCapabilities

CONTENTS, TAGS = 0, 1

def addPVCache(dev, l1i, l1d, l2):
    rams = [
        (l1i, 'L1I', CONTENTS),
        (l1d, 'L1D', CONTENTS),
        (l1i, 'L1ITAG', TAGS),
        (l1d, 'L1DTAG', TAGS),
        (l2, 'L2', CONTENTS),
        (l2, 'L2TAG', TAGS)
    ]
    ramCapabilities = PVCacheMemoryCapabilities()
    for cacheDev, name, id in rams:
        cacheAcc = PVCacheMemoryAccessor(cacheDev, name, id)
        dev.registerAddressFilter(cacheAcc)
        ramCapabilities.addRAM(cacheAcc)
    dev.addCapabilities(ramCapabilities)
