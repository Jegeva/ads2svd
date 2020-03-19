# Copyright (C) 2009-2011 ARM Limited. All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import RDDISyncSMPDevice

def getFunnelPort(core):

    # select port for desired core
    port = -1
    if core == 3:
        # core 3 isn't on port 3, but on port 4!
        port = 4
    else:
        # otherwise core n is on port n
        port = core
    return port


class TargetA9SingleCoreDSTREAM(DTSLv1):
    def __init__(self, root, coreNo):
        DTSLv1.__init__(self, root)

        self.core = int(coreNo)

        # configure the TPIU for continuous mode, 16bit
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(True)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        tpiu.setPortSize(16)

        # enable port for self. core on the funnel
        funnelDev = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev, "Funnel")
        funnel.setAllPortsDisabled()
        funnel.setPortEnabled(getFunnelPort(self.core))

        # find first core/PTM
        coreDev = self.findDevice("Cortex-A9")
        ptmDev = self.findDevice("CSPTM")

        # skip through list to desired core/PTM
        for i in range(0, self.core):
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)

        # create a Device representing this core
        self.addDeviceInterface(Device(self, coreDev, "Cortex-A9_%d" % self.core))

        # create the PTM for this core
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

class TargetA9_0_DSTREAM(TargetA9SingleCoreDSTREAM):
    def __init__(self, root):
        TargetA9SingleCoreDSTREAM.__init__(self, root, 0)

class TargetA9_1_DSTREAM(TargetA9SingleCoreDSTREAM):
    def __init__(self, root):
        TargetA9SingleCoreDSTREAM.__init__(self, root, 1)

class TargetA9_2_DSTREAM(TargetA9SingleCoreDSTREAM):
    def __init__(self, root):
        TargetA9SingleCoreDSTREAM.__init__(self, root, 2)

class TargetA9_3_DSTREAM(TargetA9SingleCoreDSTREAM):
    def __init__(self, root):
        TargetA9SingleCoreDSTREAM.__init__(self, root, 3)

class TargetA9_0_DSTREAM_KernelOnly(TargetA9SingleCoreDSTREAM):
    def __init__(self, root):
        TargetA9SingleCoreDSTREAM.__init__(self, root, 0)
        self.PTM.addTraceRange(0x7F000000,0xFFFFFFFF)

class TargetA9_1_DSTREAM_KernelOnly(TargetA9SingleCoreDSTREAM):
    def __init__(self, root):
        TargetA9SingleCoreDSTREAM.__init__(self, root, 1)
        self.PTM.addTraceRange(0x7F000000,0xFFFFFFFF)

class TargetA9_2_DSTREAM_KernelOnly(TargetA9SingleCoreDSTREAM):
    def __init__(self, root):
        TargetA9SingleCoreDSTREAM.__init__(self, root, 2)
        self.PTM.addTraceRange(0x7F000000,0xFFFFFFFF)

class TargetA9_3_DSTREAM_KernelOnly(TargetA9SingleCoreDSTREAM):
    def __init__(self, root):
        TargetA9SingleCoreDSTREAM.__init__(self, root, 3)
        self.PTM.addTraceRange(0x7F000000,0xFFFFFFFF)

class TargetA9_SMP(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # find each core and build list of Devices
        coreDev = 1
        coreDevices= []
        for i in range(0, 2):
            # create Device representation for the core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            dev = Device(self, coreDev, "Cortex-A9_%d" % i)
            self.addDeviceInterface(dev)
            coreDevices.append(dev)

        # create SMP device and expose from configuration
        self.addDeviceInterface(RDDISyncSMPDevice(self, "SMP", 1, coreDevices))



class TargetA9_SMP_DSTREAM(DTSLv1):
    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # configure the TPIU for continuous mode, 16bit
        tpiuDev = self.findDevice("CSTPIU")
        tpiu = CSTPIU(self, tpiuDev, "TPIU")
        tpiu.setEnabled(True)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        tpiu.setPortSize(16)

        # enable ports for each core on the funnel
        funnelDev = self.findDevice("CSTFunnel")
        funnel = CSFunnel(self, funnelDev, "Funnel")
        funnel.setAllPortsDisabled()

        # configure the DSTREAM for 16 bit continuous trace
        DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        DSTREAM.setPortWidth(16)

        # find each core/PTM and enable trace
        coreDev = 1
        ptmDev = 1
        coreDevices= []
        self.PTMs = []
        for i in range(0, 2):
            # find the next core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)

            # create the PTM for this core
            streamID = i+1
            PTM = PTMTraceSource(self, ptmDev, streamID, "PTM%d" % i)
            self.PTMs.append(PTM)

            # enable the funnel for this core
            funnel.setPortEnabled(getFunnelPort(i))

            # register trace source with DSTREAM
            DSTREAM.addTraceSource(PTM, coreDev)

            # create Device representation for the core
            dev = Device(self, coreDev, "Cortex-A9_%d" % i)
            self.addDeviceInterface(dev)
            coreDevices.append(dev)

        # register other trace components
        DSTREAM.setTraceComponentOrder([ funnel, tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.setManagedDevices(self.PTMs + [ funnel, tpiu, DSTREAM ])

        # create SMP device and expose from configuration
        self.addDeviceInterface(RDDISyncSMPDevice(self, "SMP", 1, coreDevices))

class TargetA9_SMP_DSTREAM_KERNEL_ONLY(TargetA9_SMP_DSTREAM):
    def __init__(self, root):
        TargetA9_SMP_DSTREAM.__init__(self, root)

        for ptm in self.PTMs:
            ptm.addTraceRange(0x7F000000,0xFFFFFFFF)
