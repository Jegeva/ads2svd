# Copyright (C) 2008-2018 Arm Limited (or its affiliates). All rights reserved.
from utilities.retarget_ini import retargetIniFile
from arm_ds_launcher.targetcontrol import TargetControl

import time
import sys
import os
import os.path
import re
import socket
import processrunner

from com.arm.debug.dtsl.rddi import RDDIConnection

from java.lang import System
from java.lang import Exception

# API object to get launch config, progress etc
targetControl = TargetControl()

DEFAULT_TIMEOUT = 60


def usage():
    print >> sys.stderr, "usage: debug_server.py [ --timeout timeout ] config_file rddi-dap_name"


def isWindows():
    '''Detect whether running on windows by examining JVM property'''
    return System.getProperty("os.name").lower().startswith("win")

def is64bit():
    '''Detect whether running on 64-bit architecture by examining JVM property'''
    return System.getProperty("os.arch").endswith("64")

def getRDDIDapDLL(baseName):
    if isWindows():
        return baseName+"_2.dll"
    else:
        return "lib"+baseName+".so.2"


def isAcceptingConnections(host, port):
    s = socket.socket()
    try:
        s.connect((host, port))
        return True
    except:
        return False
    finally:
        s.close()


class DebugServerLauncher:

    def __init__(self, targetControl, configPath, rddidapBaseName, timeout):
        self.targetControl = targetControl
        self.configPath = configPath
        self.rddidapBaseName = rddidapBaseName
        self.timeout = timeout
        self.platformName = targetControl.getParameters().get('config_db_platform_name')
        self.isReady = False
        self.enableLogging = False


    def fetchMemo(self):
        class SharedState(object):
            def __init__(self):
                self.refCount = 0
                self.debugHardwareIdentifier = ''
                self.debugServerConnectionString = ''
                self.serverProc = None

        return self.targetControl.fetchMemo(self.platformName) or SharedState()


    def storeMemo(self, memo):
        self.targetControl.storeMemo(self.platformName, memo)


    def launch(self):

        # Save the debug hardware identifier from the user's browse selection.
        # The implementation of doLaunch() will overwrite this parameter with
        # the internal debug server connection string, typically 'TCP:localhost'.
        debugHardwareIdentifier = self.targetControl.getParameters()['rvi_address']

        memo = self.fetchMemo()
        if memo.refCount:

            # A debug server is already running.  Is it connected to the chosen
            # debug hardware unit?
            if memo.debugHardwareIdentifier != debugHardwareIdentifier:
                err = 'Already connected to ' + memo.debugHardwareIdentifier
                print >> sys.stderr, err
                raise RuntimeError, err

            # Safe to reuse the existing debug server instance.
            print 'A suitable Debug Server is already running'
            memo.refCount += 1
            self.targetControl.setParameter('rvi_address', memo.debugServerConnectionString)
            self.storeMemo(memo)
        else:
            # we are the first
            serverProc = self.doLaunch()
            if serverProc:
                memo.refCount = 1
                memo.debugHardwareIdentifier = debugHardwareIdentifier
                memo.debugServerConnectionString = self.targetControl.getParameters()['rvi_address']
                memo.serverProc = serverProc
                self.storeMemo(memo)


    def doLaunch(self):
        '''Launch the debug server

        Return server process on success. Return None if cancelled (not an error). Throw on error.
        '''
        # 10 units to start server, 120 while waiting to start (up to 1 minute @ 0.5s/unit)
        self.targetControl.beginTask("Launching debug server", 10 + 120)

        serverProg = self.getServerProg()
        serverDir = os.path.dirname(serverProg)
        dapDLLPath = self.locateDapDLL()
        serverCmd = self.buildServerCommand(serverProg, self.configPath, dapDLLPath)
        serverEnv = self.getEnvironment(dapDLLDir=os.path.dirname(dapDLLPath),
            enableLogging=self.enableLogging)

        # SDDEBUG-14863 - If there is already a serverd, then the later
        # test for isAcceptingConnections() often succeeds before we detect
        # that the new serverd subprocess terminated.  Jython does not let
        # us see the subprocess pid, which scuppers any attempts at reliably
        # distinguishing serverd instances.  Make do with this slightly
        # race-prone workaround.
        if isAcceptingConnections('localhost', 3010):
            print >> sys.stderr, 'Port 3010 is already in use'
            raise RuntimeError, 'Port 3010 is already in use'

        print 'Starting debug server'

        # start the server, connecting to input/output/error streams
        # print "Starting %s in %s" % (' '.join(serverCmd), serverDir)
        serverProc = processrunner.ProcessRunner(serverCmd,
                                                 cwd=serverDir,
                                                 env=serverEnv
                                                 )

        self.targetControl.reportWork(10)

        timeElapsed = 0
        pollInterval = 0.5

        print 'Waiting for debug server to start accepting connections'

        # wait for server to report it's ready
        while timeElapsed < self.timeout:
            self.isReady = isAcceptingConnections('localhost', 3010)
            if self.isReady:
                break
            if not DebugServerLauncher.isRunning(serverProc):
                break
            if self.targetControl.isCancelled():
                break

            time.sleep(pollInterval)
            timeElapsed += pollInterval
            self.targetControl.reportWork(1)

        if self.targetControl.isCancelled():
            # clean up and exit if cancelled
            print "Connection has been cancelled"
            self.doShutdown(serverProc)
            return None

        elif not DebugServerLauncher.isRunning(serverProc):
            # failed to start:
            #   report full error in console
            print >> sys.stderr, "Failed to launch debug server. Command:\n  %s\nexited with error code: %d" % \
             (' '.join(serverCmd), serverProc.returncode)
            #   brief message for exception (& pop-up box)
            raise RuntimeError, \
             "Failed to launch debug server.\n%s exited with error code %d" % \
             (serverCmd[0], serverProc.returncode)

        elif not self.isReady:
            self.doShutdown(serverProc)
            raise RuntimeError, \
             "Debug server not ready after %ds" % \
             self.timeout

        # Server has launched successfully
        print 'Debug server started successfully\n'

        # Set target address in launch configuration
        self.targetControl.setParameter('rvi_address', 'TCP:localhost')
        return serverProc


    def buildServerCommand(self, serverProg, configPath, dapDLLPath):
        '''Build the command to launch the server in serverPath with arguments from args'''

        configdbPath = os.path.dirname(configPath)

        serverCmd = [ serverProg,
                     "-rddi_dap_dll", dapDLLPath,
                     "-rddi_dap_cfg", configPath,
                     "-pollrate", "200",
                     ]

        return serverCmd


    def locateDapDLL(self):
        dapDLL = getRDDIDapDLL(self.rddidapBaseName)

        # locate the dapDLL: try config DB folder first
        configdbPath = os.path.dirname(self.configPath)
        configdbDLLPath = os.path.join(configdbPath, dapDLL)
        if os.path.exists(configdbDLLPath):
            # in config DB
            dapDLLPath = configdbDLLPath
        else:
            # assume same directory as VSTREAM server
            dapDLLPath = dapDLL

        return dapDLLPath


    def getServerProg(self):
        return self.targetControl.resolveFile("rddidap_serverd")


    def getEnvironment(self, dapDLLDir=None, enableLogging=False):
        extraEnv = {}

        # Set LD_LIBRARY_PATH on linux
        if not isWindows():
            extraPath = '.'
            if dapDLLDir:
                extraPath += ':' + dapDLLDir
            if 'LD_LIBRARY_PATH' in os.environ:
                extraPath = extraPath + ":" + os.environ['LD_LIBRARY_PATH']

            extraEnv['LD_LIBRARY_PATH'] = extraPath

        if enableLogging:
            extraEnv['SERVERD_LOGLEVEL'] = 'info'
            extraEnv['RVILOG'] = 'CONSOLE'

        env = None
        if extraEnv:
            env = os.environ.copy()
            env.update(extraEnv)

        return env


    def processOutput(self, l):
        m = self.ipExpr.search(l)
        if m:
            self.ipAddr = m.group(1)

        m = self.readyExpr.search(l)
        if m:
            self.isReady = True


    @staticmethod
    def isRunning(serverProc):
        '''Whether the server is running

        True if there is a server process and it hasn't set a return code
        '''
        if serverProc is None:
            return False
        else:
            return (serverProc.poll() is None)


    def getShutdownProg(self):
        return self.targetControl.resolveFile("vstrm_shutdown")


    def shutdown(self):
        memo = self.fetchMemo()
        memo.refCount -= 1
        self.storeMemo(memo)
        if memo.refCount is 0:
            self.doShutdown(memo.serverProc)


    def doShutdown(self, serverProc):
        '''Shutdown the server after debug session has finished
        '''
        if serverProc:
            # Run the server shutdown command
            stopped = False
            shutdownProg = self.getShutdownProg()
            serverDir = os.path.dirname(shutdownProg)
            shutdownCmd = [ shutdownProg, 'VSTRM_SERVERDEXIT', 'Debug server' ]
            if processrunner.ProcessRunner.call(shutdownCmd, stdin=None, cwd=serverDir, env=self.getEnvironment()) == 0:
                stopped = True
            else:
                print 'Server did not shutdown cleanly, killing'

            # kill if it didn't shut down cleanly
            if not stopped:
                # TODO: this results in exception on stderr pipe - close first?
                serverProc.terminate()

            # wait for it to stop
            serverProc.wait()


