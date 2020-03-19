# Copyright (C) 2014-2019 Arm Limited (or its affiliates). All rights reserved.
from arm_ds_launcher.targetcontrol import TargetControl
from time import sleep
import sys
from com.arm.debug.dtsl.rddi import RDDIConnection
from java.lang import Exception
from com.arm.rddi import RDDI_ACC_SIZE
from struct import pack, unpack
from jarray import zeros

# API object to get launch config, progress etc
targetControl = TargetControl()
DEFAULT_TIMEOUT = 180


def usage():
    print >> sys.stderr, "usage: hsstp_setup.py [ --timeout timeout ]"


class HSSTPSetup:

    def __init__(self, targetControl, timeout):
        self.targetControl = targetControl
        self.timeout = timeout
        self.isReady = False
        self.enableLogging = False


    def configure(self):
        '''Configure DSTREAM HSSTP trace probe
        Return None if cancelled (not an error). Throw on error.
        '''
        self.targetControl.beginTask("Configuring DSTREAM HSSTP probe", timeout*2)
        configFile = targetControl.getParameters().get('config_file')
        configFile = targetControl.resolveFile(configFile)
        address = targetControl.getParameters().get('rvi_address')

        conn = RDDIConnection(configFile, address, "HSSTP")
        print 'Starting DSTREAM HSSTP probe configuration'

        probeReady = False
        try:
            traceConn = None
            trace = conn.getTrace()
            if trace != None:
                traceConn = trace.connect()

                # If multiple targets are in use then a more sophisticated check than the following may be needed,
                # this requires the probe to be power cycled before a different type of target may be used
                #if self.isProbeConfigured(trace, traceConn):
                #    print 'Probe is already configured\n'
                #    return

                # Do InitPort command via generic RDDI trace transaction
                self.doInitPort(trace, traceConn)
                # Now need to check and wait for FPGA ready after FPGA's have been checked
                # and HSSTP lane rate has been configured
                # Wait 2 minutes 10 seconds in worst case for FPGA to reprogram
                timeElapsed = 0
                pollInterval = 0.5
                while not(probeReady) and timeElapsed < self.timeout:
                    sleep(pollInterval)
                    timeElapsed += pollInterval
                    self.targetControl.reportWork(1)
                    probeReady = self.isProbeConfigured(trace, traceConn)
                    if self.targetControl.isCancelled():
                        print 'Connection has been cancelled\n'
                        break
                # Probe FPGA now ready
        except:
            raise RuntimeError, "Failed to configure the HSSTP probe successfully - power-cycle of the target and the probe may resolve this."

        finally:
            # Ensure all RDDI resources are cleaned up even if connect() failed
            if traceConn:
                trace.disconnect(traceConn)
            conn.disconnect()

        if not probeReady:
            if self.targetControl.isCancelled():
                raise RuntimeError, "Connection has been cancelled"
            else:
                raise RuntimeError, \
                    "DSTREAM HSSTP probe not configured successfully after %ds" % \
                     self.timeout

        print 'DSTREAM HSSTP probe configured successfully'
        return probeReady


    def isProbeConfigured(self, trace, traceConn):
        '''True if probe FGPA is configured
        '''
        currentStatus = trace.getStatus(traceConn)
        return (currentStatus & 0x10000000 != 0)


    def doInitPort(self, trace, traceConn):
        '''Perform trace initport command via generic RDDI trace transaction
        '''
        initPortCommand = zeros(1, 'b')
        dataOut = zeros(4, 'b')
        dataOutLen = zeros(1, 'i')
        trace.transaction(traceConn, initPortCommand, dataOut, dataOutLen)


def configureHSSTP(timeout):
    # start the debug server
    hsstp = HSSTPSetup(targetControl, timeout)
    hsstp.configure()


if __name__ == "__main__":

    timeout = DEFAULT_TIMEOUT

    import getopt
    opts, args = getopt.getopt(sys.argv[1:], "t:", [ "timeout=" ])
    for o, a in opts:
        if o in [ '-t', '--timeout' ]:
            timeout = int(a)

    configureHSSTP(timeout)
