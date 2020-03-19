# Copyright (C) 2008-2019 Arm Limited (or its affiliates). All rights reserved.
from arm_ds_launcher.targetcontrol import TargetControl

import time
import sys
import os
import os.path
import re
import getopt
import shlex

import processrunner

from com.arm.debug.dtsl.rddi import RDDIConnection

from java.lang import System
from java.lang import Exception

# API object to get launch config, progress etc
targetControl = TargetControl()

DEFAULT_TIMEOUT = 60

INVALID_PATH_CHARS = ["*", ">", "<", "|", "?", "'", "\"", "="]

def usage():
    print >> sys.stderr, "usage: rtsm_launcher.py rtsm_path"


def checkForServer(connectionAddress = None):
    '''Detect whether a CADI/Iris server is running for the target

    Extracts the configuration file and address from the launch parameters
    '''
    configFile = targetControl.getParameters().get('config_file')
    configFile = targetControl.resolveFile(configFile)
    if not connectionAddress:
        address = targetControl.getParameters().get('rvi_address')
    else:
        address = connectionAddress


    conn = RDDIConnection(configFile, address)
    found = False
    try:
        conn.connect()
        found = True
    except:
        # Error is expected if no CADI/Iris server running yet
        pass
    finally:
        # Ensure all RDDI resources are cleaned up even if connect() failed
        conn.disconnect()

    return found


def isWindows():
    '''Detect whether running on windows by examining JVM property'''
    return System.getProperty("os.name").lower().startswith("win")


def get_suffixes() :
    if isWindows():
        return ".dll", ".exe"
    else:
         return ".so", ""

def get_lib_suffix():
    return get_suffixes()[0]

def get_exe_suffix():
    return get_suffixes()[1]


class serverPortDetector():
    '''Monitor output from model for report of CADI/Iris port number

    ARM Fast Models will print CADI/Iris port number when given the --print-port-number option

    Other models may required a different option and output the port in a different format
    '''

    def __init__(self):
        self.port = None


