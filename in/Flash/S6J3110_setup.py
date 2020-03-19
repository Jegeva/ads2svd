from com.arm.debug.flashprogrammer.IFlashClient import MessageLevel

from flashprogrammer.device import ensureDeviceOpen
from flashprogrammer.execution import ensureDeviceStopped
from flashprogrammer.device_memory import writeToTarget, readFromTarget, intToBytes, intFromBytes

import time

import sys

# Security Checker related definitions
REG_APB__SCCFG_UNLCK        = 0x000C01A4
REG_APB__SCSCU_CNTL         = 0x000C01B4
KEY__SCCFG_UNLOCK           = 0x5ECACCE5
KEY__SCCFG_LOCK             = 0xA135331A
VALUE_WDGRST_MASK           = 0x00000100
# TCMRAM related definitions
TCMRAM_START_ADDRESS           =    0x00000000
TCMRAM_SIZE_BYTES              =    (64*1024)

SYSRAM_START_ADDRESS            =   0x02000000
SYSRAM_SIZE_BYTES               =   (256*1024)

# Reset controller related definitions
REG_AHB__SYSC0_PROTKEYR     = 0xB0600000
REG_AHB__SYSC_RSTCNTR       = 0xB0600380
REG_AHB__SYSC_RSTCAUSEUR    = 0xB0600390
KEY__SYSC0_UNLOCK           = 0x5CACCE55
VALUE__TRIGGER_SWHRST_DBGR  = 0xDAA50000

def findDeviceByName(conn, name):
    for dev in conn.getDevices():
        if dev.getName() == name:
            return dev
    raise RuntimeError, "Device %s not found" % name

def setup(client, services):
    # get a connection to the core
    conn = services.getConnection()
    dev = conn.getDeviceInterfaces().get("Cortex-R5")
    ensureDeviceOpen(dev)
    ensureDeviceStopped(dev)

    devAPB = findDeviceByName(conn, "APB")
    ensureDeviceOpen(devAPB)

    # Mask watch dog reset
    writeToTarget(devAPB, REG_APB__SCCFG_UNLCK, intToBytes(KEY__SCCFG_UNLOCK)) # Unlock SCCFG_UNLCK
    writeToTarget(devAPB, REG_APB__SCSCU_CNTL, intToBytes(VALUE_WDGRST_MASK))  # Set SCSCU_CNTL.WDG_RST_MASK bit
    writeToTarget(devAPB, REG_APB__SCCFG_UNLCK, intToBytes(KEY__SCCFG_LOCK))   # Lock SCCFG_UNLCK

    # Initialise TCMRAM
    writeToTarget(dev, TCMRAM_START_ADDRESS, "\x00" * TCMRAM_SIZE_BYTES)






