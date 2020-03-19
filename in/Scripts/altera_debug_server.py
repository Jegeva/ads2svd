from arm_ds_launcher.targetcontrol import TargetControl
import sys
import os
import os.path
import getopt
from utilities.retarget_ini import retargetIniFile
from rddi_dap_debug_server import startDebugServer
from altera_common import pathToJtagClientLibrary, pathToQuartusBinDir, isWindows

# API object to get launch config, progress etc
targetControl = TargetControl()

DEFAULT_TIMEOUT = 60


def usage():
    print >> sys.stderr, "usage: altera_debug_server.py config_file rddi-dap-name"


if __name__ == '__main__':

    timeout = DEFAULT_TIMEOUT

    opts, args = getopt.getopt(sys.argv[1:], "t:", [ "timeout=" ])
    for o, a in opts:
        if o in [ '-t', '--timeout' ]:
            timeout = int(a)

    if len(args) < 2:
        usage()

    configFile = sys.argv[1]
    rddidapBaseName = sys.argv[2]

    overrideAddress = targetControl.getParameters()['rvi_address']
    assert overrideAddress, 'No debug hardware is specified.  Please check the debug configuration.'
    # Token before first ':' separator, else the whole address.
    overrideId = overrideAddress.split(':')[0]
    configFile = retargetIniFile(configFile,
                             'rddi-dap-altera', 'CableID', overrideId,
                             'rddi-dap-altera', 'JTAG_DLL_PATH', pathToJtagClientLibrary())

    # Add Quartus bin directory to $PATH, for VS2013 redistributable dll(s)
    if isWindows():
        os.environ["PATH"] += os.pathsep + pathToQuartusBinDir()

    # start the debug server
    startDebugServer(configFile, rddidapBaseName, timeout)

