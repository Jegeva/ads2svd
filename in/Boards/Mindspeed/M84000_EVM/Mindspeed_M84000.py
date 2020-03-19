# Copyright (C) 2009-2011 ARM Limited. All rights reserved.
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CTISyncSMPDevice
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSFunnel
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import ETBTraceCapture
from com.arm.debug.dtsl.components import DSTREAMTraceCapture

PTM_ATB_ID_BASE = 2

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



class SMP_Cluster_0(DTSLv1):
    '''SMP configuration for cores 0-3'''

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # find trace output cross trigger
        outCTIDev = self.findDevice("CSCTI")

        # find each core and build list of Devices
        coreDev = 1
        coreCTIDev = outCTIDev
        coreDevices= []
        ctis = []
        ctiMap = {}
        for i in range(0, 4):
            # create Device representation for the core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)

            dev = Device(self, coreDev, "Cortex-A9_%d" % i)
            self.addDeviceInterface(dev)
            coreDevices.append(dev)

            # setup cross trigger to stop cores together
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            coreCTI.enableInputEvent(0, 0) # use channel 0 for sync stop
            coreCTI.enableOutputEvent(0, 0)
            coreCTI.enableOutputEvent(7, 1) # use channel 1 for sync start
            ctis.append(coreCTI)
            ctiMap[dev] = coreCTI

        # automatically handle connection/disconnection
        self.setManagedDevices(ctis)

        # create SMP device and expose from configuration
        self.addDeviceInterface(CTISyncSMPDevice(self, "SMP", 1, coreDevices, ctiMap, 1, 0))



