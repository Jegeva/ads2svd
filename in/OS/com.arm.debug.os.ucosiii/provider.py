# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from tasks import Tasks
from kernel import KernelData
from mempartitions import MemPartitions
from timers import Timers
from contexts import ContextsProvider
from mutexes import Mutexes
from messages import Messages
from semaphores import Semaphores
from flags import Flags

# this script effectively implements com.arm.debug.extension.os.IOSProvider

def getOSContextProvider():
    return ContextsProvider()

def getDataModel():
    return Model("ucosiii", [
                             Tasks(),
                             Semaphores(),
                             Mutexes(),
                             Messages(),
                             MemPartitions(),
                             Timers(),
                             Flags(),
                             KernelData(),
                             ])

def isOSInitialised(debugger):
    try:
        return debugger.evaluateExpression( "OSRunning" ).readAsNumber( ) == 1
    except DebugSessionException:
        return False;

def areOSSymbolsLoaded(debugger):
    return debugger.symbolExists("OSTCBCurPtr") and debugger.symbolExists("OSRunning")