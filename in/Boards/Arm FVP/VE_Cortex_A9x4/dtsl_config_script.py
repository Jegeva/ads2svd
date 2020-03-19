from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.components import Device
from com.arm.debug.dtsl.components import CadiSyncSMPDevice
from com.arm.debug.dtsl.components import DeviceCluster
from com.arm.debug.dtsl.components import FMTraceCapture
from com.arm.debug.dtsl.components import FMTraceSource
from com.arm.debug.dtsl.components import FMEventSource
from com.arm.debug.dtsl.components import FMTraceDevice

FM_SOURCE_ID_BASE    = 32
# Source ID Base - Don't change this
MTS_SERVER_PORT      = 31628
# Source ID Device Base - Don't change this
# We can't find trace sources, we need to create id's here and make sure they
# are out of the range of normal devices
FM_TRACE_SOURCE_BASE = 32768


class DtslScript(DTSLv1):

    @staticmethod
    def getOptionList():
        return [
                DTSLv1.tabSet(
                name='options',
                displayName='Trace Options',
                childOptions=
                [
                    DtslScript.getTraceConfigOptionsPage()
                ]
            )
        ]


    def __init__(self, root):
        DTSLv1.__init__(self, root)
        '''Do not add directly to this list - first check if the item you are adding is already present'''
        self.mgdPlatformDevs = []
        # locate devices on the platform and create corresponding objects
        self.discoverDevices()

        self.exposeCores()

        self.setupCadiSyncSMP()

        self.setupTrace()

    @staticmethod
    def getTraceConfigOptionsPage():
        # If you change the position or name of the traceCapture
        # device option you MUST modify the project_types.xml to
        # tell the debugger about the new location/name
        return DTSLv1.tabPage(
            name='traceBuffer',
            displayName='Trace Configuration',
            childOptions=[
                DTSLv1.enumOption(
                    name='traceCaptureDevice',
                    displayName='Trace capture method',
                    defaultValue='None',
                    values=[
                        ('None', 'No Trace'),
                        ('FMTrace', 'Fast Models Trace')
                    ]
                ),
                DTSLv1.booleanOption(
                    name='clearTraceOnConnect',
                    displayName='Clear Trace Buffer on connect',
                    defaultValue=True
                ),
                DTSLv1.booleanOption(
                    name='startTraceOnConnect',
                    displayName='Start Trace Buffer on connect',
                    defaultValue=True
                ),
                 DTSLv1.enumOption(
                    name='bufferSize',
                    displayName='Trace capture buffer',
                    defaultValue='Buffer16M',
                    values=[
                        ('Buffer16M', '16MB '),
                        ('Buffer32M', '32MB '),
                        ('Buffer64M', '64MB '),
                        ('Buffer128M', '128MB '),
                    ]
                ),
                DTSLv1.enumOption(
                    name='traceWrapMode',
                    displayName='Trace full action',
                    defaultValue='wrap',
                    values=[
                        ('wrap', 'Trace wraps on full and continues to store data'),
                        ('stop', 'Trace halts on full')
                    ]
                ),
            ]
        )

    # +----------------------------+
    # | Target dependent functions |
    # +----------------------------+

    def discoverDevices(self):
        '''Find and create devices'''

        self.cores = dict()

        self.cores["cluster.cpu0"] = Device(self, self.findDevice("cluster.cpu0"), "ARM_Cortex-A9MP_0" )
        self.cores["cluster.cpu1"] = Device(self, self.findDevice("cluster.cpu1"), "ARM_Cortex-A9MP_1" )
        self.cores["cluster.cpu2"] = Device(self, self.findDevice("cluster.cpu2"), "ARM_Cortex-A9MP_2" )
        self.cores["cluster.cpu3"] = Device(self, self.findDevice("cluster.cpu3"), "ARM_Cortex-A9MP_3" )

        self.cluster0cores = []

        self.cluster0cores.append(self.cores["cluster.cpu0"])
        self.cluster0cores.append(self.cores["cluster.cpu1"])
        self.cluster0cores.append(self.cores["cluster.cpu2"])
        self.cluster0cores.append(self.cores["cluster.cpu3"])


    def exposeCores(self):
        '''Expose cores'''
        self.addDeviceInterface(self.cores["cluster.cpu0"])
        self.addDeviceInterface(self.cores["cluster.cpu1"])
        self.addDeviceInterface(self.cores["cluster.cpu2"])
        self.addDeviceInterface(self.cores["cluster.cpu3"])


    def setupCadiSyncSMP(self):
        '''Create SMP device using RDDI synchronization'''

        # Create SMP device and expose from configuration
        # cluster0 SMP
        smp = CadiSyncSMPDevice(self, "Cortex-A9x4 SMP0", self.cluster0cores)
        self.addDeviceInterface(smp)

    def setupTrace(self):
        '''Setup the trace devices'''

        # Create Fast Models Trace Capture Device on a fixed MTS server port
        self.tracecapture = FMTraceCapture(self, "FMTrace", MTS_SERVER_PORT )
        self.tracecapture.setTraceMode(FMTraceCapture.TraceMode.Continuous)

        self.traceSources = []
        # Expose Trace Sources

        # We are using a fixed StreamID base, this needs to match the Stream ID
        # embedded in the trace stream for that core
        StreamId  = FM_SOURCE_ID_BASE
        DeviceId  = FM_TRACE_SOURCE_BASE

        # Importer to generate one of these for each cluster
        for i, c in enumerate(self.cluster0cores):
            fmtSource = self.createFMTraceSource(DeviceId+i, StreamId+i, "FMT_%d" % i)
            self.tracecapture.addTraceSource(fmtSource, c.getID())
            fmtSource.setEnabled(True)

        self.addTraceCaptureInterface(self.tracecapture)
        # self.setManagedDevices( [ self.tracecapture ] )


    # +--------------------------------+
    # | Callback functions for options |
    # +--------------------------------+
    def optionValuesChanged(self):
        '''Callback to update the configuration state after options are changed'''
        obase = "options"
        self.setInitialOptions(obase)

    def setInitialOptions(self, obase):
        '''Takes the configuration options and configures the
           DTSL objects prior to target connection
           Param: obase the option path string to top level options
        '''
        self.setTraceWrapMode(self.getOptionValue(obase+".traceBuffer.traceWrapMode"))
        self.setClearTraceOnConnect(self.getOptionValue(obase+".traceBuffer.clearTraceOnConnect"))
        self.setStartTraceOnConnect(self.getOptionValue(obase+".traceBuffer.startTraceOnConnect"))
        self.setTraceBufferSize(self.getOptionValue(obase+".traceBuffer.bufferSize"))

        # currently disabled until event view added
        self.setInstructionStartTrace( "OFF" )
        self.setInstructionStopTrace( "OFF" )

        # Add/Remove the trace capture device as per the status of traceCaptureDevice
        if self.getOptionValue(obase+".traceBuffer.traceCaptureDevice") == "FMTrace":
            if self.tracecapture not in self.mgdPlatformDevs:
                self.mgdPlatformDevs.append(self.tracecapture)
        else:
            if self.tracecapture in self.mgdPlatformDevs:
                self.mgdPlatformDevs.remove(self.tracecapture)

        self.setManagedDeviceList(self.mgdPlatformDevs)


    def setTraceWrapMode(self, mode):
        '''Configuration option setter method for the buffer wrap mode'''
        if mode == "wrap":
            self.tracecapture.setWrapOnFull(True)
        else:
            self.tracecapture.setWrapOnFull(False)

    def setTraceBufferSize(self, mode):
        '''Configuration option setter method for the buffer size'''
        if (mode == "Buffer16M"):
            self.tracecapture.setMaxCaptureSize( 16*1024*1024 )
        elif (mode == "Buffer32M"):
            self.tracecapture.setMaxCaptureSize( 32*1024*1024 )
        elif (mode == "Buffer64M"):
            self.tracecapture.setMaxCaptureSize( 64*1024*1024 )
        elif (mode == "Buffer128M"):
            self.tracecapture.setMaxCaptureSize( 128*1024*1024 )
        else:
            self.tracecapture.setMaxCaptureSize( 16*1024*1024 )

    def setInstructionStartTrace(self, mode):
        if (mode == True):
            self.tracecapture.setTraceOption( "INST_START", "ON")
        else:
            self.tracecapture.setTraceOption( "INST_START", "OFF")

    def setInstructionStopTrace(self, mode):
        if (mode == True):
            self.tracecapture.setTraceOption( "INST_END", "ON")
        else:
            self.tracecapture.setTraceOption( "INST_END", "OFF")

    def setClearTraceOnConnect(self, enabled):
        '''Configuration option setter method to enable/disable clear trace buffer on connect'''
        self.tracecapture.setClearOnConnect(enabled)

    def setStartTraceOnConnect(self, enabled):
        '''Configuration option setter method to enable/disable auto start trace buffer on connect only'''
        self.tracecapture.setAutoStartTraceOnConnect(enabled)

    def createFMTraceSource(self, fmtDev, streamID, name):
        traceSource = FMTraceSource(self, fmtDev, streamID, name)
        traceSource.setEnabled(True)
        self.traceSources.append(traceSource)
        return traceSource





