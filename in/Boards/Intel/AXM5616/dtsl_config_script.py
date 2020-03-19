'''
Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.
'''
from com.arm.debug.dtsl.configurations import ConfigurationBaseSDF
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import FormatterMode
from com.arm.debug.dtsl.components import AXIAP
from com.arm.debug.dtsl.components import APBAP
from com.arm.debug.dtsl.components import AHBAP
from com.arm.debug.dtsl.configurations import TimestampInfo
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.configurations.options import IIntegerOption
from com.arm.debug.dtsl.components import CSTMC
from com.arm.debug.dtsl.components import TMCETBTraceCapture
from com.arm.debug.dtsl.components import CSCTI
from com.arm.debug.dtsl.components import ETMv4TraceSource
from com.arm.debug.dtsl.components import CSTPIU
from com.arm.debug.dtsl.components import CSATBReplicator
from com.arm.debug.dtsl.components import STMTraceSource
from jarray import zeros

clusterNames = ["Cortex-A57_SMP_0", "Cortex-A57_SMP_1", "Cortex-A57_SMP_2", "Cortex-A57_SMP_3"]
clusterCores = [["Cortex-A57_0_0", "Cortex-A57_0_1", "Cortex-A57_0_2", "Cortex-A57_0_3"], ["Cortex-A57_1_0", "Cortex-A57_1_1", "Cortex-A57_1_2", "Cortex-A57_1_3"], ["Cortex-A57_2_0", "Cortex-A57_2_1", "Cortex-A57_2_2", "Cortex-A57_2_3"], ["Cortex-A57_3_0", "Cortex-A57_3_1", "Cortex-A57_3_2", "Cortex-A57_3_3"]]
coreNames_cortexA57 = ["Cortex-A57_0_0", "Cortex-A57_0_1", "Cortex-A57_0_2", "Cortex-A57_0_3", "Cortex-A57_1_0", "Cortex-A57_1_1", "Cortex-A57_1_2", "Cortex-A57_1_3", "Cortex-A57_2_0", "Cortex-A57_2_1", "Cortex-A57_2_2", "Cortex-A57_2_3", "Cortex-A57_3_0", "Cortex-A57_3_1", "Cortex-A57_3_2", "Cortex-A57_3_3"]
numberOfClusters = 4

TIMESTAMP_CONTROL_REGISTER = 0x80140000

# Import core specific functions
import a57_rams