class ModelLauncher:
    def __init__(self, targetControl, modelPath, modelArgs, iris, timeout):
        self.targetControl = targetControl
        self.modelPath = modelPath
        self.modelArgs = modelArgs
        self.timeout = timeout
        self.iris = iris

        # Change this if the model reports port is a different way
        self.portExpr = re.compile('(?:CADI|Iris) server started listening to port (\\d+)')


    def launch(self):
        '''Launch the model in modelPath with arguments from modelArgs

        Runs the command and waits up to 60s for CADI/Iris server to be available
        '''
        # 10 units to start model, 120 while waiting to start (up to 1 minute @ 0.5s/unit)
        self.targetControl.beginTask("Launching model", 10 + 120)

        self.modelArgs += self.getArgumentsFromLaunchConfiguration()

        modelPath, modelCmd = self.buildModelCommand(self.modelPath, self.modelArgs)

        myEnv = os.environ.copy() # copy existing environment

        self.serverPort = None

        # start the process
        try:
            self.modelProc = processrunner.ProcessRunner(modelCmd,
                                                         # with output observer to extract port number
                                                         outputObservers=[self.checkModelOutputForServerPort],
                                                         name="model",
                                                         env=myEnv)
            self.targetControl.reportWork(10)

            timeElapsed = 0
            pollInterval = 0.5

            # allow 1 second to start
            time.sleep(1.0)
            timeElapsed += 1
            self.targetControl.reportWork(2)

            # wait for port to be reported
            while timeElapsed < timeout:
                if not self.serverPort is None:
                    break
                if not self.isRunning():
                    break
                if self.targetControl.isCancelled():
                    break

                time.sleep(pollInterval)
                timeElapsed += pollInterval
                self.targetControl.reportWork(1)

        except BaseException, ex1:
            # Put full details on Target Console
            sys.stderr.write(ex1[0].encode('utf-8', 'replace'))
            sys.stderr.write('\n')
            sys.stderr.flush()
            # Raise exception
            if os.path.isabs(self.modelPath):
                # explicitly specified model path
                msg = """Failed to start model '%s'. Please check that the model is installed correctly""" % \
                (os.path.split(self.modelPath)[1], )
            else:
                # command name only - assume it failed because it wasn't on PATH
                msg = """Failed to start model '%s'. Please check that the model is installed correctly and its installation directory is included in your PATH environment variable""" % \
                (os.path.split(self.modelPath)[1], )
            raise RuntimeError, msg

        # Report error if failed to start
        if not self.isRunning():
            raise RuntimeError, \
             "Failed to launch model %s. Command:\n  %s\nexited with error code: %d" % \
             (os.path.split(self.modelPath)[1], ' '.join(modelCmd), self.modelProc.returncode)

        elif self.serverPort is None:
            print 'CADI/Iris server port was not reported, using first available model'
            self.serverPort = -1

        else:
            # set address to this port ensures Arm DS only connects to the model it started
            if self.iris:
                print 'Iris server is reported on port %d' % self.serverPort
                self.targetControl.setParameter('rvi_address', '127.0.0.1:%d' % self.serverPort)
            else:
                print 'cadi server is reported on port %d' % self.serverPort
                self.targetControl.setParameter('rvi_address', 'port=%d' % self.serverPort)

        # wait for CADI/Iris service to be available
        serverAvailable = False
        while timeElapsed < timeout:
            if not self.isRunning():
                break
            if self.targetControl.isCancelled():
                break
            serverAvailable = checkForServer()
            if serverAvailable:
                break

            time.sleep(pollInterval)
            timeElapsed += pollInterval
            targetControl.reportWork(1)

        if self.targetControl.isCancelled():
            # clean up and exit if cancelled
            print "Connection has been cancelled"
            self.shutdown()
            return

        elif not self.isRunning():
            raise RuntimeError, \
             "Failed to launch model %s. Command:\n  %s\nexited with error code: %d" % \
             (os.path.split(self.modelPath)[1], ' '.join(modelCmd), self.modelProc.returncode)

        elif not serverAvailable:
            self.shutdown()
            if self.serverPort:
                portInfo = '%d' % self.serverPort
            else:
                portInfo = "<unknown>"
            raise RuntimeError, \
             "Failed to launch model %s - no CADI/Iris server available on port %s. Command:\n  %s" % \
             (os.path.split(self.modelPath)[1], portInfo, ' '.join(modelCmd))

        # Model has launched successfully and CADI/Iris server is available


    def getArgumentsFromLaunchConfiguration(self):
        '''Extract model parameters from launch configuration if available'''
        modelParams = self.targetControl.getParameters().get('model_params')

        plugins = self.targetControl.getParameters().get('model_plugins')

        # if modelParams:
        # use shlex to cope with quoted arguments
        modelArgs = shlex.split(modelParams)

        for i in range(len(modelArgs)):
            fixedArgs = []
            # A single argument to the model can be "ABC=~/DEF" or "ABC=CDB://DEF".
            # Since it would not make sense to provide both formats simultaneously,
            # the tilde can be resolved by simply expanding the path.
            # This is done by splitting the model on "=" giving a list containing
            # ["ABC", "~/DEF"] or ["ABC", "CDB://DEF"] and expanding the tilde and
            # prefix tags in each part separately.
            for arg in modelArgs[i].split("="):
                if any(char in arg for char in INVALID_PATH_CHARS):
                    fixedArgs.append(arg)
                else:
                    fixedArgs.append(self.targetControl.resolveFile(os.path.expanduser(arg)))

            # Once the path is fully resolved, reconstruct and update the argument.
            modelArgs[i] = "=".join(fixedArgs)

        libExt = get_lib_suffix()

        # Enable loading of MTS plugin if --plugin MTS specified in model params (old method) or
        # options.traceBuffer.traceCaptureDevice==FMTrace

        # Resolve plugin location
        MTS_Plugin = self.targetControl.resolveFile('MTS' + libExt, True)

        MTS_Enabled = False
        Plugin_Param = False
        for i in range(len(modelArgs)):
            if modelArgs[i] == "--plugin":
                Plugin_Param = True
            else:
                if modelArgs[i] == "MTS" and Plugin_Param == True:
                    # Replace MTS with path to MTS library
                    modelArgs[i] = MTS_Plugin
                    MTS_Enabled = True
                Plugin_Param = False

        # Don't want to enable twice
        if MTS_Enabled == False:
            # Check DTSL to see if we have enabled
            traceCaptureDevice = targetControl.getOptions().get('options.traceBuffer.traceCaptureDevice')
            if traceCaptureDevice == 'FMTrace':
                modelArgs.append('--plugin')
                modelArgs.append(MTS_Plugin)

        # Now any other plugins
        if plugins:
            for plugin in plugins.split(";"):
                pluginPath = self.targetControl.resolveFile(plugin)
                if not os.path.exists(pluginPath):
                    pluginPath = self.targetControl.resolveFile(plugin + libExt)
                modelArgs.append('--plugin')
                modelArgs.append(pluginPath)

        return modelArgs

    def buildModelCommand(self, modelPath, args):
        '''Build the command to launch the model in modelPath with arguments from args'''

        # resolve any environment variables here, e.g.
        # modelPath = os.path.expandvars(modelPath)

        libExt, exeExt = get_suffixes()

        # fix modelPath for windows
        if isWindows():
            # change directory separators
            modelPath = modelPath.replace("/", "\\")
            # add .exe or .dll suffix if missing
            if not modelPath.endswith(".exe") and os.path.exists(modelPath + ".exe"):
                modelPath += ".exe"
            elif not modelPath.endswith(".dll") and os.path.exists(modelPath + ".dll"):
                modelPath += ".dll"

        # use model_shell if .so or .dll
        if modelPath.endswith(libExt):
            # model becomes first arg
            args = [ '-m', modelPath ] + args
            cmdPath = targetControl.resolveFile("model_shell" + exeExt)
        else:
            cmdPath = modelPath

        if self.iris:
            cmd = [ cmdPath, '--iris-server', '--print-port-number', ] + args
        else:
            cmd = [ cmdPath, '--cadi-server', '--print-port-number', ] + args

        return modelPath, cmd


    def checkModelOutputForServerPort(self, l):
        m = self.portExpr.search(l)
        if m:
            self.serverPort = int(m.group(1))


    def isRunning(self):
        '''Whether the model is running

        True if there is a model process and it hasn't set a return code
        '''
        if self.modelProc is None:
            return False
        else:
            return (self.modelProc.poll() is None)


    def getShutdownProg(self):
        # Shutdown program is in Arm DS installation
        shutdownProg = 'cadishutdown'
        if isWindows():
            shutdownProg += '.exe'

        # resolve to absolute path
        shutdownProg = self.targetControl.resolveFile(shutdownProg)

        return shutdownProg


    def shutdown(self):
        '''Shutdown the model after debug session has finished

        Uses the CADI/Iris interface to request model to shutdown cleanly.  Terminates the model if this fails.
        '''

        if self.modelProc:
            # Run the model shutdown command
            stopped = False
            if not self.iris:
                if not self.serverPort is None:
                    shutdownCmd = [ self.getShutdownProg(), '%d' % self.serverPort ]
                    if processrunner.ProcessRunner.call(shutdownCmd, stdin=None) == 0:
                        stopped = True
                    else:
                        print 'Model did not shutdown after CADISimulation::Release, killing'

            # kill if it didn't shut down cleanly
            if not stopped:
                self.modelProc.terminate()

            # wait for it to stop
            self.modelProc.wait()

             # no longer running - no need to shutdown again
            self.modelProc = None


timeout = DEFAULT_TIMEOUT

expectedConnectionAddress = targetControl.getParameters().get('model_connection_address')
connectToExistingModel = targetControl.getParameters().get('connect_existing_model')
iris = targetControl.getParameters().get('model_iris')

opts, args = getopt.getopt(sys.argv[1:], "t:", [ "timeout=" ])
for o, a in opts:
    if o in [ '-t', '--timeout' ]:
        timeout = int(a)

if len(args) < 1:
    usage()

modelPath = sys.argv[1]
modelArgs = sys.argv[2:]

if iris and connectToExistingModel == "true":
    serverFound = checkForServer(expectedConnectionAddress)
    if not serverFound:
        raise RuntimeError, \
             "Failed to connect to the model - no iris server available on address %s." % \
             expectedConnectionAddress

elif not iris and checkForServer():
    # model is already running
    #  use this for the connection, so nothing more to do
    pass

else:
    # no model running - launch the model
    modelLauncher = ModelLauncher(targetControl, modelPath, modelArgs, iris, timeout)
    modelLauncher.launch()

    # and register shutdown hook to stop it on disconnect
    targetControl.setShutdownHook(modelLauncher.shutdown)