def startDebugServer(configFile, rddidapBaseName, timeout, enableLogging=False):
    # start the debug server
    launcher = DebugServerLauncher(targetControl, configFile, rddidapBaseName, timeout)
    launcher.enableLogging = enableLogging
    launcher.launch()

    # and register shutdown hook to stop it on disconnect
    targetControl.setShutdownHook(launcher.shutdown)

def retargetConfig(configFile):
    '''Retarget a config file for RDDI-DAP connections

    Returns path to retargeted file
    '''
    overrideAddress = targetControl.getParameters()['rvi_address']
    if overrideAddress:
        # Token before first ':' separator, else the whole address.
        overrideId = overrideAddress.split(':')[0]
        configFile = retargetIniFile(configFile, 'rddi-dap-dev', 'SERNUM', overrideId)
    return configFile


if __name__ == "__main__":

    timeout = DEFAULT_TIMEOUT

    import getopt
    opts, args = getopt.getopt(sys.argv[1:], "t:", [ "timeout=" ])
    for o, a in opts:
        if o in [ '-t', '--timeout' ]:
            timeout = int(a)

    if len(args) < 2:
        usage()

    configFile = args[0]

    # edit config file for specific device etc
    configFile = retargetConfig(configFile)

    rddidapBaseName = args[1]

    startDebugServer(configFile, rddidapBaseName, timeout)
