# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from contexts import ContextsProvider
from flags import Flags
from mailboxes import Mailboxes
from mutexes import Mutexes
from tasks import Tasks
from kernel import KernelData
from mempartitions import MemPartitions
from events import Events
from queues import Queues
from semaphores import Semaphores
from timers import Timers

# this script effectively implements com.arm.debug.extension.os.IOSProvider

def getOSContextProvider( ):
    return ContextsProvider( )

def getDataModel( ):

    return Model ("ucosii", [
                              Events( ),
                              Flags( ),
                              KernelData( ),
                              Mailboxes( ),
                              MemPartitions( ),
                              Mutexes( ),
                              Queues( ),
                              Semaphores( ),
                              Tasks( ),
                              Timers( )
                            ] )

def isOSInitialised( debugger ):
    return debugger.evaluateExpression( "OSRunning" ).readAsNumber( ) == 1

def areOSSymbolsLoaded( debugger ):
    return debugger.symbolExists( "OSTCBCur" ) and debugger.symbolExists( "OSRunning" )
