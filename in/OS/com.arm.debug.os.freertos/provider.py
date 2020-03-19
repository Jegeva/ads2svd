# ###############################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# FreeRTOS - V7.6.0 / V8.0.0RC ARM Cortex M / A
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi      import *
from globs      import *
from contexts   import ContextsProvider
from queues     import Queues
from kernel     import KernelData
from tasks      import Tasks
from timers     import Timers
from mutexes    import Mutexes
from semaphores import Semaphores

# this script effectively implements com.arm.debug.extension.os.IOSProvider

def getOSContextProvider( ):
    return ContextsProvider( )

def getDataModel( ):
    return Model( OS_NAME, [ KernelData( ), Mutexes( ), Queues( ), Semaphores( ), Tasks( ), Timers( ) ] )

def isOSInitialised( debugger ):
    try:
        return debugger.evaluateExpression( X_SCHEDULER_RUNNING ).readAsNumber( ) == 1
    except DebugSessionException:
        return False;

def areOSSymbolsLoaded( debugger ):
    # The image should be built with -DportREMOVE_STATIC_QUALIFIER in order to make the
    # debugging symbols visible. If this is not the case, then xSchedulerRunning may not be found.
    return debugger.symbolExists( PX_CURRENT_TCB ) and debugger.symbolExists( X_SCHEDULER_RUNNING )
