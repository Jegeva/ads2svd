from rddi_dap_debug_server import startDebugServer
from utilities.retarget_ini import retargetIniFile
from arm_ds_launcher.targetcontrol import TargetControl
import sys

# API object to get launch config, progress etc
targetControl = TargetControl()

DEFAULT_RDDI_DAP_NAME = "rddi-dap_cmsis-dap"
DEFAULT_TIMEOUT = 60

def usage():
    print >> sys.stderr, "usage: cmsis_dap_debug_server.py [ --timeout timeout ] [ --rddi-dap rddi_dap_name ] config_file"


def retargetConfig(configFile):
    '''Retarget a config file for RDDI-DAP_CMSIS-DAP connections

    Returns path to retargeted file
    '''
    overrideAddress = targetControl.getParameters()['rvi_address']
    if overrideAddress:
        # Token before first ':' separator, else the whole address.
        overrideId = overrideAddress.split(':')[0]
        configFile = retargetIniFile(configFile, 'cmsis-dap-dev', 'SERNUM', overrideId)
    return configFile


if __name__ == "__main__":

    # default parameters
    rddidapBaseName = DEFAULT_RDDI_DAP_NAME
    timeout = DEFAULT_TIMEOUT
    logging = False

    # process options
    import getopt
    opts, args = getopt.getopt(sys.argv[1:], "t:l", [ "timeout=", "rddi-dap=", "logging" ])
    for o, a in opts:
        if o in [ '-t', '--timeout' ]:
            timeout = int(a)
        elif o in [ '--rddi-dap' ]:
            rddidapBaseName = a
        elif o in [ '-l', '--logging' ]:
            logging = True

    if len(args) < 1:
        usage()

    configFile = args[0]

    # edit config file for specific device etc
    configFile = retargetConfig(configFile)

    startDebugServer(configFile, rddidapBaseName, timeout, enableLogging=logging)
