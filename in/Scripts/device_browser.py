from java.lang import System
from arm_ds_launcher.targetcontrol import TargetControl


import sys
import subprocess
import sys
import os
import os.path

# Determine whether we are running on windows
def isWindows():
    return System.getProperty("os.name").lower().startswith("win")
    return True


# Get executable name - append .exe if windows
def getExecutableName(appName):
    if isWindows() and not appName.endswith(".exe"):
        return appName + ".exe"
    else:
        return appName

# Returns true if specified file exists
def fileExists(fileName):
    return os.path.isfile(fileName)


# Runs the specified app
def runApplication(name):
    p = subprocess.Popen(name,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    returncode = p.wait()
    if returncode == 0:
        print p.stdout.read()
    else:
        error_message = "Error: " + p.stderr.read()
        raise Exception(error_message)


# To simulate devices connected / unavailable
def runSimulation():
    print "ID, Name, Available"
    print "1, debug-name-1, 1"
    print "2, debug-name-2, 0"
    print "3, debug-name-3, 1"



# Run the application (specified in sys.argv[1])
if len(sys.argv) > 1:
    # Get Application Name adding .exe if we are running on windows os
    executableName = getExecutableName(sys.argv[1])

    if isWindows() and ("browse_usb_blaster" in executableName):
        # Browsing for Blaster, so add Quartus bin directory to $PATH for VS2013 redistributable dll(s)
        from altera_common import pathToQuartusBinDir
        os.environ["PATH"] += os.pathsep + pathToQuartusBinDir()

    # List used to construct the command
    arg_list = []

    # If we have additional arguments (on top of app name)
    # copy them in to the empty list
    if(len(sys.argv) > 2) :
        arg_list = sys.argv[2:]

    # Insert executable name at front of list
    arg_list.insert(0, executableName)

    # Run the application
    runApplication(arg_list)

    # Can use this for testing - comment out runApplication()
    #runSimulation()








