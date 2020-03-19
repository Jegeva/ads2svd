import sys
import os
import os.path

from java.lang import System

# These environment variables, if set, will point to the root directories of
# Altera software installations where we might find a jtag_client library.
ROOT_ENV_VARS = ['QUARTUS_ROOTDIR']

def isWindows():
    '''Detect whether running on windows by examining JVM property'''
    return System.getProperty("os.name").lower().startswith("win")

def is64bit():
    '''Detect whether running on 64-bit architecture by examining JVM property'''
    return System.getProperty("os.arch").endswith("64")


def clientLibrarySearchDirs():
    if is64bit():
        if isWindows():
            search_dirs = [ "bin64", "bin" ]
        else:
            search_dirs = [ "linux64", "linux" ]
    else:
        if isWindows():
            search_dirs = [ "bin32", "bin" ]
        else:
            search_dirs = [ "linux32", "linux" ]

    return search_dirs


JTAG_CLIENT_LIB = 'jtag_client.dll' if isWindows() else 'libjtag_client.so'

def fullPath(root):
    return os.path.join(root, JTAG_CLIENT_SUBDIR, JTAG_CLIENT_LIB)

def pathToJtagClientLibrary():
    candidates = [ os.path.join(base, subdir, JTAG_CLIENT_LIB)
                   for subdir in clientLibrarySearchDirs()
                   for base in map(os.getenv, ROOT_ENV_VARS) if (base) ]
    found = [ c for c in candidates if os.path.exists(c) ]
    # Use the first full path found, if any.  Otherwise take our chances with
    # just the file name and hope it's on the system path.
    return found[0] if found else JTAG_CLIENT_LIB

def pathToQuartusBinDir():
    return pathToJtagClientLibrary().replace(JTAG_CLIENT_LIB, '')
