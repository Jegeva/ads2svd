from struct import pack, unpack

from com.arm.rddi import RDDI_ACC_SIZE
from jarray import zeros
from java.lang import StringBuilder
from com.arm.debug.dtsl.components import TraceSource
from com.arm.debug.dtsl.interfaces import ISTMTraceSource
from com.arm.debug.dtsl.interfaces.ITraceSource import TraceSourceEncodingType


SP_CFG = 0x0
SP_CFG_MODE = 0x1
SP_CFG_WT_CAP = 0x2
SP_CFG_TMR_EN = 0x8

SP_CTRL = 0x4
SP_CTRL_EN = 0x1

SP_SECURE = 0x8000
SP_SECURE_COUNT_SECURE = 0x2

SP_MTR_EN = 0xC
SP_WIN_DUR = 0x10
SP_TCFG = 0x800C

SP_DEFAULT_WIN_DUR = 0x40000000

CCI_EVENT = 0x400


class SystemProfiler(TraceSource, ISTMTraceSource):

    def __init__(self, configuration, axi, address, streamID, name):
        TraceSource.__init__(self, streamID, name, TraceSourceEncodingType.STM,
                             "Juno System Profiler - STPv2")
        # Default values for system profiler config
        self.axi = axi
        self.sp_monitors = 0
        self.sp_duration = SP_DEFAULT_WIN_DUR
        self.sp_secure = False
        self.sp_win = False
        self.sp_id = streamID
        self.baseAddress = address

    def setMonitors(self, monitors):
        self.sp_monitors = monitors

    def setWindowDuration(self, duration):
        self.sp_duration = duration

    def setCountSecure(self, countSecure):
        self.sp_secure = countSecure

    def setWindowTimerEnabled(self, enabled):
        self.sp_win = enabled

    def writeReg(self, reg, value):
        self.axi.writeMem(self.baseAddress + reg, False, value)

    def readReg(self, reg):
        return self.axi.readMem(self.baseAddress + reg)

    # If the profiler is enabled, write 1 to CTRL.EN to stop it
    def traceStop(self, traceCapture):
        value = self.readReg(SP_CTRL)
        if (value & SP_CTRL_EN):
            self.writeReg(SP_CTRL, SP_CTRL_EN)

        for i in range(100):
            value = self.readReg(SP_CTRL)

    def traceStart(self, traceCapture):
        self.traceStop(traceCapture)

        if self.isEnabled():
            # initial value of CFG reg - we'll fill in later.
            value = SP_CFG_MODE

            if self.sp_win:
                value |= SP_CFG_WT_CAP
                value |= SP_CFG_TMR_EN

            self.writeReg(SP_CFG, value)

            # Enable the monitors
            # Ignore MTR_ACK
            self.writeReg(SP_MTR_EN, self.sp_monitors)

            if self.sp_win:
                self.writeReg(SP_WIN_DUR, self.sp_duration)

            # secure counting...
            value = self.readReg(SP_SECURE)
            if self.sp_secure:
                value |= SP_SECURE_COUNT_SECURE
            else:
                value &= ~SP_SECURE_COUNT_SECURE
            self.writeReg(SP_SECURE, value)

            # Set the profiler's trace ID
            self.writeReg(SP_TCFG, self.sp_id)

            # Start the profiler by writing CTRL.EN
            self.writeReg(SP_CTRL, SP_CTRL_EN)
