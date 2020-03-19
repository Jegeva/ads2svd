import struct

from com.arm.debug.dtsl.components import CSDAP
from com.arm.debug.dtsl.components import MEMAP

def writeMem(device, addr, data):
    if isinstance(device, CSDAP):
        device.writeMem(0, addr, data)
    elif isinstance(device, MEMAP):
        device.writeMem(addr, data)

# The script must implements streamlineSetupScript(connection)
def streamlineSetupScript(connection):
    for device in connection.getDevices():
        if isinstance(device, CSDAP) or isinstance(device, MEMAP):
            # Set ITM Lock Access Register to enable more write access to the Control Registers
            writeMem(device, 0xE0000FB0, 0xC5ACCE55)
            # Set the ITM Trace Control Register
            # [22:16] Set ATBID to 2
            # [9:8] No timestamp prescaling (00)
            # [4] Disable SWV behavior
            # [3] Enable DWT stimulus
            # [2] Enable sync packets
            # [1] Enables differential timestamps
            # [0] Enable ITM
            writeMem(device, 0xE0000E80, 0x0002000F)
            # Set ITM Trace Control Register to enable tracing on all ITM stimulus ports
            writeMem(device, 0xE0000E00, 0xFFFFFFFF)
            # Set ITM Trace Privilege Register to enable tracing on all ITM stimulus ports
            writeMem(device, 0xE0000E40, 0x0000000F)
            # [22] Disable Cycle count event
            # [21] Enable Folded instruction count event (ARM_Cortex-M3_fold)
            # [20] Enable LSU count event (ARM_Cortex-M3_lsu)
            # [19] Enable Sleep count event (ARM_Cortex-M3_sleep)
            # [18] Enable Interrupt overhead event ( ARM_Cortex-M3_exc)
            # [17] Enable CPI count event (ARM_Cortex-M3_cpi)
            # [16] Enable Interrupt event tracing (ARM_Cortex-M3_exception)
            # [12] Enable PC Sampling event
            # [11:10] Tap at CYCCNT bit 24 (01)
            # [9] select bit [10] to tap (1)
            # [4:1] Reload value for POSTCNT (1111)
            # [0] Enable the CYCCNT counter
            writeMem(device, 0xE0001000, 0x403F161F)
            # Return the Streamline name of the enabled events
            return ("ARM_Cortex-M3_cpi", "ARM_Cortex-M3_exc", "ARM_Cortex-M3_sleep", "ARM_Cortex-M3_lsu", "ARM_Cortex-M3_fold", "ARM_Cortex-M3_exception")

    return ()