class DtslScript(ConfigurationBaseSDF):
    @staticmethod
    def getOptionList():
        return [
            DTSLv1.tabSet("options", "Options", childOptions=
                [DTSLv1.tabPage("trace", "Trace Capture", childOptions=[
                    DTSLv1.enumOption('traceCapture', 'Trace capture method', defaultValue="none",
                        values = [("none", "None"), ("CSTMC_0", "On Chip Trace Buffer (CSTMC_0/ETF)"), ("CSTMC_1", "On Chip Trace Buffer (CSTMC_1/ETF)"), ("CSTMC_2", "On Chip Trace Buffer (CSTMC_2/ETF)"), ("CSTMC_3", "On Chip Trace Buffer (CSTMC_3/ETF)"), ("CSTMC_4", "On Chip Trace Buffer (CSTMC_4/ETF)"), ("CSTMC_5", "On Chip Trace Buffer (CSTMC_5/ETF)")],
                        setter=DtslScript.setTraceCaptureMethod),
                    DTSLv1.infoElement("traceOpts", "Trace Options", childOptions=[
                        DTSLv1.integerOption('timestampFrequency', 'Timestamp frequency', defaultValue=25000000, isDynamic=False, description="This value will be used to set the Counter Base Frequency ID Register of the Timestamp generator.\nIt represents the number of ticks per second and is used to translate the timestamp value reported into a number of seconds.\nNote that changing this value may not result in a change in the observed frequency."),
                    ]),
                ])]
                +[DTSLv1.tabPage("Cortex-A57_SMP_%d" % cluster, "Cluster %d" % cluster, childOptions=[
                    DTSLv1.booleanOption('coreTrace', 'Enable Cortex-A57_SMP_%d core trace' % cluster, defaultValue=False,
                        childOptions = [
                            DTSLv1.booleanOption('Cortex-A57_SMP_%d_0' % cluster, 'Enable Cortex-A57_%d_0 trace' % cluster, defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A57_SMP_%d_1' % cluster, 'Enable Cortex-A57_%d_1 trace' % cluster, defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A57_SMP_%d_2' % cluster, 'Enable Cortex-A57_%d_2 trace' % cluster, defaultValue=True),
                            DTSLv1.booleanOption('Cortex-A57_SMP_%d_3' % cluster, 'Enable Cortex-A57_%d_3 trace' % cluster, defaultValue=True),
                            DTSLv1.booleanOption('timestamp', "Enable ETM Timestamps", description="Controls the output of timestamps into the ETM output streams", defaultValue=True),
                            DTSLv1.booleanOption('contextIDs', "Enable ETM Context IDs", description="Controls the output of context ID values into the ETM output streams", defaultValue=True),
                            ETMv4TraceSource.cycleAccurateOption(DtslScript.getSourcesForCluster("Cortex-A57_SMP_%d" % cluster)),
                        ]
                    ),
                ]) for cluster in range(numberOfClusters) ]
                +[DTSLv1.tabPage("stm", "STM", childOptions=[
                    DTSLv1.booleanOption('CSSTM_0', 'Enable System STM trace', defaultValue=False),
                    DTSLv1.booleanOption('CSSTM_1', 'Enable CCN-504 STM trace', defaultValue=False),
                ])]
                +[DTSLv1.tabPage("rams", "Cache RAMs", childOptions=[
                    # Turn cache debug mode on/off
                    DTSLv1.booleanOption('cacheDebug', 'Cache debug mode',
                                         description='Turning cache debug mode on enables reading the cache RAMs. Enabling it may adversely impact debug performance.',
                                         defaultValue=False, isDynamic=True),
                    DTSLv1.booleanOption('cachePreserve', 'Preserve cache contents in debug state',
                                         description='Preserve the contents of caches while the core is stopped.',
                                         defaultValue=False, isDynamic=True),
                ])]
            )
        ]
    
    def __init__(self, root):
        ConfigurationBaseSDF.__init__(self, root)
        
        self.discoverDevices()
        self.createTraceCapture()
    
    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+
    
    def discoverDevices(self):
        '''Find and create devices'''
        
        #MemAp devices
        AXIAP(self, self.findDevice("CSMEMAP_0"), "CSMEMAP_0")
        self.APB = APBAP(self, self.findDevice("CSMEMAP_1"), "CSMEMAP_1")
        AHBAP(self, self.findDevice("CSMEMAP_2"), "CSMEMAP_2")
        
        # Trace start/stop CTIs
        CSCTI(self, self.findDevice("CSCTI_0"), "CSCTI_0")
        
        CSCTI(self, self.findDevice("CSCTI_1"), "CSCTI_1")
        
        CSCTI(self, self.findDevice("CSCTI_2"), "CSCTI_2")
        
        CSCTI(self, self.findDevice("CSCTI_3"), "CSCTI_3")
        
        CSCTI(self, self.findDevice("CSCTI_4"), "CSCTI_4")
        
        CSCTI(self, self.findDevice("CSCTI_5"), "CSCTI_5")
        
        CSCTI(self, self.findDevice("CSCTI_6"), "CSCTI_6")
        
        

        # The ATB stream ID which will be assigned to trace sources.
        streamID = 1
        
        stm = STMTraceSource(self, self.findDevice("CSSTM_0"), streamID, "CSSTM_0")
        stm.setEnabled(False)
        streamID += 1
        
        stm = STMTraceSource(self, self.findDevice("CSSTM_1"), streamID, "CSSTM_1")
        stm.setEnabled(False)
        streamID += 1
        
        self.cortexA57cores = []
        # Ensure that macrocell StreamIDs are grouped such that they can be filtered by a programmable replicator.
        streamID += (0x10 - (streamID % 0x10))
        for coreName in (coreNames_cortexA57):
            # Create core
            coreDevice = a57_rams.A57CoreDevice(self, self.findDevice(coreName), coreName)
            self.cortexA57cores.append(coreDevice)
            self.addDeviceInterface(coreDevice)
            a57_rams.registerInternalRAMs(coreDevice)
            
            # Create CTI (if a CTI exists for this core)
            ctiName = self.getCTINameForCore(coreName)
            if not ctiName is None:
                coreCTI = CSCTI(self, self.findDevice(ctiName), ctiName)
            
            # Create Trace Macrocell (if a macrocell exists for this core - disabled by default - will enable with option)
            tmName = self.getTraceSourceNameForCore(coreName)
            if not tmName == None:
                tm = ETMv4TraceSource(self, self.findDevice(tmName), streamID, tmName)
                streamID += 2
                tm.setEnabled(False)
            
        tmc = CSTMC(self, self.findDevice("CSTMC_0"), "CSTMC_0")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("CSTMC_1"), "CSTMC_1")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("CSTMC_2"), "CSTMC_2")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("CSTMC_3"), "CSTMC_3")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("CSTMC_4"), "CSTMC_4")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tmc = CSTMC(self, self.findDevice("CSTMC_5"), "CSTMC_5")
        tmc.setMode(CSTMC.Mode.ETF)
        
        tpiu = CSTPIU(self, self.findDevice("CSTPIU"), "CSTPIU")
        tpiu.setEnabled(False)
        tpiu.setFormatterMode(FormatterMode.CONTINUOUS)
        
        # Create and Configure Funnels
        self.createFunnel("CSTFunnel_0")
        self.createFunnel("CSTFunnel_1")
        self.createFunnel("CSTFunnel_2")
        self.createFunnel("CSTFunnel_3")
        self.createFunnel("CSTFunnel_4")
        
        # Replicators
        CSATBReplicator(self, self.findDevice("CSATBReplicator"), "CSATBReplicator")
        
        
        self.setupCTISyncSMP()
        
    def createTraceCapture(self):
        # ETF Devices
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_0"), "CSTMC_0")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_1"), "CSTMC_1")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_2"), "CSTMC_2")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_3"), "CSTMC_3")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_4"), "CSTMC_4")
        self.addTraceCaptureInterface(etfTrace)
        etfTrace = TMCETBTraceCapture(self, self.getDeviceInterface("CSTMC_5"), "CSTMC_5")
        self.addTraceCaptureInterface(etfTrace)


    def verify(self):
        addr = 0x00000FE0
        expected = [ 0x4E, 0x90, 0x08, 0x0 ]
        mask = [ 0xFF, 0xFF, 0x0F, 0x0 ]
        return self.confirmValue(self.APB, addr, expected, mask)


    def confirmValue(self, ap, addr, expected, mask):
        buffer = zeros(len(expected), 'i')
        ap.readMem(addr, len(expected), buffer)
        actual = [ buffer[i] for i in range(len(buffer)) ]
        for e, m, a in zip(expected, mask, actual):
            if ((a & m) != (e & m)):
                print "Expected %08x but read %08x (with mask %08x)" % (e, a, m)
                return False
        return True

    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+
    
    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        if not self.isConnected():
            self.setInitialOptions()
        
        self.updateDynamicOptions()
        
    def setInitialOptions(self):
        '''Set the initial options'''
        
        traceMode = self.getOptionValue("options.trace.traceCapture")
        
        coreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace")
        for core in range(len(clusterCores[0])):
            tmName = self.getTraceSourceNameForCore(clusterCores[0][core])
            if tmName:
                coreTM = self.getDeviceInterface(tmName)
                thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace.Cortex-A57_SMP_0_%d" % core)
                enableSource = coreTraceEnabled and thisCoreTraceEnabled
                self.setTraceSourceEnabled(tmName, enableSource)
                coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace.timestamp"))
                self.setContextIDEnabled(coreTM,
                                     self.getOptionValue("options.Cortex-A57_SMP_0.coreTrace.contextIDs"),
                                     "32")
        
        if numberOfClusters > 1:
            coreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_1.coreTrace")
            for core in range(len(clusterCores[1])):
                tmName = self.getTraceSourceNameForCore(clusterCores[1][core])
                if tmName:
                    coreTM = self.getDeviceInterface(tmName)
                    thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_1.coreTrace.Cortex-A57_SMP_1_%d" % core)
                    enableSource = coreTraceEnabled and thisCoreTraceEnabled
                    self.setTraceSourceEnabled(tmName, enableSource)
                    coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A57_SMP_1.coreTrace.timestamp"))
                    self.setContextIDEnabled(coreTM,
                                         self.getOptionValue("options.Cortex-A57_SMP_1.coreTrace.contextIDs"),
                                         "32")
        
        if numberOfClusters > 2:
            coreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_2.coreTrace")
            for core in range(len(clusterCores[2])):
                tmName = self.getTraceSourceNameForCore(clusterCores[2][core])
                if tmName:
                    coreTM = self.getDeviceInterface(tmName)
                    thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_2.coreTrace.Cortex-A57_SMP_2_%d" % core)
                    enableSource = coreTraceEnabled and thisCoreTraceEnabled
                    self.setTraceSourceEnabled(tmName, enableSource)
                    coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A57_SMP_2.coreTrace.timestamp"))
                    self.setContextIDEnabled(coreTM,
                                         self.getOptionValue("options.Cortex-A57_SMP_2.coreTrace.contextIDs"),
                                         "32")
        
        if numberOfClusters > 3:
            coreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_3.coreTrace")
            for core in range(len(clusterCores[3])):
                tmName = self.getTraceSourceNameForCore(clusterCores[3][core])
                if tmName:
                    coreTM = self.getDeviceInterface(tmName)
                    thisCoreTraceEnabled = self.getOptionValue("options.Cortex-A57_SMP_3.coreTrace.Cortex-A57_SMP_3_%d" % core)
                    enableSource = coreTraceEnabled and thisCoreTraceEnabled
                    self.setTraceSourceEnabled(tmName, enableSource)
                    coreTM.setTimestampingEnabled(self.getOptionValue("options.Cortex-A57_SMP_3.coreTrace.timestamp"))
                    self.setContextIDEnabled(coreTM,
                                         self.getOptionValue("options.Cortex-A57_SMP_3.coreTrace.contextIDs"),
                                         "32")
        
        stmEnabled = self.getOptionValue("options.stm.CSSTM_0")
        self.setTraceSourceEnabled("CSSTM_0", stmEnabled)
        
        stmEnabled = self.getOptionValue("options.stm.CSSTM_1")
        self.setTraceSourceEnabled("CSSTM_1", stmEnabled)
        
        self.configureTraceCapture(traceMode)
        
    def updateDynamicOptions(self):
        '''Update the dynamic options'''
        
        for core in range(len(self.cortexA57cores)):
            a57_rams.applyCacheDebug(configuration = self,
                                     optionName = "options.rams.cacheDebug",
                                     device = self.cortexA57cores[core])
            a57_rams.applyCachePreservation(configuration = self,
                                            optionName = "options.rams.cachePreserve",
                                            device = self.cortexA57cores[core])
        
    def setTraceCaptureMethod(self, method):
        '''Simply call into the configuration to enable the trace capture device.
        CTI devices associated with the capture will also be configured'''
        self.enableTraceCapture(method)
    
    @staticmethod
    def getSourcesForCluster(cluster):
        '''Get the Trace Sources for a given coreType
           Use parameter-binding to ensure that the correct Sources
           are returned for the core type and cluster passed only'''
        def getClusterSources(self):
            return self.getTraceSourcesForCluster(cluster)
        return getClusterSources
    
    # +------------------------------+
    # | Target independent functions |
    # +------------------------------+
    
    def postConnect(self):
        ConfigurationBaseSDF.postConnect(self)
        
        try:
            freq = self.getOptionValue("options.trace.traceOpts.timestampFrequency")
        except:
            return
        
        # Update the value so the trace decoder can access it
        tsInfo = TimestampInfo(freq)
        self.setTimestampInfo(tsInfo)

        # enable global timestamping via the APB
        # set control_register bit 0
        self.APB.writeMem(TIMESTAMP_CONTROL_REGISTER, 0x1)
        
class DtslScript_AXM5616(DtslScript):
    @staticmethod
    def getOptionList():
        global numberOfClusters
        numberOfClusters = 4
        return DtslScript.getOptionList()
    
    def __init__(self, root):
        global numberOfClusters
        numberOfClusters = 4
        DtslScript.__init__(self, root)

class DtslScript_AXM5612(DtslScript):
    @staticmethod
    def getOptionList():
        global numberOfClusters
        numberOfClusters = 3
        return DtslScript.getOptionList()
    
    def __init__(self, root):
        global numberOfClusters
        numberOfClusters = 3
        DtslScript.__init__(self, root)

class DtslScript_AXM5608(DtslScript):
    @staticmethod
    def getOptionList():
        global numberOfClusters
        numberOfClusters = 2
        return DtslScript.getOptionList()
    
    def __init__(self, root):
        global numberOfClusters
        numberOfClusters = 2
        DtslScript.__init__(self, root)

class DtslScript_AXM5604(DtslScript):
    @staticmethod
    def getOptionList():
        global numberOfClusters
        numberOfClusters = 1
        return DtslScript.getOptionList()
    
    def __init__(self, root):
        global numberOfClusters
        numberOfClusters = 1
        DtslScript.__init__(self, root)