class SMP_Cluster_0_DSTREAM(DTSLv1):
    '''SMP configuration for cores 0-3 with DSTREAM trace'''

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

        # enable cross trigger using channel 2 for trace trigger
        outCTIDev = self.findDevice("CSCTI")
        outCTI = CSCTI(self, outCTIDev, "CTI_out")
        outCTI.enableOutputEvent(3, 2) # TPIU trigger input is CTI out 3

        # configure the DSTREAM for 16 bit continuous trace
        DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        DSTREAM.setPortWidth(16)

        # find each core/PTM and enable trace
        coreDev = 1
        ptmDev = 1
        coreCTIDev = outCTIDev
        coreDevices= []
        self.PTMs = []
        ctis = []
        ctiMap = {}
        for i in range(0, 4):
            # find the next core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)

            # create the PTM for this core
            streamID = PTM_ATB_ID_BASE + i
            PTM = PTMTraceSource(self, ptmDev, streamID, "PTM%d" % i)
            self.PTMs.append(PTM)

            # enable the funnel for this core
            #   assumes core N is on funnel port N
            funnel.setPortEnabled(i)

            # register trace source with DSTREAM
            DSTREAM.addTraceSource(PTM, coreDev)

            # create Device representation for the core
            dev = Device(self, coreDev, "Cortex-A9_%d" % i)
            self.addDeviceInterface(dev)
            coreDevices.append(dev)

            # setup cross trigger to stop cores together and forward trace trigger
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            coreCTI.enableInputEvent(0, 0) # use channel 0 for sync stop
            coreCTI.enableOutputEvent(0, 0)
            coreCTI.enableOutputEvent(7, 1) # use channel 1 for sync start
            coreCTI.enableInputEvent(6, 2) # use channel 2 for PTM trigger
            ctis.append(coreCTI)
            ctiMap[dev] = coreCTI

        # register other trace components
        DSTREAM.setTraceComponentOrder([ funnel, tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.setManagedDevices(self.PTMs + ctis + [ funnel, tpiu, outCTI, DSTREAM ])

        # create SMP device and expose from configuration
        self.addDeviceInterface(CTISyncSMPDevice(self, "SMP", 1, coreDevices, ctiMap, 1, 0))



class SMP_Cluster_1(DTSLv1):
    '''SMP configuration for cores 4-5'''

    def __init__(self, root):
        DTSLv1.__init__(self, root)

        # find trace output cross trigger
        outCTIDev = self.findDevice("CSCTI")

        # skip past the cores & ctis of the first cluster
        coreDev = 1
        coreCTIDev = outCTIDev
        for i in range(0, 4):
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)

        # find each core & CTI in the 2nd cluster and build list of Devices
        coreDevices= []
        ctis = []
        ctiMap = {}
        for i in range(0, 2):
            # create Device representation for the core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)

            dev = Device(self, coreDev, "Cortex-A9_%d" % i)
            self.addDeviceInterface(dev)
            coreDevices.append(dev)

            # setup cross trigger to stop cores together
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            coreCTI.enableInputEvent(0, 0) # use channel 0 for sync stop
            coreCTI.enableOutputEvent(0, 0)
            coreCTI.enableOutputEvent(7, 1) # use channel 1 for sync start
            ctis.append(coreCTI)
            ctiMap[dev] = coreCTI

        # automatically handle connection/disconnection
        self.setManagedDevices(ctis)

        # create SMP device and expose from configuration
        self.addDeviceInterface(CTISyncSMPDevice(self, "SMP", 1, coreDevices, ctiMap, 1, 0))



class SMP_Cluster_1_DSTREAM(DTSLv1):
    '''SMP configuration for cores 4-5 with DSTREAM trace'''

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

        # enable cross trigger using channel 2 for trace trigger
        outCTIDev = self.findDevice("CSCTI")
        outCTI = CSCTI(self, outCTIDev, "CTI_out")
        outCTI.enableOutputEvent(3, 2) # TPIU trigger input is CTI out 3

        # configure the DSTREAM for 16 bit continuous trace
        DSTREAM = DSTREAMTraceCapture(self, "DSTREAM")
        DSTREAM.setTraceMode(DSTREAMTraceCapture.TraceMode.Continuous)
        DSTREAM.setPortWidth(16)

        # skip past the cores, PTMs & ctis of the first cluster
        coreDev = 1
        ptmDev = 1
        coreCTIDev = outCTIDev
        for i in range(0, 4):
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)

        # find each core/PTM and enable trace
        coreDevices= []
        self.PTMs = []
        ctis = []
        ctiMap = {}
        for i in range(0, 2):
            # find the next core
            coreDev = self.findDevice("Cortex-A9", coreDev+1)
            ptmDev = self.findDevice("CSPTM", ptmDev+1)
            coreCTIDev = self.findDevice("CSCTI", coreCTIDev+1)

            # create the PTM for this core
            streamID = PTM_ATB_ID_BASE + i
            PTM = PTMTraceSource(self, ptmDev, streamID, "PTM%d" % i)
            self.PTMs.append(PTM)

            # enable the funnel for this core
            #   assumes core N is on funnel port N
            funnel.setPortEnabled(4+i)

            # register trace source with DSTREAM
            DSTREAM.addTraceSource(PTM, coreDev)

            # create Device representation for the core
            dev = Device(self, coreDev, "Cortex-A9_%d" % i)
            self.addDeviceInterface(dev)
            coreDevices.append(dev)

            # setup cross trigger to stop cores together and forward trace trigger
            coreCTI = CSCTI(self, coreCTIDev, "CTI_%d" % i)
            coreCTI.enableInputEvent(0, 0) # use channel 0 for sync stop
            coreCTI.enableOutputEvent(0, 0)
            coreCTI.enableOutputEvent(7, 1) # use channel 1 for sync start
            coreCTI.enableInputEvent(6, 2) # use channel 2 for PTM trigger
            ctis.append(coreCTI)
            ctiMap[dev] = coreCTI

        # register other trace components
        DSTREAM.setTraceComponentOrder([ funnel, tpiu ])

        # register the DSTREAM with the configuration
        self.addTraceCaptureInterface(DSTREAM)

        # automatically handle connection/disconnection to trace components
        self.setManagedDevices(self.PTMs + ctis + [ funnel, tpiu, outCTI, DSTREAM ])

        # create SMP device and expose from configuration
        self.addDeviceInterface(CTISyncSMPDevice(self, "SMP", 1, coreDevices, ctiMap, 1, 0))



