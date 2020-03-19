# Copyright (C) 2009-2011 ARM Limited. All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import SimpleSyncSMPDevice
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture

class Cortex_A9_SingleCoreDSTREAM(DTSLv1):
    def __init__(self, root, coreNo):
        DTSLv1.__init__(self, root)

        self.core = coreNo

        # configure the TPIU for continuous mode, 16 bit
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(True)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        tpiu.setPortSize(16)

        # Enable port for self.core on the funnel.  PTM 0,1
        # are on funnel port 0, 1 respectively.
        funnelDev = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev, "Funnel")
        funnel.setAllPortsDisabled()
        funnel.setPortEnabled(self.core)

        # find first core/PTM
        coreDev = self.findDevice("Cortex-A9")
        ptmDev = self.findDevice("CSPTM")

        # skip through list to desired core/PTM
        for i in range(0, coreNo):
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)

        self.addDeviceInterface(Device(self, coreDev, "Cortex-A9_%d" % coreNo))
        self.PTM = PTMTraceSource(self, ptmDev, 1, "PTM")

        # configure the DSTREAM for 16 bit continuous trace
        DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        DSTREAM.setPortWidth(16)

        # register the trace source with the DSTREAM
        DSTREAM.addTraceSource(self.PTM, coreDev)

        # register other trace components
        DSTREAM.setTraceComponentOrder([ funnel, tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(DSTREAM)

        # automatically handle connection/disconnection
        self.setManagedDevices([ self.PTM, funnel, tpiu, DSTREAM ])

class Cortex_A9_0_DSTREAM(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 0)

class Cortex_A9_1_DSTREAM(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 1)

class Cortex_A9_2_DSTREAM(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 2)

class Cortex_A9_3_DSTREAM(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 3)

class Cortex_A9_4_DSTREAM(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 4)

class Cortex_A9_5_DSTREAM(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 5)

class Cortex_A9_0_DSTREAM_KernelOnly(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 0)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)

class Cortex_A9_1_DSTREAM_KernelOnly(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 1)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)

class Cortex_A9_2_DSTREAM_KernelOnly(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 2)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)

class Cortex_A9_3_DSTREAM_KernelOnly(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 3)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)

class Cortex_A9_4_DSTREAM_KernelOnly(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 4)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)

class Cortex_A9_5_DSTREAM_KernelOnly(Cortex_A9_SingleCoreDSTREAM):
    def __init__(self, root):
        Cortex_A9_SingleCoreDSTREAM.__init__(self, root, 5)
        self.PTM.addTraceRange(0xBF000000,0xFFFFFFFF)

